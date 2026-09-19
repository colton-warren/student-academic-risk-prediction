# Building the model comparison in KNIME

For the team members who work in the KNIME GUI. No Python knowledge needed --
there is exactly one Python node at the end, and it is copy-paste.

A caveat up front: node dialogs move between KNIME versions, and this guide was
written without a KNIME install to check against. Node *names* are stable; if a
setting sits under a different tab than described, it is almost certainly still
there under the same label.

## What you are building

```
   CSV Reader -> Duplicate Row Filter -> Missing Value        (already built)
                             |
                      Partitioning          <- ONE split, shared by everything
                       |          |
                    train        test
                       |          |
        +--------------+----------+--------------+
        |                         |              |
  enrollment_only           through_sem1     all_features     <- 3 branches
        |                         |              |
   (each branch trains BOTH a logistic regression and a random forest)
        |                         |              |
        +--------------+----------+--------------+
                       |
                  Concatenate            <- stack all 6 results
                       |
                 Python Script           <- logs the 6 runs to MLflow
```

Six results: two models times three feature sets.

## The one rule that matters

**Every branch must train and test on the same students.**

That is why `Partitioning` sits above the branches instead of inside them. If
each branch splits its own data, the six results are measured on six different
test sets, and comparing them tells you nothing -- the numbers will still look
perfectly reasonable, which is what makes this mistake expensive.

Same reason the seed must be set explicitly. Without it, the workflow will not
reproduce its own results, and reproducibility is a design principle the
proposal commits to in Section 6.

## Step 1: Partitioning

Add a **Partitioning** node after `Missing Value`. In its dialog:

| Setting | Value | Why |
|---|---|---|
| Relative | `80` % | 80/20 train/test |
| Sampling method | **Stratified sampling** on `target` | Classes are uneven (about 50/32/18). Without this the test set's class mix drifts and moves your metrics on its own |
| Use random seed | **checked**, `42` | Unchecked means a different split every execution and results nobody can reproduce |

Top output is training data, bottom is test data.

## Step 2: Build ONE branch first

Do not build all six and then debug. Build one, confirm it runs, then copy it.

For the `through_sem1` branch:

1. **Column Filter** on the *training* table. Use the wildcard/regex option and
   exclude `*2nd sem*`. That leaves 30 features plus `target`.
2. **Column Filter** on the *test* table, configured identically. Both sides
   must see the same columns.
3. **Logistic Regression Learner** -- set target column to `target`.
4. **Logistic Regression Predictor** -- takes the model from the learner and
   the filtered test table.
5. **Scorer** -- first column `target`, second the prediction column
   (usually `Prediction (target)`).

Execute and open the Scorer. You get the confusion matrix and per-class
statistics in the GUI. That view is the point of doing this in KNIME.

Then add the random forest to the same branch, off the same two filtered tables:

6. **Random Forest Learner** -- target `target`, number of models `300`, and
   **set the seed** (there is a seed field; set it rather than leaving it random).
7. **Random Forest Predictor** -> **Scorer**.

## Step 3: Tag each result so you can tell them apart

The Scorer's **second output port** ("accuracy statistics") is the table to
keep. It has one row per class with `Recall`, `Precision`, `F-measure`, and a
row carrying overall `Accuracy`.

After each Scorer, add two **Constant Value Column** nodes:

- one adding a string column `model`, value `logreg` or `forest`
- one adding a string column `feature_set`, value `enrollment_only`,
  `through_sem1` or `all_features`

Without these tags, six stacked tables are indistinguishable.

## Step 4: Copy the branch

Select the whole branch, copy, paste, and change:

- the Column Filter wildcards
- the `feature_set` constant value

| Branch | Column Filter excludes | Features |
|---|---|---:|
| `enrollment_only` | `*sem*` | 24 |
| `through_sem1` | `*2nd sem*` | 30 |
| `all_features` | nothing (no filter needed) | 36 |

The `*sem*` wildcard is safe -- the only columns containing "sem" are the
twelve `Curricular units ... sem ...` columns.

Consider wrapping each branch in a **Component** (select nodes, right-click,
"Create Component"). Three labelled boxes read better than forty loose nodes,
and keeping the canvas legible is the reason for building this in KNIME.

## Step 5: Stack the results

Feed all six tagged tables into **Concatenate** nodes. Concatenate takes two
inputs by default; either chain them or add ports via the dialog.

## Step 6: The Python node

Add a **Python Script** node after the final Concatenate. One input table, no
output table needed (or pass the table through, harmless either way).

This is the only Python in the workflow. Paste it and change the two settings
at the top.

```python
# Logs each row of the incoming table to MLflow as one experiment run.
# You should only ever need to edit TRACKING_DB and RUN_VERSION.

import knime.scripting.io as knio
import mlflow

# Absolute path to the MLflow database, because KNIME's working directory is
# not the project folder. Use forward slashes, even on Windows.
TRACKING_DB = "C:/path/to/student-academic-risk-prediction/mlflow.db"

# Bump this when you rerun after changing something, so runs stay comparable:
# v1, v2, v3 ...
RUN_VERSION = "v1"
EXPERIMENT = "Student Academic Risk Prediction"

results = knio.input_tables[0].to_pandas()

# The Scorer's column names vary a little between KNIME versions, so find them
# case-insensitively rather than assuming. If this raises, print list(results)
# and check what your Scorer actually produced.
def column(name):
    for candidate in results.columns:
        if candidate.strip().lower() == name.lower():
            return candidate
    raise KeyError(f"no column like {name!r}; table has: {list(results.columns)}")

class_column = results.columns[0]      # the per-class row label
recall_column = column("Recall")
accuracy_column = column("Accuracy")

mlflow.set_tracking_uri(f"sqlite:///{TRACKING_DB}")
mlflow.set_experiment(EXPERIMENT)

for (model, feature_set), group in results.groupby(["model", "feature_set"]):
    dropout = group[group[class_column].astype(str).str.strip() == "Dropout"]
    accuracy = group[accuracy_column].dropna()

    with mlflow.start_run(run_name=f"knime_{model}_{feature_set}_{RUN_VERSION}"):
        mlflow.log_params({
            "model_type": model,
            "feature_set": feature_set,
            "tool": "KNIME",
            "split": "80/20 stratified, seed 42",
        })
        metrics = {}
        if not accuracy.empty:
            metrics["accuracy"] = float(accuracy.iloc[0])
        if not dropout.empty:
            metrics["recall_dropout"] = float(dropout[recall_column].iloc[0])
        mlflow.log_metrics(metrics)
        print(f"logged knime_{model}_{feature_set}_{RUN_VERSION}: {metrics}")

knio.output_tables[0] = knio.Table.from_pandas(results)
```

**Before this runs**, KNIME's Python integration needs an environment with
`mlflow` installed: *File -> Preferences -> KNIME -> Python*. If the node errors
with `ModuleNotFoundError: No module named 'mlflow'`, that preference is
pointing at an environment without it. This is the step most likely to eat an
evening, so test it with a one-line script (`import mlflow`) before building
everything else.

## Checking you got it right

Open `reports/experiment_comparison.md` in the repo. It has the same six
combinations produced by the Python pipeline:

| Feature set | logreg accuracy | forest accuracy |
|---|---:|---:|
| enrollment_only | 0.625 | 0.627 |
| through_sem1 | 0.734 | 0.729 |
| all_features | 0.768 | 0.765 |

**Your KNIME numbers will not match these exactly, and that is expected.**
KNIME's learners use different defaults and implementations than scikit-learn's.
Landing within a few points is a good sign. Landing wildly off -- say
`all_features` scoring worse than `enrollment_only` -- means something is
misconfigured, most likely the split or a Column Filter applied to only one of
the train/test tables.

The shape should hold regardless of tool: accuracy rises as you add semester
data, and every model is poor at `Enrolled`.

## Committing your work

KNIME's node port caches are DVC-tracked, not Git-tracked, so after changing
the workflow:

```bash
dvc add "Student_Risk_DataOps/CSV Reader (#1)/port_1"   # and any other changed port dirs
git add Student_Risk_DataOps
git commit -m "Add model comparison branches to the KNIME workflow"
dvc push
```

Git records the workflow structure; DVC carries the data. Note that Git cannot
show a meaningful diff of a KNIME workflow -- the settings are XML blobs -- so
write commit messages that say what changed and why, since nobody can read it
from the diff.
