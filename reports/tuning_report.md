# Tuning report

Primary metric: recall on **Dropout**. Selection used 5-fold stratified cross-validation on the training rows only; the test set was scored once per configuration, afterwards.

Rules: a configuration is eligible if its cross-validated macro F1 is within 0.02 of the baseline's; the threshold must keep Dropout precision at or above 0.7 on out-of-fold predictions.

## Cross-validated selection (training rows)

| Model | Feature set | Grid size | Baseline CV recall | Tuned CV recall | Baseline CV macro F1 | Tuned CV macro F1 | Threshold |
|---|---|---:|---:|---:|---:|---:|---:|
| logreg | enrollment_only | 42 | 0.552 | 0.552 | 0.477 | 0.478 | 0.45 |
| forest | enrollment_only | 72 | 0.623 | 0.646 | 0.521 | 0.562 | 0.43 |
| logreg | through_sem1 | 42 | 0.748 | 0.753 | 0.616 | 0.617 | 0.31 |
| forest | through_sem1 | 72 | 0.751 | 0.759 | 0.649 | 0.646 | 0.31 |
| logreg | all_features | 42 | 0.767 | 0.769 | 0.676 | 0.676 | 0.27 |
| forest | all_features | 72 | 0.764 | 0.773 | 0.684 | 0.686 | 0.28 |

## Held-out test results (baseline v1 vs tuned)

| Model | Feature set | Recall Dropout (v1) | Recall Dropout (tuned) | Change | 95% CI of change | Precision Dropout (v1 -> tuned) | Accuracy (v1 -> tuned) | Macro F1 (v1 -> tuned) |
|---|---|---:|---:|---:|---|---|---|---|
| logreg | enrollment_only | 0.588 | 0.493 | -0.095 | -0.130 to -0.063 | 0.655 -> 0.704 | 0.625 -> 0.610 | 0.473 -> 0.471 |
| forest | enrollment_only | 0.616 | 0.560 | -0.056 | -0.085 to -0.028 | 0.639 -> 0.688 | 0.627 -> 0.610 | 0.519 -> 0.554 |
| logreg | through_sem1 | 0.746 | 0.813 | +0.067 | +0.039 to +0.095 | 0.752 -> 0.709 | 0.734 -> 0.734 | 0.612 -> 0.583 |
| forest | through_sem1 | 0.725 | 0.810 | +0.085 | +0.053 to +0.123 | 0.741 -> 0.682 | 0.729 -> 0.724 | 0.614 -> 0.578 |
| logreg | all_features | 0.768 | 0.845 | +0.077 | +0.049 to +0.109 | 0.793 -> 0.688 | 0.768 -> 0.751 | 0.683 -> 0.622 |
| forest | all_features | 0.732 | 0.835 | +0.102 | +0.067 to +0.141 | 0.819 -> 0.691 | 0.765 -> 0.748 | 0.687 -> 0.618 |

## Chosen hyperparameters

| Model | Feature set | Parameters |
|---|---|---|
| logreg | enrollment_only | C=3.0, class_weight=None, l1_ratio=0, solver=lbfgs |
| forest | enrollment_only | class_weight=balanced, max_depth=None, max_features=sqrt, min_samples_split=2, n_estimators=500 |
| logreg | through_sem1 | C=0.3, class_weight=None, l1_ratio=1, max_iter=5000, solver=saga |
| forest | through_sem1 | class_weight=None, max_depth=None, max_features=sqrt, min_samples_split=10, n_estimators=100 |
| logreg | all_features | C=10.0, class_weight=None, l1_ratio=0, solver=lbfgs |
| forest | all_features | class_weight=None, max_depth=16, max_features=sqrt, min_samples_split=10, n_estimators=100 |
