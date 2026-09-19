# student-academic-risk-prediction

Group 7 Student Academic Risk Prediction MVP.

Code, parameters and metrics live in **Git**. Data, models and KNIME node
caches live in **DVC**, which keeps the big files out of Git and shares them
through a single remote.

## One-time setup

```bash
git clone https://github.com/colton-warren/student-academic-risk-prediction.git
cd student-academic-risk-prediction
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

Then add your own AWS keys for the DVC remote. Ask whoever set up the bucket
for your personal access key pair -- everyone gets their own, they are not
shared:

```bash
dvc remote modify --local storage access_key_id <your-access-key-id>
dvc remote modify --local storage secret_access_key <your-secret-access-key>
```

`--local` is not optional. It writes to `.dvc/config.local`, which is
gitignored; without it your keys land in `.dvc/config`, which is committed to a
**public** repo. Check with `git status --short` -- `.dvc/config.local` should
never appear there.

If you do commit a key, say so immediately. It has to be revoked in the AWS
console; deleting the line does not undo it. See
[docs/aws-s3-setup.md](docs/aws-s3-setup.md), which also covers creating the
bucket and IAM users in the first place.

## Everyday use

```bash
source .venv/bin/activate
dvc pull        # fetch data + models matching the current commit
dvc repro       # rerun any stage whose code, data or params changed
dvc push        # upload anything new you produced
```

Always `source .venv/bin/activate` first. The pipeline calls plain `python`, so
without the venv it will pick up the wrong interpreter and fail.

Commit the small files that `dvc repro` updates (`dvc.lock`, `metrics/`,
`reports/`) alongside your code changes, then `dvc push` so teammates can pull
the matching data.

## The pipeline

```
data/raw/student_data.csv
        |
        v
  clean  (src/clean_data.py)          -> data/processed/cleaned_student_data.csv
        |                                reports/cleaning_report.json
        v
  train  (src/train_multinomial_logistic_regression_model.py)
                                      -> models/multinomial_logistic_regression.joblib
                                         metrics/train_metrics.json
```

`dvc dag` draws it. `dvc metrics show` prints the current numbers.

Tune the experiment through `params.yaml` rather than by editing the scripts:

```bash
dvc exp run --set-param train.max_iter=2000
dvc exp show
```

### About the cleaning stage

`src/clean_data.py` is a Python port of the `Student_Risk_DataOps` KNIME
workflow, so the pipeline runs on machines without KNIME. It reproduces that
workflow's output **byte for byte**.

Worth knowing: the KNIME cleaning is currently a no-op. The Missing Value (#3)
node is set to `DoNothing` for every column type, and the dataset contains no
duplicate rows and no missing cells, so the processed CSV is identical to the
raw one. `reports/cleaning_report.json` records this on every run. If real
cleaning gets added, change it in both places, or drop the KNIME workflow and
keep the Python.

The KNIME workflow stays in Git as the source of truth for *what* the cleaning
does. Its node port caches are DVC-tracked (the `port_*.dvc` files) so they are
shareable without bloating Git.

## Experiment tracking

Metrics are written to `metrics/train_metrics.json` and tracked by DVC, so
`dvc metrics diff` works without any server.

MLflow logging is extra, and stays local: by default it writes to
`sqlite:///mlflow.db`, which only you can see. Comparing runs across the team
goes through DVC (`dvc metrics diff`, `dvc exp show`), not MLflow.

If the group later wants pooled MLflow runs, point everyone at one tracking
server by setting `MLFLOW_TRACKING_URI`; the training script already reads it.
Sharing the SQLite file is not an option -- see below.

Do not commit `mlflow.db`. It stores **absolute** artifact paths, so a database
created on one machine points at directories that do not exist on any other --
the copy previously committed here pointed at `C:\Users\...\mlruns` and crashed
on macOS and Linux. It is gitignored for that reason.

## What goes where

| Kind of file | Tracked by | Example |
|---|---|---|
| Code, params, pipeline | Git | `src/`, `params.yaml`, `dvc.yaml` |
| Metrics and reports | Git | `metrics/`, `reports/` |
| Pointers to data | Git | `*.dvc`, `dvc.lock` |
| Datasets and models | DVC | `data/`, `models/` |
| KNIME node caches | DVC | `Student_Risk_DataOps/**/port_*` |
| Credentials, local DBs | Neither | `.dvc/config.local`, `mlflow.db` |

Bucket and IAM setup lives in [docs/aws-s3-setup.md](docs/aws-s3-setup.md).
