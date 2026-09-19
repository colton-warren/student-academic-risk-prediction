"""Train and log the multinomial logistic regression baseline.

Run it through the pipeline (`dvc repro`) rather than directly, so the inputs
are the DVC-tracked ones and the outputs land where dvc.yaml expects them.

Hyperparameters live in params.yaml. MLflow logging is unchanged in substance;
the tracking URI is read from MLFLOW_TRACKING_URI so the team can point at a
shared server instead of each keeping a private mlflow.db.
"""

import json
import os
from pathlib import Path

import joblib
import mlflow
import mlflow.sklearn
import pandas as pd
import yaml
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

DATA = "data/processed/cleaned_student_data.csv"
MODEL_OUT = "models/multinomial_logistic_regression.joblib"
METRICS_OUT = "metrics/train_metrics.json"
# Each teammate's private default. Set MLFLOW_TRACKING_URI to a shared server
# (e.g. the DagsHub one) to pool runs instead.
DEFAULT_TRACKING_URI = "sqlite:///mlflow.db"


def main():
    params = yaml.safe_load(Path("params.yaml").read_text())["train"]

    data = pd.read_csv(DATA)
    X = data.drop(columns=[params["target_column"]])
    y = data[params["target_column"]]
    print(f"Loaded {len(data)} rows, {X.shape[1]} features")

    X_train, X_val, y_train, y_val = train_test_split(
        X,
        y,
        test_size=params["test_size"],
        random_state=params["random_state"],
    )

    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_val_scaled = scaler.transform(X_val)

    # `multi_class` was removed in scikit-learn 1.7. lbfgs is multinomial by
    # default for multiclass targets, so dropping it preserves the behaviour.
    model = LogisticRegression(
        solver=params["solver"],
        max_iter=params["max_iter"],
        random_state=params["random_state"],
    )
    model.fit(X_train_scaled, y_train)
    y_pred = model.predict(X_val_scaled)

    metrics = {
        "accuracy": accuracy_score(y_val, y_pred),
        "precision_macro": precision_score(y_val, y_pred, average="macro", zero_division=0),
        "recall_macro": recall_score(y_val, y_pred, average="macro", zero_division=0),
        "f1_macro": f1_score(y_val, y_pred, average="macro", zero_division=0),
        f"recall_{params['focus_class'].lower()}": recall_score(
            y_val,
            y_pred,
            labels=[params["focus_class"]],
            average="micro",
            zero_division=0,
        ),
    }

    # Persist the fitted pipeline and the metrics as DVC-tracked outputs, so
    # the results survive independently of whichever MLflow backend is in use.
    Path(MODEL_OUT).parent.mkdir(parents=True, exist_ok=True)
    joblib.dump({"scaler": scaler, "model": model}, MODEL_OUT)
    Path(METRICS_OUT).parent.mkdir(parents=True, exist_ok=True)
    Path(METRICS_OUT).write_text(json.dumps(metrics, indent=2) + "\n")

    mlflow.set_tracking_uri(os.environ.get("MLFLOW_TRACKING_URI", DEFAULT_TRACKING_URI))
    mlflow.set_experiment("Student Academic Risk Prediction")

    with mlflow.start_run(run_name="Multinomial Logistic Regression Model"):
        mlflow.log_param("model_type", "Multinomial Logistic Regression")
        mlflow.log_param("preprocessing", "StandardScaler")
        mlflow.log_params(params)
        mlflow.log_metrics(metrics)
        mlflow.sklearn.log_model(model, name="model")

        run_id = mlflow.active_run().info.run_id
        register_model(f"runs:/{run_id}/model")

    for name, value in metrics.items():
        print(f"{name}: {value:.4f}")


def register_model(model_uri):
    """Register the run in the MLflow model registry, if one is available.

    Not every tracking backend exposes a registry, and a registry outage is no
    reason to fail the pipeline once the model and metrics are already written.
    """
    name = "Multinomial Logistic Regression Model"
    try:
        registered = mlflow.register_model(model_uri=model_uri, name=name)
        client = mlflow.tracking.MlflowClient()
        client.set_registered_model_tag(registered.name, "validation_status", "pending")
        client.set_registered_model_alias(
            registered.name, "challenger", version=registered.version
        )
        print(f"Registered {registered.name} version {registered.version} as challenger")
    except Exception as error:  # noqa: BLE001 - registry is optional
        print(f"Skipped model registry: {error}")


if __name__ == "__main__":
    main()
