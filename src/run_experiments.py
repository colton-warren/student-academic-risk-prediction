"""Run the experiment grid: every model against every feature set.

The comparison the project needs is two-dimensional. Which algorithm performs
better is one question; how early a useful prediction can be made is the other,
and it is the one the stakeholder story depends on. Sweeping both together
makes the trade-off between them visible in a single table.

Every run shares one train/test split, drawn once and reused, so differences in
the results come from the model and the feature set rather than from the luck
of the split.

Each run is logged to MLflow with the metadata the conceptual design calls for:
run name, feature set, preprocessing steps, dataset version and the model's own
hyperparameters. The dataset version is the md5 DVC uses, which is what ties a
result back to the exact data that produced it.
"""

import hashlib
import json
import os
import sys
from pathlib import Path

import joblib
import mlflow
import mlflow.sklearn
import pandas as pd
import yaml
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

sys.path.insert(0, str(Path(__file__).parent))
from features import feature_sets  # noqa: E402

DATA = "data/processed/cleaned_student_data.csv"
RESULTS = "metrics/experiment_results.json"
COMPARISON = "reports/experiment_comparison.md"
MODEL_DIR = "models"
DEFAULT_TRACKING_URI = "sqlite:///mlflow.db"
EXPERIMENT = "Student Academic Risk Prediction"

# Every run is registered as a version of one registered model, so the registry
# shows the whole comparison rather than a single winner, and the alias can move
# as results change. The KNIME workflow logs into the same experiment with
# tool=KNIME, which is how the two implementations are told apart in the UI.
REGISTERED_MODEL = "student-risk-classifier"

# MLflow serialises sklearn models with skops, which refuses to write a tree
# ensemble's internal node arrays unless they are explicitly trusted: a
# hand-crafted model file with out-of-range node indices can crash the process
# on predict. These models are fitted in this process moments earlier, so the
# provenance skops is worried about is our own pipeline.
TRUSTED_TYPES = {"forest": ["sklearn.tree._tree.Tree"]}


def build_model(kind, hyperparams, random_state):
    """Build an estimator. Only the linear model needs its inputs scaled;
    a forest splits on raw values, so scaling it would add noise to no end."""
    if kind == "logreg":
        return Pipeline([
            ("scale", StandardScaler()),
            ("model", LogisticRegression(random_state=random_state, **hyperparams)),
        ]), {"preprocessing": "StandardScaler"}
    if kind == "forest":
        return RandomForestClassifier(
            random_state=random_state, n_jobs=-1, **hyperparams
        ), {"preprocessing": "none"}
    raise ValueError(f"unknown model: {kind}")


def evaluate(y_true, y_pred, labels, focus_class):
    metrics = {
        "accuracy": accuracy_score(y_true, y_pred),
        "precision_macro": precision_score(y_true, y_pred, average="macro", zero_division=0),
        "recall_macro": recall_score(y_true, y_pred, average="macro", zero_division=0),
        "f1_macro": f1_score(y_true, y_pred, average="macro", zero_division=0),
    }
    # Per-class recall: the macro average hides that "Enrolled" is by far the
    # hardest class, and hiding that would be the wrong summary of this model.
    per_class = recall_score(y_true, y_pred, labels=labels, average=None, zero_division=0)
    for label, value in zip(labels, per_class):
        metrics[f"recall_{label.lower()}"] = float(value)
    metrics["recall_focus"] = metrics[f"recall_{focus_class.lower()}"]
    return {k: float(v) for k, v in metrics.items()}


def main():
    params = yaml.safe_load(Path("params.yaml").read_text())
    cfg = params["experiment"]
    target = cfg["target_column"]
    focus = cfg["focus_class"]

    df = pd.read_csv(DATA)
    dataset_version = hashlib.md5(Path(DATA).read_bytes()).hexdigest()
    labels = sorted(df[target].unique())
    sets = feature_sets(df.columns)

    # One split, drawn once on the row index and reused for every run, so the
    # feature sets are compared on identical students.
    index_train, index_test = train_test_split(
        df.index,
        test_size=cfg["test_size"],
        random_state=cfg["random_state"],
        stratify=df[target] if cfg["stratify"] else None,
    )
    y_train, y_test = df.loc[index_train, target], df.loc[index_test, target]

    mlflow.set_tracking_uri(os.environ.get("MLFLOW_TRACKING_URI", DEFAULT_TRACKING_URI))
    mlflow.set_experiment(EXPERIMENT)
    Path(MODEL_DIR).mkdir(parents=True, exist_ok=True)

    runs = []
    for set_name in cfg["feature_sets"]:
        columns = sets[set_name]
        X_train, X_test = df.loc[index_train, columns], df.loc[index_test, columns]

        for model_name, hyperparams in params["models"].items():
            run_name = f"{model_name}_{set_name}_{cfg['run_version']}"
            estimator, prep = build_model(model_name, dict(hyperparams), cfg["random_state"])
            estimator.fit(X_train, y_train)
            metrics = evaluate(y_test, estimator.predict(X_test), labels, focus)

            model_path = f"{MODEL_DIR}/{model_name}_{set_name}.joblib"
            joblib.dump(estimator, model_path)

            with mlflow.start_run(run_name=run_name):
                mlflow.log_params({
                    "tool": "python",
                    "model_type": model_name,
                    "feature_set": set_name,
                    "n_features": len(columns),
                    "dataset_version_md5": dataset_version,
                    "split_stratified": cfg["stratify"],
                    "test_size": cfg["test_size"],
                    **prep,
                    **{f"hp_{k}": v for k, v in hyperparams.items()},
                })
                mlflow.log_metrics(metrics)
                info = mlflow.sklearn.log_model(
                    estimator,
                    name="model",
                    skops_trusted_types=TRUSTED_TYPES.get(model_name, []),
                )
                version = register_version(info.model_uri, run_name, model_name,
                                           set_name, len(columns), metrics)

            runs.append({
                "run_name": run_name,
                "registered_version": version,
                "model": model_name,
                "feature_set": set_name,
                "n_features": len(columns),
                "model_path": model_path,
                "confusion_matrix": {
                    "labels": labels,
                    "counts": confusion_matrix(
                        y_test, estimator.predict(X_test), labels=labels
                    ).tolist(),
                },
                **metrics,
            })
            print(f"{run_name:<34} accuracy {metrics['accuracy']:.3f}  "
                  f"recall[{focus}] {metrics['recall_focus']:.3f}")

    best = max(runs, key=lambda r: r["recall_focus"])
    promote_champion(best)
    write_reports(runs, best, focus, dataset_version, labels)
    print(f"\nBest by recall[{focus}]: {best['run_name']} ({best['recall_focus']:.3f})")
    return 0


def register_version(model_uri, run_name, model_name, set_name, n_features, metrics):
    """Add this run to the model registry as a new version, documented.

    The assignment asks for versioned models with clear documentation per
    version, so the description records what the version actually is -- which
    algorithm, which feature set, and how it scored -- rather than leaving a
    reader to open the run to find out. Registry availability varies by backend,
    and a registry outage is no reason to lose a completed training run, so a
    failure here is reported and stepped over.
    """
    try:
        registered = mlflow.register_model(model_uri=model_uri, name=REGISTERED_MODEL)
        client = mlflow.tracking.MlflowClient()
        client.update_model_version(
            name=REGISTERED_MODEL,
            version=registered.version,
            description=(
                f"{model_name} trained on the {set_name} feature set "
                f"({n_features} features). Accuracy {metrics['accuracy']:.3f}, "
                f"macro F1 {metrics['f1_macro']:.3f}, "
                f"recall on the focus class {metrics['recall_focus']:.3f}. "
                f"Produced by the Python pipeline as run {run_name}."
            ),
        )
        for key, value in (("tool", "python"), ("model_type", model_name),
                           ("feature_set", set_name), ("validation_status", "pending")):
            client.set_model_version_tag(REGISTERED_MODEL, registered.version, key, value)
        return int(registered.version)
    except Exception as error:  # noqa: BLE001 - the registry is optional
        print(f"  (registry unavailable, not versioned: {error})")
        return None


def promote_champion(best):
    """Point the `champion` alias at the best run, and record why.

    An alias rather than a stage, because a name like `champion` survives the
    version numbers changing underneath it: anything loading
    `models:/student-risk-classifier@champion` keeps working across reruns.
    """
    if best.get("registered_version") is None:
        return
    try:
        client = mlflow.tracking.MlflowClient()
        client.set_registered_model_alias(
            REGISTERED_MODEL, "champion", best["registered_version"]
        )
        client.set_model_version_tag(
            REGISTERED_MODEL, best["registered_version"], "validation_status", "champion"
        )
        print(f"champion alias -> version {best['registered_version']} ({best['run_name']})")
    except Exception as error:  # noqa: BLE001
        print(f"  (could not set champion alias: {error})")


def write_reports(runs, best, focus, dataset_version, labels):
    Path(RESULTS).parent.mkdir(parents=True, exist_ok=True)
    # Deliberately small. `dvc metrics show` puts every key in its own column
    # and unions them across files, so logging all six runs x four metrics here
    # produces a table nobody can read. The primary metric per run is enough to
    # make `dvc metrics diff` meaningful between commits; the full breakdown,
    # including confusion matrices, lives in the markdown report.
    summary = {"best_run": best["run_name"], "best_recall_focus": round(best["recall_focus"], 4)}
    for run in runs:
        summary[f"recall_focus.{run['run_name']}"] = round(run["recall_focus"], 4)
    Path(RESULTS).write_text(json.dumps(summary, indent=2) + "\n")

    lines = [
        "# Experiment comparison",
        "",
        f"Dataset version (md5): `{dataset_version}`  ",
        f"Primary metric: recall on **{focus}** -- a false negative is a student "
        "who needed help and did not get flagged.",
        "",
        "| Model | Feature set | Features | Accuracy | Macro F1 | "
        + " | ".join(f"Recall {label}" for label in labels) + " |",
        "|---|---|---:|---:|---:|" + "---:|" * len(labels),
    ]
    for run in runs:
        recalls = " | ".join(f"{run['recall_' + label.lower()]:.3f}" for label in labels)
        lines.append(
            f"| {run['model']} | {run['feature_set']} | {run['n_features']} | "
            f"{run['accuracy']:.3f} | {run['f1_macro']:.3f} | {recalls} |"
        )

    lines += ["", "## Confusion matrices", ""]
    for run in runs:
        matrix = run["confusion_matrix"]
        lines += [f"**{run['run_name']}** (rows = actual, columns = predicted)", "",
                  "| | " + " | ".join(matrix["labels"]) + " |",
                  "|---|" + "---:|" * len(matrix["labels"])]
        for label, row in zip(matrix["labels"], matrix["counts"]):
            lines.append(f"| **{label}** | " + " | ".join(str(v) for v in row) + " |")
        lines.append("")

    Path(COMPARISON).write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    sys.exit(main())
