import os
from pathlib import Path

import mlflow
import mlflow.sklearn
import pandas as pd
import yaml
from fastapi import FastAPI, HTTPException
from mlflow import MlflowClient
from pydantic import BaseModel
from fastapi import UploadFile, File
from fastapi.responses import StreamingResponse
from io import BytesIO

from src.features import feature_sets


# ---------------------------------------------------------
# Configuration
# ---------------------------------------------------------

TRACKING_URI = os.environ.get(
    "MLFLOW_TRACKING_URI",
    "sqlite:///mlflow.db"
)

MODEL_NAME = os.environ.get(
    "MODEL_NAME",
    "student-risk-classifier"
)

MODEL_ALIAS = os.environ.get(
    "MODEL_ALIAS",
    "early-intervention"
)


# ---------------------------------------------------------
# Connect to MLflow
# ---------------------------------------------------------

mlflow.set_tracking_uri(TRACKING_URI)

client = MlflowClient()

model_version = client.get_model_version_by_alias(
    MODEL_NAME,
    MODEL_ALIAS
)

feature_set_name = model_version.tags.get("feature_set")
model_type = model_version.tags.get("model_type")

if feature_set_name is None:
    raise RuntimeError(
        "The registered model version has no feature_set tag."
    )


# ---------------------------------------------------------
# Determine the columns required by this model
# ---------------------------------------------------------

contract = yaml.safe_load(
    Path("data_contract.yaml").read_text()
)

all_columns = list(contract["columns"].keys())

available_feature_sets = feature_sets(all_columns)

if feature_set_name not in available_feature_sets:
    raise RuntimeError(
        f"Unknown feature set: {feature_set_name}"
    )

required_features = available_feature_sets[feature_set_name]


# ---------------------------------------------------------
# Load the actual sklearn model from MLflow
# ---------------------------------------------------------

model_uri = f"models:/{MODEL_NAME}@{MODEL_ALIAS}"

model = mlflow.sklearn.load_model(model_uri)


# ---------------------------------------------------------
# FastAPI application
# ---------------------------------------------------------

app = FastAPI(
    title="Student Academic Risk Prediction API",
    description=(
        "Predicts whether a student's outcome is "
        "Dropout, Enrolled, or Graduate."
    ),
    version="1.0.0"
)


class PredictionRequest(BaseModel):
    features: dict[str, int | float]


# ---------------------------------------------------------
# Health endpoint
# ---------------------------------------------------------

@app.get("/health")
def health():
    return {
        "status": "ok",
        "model_name": MODEL_NAME,
        "model_alias": MODEL_ALIAS,
        "model_version": model_version.version,
    }


# ---------------------------------------------------------
# Model information endpoint
# ---------------------------------------------------------

@app.get("/model-info")
def model_info():
    return {
        "model_name": MODEL_NAME,
        "model_alias": MODEL_ALIAS,
        "model_version": model_version.version,
        "model_type": model_type,
        "feature_set": feature_set_name,
        "required_feature_count": len(required_features),
        "required_features": required_features,
    }


# ---------------------------------------------------------
# Prediction endpoint
# ---------------------------------------------------------

@app.post("/predict")
def predict(request: PredictionRequest):

    provided = request.features

    # Check required features.
    missing = [
        column
        for column in required_features
        if column not in provided
    ]

    if missing:
        raise HTTPException(
            status_code=422,
            detail={
                "message": "Required features are missing.",
                "missing_features": missing,
            }
        )

    # Reject columns that aren't part of the project's data contract.
    known_features = set(all_columns) - {"target"}

    unknown = [
        column
        for column in provided
        if column not in known_features
    ]

    if unknown:
        raise HTTPException(
            status_code=422,
            detail={
                "message": "Unknown features were supplied.",
                "unknown_features": unknown,
            }
        )

    # Basic range validation using your existing data contract.
    range_errors = []

    for column in required_features:
        value = provided[column]
        rules = contract["columns"].get(column, {})

        minimum = rules.get("min")
        maximum = rules.get("max")

        if minimum is not None and value < minimum:
            range_errors.append(
                f"{column} must be >= {minimum}"
            )

        if maximum is not None and value > maximum:
            range_errors.append(
                f"{column} must be <= {maximum}"
            )

    if range_errors:
        raise HTTPException(
            status_code=422,
            detail={
                "message": "One or more values are outside expected ranges.",
                "errors": range_errors,
            }
        )

    # Ensure columns are in exactly the same order as training.
    row = {
        column: provided[column]
        for column in required_features
    }

    input_df = pd.DataFrame(
        [row],
        columns=required_features
    )

    # Prediction
    prediction = model.predict(input_df)[0]

    # Probabilities
    probabilities = model.predict_proba(input_df)[0]

    classes = model.classes_

    probability_dict = {
        str(label): round(float(probability), 4)
        for label, probability in zip(
            classes,
            probabilities
        )
    }

    return {
        "prediction": str(prediction),
        "probabilities": probability_dict,
        "model": {
            "name": MODEL_NAME,
            "alias": MODEL_ALIAS,
            "version": model_version.version,
            "type": model_type,
            "feature_set": feature_set_name,
        }
    }

# ---------------------------------------------------------
# template endpoint
# ---------------------------------------------------------
@app.get("/template")
def download_template():

    # Add Student ID as a non-model identifier column
    template_columns = ["Student ID"] + required_features

    # Create one blank example row
    sample_row = {column: None for column in template_columns}
    template_df = pd.DataFrame([sample_row])

    # Write Excel file in memory
    output = BytesIO()

    with pd.ExcelWriter(
        output,
        engine="openpyxl"
    ) as writer:
        template_df.to_excel(
            writer,
            index=False,
            sheet_name="Student Input Template"
        )

    output.seek(0)

    return StreamingResponse(
        output,
        media_type=(
            "application/vnd.openxmlformats-officedocument."
            "spreadsheetml.sheet"
        ),
        headers={
            "Content-Disposition":
                'attachment; filename="student_prediction_template.xlsx"'
        }
    )

# ---------------------------------------------------------
# Predict-file endpoint
# ---------------------------------------------------------

@app.post("/predict-file")
async def predict_file(file: UploadFile = File(...)):

    # ---------------------------------------------------------
    # Validate file type
    # ---------------------------------------------------------

    if not file.filename.lower().endswith((".xlsx", ".xls")):
        raise HTTPException(
            status_code=400,
            detail="Please upload an Excel file (.xlsx or .xls)."
        )

    # ---------------------------------------------------------
    # Read Excel file
    # ---------------------------------------------------------

    try:
        contents = await file.read()
        df = pd.read_excel(BytesIO(contents))
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Could not read Excel file: {str(e)}"
        )

    if df.empty:
        raise HTTPException(
            status_code=400,
            detail="The uploaded Excel file contains no rows."
        )

    # ---------------------------------------------------------
    # Check required columns
    # ---------------------------------------------------------

    missing = [
        column
        for column in required_features
        if column not in df.columns
    ]

    if missing:
        raise HTTPException(
            status_code=422,
            detail={
                "message": "Required features are missing.",
                "missing_features": missing,
            }
        )

    # ---------------------------------------------------------
    # Select only the model's required features
    # ---------------------------------------------------------

    input_df = df[required_features].copy()

    # ---------------------------------------------------------
    # Check for missing values
    # ---------------------------------------------------------

    null_counts = input_df.isnull().sum()

    columns_with_nulls = {
        column: int(count)
        for column, count in null_counts.items()
        if count > 0
    }

    if columns_with_nulls:
        raise HTTPException(
            status_code=422,
            detail={
                "message": "Missing values were found in required columns.",
                "columns_with_missing_values": columns_with_nulls,
            }
        )

    # ---------------------------------------------------------
    # Validate ranges using data_contract.yaml
    # ---------------------------------------------------------

    range_errors = []

    for column in required_features:

        rules = contract["columns"].get(column, {})

        minimum = rules.get("min")
        maximum = rules.get("max")

        if minimum is not None:
            invalid_count = int((input_df[column] < minimum).sum())

            if invalid_count > 0:
                range_errors.append(
                    f"{column}: {invalid_count} value(s) below {minimum}"
                )

        if maximum is not None:
            invalid_count = int((input_df[column] > maximum).sum())

            if invalid_count > 0:
                range_errors.append(
                    f"{column}: {invalid_count} value(s) above {maximum}"
                )

    if range_errors:
        raise HTTPException(
            status_code=422,
            detail={
                "message": "Some values are outside expected ranges.",
                "errors": range_errors,
            }
        )

    # ---------------------------------------------------------
    # Generate predictions
    # ---------------------------------------------------------

    try:
        predictions = model.predict(input_df)
        probabilities = model.predict_proba(input_df)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Prediction failed: {str(e)}"
        )

    # ---------------------------------------------------------
    # Add prediction columns to original data
    # ---------------------------------------------------------

    result_df = df.copy()

    result_df["Predicted Outcome"] = predictions

    for index, class_name in enumerate(model.classes_):
        result_df[f"Probability {class_name}"] = probabilities[:, index]

    # ---------------------------------------------------------
    # Add model metadata
    # ---------------------------------------------------------

    result_df["Model Version"] = model_version.version
    result_df["Model Alias"] = MODEL_ALIAS
    result_df["Feature Set"] = feature_set_name

    # ---------------------------------------------------------
    # Write results to Excel in memory
    # ---------------------------------------------------------

    output = BytesIO()

    with pd.ExcelWriter(
        output,
        engine="openpyxl"
    ) as writer:

        result_df.to_excel(
            writer,
            index=False,
            sheet_name="Predictions"
        )

    output.seek(0)

    # ---------------------------------------------------------
    # Return downloadable Excel file
    # ---------------------------------------------------------

    return StreamingResponse(
        output,
        media_type=(
            "application/vnd.openxmlformats-officedocument."
            "spreadsheetml.sheet"
        ),
        headers={
            "Content-Disposition":
                'attachment; filename="student_predictions.xlsx"'
        }
    )

