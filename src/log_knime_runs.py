"""Log the KNIME workflow's Scorer results to MLflow.

The KNIME side of this needs no Python extension: each Scorer's accuracy
statistics go to a plain CSV Writer, a node the workflow already uses. This
script reads those CSVs and logs one MLflow run per file, so the KNIME results
sit beside the Python ones in a single experiment.

That split matters for a team where only some people write Python. Configuring
KNIME's Python Integration means installing an extension, pointing it at an
interpreter and matching package versions, on every machine -- and a workflow
containing a node someone cannot run will not execute for them at all. A CSV
Writer works everywhere, and this script runs wherever `pip install -r
requirements.txt` has been run.

Which run a file represents comes from its name, `{model}_{feature_set}.csv`,
so there is no port order to get backwards.
"""

import argparse
import json
import os
import sys
from pathlib import Path

import mlflow
import pandas as pd
import yaml

RESULTS_DIR = "reports/knime"
EXPERIMENT = "Student Academic Risk Prediction"
DEFAULT_TRACKING_URI = "sqlite:///mlflow.db"
CLASSES = ("Dropout", "Enrolled", "Graduate")
FEATURE_COUNTS = {"enrollment_only": 24, "through_sem1": 30, "all_features": 36}


def metrics_from_scorer(df):
    """Read a KNIME Scorer accuracy-statistics table.

    One row per class carrying Recall, Precision and F-measure, then an overall
    row where only Accuracy and Cohen's kappa are filled in. Each value is taken
    from whichever row actually holds it rather than assuming a row order.
    """
    label_column = df.columns[0]
    metrics = {}

    for column, name in (("Accuracy", "accuracy"), ("Cohen's kappa", "cohens_kappa")):
        if column in df.columns:
            values = pd.to_numeric(df[column], errors="coerce").dropna()
            if len(values):
                metrics[name] = float(values.iloc[-1])

    for _, row in df.iterrows():
        label = str(row[label_column]).strip().lower()
        if label not in {c.lower() for c in CLASSES}:
            continue
        for column, prefix in (("Recall", "recall"), ("Precision", "precision"),
                               ("F-measure", "f1")):
            value = pd.to_numeric(pd.Series([row.get(column)]), errors="coerce").iloc[0]
            if pd.notna(value):
                metrics[f"{prefix}_{label}"] = float(value)

    if "recall_dropout" in metrics:
        metrics["recall_focus"] = metrics["recall_dropout"]
    return metrics


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results-dir", default=RESULTS_DIR)
    parser.add_argument("--run-version", default="v1",
                        help="suffix distinguishing repeat runs: v1, v2, ...")
    args = parser.parse_args()

    params = yaml.safe_load(Path("params.yaml").read_text())
    hyperparameters = params.get("knime_models", {})

    files = sorted(Path(args.results_dir).glob("*.csv"))
    if not files:
        print(f"No Scorer CSVs in {args.results_dir}/.")
        print("Execute the KNIME workflow first; each Scorer's second output port "
              "should go to a CSV Writer named {model}_{feature_set}.csv")
        return 1

    mlflow.set_tracking_uri(os.environ.get("MLFLOW_TRACKING_URI", DEFAULT_TRACKING_URI))
    mlflow.set_experiment(EXPERIMENT)

    logged = []
    for path in files:
        stem = path.stem
        if "_" not in stem:
            print(f"  skipping {path.name}: expected {{model}}_{{feature_set}}.csv")
            continue
        model, feature_set = stem.split("_", 1)

        df = pd.read_csv(path)
        metrics = metrics_from_scorer(df)
        if not metrics:
            print(f"  skipping {path.name}: no metrics found -- is 'write row ID' "
                  "enabled on the CSV Writer?")
            continue

        run_name = f"knime_{model}_{feature_set}_{args.run_version}"
        with mlflow.start_run(run_name=run_name):
            mlflow.log_params({
                "tool": "KNIME",
                "model_type": model,
                "feature_set": feature_set,
                "n_features": FEATURE_COUNTS.get(feature_set, "unknown"),
                "split": "80/20 stratified on target, seed fixed",
                "source_file": path.name,
                **{f"hp_{k}": v for k, v in hyperparameters.get(model, {}).items()},
            })
            mlflow.log_metrics(metrics)
            # The Scorer table itself, so a run can be checked against what KNIME
            # actually produced rather than only the numbers extracted from it.
            mlflow.log_artifact(str(path), artifact_path="knime_scorer_output")

        logged.append((model, feature_set, metrics.get("accuracy")))
        print(f"{run_name:<40} accuracy={metrics.get('accuracy')}  "
              f"recall[Dropout]={metrics.get('recall_dropout')}")

    check_ordering(logged)
    print(f"\nLogged {len(logged)} KNIME runs to '{EXPERIMENT}'")
    return 0


def check_ordering(logged):
    """Warn if accuracy falls as features are added.

    Nothing in a Scorer's output identifies which branch produced it, so a
    mislabelled CSV Writer would log confident, wrong results. More features
    should not reduce accuracy, and a violation is a good hint that two files
    are named the wrong way round.
    """
    order = ["enrollment_only", "through_sem1", "all_features"]
    by_model = {}
    for model, feature_set, accuracy in logged:
        if accuracy is not None:
            by_model.setdefault(model, {})[feature_set] = accuracy

    problems = []
    for model, scores in by_model.items():
        seen = [(f, scores[f]) for f in order if f in scores]
        for (earlier, a), (later, b) in zip(seen, seen[1:]):
            if b < a - 0.02:
                problems.append(f"{model}: {earlier} scored {a:.3f} but {later} scored {b:.3f}")
    if problems:
        print("\nWARNING: accuracy drops as features are added, which usually means")
        print("two Scorer CSVs are named the wrong way round:")
        for line in problems:
            print(f"  {line}")


if __name__ == "__main__":
    sys.exit(main())
