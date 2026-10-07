"""Tune hyperparameters and the Dropout decision threshold.

The v1 experiments ran every model at its default settings. This script asks
whether tuning changes the picture, without spending the test set to find out:

  1. A grid search per model x feature set, scored by 5-fold stratified
     cross-validation on the TRAINING rows only. The scaler sits inside the
     pipeline, so it is refit on each fold's training part and nothing leaks.
  2. The winner is the best cross-validated Dropout recall among configurations
     whose cross-validated macro F1 stays within a tolerance of the baseline's.
     Without that guard the search could "win" by flagging nearly everyone.
  3. A decision-threshold sweep on out-of-fold probabilities: flag a student as
     Dropout when P(Dropout) reaches the threshold, otherwise take the likelier
     of the other two classes. The threshold is the lowest-cost way to trade
     precision for recall, so it needs a floor on precision: advisors have
     limited time.
  4. Only then is the held-out test set scored, once per configuration, next to
     the untuned baseline, with a paired bootstrap on the difference in Dropout
     recall so that a gain inside the noise is reported as one.

Runs are logged to the same MLflow experiment as the v1 runs, named
{model}_{feature_set}_{run_version}_tuned, and registered as new versions of
the same registered model. No alias is moved: choosing what to deploy is a
decision for the team, not a side effect of a tuning run.
"""

import json
import os
import sys
from pathlib import Path

import joblib
import mlflow
import mlflow.sklearn
import numpy as np
import pandas as pd
import yaml
from sklearn.metrics import make_scorer, precision_score, recall_score, f1_score
from sklearn.model_selection import (
    GridSearchCV,
    StratifiedKFold,
    cross_val_predict,
    cross_validate,
    train_test_split,
)

sys.path.insert(0, str(Path(__file__).parent))
from features import feature_sets  # noqa: E402
from run_experiments import (  # noqa: E402
    DATA,
    DEFAULT_TRACKING_URI,
    EXPERIMENT,
    REGISTERED_MODEL,
    TRUSTED_TYPES,
    build_model,
    evaluate,
)

REPORT = "reports/tuning_report.md"
RESULTS = "metrics/tuning_results.json"
SWEEP_CSV = "reports/tuning_threshold_sweep.csv"
MODEL_DIR = "models_tuned"

# Search spaces. Each includes the v1 defaults so the baseline is one of the
# candidates and "tuning found nothing better" is a possible answer.
# class_weight is searched because it is the most direct lever on minority-class
# recall. lbfgs only does L2, so any l1_ratio above 0 needs saga.
GRIDS = {
    "logreg": [
        {"model__C": [0.01, 0.03, 0.1, 0.3, 1.0, 3.0, 10.0],
         "model__l1_ratio": [0], "model__solver": ["lbfgs"],
         "model__class_weight": [None, "balanced"]},
        {"model__C": [0.01, 0.03, 0.1, 0.3, 1.0, 3.0, 10.0],
         "model__l1_ratio": [0.5, 1], "model__solver": ["saga"],
         "model__max_iter": [5000],
         "model__class_weight": [None, "balanced"]},
    ],
    "forest": {
        "n_estimators": [100, 300, 500],
        "max_depth": [None, 8, 16],
        "min_samples_split": [2, 10],
        "max_features": ["sqrt", 0.5],
        "class_weight": [None, "balanced"],
    },
}


def apply_threshold(proba, classes, focus, threshold):
    """Flag `focus` when its probability reaches the threshold.

    Otherwise pick the likelier of the remaining classes. threshold=None means
    the model's own argmax, which is what v1 used.
    """
    classes = list(classes)
    if threshold is None:
        return np.array(classes)[proba.argmax(axis=1)]
    f = classes.index(focus)
    rest = [i for i in range(len(classes)) if i != f]
    best_rest = np.array(rest)[proba[:, rest].argmax(axis=1)]
    pick = np.where(proba[:, f] >= threshold, f, best_rest)
    return np.array(classes)[pick]


def focus_scores(y_true, y_pred, focus):
    return (
        recall_score(y_true, y_pred, labels=[focus], average="macro", zero_division=0),
        precision_score(y_true, y_pred, labels=[focus], average="macro", zero_division=0),
    )


def select_config(search, baseline_f1, tolerance):
    """Best CV Dropout recall among configurations whose macro F1 held up."""
    r = pd.DataFrame(search.cv_results_)
    ok = r[r["mean_test_f1"] >= baseline_f1 - tolerance]
    if ok.empty:  # cannot happen when the baseline is in the grid, but be safe
        ok = r
    return int(ok.sort_values(["mean_test_recall", "mean_test_f1"],
                              ascending=False).index[0])


def sweep_threshold(y_true, proba, classes, focus, floor):
    """Evaluate argmax plus a range of thresholds on out-of-fold probabilities."""
    rows = []
    for t in [None] + [round(x, 2) for x in np.arange(0.20, 0.71, 0.01)]:
        pred = apply_threshold(proba, classes, focus, t)
        recall, precision = focus_scores(y_true, pred, focus)
        rows.append({"threshold": t, "recall": recall, "precision": precision,
                     "macro_f1": f1_score(y_true, pred, average="macro", zero_division=0)})
    table = pd.DataFrame(rows)
    ok = table[table["precision"] >= floor]
    if ok.empty:
        return None, table
    best = ok.sort_values(["recall", "precision"], ascending=False).iloc[0]
    t = best["threshold"]
    return (None if pd.isna(t) else float(t)), table


def paired_bootstrap(y_true, pred_a, pred_b, focus, n=2000, seed=0):
    """95% interval for Dropout recall of b minus a, resampling test students."""
    y = np.asarray(y_true)
    a, b = np.asarray(pred_a), np.asarray(pred_b)
    idx = np.flatnonzero(y == focus)
    rng = np.random.default_rng(seed)
    diffs = []
    for _ in range(n):
        s = rng.choice(idx, size=len(idx), replace=True)
        diffs.append((b[s] == focus).mean() - (a[s] == focus).mean())
    return tuple(np.percentile(diffs, [2.5, 97.5]))


def main():
    params = yaml.safe_load(Path("params.yaml").read_text())
    cfg, tune = params["experiment"], params["tuning"]
    target, focus, rs = cfg["target_column"], cfg["focus_class"], cfg["random_state"]

    df = pd.read_csv(DATA)
    labels = sorted(df[target].unique())
    sets = feature_sets(df.columns)

    # The identical split run_experiments.py draws, so v1 and v2 are scored on
    # the same students.
    index_train, index_test = train_test_split(
        df.index, test_size=cfg["test_size"], random_state=rs,
        stratify=df[target] if cfg["stratify"] else None)
    y_train, y_test = df.loc[index_train, target], df.loc[index_test, target]

    cv = StratifiedKFold(n_splits=tune["cv_folds"], shuffle=True, random_state=rs)
    scoring = {
        "recall": make_scorer(recall_score, labels=[focus], average="macro", zero_division=0),
        "f1": "f1_macro",
    }

    mlflow.set_tracking_uri(os.environ.get("MLFLOW_TRACKING_URI", DEFAULT_TRACKING_URI))
    mlflow.set_experiment(EXPERIMENT)
    Path(MODEL_DIR).mkdir(exist_ok=True)

    results, sweeps = [], []
    for set_name in cfg["feature_sets"]:
        columns = sets[set_name]
        X_train, X_test = df.loc[index_train, columns], df.loc[index_test, columns]

        for model_name in params["models"]:
            run_name = f"{model_name}_{set_name}_{tune['run_version']}_tuned"
            print(f"\n== {run_name}")

            # Baseline: v1 defaults, same CV folds, same test students.
            base_est, prep = build_model(model_name, dict(params["models"][model_name]), rs)
            base_cv = cross_validate(base_est, X_train, y_train, cv=cv, scoring=scoring)
            base_recall, base_f1 = base_cv["test_recall"].mean(), base_cv["test_f1"].mean()
            base_est.fit(X_train, y_train)
            base_pred = base_est.predict(X_test)

            # Grid search; refit=False because the winner is chosen by the rule
            # above, not by a single score.
            template, _ = build_model(model_name, {}, rs)
            search = GridSearchCV(template, GRIDS[model_name], cv=cv, scoring=scoring,
                                  refit=False, n_jobs=1)
            search.fit(X_train, y_train)
            best_i = select_config(search, base_f1, tune["f1_tolerance"])
            best_params = search.cv_results_["params"][best_i]
            cv_recall = float(search.cv_results_["mean_test_recall"][best_i])
            cv_f1 = float(search.cv_results_["mean_test_f1"][best_i])
            print(f"  grid: {len(search.cv_results_['params'])} configs | CV Dropout recall "
                  f"{base_recall:.3f} -> {cv_recall:.3f} | CV macro F1 {base_f1:.3f} -> {cv_f1:.3f}")

            # Threshold from out-of-fold probabilities of the chosen config.
            est, _ = build_model(model_name, {}, rs)
            est.set_params(**best_params)
            oof = cross_val_predict(est, X_train, y_train, cv=cv, method="predict_proba")
            classes = sorted(y_train.unique())
            threshold, sweep = sweep_threshold(y_train, oof, classes, focus,
                                               tune["min_precision"])
            sweep.insert(0, "run", run_name)
            sweeps.append(sweep)
            print(f"  threshold: {'argmax (no change)' if threshold is None else threshold}")

            # The only look at the test set for this configuration.
            est.fit(X_train, y_train)
            proba_test = est.predict_proba(X_test)
            pred = apply_threshold(proba_test, est.classes_, focus, threshold)
            metrics = evaluate(y_test, pred, labels, focus)
            _, metrics["precision_focus"] = focus_scores(y_test, pred, focus)
            base_metrics = evaluate(y_test, base_pred, labels, focus)
            _, base_metrics["precision_focus"] = focus_scores(y_test, base_pred, focus)
            lo, hi = paired_bootstrap(y_test, base_pred, pred, focus)
            delta = metrics["recall_focus"] - base_metrics["recall_focus"]
            print(f"  test Dropout recall {base_metrics['recall_focus']:.3f} -> "
                  f"{metrics['recall_focus']:.3f}  (95% CI of change {lo:+.3f} to {hi:+.3f})")

            joblib.dump({"estimator": est, "threshold": threshold, "focus": focus},
                        f"{MODEL_DIR}/{model_name}_{set_name}.joblib")

            with mlflow.start_run(run_name=run_name):
                mlflow.log_params({
                    "tool": "python", "tuned": True, "model_type": model_name,
                    "feature_set": set_name, "n_features": len(columns),
                    "cv_folds": tune["cv_folds"], "grid_size": len(search.cv_results_["params"]),
                    "decision_threshold": "argmax" if threshold is None else threshold,
                    "selection_f1_tolerance": tune["f1_tolerance"],
                    "threshold_min_precision": tune["min_precision"],
                    **prep, **{f"hp_{k.split('__')[-1]}": v for k, v in best_params.items()},
                })
                mlflow.log_metrics({
                    **{f"test_{k}": v for k, v in metrics.items()},
                    **{f"baseline_test_{k}": v for k, v in base_metrics.items()},
                    "cv_recall_focus": cv_recall, "cv_f1_macro": cv_f1,
                    "baseline_cv_recall_focus": float(base_recall),
                    "baseline_cv_f1_macro": float(base_f1),
                    "delta_recall_focus": float(delta),
                    "delta_recall_focus_ci_low": float(lo),
                    "delta_recall_focus_ci_high": float(hi),
                })
                pd.DataFrame(search.cv_results_).to_csv("cv_results.csv", index=False)
                mlflow.log_artifact("cv_results.csv", artifact_path="tuning")
                os.remove("cv_results.csv")
                info = mlflow.sklearn.log_model(
                    est, name="model", skops_trusted_types=TRUSTED_TYPES.get(model_name, []))
                version = register(info.model_uri, run_name, model_name, set_name,
                                   len(columns), metrics, threshold)

            results.append({
                "run": run_name, "model": model_name, "feature_set": set_name,
                "version": version, "params": best_params, "threshold": threshold,
                "cv_recall": cv_recall, "cv_f1": cv_f1,
                "base_cv_recall": float(base_recall), "base_cv_f1": float(base_f1),
                "grid_size": len(search.cv_results_["params"]),
                "test": metrics, "base_test": base_metrics,
                "delta": float(delta), "ci": (float(lo), float(hi)),
            })

    write_outputs(results, pd.concat(sweeps), focus, tune)
    return 0


def register(model_uri, run_name, model_name, set_name, n_features, metrics, threshold):
    """Register as a new version, documented, without touching any alias."""
    try:
        registered = mlflow.register_model(model_uri=model_uri, name=REGISTERED_MODEL)
        client = mlflow.tracking.MlflowClient()
        rule = "argmax" if threshold is None else f"flag Dropout at P >= {threshold:.2f}"
        client.update_model_version(
            name=REGISTERED_MODEL, version=registered.version,
            description=(
                f"TUNED {model_name} on the {set_name} feature set ({n_features} features), "
                f"decision rule: {rule}. Test accuracy {metrics['accuracy']:.3f}, macro F1 "
                f"{metrics['f1_macro']:.3f}, Dropout recall {metrics['recall_focus']:.3f}. "
                f"Run {run_name}. The decision threshold is not stored in the MLflow model "
                f"itself; see tuned_model_threshold tag."))
        for key, value in (("tool", "python"), ("model_type", model_name),
                           ("feature_set", set_name), ("tuned", "true"),
                           ("tuned_model_threshold", "argmax" if threshold is None else threshold),
                           ("validation_status", "pending")):
            client.set_model_version_tag(REGISTERED_MODEL, registered.version, key, str(value))
        return int(registered.version)
    except Exception as error:  # noqa: BLE001 - the registry is optional
        print(f"  (registry unavailable, not versioned: {error})")
        return None


def write_outputs(results, sweeps, focus, tune):
    Path(RESULTS).parent.mkdir(exist_ok=True)
    summary = {}
    for r in results:
        summary[f"recall_focus.{r['run']}"] = round(r["test"]["recall_focus"], 4)
        summary[f"delta_recall_focus.{r['run']}"] = round(r["delta"], 4)
    Path(RESULTS).write_text(json.dumps(summary, indent=2) + "\n")
    sweeps.to_csv(SWEEP_CSV, index=False, float_format="%.4f")

    L = ["# Tuning report", "",
         f"Primary metric: recall on **{focus}**. Selection used {tune['cv_folds']}-fold "
         "stratified cross-validation on the training rows only; the test set was scored "
         "once per configuration, afterwards.", "",
         f"Rules: a configuration is eligible if its cross-validated macro F1 is within "
         f"{tune['f1_tolerance']} of the baseline's; the threshold must keep {focus} "
         f"precision at or above {tune['min_precision']} on out-of-fold predictions.", "",
         "## Cross-validated selection (training rows)", "",
         "| Model | Feature set | Grid size | Baseline CV recall | Tuned CV recall | "
         "Baseline CV macro F1 | Tuned CV macro F1 | Threshold |",
         "|---|---|---:|---:|---:|---:|---:|---:|"]
    for r in results:
        t = "argmax" if r["threshold"] is None else f"{r['threshold']:.2f}"
        L.append(f"| {r['model']} | {r['feature_set']} | {r['grid_size']} | "
                 f"{r['base_cv_recall']:.3f} | {r['cv_recall']:.3f} | "
                 f"{r['base_cv_f1']:.3f} | {r['cv_f1']:.3f} | {t} |")
    L += ["", "## Held-out test results (baseline v1 vs tuned)", "",
          "| Model | Feature set | Recall Dropout (v1) | Recall Dropout (tuned) | Change | "
          "95% CI of change | Precision Dropout (v1 -> tuned) | Accuracy (v1 -> tuned) | "
          "Macro F1 (v1 -> tuned) |", "|---|---|---:|---:|---:|---|---|---|---|"]
    for r in results:
        b, t = r["base_test"], r["test"]
        L.append(f"| {r['model']} | {r['feature_set']} | {b['recall_focus']:.3f} | "
                 f"{t['recall_focus']:.3f} | {r['delta']:+.3f} | "
                 f"{r['ci'][0]:+.3f} to {r['ci'][1]:+.3f} | "
                 f"{b['precision_focus']:.3f} -> {t['precision_focus']:.3f} | "
                 f"{b['accuracy']:.3f} -> {t['accuracy']:.3f} | "
                 f"{b['f1_macro']:.3f} -> {t['f1_macro']:.3f} |")
    L += ["", "## Chosen hyperparameters", "",
          "| Model | Feature set | Parameters |", "|---|---|---|"]
    for r in results:
        p = ", ".join(f"{k.split('__')[-1]}={v}" for k, v in r["params"].items())
        L.append(f"| {r['model']} | {r['feature_set']} | {p} |")
    Path(REPORT).write_text("\n".join(L) + "\n")
    print(f"\nWrote {REPORT}, {RESULTS}, {SWEEP_CSV}")


if __name__ == "__main__":
    sys.exit(main())
