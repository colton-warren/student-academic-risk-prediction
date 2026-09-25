# KNIME Python Script node -- logs the six experiment runs to MLflow.
#
# SETUP: the node needs SIX table input ports. In the node's dialog, add input
# ports until there are six, then connect the SECOND output (accuracy
# statistics) of each Scorer in the order listed in RUNS below.
#
# Only the three settings directly below should ever need editing.

import knime.scripting.io as knio
import mlflow

# Absolute path to the MLflow database. KNIME's working directory is not the
# project folder, so a relative path will not find it. Forward slashes on
# Windows too, e.g. "C:/Users/you/student-academic-risk-prediction/mlflow.db"
TRACKING_DB = "/Users/pthaden/dev/student-academic-risk-prediction/mlflow.db"

# Bump when you re-run after changing something, so runs stay distinguishable.
RUN_VERSION = "v1"
EXPERIMENT = "Student Academic Risk Prediction"

# Input port order -> which run it is. Connect the Scorers in this order.
RUNS = [
    ("forest", "enrollment_only"),   # port 0  <- Scorer (#23)
    ("forest", "through_sem1"),      # port 1  <- Scorer (#24)
    ("forest", "all_features"),      # port 2  <- Scorer (#27)
    ("logreg", "enrollment_only"),   # port 3  <- Scorer (#34)
    ("logreg", "through_sem1"),      # port 4  <- Scorer (#35)
    ("logreg", "all_features"),      # port 5  <- Scorer (#40)
]

# What was configured in the learner dialogs. KNIME does not pass node settings
# to this script, so they are recorded here -- keep them in step with the nodes.
HYPERPARAMETERS = {
    "forest": {
        "n_trees": 300,
        "max_depth": "unlimited",
        "min_node_size": 1,
        "max_features": "sqrt",
    },
    "logreg": {
        "solver": "iteratively_reweighted_least_squares",
        "regularization": "none",
        "max_epochs": 100,
        "preprocessing": "z_score_normalizer",
    },
}

FEATURE_COUNTS = {"enrollment_only": 24, "through_sem1": 30, "all_features": 36}


def metrics_from_scorer(table):
    """Pull metrics out of a KNIME Scorer node's accuracy-statistics table.

    That table has one row per class, each carrying Recall, Precision and
    F-measure, plus a final overall row where only Accuracy and Cohen's kappa
    are filled in. Everything else in the class rows is missing, so each value
    is read from whichever row actually holds it.
    """
    df = table.to_pandas()
    out = {}

    for column, name in (("Accuracy", "accuracy"), ("Cohen's kappa", "cohens_kappa")):
        if column in df.columns:
            values = df[column].dropna()
            if len(values):
                out[name] = float(values.iloc[-1])

    # Row labels are the class names; the overall row has no per-class metrics.
    for label, row in df.iterrows():
        cls = str(label).strip().lower()
        if cls in ("dropout", "enrolled", "graduate"):
            for column, prefix in (("Recall", "recall"),
                                   ("Precision", "precision"),
                                   ("F-measure", "f1")):
                value = row.get(column)
                if value is not None and value == value:  # not NaN
                    out[f"{prefix}_{cls}"] = float(value)

    # The metric the project is judged on, named consistently with the Python
    # pipeline so the two are comparable in the MLflow UI.
    if "recall_dropout" in out:
        out["recall_focus"] = out["recall_dropout"]
    return out


# A wrong path here does not fail -- SQLite simply creates a new, empty
# database, the node reports success, and the runs land somewhere nobody else
# can see. Checking the folder exists turns that silent mistake into a message.
import os
_folder = os.path.dirname(TRACKING_DB)
if not os.path.isdir(_folder):
    raise ValueError(
        f"TRACKING_DB points into a folder that does not exist: {_folder}\n"
        "Set TRACKING_DB to the absolute path of mlflow.db in your own clone of "
        "the repository, using forward slashes on Windows too, e.g.\n"
        "  C:/Users/you/student-academic-risk-prediction/mlflow.db"
    )
if not os.path.exists(TRACKING_DB):
    print(f"NOTE: {TRACKING_DB} does not exist yet; a new database will be created. "
          "If you expected to add to the team's existing runs, check the path.")

mlflow.set_tracking_uri(f"sqlite:///{TRACKING_DB}")
mlflow.set_experiment(EXPERIMENT)

logged = []
for port, (model, feature_set) in enumerate(RUNS):
    if port >= len(knio.input_tables):
        print(f"SKIPPED port {port} ({model}/{feature_set}): no table connected")
        continue

    metrics = metrics_from_scorer(knio.input_tables[port])
    run_name = f"knime_{model}_{feature_set}_{RUN_VERSION}"

    with mlflow.start_run(run_name=run_name):
        mlflow.log_params({
            "tool": "KNIME",
            "model_type": model,
            "feature_set": feature_set,
            "n_features": FEATURE_COUNTS[feature_set],
            "split": "80/20 stratified on target, seed fixed",
            **{f"hp_{k}": v for k, v in HYPERPARAMETERS[model].items()},
        })
        mlflow.log_metrics(metrics)

    accuracy = metrics.get("accuracy")
    recall = metrics.get("recall_dropout")
    logged.append(run_name)
    print(f"{run_name:<38} accuracy={accuracy}  recall[Dropout]={recall}")

print(f"\nLogged {len(logged)} runs to {EXPERIMENT}")

# Pass the first table through so the node has an output.
knio.output_tables[0] = knio.input_tables[0]
