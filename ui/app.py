import streamlit as st
import requests
import pandas as pd
from io import BytesIO
from category_mappings import CATEGORY_OPTIONS

# ---------------------------------------------------------
# Configuration
# ---------------------------------------------------------

API_URL = "http://127.0.0.1:8000"

st.set_page_config(
    page_title="Student Academic Risk Prediction",
    page_icon="🎓",
    layout="wide"
)

st.title("🎓 Student Academic Risk Prediction")

st.write(
    "Use the deployed early-intervention model to identify students "
    "who may be at risk of dropping out."
)


# ---------------------------------------------------------
# Get model information
# ---------------------------------------------------------

try:
    response = requests.get(
        f"{API_URL}/model-info",
        timeout=10
    )

    response.raise_for_status()
    model_info = response.json()

except Exception as e:
    st.error(
        f"Unable to connect to the prediction API: {e}"
    )
    st.stop()


required_features = model_info["required_features"]


# ---------------------------------------------------------
# Model information
# ---------------------------------------------------------

st.subheader("Current Prediction Model")

col1, col2, col3, col4 = st.columns(4)

col1.metric(
    "Model",
    model_info.get("model_type", "Unknown")
)

col2.metric(
    "Feature Set",
    model_info.get("feature_set", "Unknown")
)

col3.metric(
    "Model Version",
    model_info.get("model_version", "Unknown")
)

col4.metric(
    "Features",
    model_info.get("required_feature_count", len(required_features))
)

st.divider()


# ---------------------------------------------------------
# Tabs
# ---------------------------------------------------------

batch_tab, single_tab = st.tabs(
    [
        "📊 Batch Predictions",
        "👤 Single Student"
    ]
)


# =========================================================
# TAB 1: BATCH PREDICTIONS
# =========================================================

with batch_tab:

    st.header("Batch Student Predictions")

    st.write(
        "Upload an Excel file containing multiple students. "
        "Each row should represent one student."
    )

    # -----------------------------------------------------
    # Download template
    # -----------------------------------------------------

    st.subheader("1. Download Template")

    try:
        template_response = requests.get(
            f"{API_URL}/template",
            timeout=10
        )

        if template_response.status_code == 200:

            st.download_button(
                label="⬇️ Download Excel Template",
                data=template_response.content,
                file_name="student_prediction_template.xlsx",
                mime=(
                    "application/vnd.openxmlformats-officedocument."
                    "spreadsheetml.sheet"
                )
            )

    except Exception as e:
        st.error(f"Could not retrieve template: {e}")


    # -----------------------------------------------------
    # Upload file
    # -----------------------------------------------------

    st.subheader("2. Upload Student Data")

    uploaded_file = st.file_uploader(
        "Choose an Excel file",
        type=["xlsx"],
        key="batch_upload"
    )


    if uploaded_file is not None:

        try:

            preview_df = pd.read_excel(uploaded_file)

            st.write(
                f"**{len(preview_df)} students loaded**"
            )

            with st.expander("Preview Uploaded Data"):

                st.dataframe(
                    preview_df,
                    use_container_width=True
                )

            uploaded_file.seek(0)


            # -------------------------------------------------
            # Run predictions
            # -------------------------------------------------

            if st.button(
                "Run Predictions",
                type="primary",
                key="batch_predict"
            ):

                files = {
                    "file": (
                        uploaded_file.name,
                        uploaded_file.getvalue(),
                        "application/vnd.openxmlformats-officedocument."
                        "spreadsheetml.sheet"
                    )
                }

                with st.spinner(
                    "Generating student predictions..."
                ):

                    prediction_response = requests.post(
                        f"{API_URL}/predict-file",
                        files=files,
                        timeout=120
                    )


                if prediction_response.status_code == 200:

                    results = pd.read_excel(
                        BytesIO(
                            prediction_response.content
                        )
                    )

                    # Save results in Streamlit session
                    st.session_state["batch_results"] = results
                    st.session_state["batch_file"] = (
                        prediction_response.content
                    )

                    st.success(
                        "Predictions completed successfully."
                    )

                else:

                    st.error(
                        "Prediction failed."
                    )

                    st.code(
                        prediction_response.text
                    )

        except Exception as e:

            st.error(
                f"Could not process the uploaded file: {e}"
            )


    # -----------------------------------------------------
    # Display predictions
    # -----------------------------------------------------

    if "batch_results" in st.session_state:

        results = st.session_state["batch_results"].copy()

        st.divider()

        st.subheader("3. Prediction Results")


        # -------------------------------------------------
        # Summary
        # -------------------------------------------------

        dropout_count = (
            results["Predicted Outcome"] == "Dropout"
        ).sum()

        enrolled_count = (
            results["Predicted Outcome"] == "Enrolled"
        ).sum()

        graduate_count = (
            results["Predicted Outcome"] == "Graduate"
        ).sum()


        col1, col2, col3, col4 = st.columns(4)

        col1.metric(
            "Students",
            len(results)
        )

        col2.metric(
            "Predicted Dropout",
            int(dropout_count)
        )

        col3.metric(
            "Predicted Enrolled",
            int(enrolled_count)
        )

        col4.metric(
            "Predicted Graduate",
            int(graduate_count)
        )


        # -------------------------------------------------
        # Risk threshold
        # -------------------------------------------------

        st.subheader("Students With Highest Dropout Risk")

        risk_threshold = st.slider(
            "Dropout probability threshold",
            min_value=0.0,
            max_value=1.0,
            value=0.60,
            step=0.05
        )


        # -------------------------------------------------
        # Risk flag
        # -------------------------------------------------

        results["Risk Flag"] = results[
            "Probability Dropout"
        ].apply(
            lambda x:
            "⚠️ High Risk"
            if x >= risk_threshold
            else ""
        )


        # -------------------------------------------------
        # Sort by dropout probability
        # -------------------------------------------------

        results = results.sort_values(
            by="Probability Dropout",
            ascending=False
        )


        # -------------------------------------------------
        # Columns displayed
        # -------------------------------------------------

        display_columns = [
            column
            for column in [
                "Student ID",
                "Risk Flag",
                "Predicted Outcome",
                "Probability Dropout",
                "Probability Enrolled",
                "Probability Graduate"
            ]
            if column in results.columns
        ]


        display_df = results[
            display_columns
        ].copy()


        # -------------------------------------------------
        # Highlight high-risk rows
        # -------------------------------------------------

        def highlight_high_risk(row):

            if (
                "Probability Dropout" in row
                and
                row["Probability Dropout"]
                >= risk_threshold
            ):

                return [
                    "background-color: #ffcccc"
                ] * len(row)

            return [""] * len(row)


        styled_results = (
            display_df
            .style
            .apply(
                highlight_high_risk,
                axis=1
            )
            .format(
                {
                    "Probability Dropout": "{:.1%}",
                    "Probability Enrolled": "{:.1%}",
                    "Probability Graduate": "{:.1%}"
                }
            )
        )


        st.dataframe(
            styled_results,
            use_container_width=True,
            hide_index=True
        )


        # -------------------------------------------------
        # High-risk subset
        # -------------------------------------------------

        high_risk_students = results[
            results["Probability Dropout"]
            >= risk_threshold
        ]


        st.write(
            f"**{len(high_risk_students)} students "
            f"are above the selected risk threshold.**"
        )


        # -------------------------------------------------
        # Download results
        # -------------------------------------------------

        st.download_button(
            label="⬇️ Download Prediction Results",
            data=st.session_state["batch_file"],
            file_name="student_predictions.xlsx",
            mime=(
                "application/vnd.openxmlformats-officedocument."
                "spreadsheetml.sheet"
            )
        )


# =========================================================
# TAB 2: SINGLE STUDENT
# =========================================================

with single_tab:

    st.header("Single Student Prediction")

    st.write(
        "Enter information for one student to generate "
        "an academic-risk prediction."
    )

    # -----------------------------------------------------
    # Organize model features into user-friendly groups
    # -----------------------------------------------------

    FEATURE_GROUPS = {

        "👤 Demographics": [
            "Marital Status",
            "Nacionality",
            "Gender",
            "Age at enrollment",
            "International",
            "Displaced"
        ],

        "🎓 Application & Academic Background": [
            "Application mode",
            "Application order",
            "Course",
            "Daytime/evening attendance",
            "Previous qualification",
            "Previous qualification (grade)",
            "Admission grade"
        ],

        "💰 Financial & Student Support": [
            "Educational special needs",
            "Debtor",
            "Tuition fees up to date",
            "Scholarship holder"
        ],

        "👨‍👩‍👧 Family Background": [
            "Mother's qualification",
            "Father's qualification",
            "Mother's occupation",
            "Father's occupation"
        ],

        "📈 Economic Environment": [
            "Unemployment rate",
            "Inflation rate",
            "GDP"
        ],

        "📚 First-Semester Performance": [
            "Curricular units 1st sem (credited)",
            "Curricular units 1st sem (enrolled)",
            "Curricular units 1st sem (evaluations)",
            "Curricular units 1st sem (approved)",
            "Curricular units 1st sem (grade)",
            "Curricular units 1st sem (without evaluations)"
        ]
    }


    # -----------------------------------------------------
    # Helper function for creating each input
    # -----------------------------------------------------

    def create_feature_input(feature):

        # Friendly categorical dropdowns
        if feature in CATEGORY_OPTIONS:

            options = CATEGORY_OPTIONS[feature]
            codes = list(options.keys())

            return st.selectbox(
                feature,
                options=codes,
                format_func=lambda code, opts=options: opts[code],
                key=f"single_{feature}"
            )

        # Application order
        elif feature == "Application order":

            return st.number_input(
                feature,
                min_value=0,
                max_value=9,
                value=0,
                step=1,
                help="0 = first choice; higher values represent lower preference.",
                key=f"single_{feature}"
            )

        # Grades measured on 0–200 scale
        elif feature in {
            "Previous qualification (grade)",
            "Admission grade"
        }:

            return st.number_input(
                feature,
                min_value=0.0,
                max_value=200.0,
                value=120.0,
                step=0.1,
                key=f"single_{feature}"
            )

        # Semester grade measured on 0–20 scale
        elif feature == "Curricular units 1st sem (grade)":

            return st.number_input(
                feature,
                min_value=0.0,
                max_value=20.0,
                value=10.0,
                step=0.1,
                key=f"single_{feature}"
            )

        # Age
        elif feature == "Age at enrollment":

            return st.number_input(
                feature,
                min_value=15,
                max_value=100,
                value=18,
                step=1,
                key=f"single_{feature}"
            )

        # Economic variables
        elif feature in {
            "Unemployment rate",
            "Inflation rate",
            "GDP"
        }:

            return st.number_input(
                feature,
                value=0.0,
                step=0.1,
                format="%.2f",
                key=f"single_{feature}"
            )

        # Remaining numeric/count variables
        else:

            return st.number_input(
                feature,
                min_value=0,
                value=0,
                step=1,
                key=f"single_{feature}"
            )


    # -----------------------------------------------------
    # Prediction form
    # -----------------------------------------------------

    with st.form("single_student_form"):

        student_id = st.text_input(
            "Student ID",
            placeholder="Example: 10001"
        )

        feature_values = {}

        # Keep track of fields assigned to a group
        grouped_features = set()

        for group_name, group_features in FEATURE_GROUPS.items():

            # Only show fields required by the currently loaded model
            active_features = [
                feature
                for feature in group_features
                if feature in required_features
            ]

            if not active_features:
                continue

            grouped_features.update(active_features)

            st.subheader(group_name)

            left_column, right_column = st.columns(2)

            for index, feature in enumerate(active_features):

                target_column = (
                    left_column
                    if index % 2 == 0
                    else right_column
                )

                with target_column:

                    feature_values[feature] = (
                        create_feature_input(feature)
                    )

        # -------------------------------------------------
        # Safety fallback
        # -------------------------------------------------

        other_features = [
            feature
            for feature in required_features
            if feature not in grouped_features
        ]

        if other_features:

            st.subheader("📋 Additional Information")

            left_column, right_column = st.columns(2)

            for index, feature in enumerate(other_features):

                target_column = (
                    left_column
                    if index % 2 == 0
                    else right_column
                )

                with target_column:

                    feature_values[feature] = (
                        create_feature_input(feature)
                    )

        # -------------------------------------------------
        # Submit button
        # -------------------------------------------------

        submit_student = st.form_submit_button(
            "Predict Student Outcome",
            type="primary",
            key="single_student_submit"
        )


    # -----------------------------------------------------
    # Generate prediction
    # -----------------------------------------------------

    if submit_student:

        payload = {
            "features": feature_values
        }

        try:

            with st.spinner("Generating prediction..."):

                response = requests.post(
                    f"{API_URL}/predict",
                    json=payload,
                    timeout=30
                )

            if response.status_code == 200:

                prediction = response.json()

                outcome = prediction["prediction"]
                probabilities = prediction["probabilities"]

                dropout_probability = probabilities.get(
                    "Dropout",
                    0
                )

                enrolled_probability = probabilities.get(
                    "Enrolled",
                    0
                )

                graduate_probability = probabilities.get(
                    "Graduate",
                    0
                )

                st.success("Prediction completed.")

                if student_id:

                    st.subheader(
                        f"Results for Student {student_id}"
                    )

                else:

                    st.subheader("Prediction Results")


                # -----------------------------------------
                # Predicted outcome
                # -----------------------------------------

                st.metric(
                    "Predicted Outcome",
                    outcome
                )


                # -----------------------------------------
                # Probabilities
                # -----------------------------------------

                col1, col2, col3 = st.columns(3)

                col1.metric(
                    "Dropout Probability",
                    f"{dropout_probability:.1%}"
                )

                col2.metric(
                    "Enrolled Probability",
                    f"{enrolled_probability:.1%}"
                )

                col3.metric(
                    "Graduate Probability",
                    f"{graduate_probability:.1%}"
                )


                # -----------------------------------------
                # Dropout risk indicator
                # -----------------------------------------

                st.subheader("Dropout Risk")

                st.progress(
                    float(dropout_probability)
                )

                if dropout_probability >= 0.60:

                    st.warning(
                        "This student has an elevated predicted "
                        "probability of dropout and may warrant "
                        "additional review."
                    )

                else:

                    st.info(
                        "This student's predicted dropout "
                        "probability is below the current "
                        "60% review threshold."
                    )


                # -----------------------------------------
                # Model details
                # -----------------------------------------

                with st.expander(
                    "Prediction Model Details"
                ):

                    model_details = prediction.get(
                        "model",
                        {}
                    )

                    st.write(
                        "Model:",
                        model_details.get(
                            "type",
                            "Unknown"
                        )
                    )

                    st.write(
                        "Feature Set:",
                        model_details.get(
                            "feature_set",
                            "Unknown"
                        )
                    )

                    st.write(
                        "Model Version:",
                        model_details.get(
                            "version",
                            "Unknown"
                        )
                    )

            else:

                st.error(
                    "Prediction could not be generated."
                )

                st.code(response.text)

        except Exception as e:

            st.error(
                f"Could not connect to the prediction API: {e}"
            )