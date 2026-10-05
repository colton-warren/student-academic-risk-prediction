# student-academic-risk-prediction

Group 7 Student Academic Risk Prediction MVP.

Colton Warren, Paul Thaden, Anisa Longe, Sahin Lokman, Sirisha Brandenburg

## Overview of the Problem & Purpose 

Colleges and universities often have information that may indicate when a student is beginning to struggle. Examples can include academic performance, attendance-related information, financial circumstances, and other student characteristics.

The challenge is that these warning signs may exist in different systems and may not be reviewed together early enough to support a student before the student drops out or experiences a serious academic setback.

The **Student Academic Risk Prediction** project is a machine learning MVP, or **minimum viable product**, designed to explore whether historical student data can be used to identify patterns associated with three student outcomes:

1*Dropout**
2**Enrolled**
3*Graduate**

This project is a prototype. No FERPA or PII was used to build this prototype. 

# Project Objective

The primary objective is to build and compare machine learning models that can classify a student's academic outcome using information available in the dataset.

The project focuses on two machine learning models:

1. **Multinomial Logistic Regression**
2. **Random Forest**

These models were selected because they provide two useful perspectives.

### Multinomial Logistic Regression

Multinomial Logistic Regression provides an interpretable baseline model. 

### Random Forest

Random Forest can work well with datasets that contain many different types of variables and complex relationships. 

Using both models allows the project team to compare predictive performance with interpretability.

The models allow the project to study those patterns across historical data and compare how different combinations of features relate to the three target outcomes.

## Data Location
Code, parameters and metrics live in **Git**. Data, models and KNIME node
caches live in **DVC**, which keeps the big files out of Git and shares them
through a single remote.

## Before you start

Install these first. The versions matter less than having them at all, except
where noted.

| | Why | Notes |
|---|---|---|
| **Git** | Everything else assumes it | Windows: install *Git for Windows*, which also gives you Git Bash |
| **Python 3.11 or newer** | Runs the pipeline | On Windows, tick **"Add Python to PATH"** in the installer. Getting this wrong is the most common setup failure |
| **KNIME Analytics Platform** | Data preparation and modelling | Only needed if you are working on the workflow |

You also need two things from a teammate:

1. **Push access to the GitHub repo** — ask Colton, who owns it. You can read it
   without access, but not push.
2. **Your own AWS access key pair** — ask Paul. Everyone gets their own; they
   are never shared. Without it `dvc pull` cannot fetch any data.

## One-time setup

Run these once, in the folder where you keep projects.

**macOS / Linux**

```bash
git clone https://github.com/colton-warren/student-academic-risk-prediction.git
cd student-academic-risk-prediction
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
git config core.hooksPath .githooks
```

**Windows** (PowerShell or Command Prompt)

```
git clone https://github.com/colton-warren/student-academic-risk-prediction.git
cd student-academic-risk-prediction
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
git config core.hooksPath .githooks
```

If you use **Git Bash** on Windows, the activate line is
`source .venv/Scripts/activate` instead.

That last command turns on a pre-commit hook that refuses to commit AWS keys.
Git does not share hooks automatically, so **everyone has to run it in their own
clone**. It is one command and it is the thing standing between a typo and a
leaked key on a public repo.

### Add your AWS keys

```bash
dvc remote modify --local storage access_key_id <your-access-key-id>
dvc remote modify --local storage secret_access_key <your-secret-access-key>
```

`--local` is not optional. It writes to `.dvc/config.local`, which is
gitignored; without it your keys land in `.dvc/config`, which is committed to a
**public** repo. If you do commit a key, say so immediately — it has to be
revoked in the AWS console, and deleting the line does not undo it.

### Check it worked

```bash
dvc pull
dvc status
```

You are set up correctly when `dvc pull` downloads files without an error and
`dvc status` prints *"Data and pipelines are up to date."* You should also now
see real data in `data/raw/` and `data/processed/` — before `dvc pull` those
folders only contain small `.dvc` pointer files.

If something failed, see [docs/troubleshooting.md](docs/troubleshooting.md).

## Working on the KNIME workflow

Git tracks the workflow's **structure** — `workflow.knime`, each node's
`settings.xml`, and `workflow.svg`. It does not track node results: the port
data, node internals and the trained-model blobs under `filestore/` are
regenerated every time the workflow executes, with new filenames each run, so
Git cannot diff them and simply stores a fresh copy. Three commits of that took
the repo from 17 MB to 60 MB.

So after pulling a workflow change, **open it in KNIME and Execute All**. Your
nodes will start grey rather than green, and executing takes seconds.

Two things worth knowing:

- **KNIME writes node data to disk only when you save**, not when you execute.
  Execute, then save, or your work never reaches Git.
- To share a workflow *with* its results — for a demo, say — export it with
  File → Export KNIME Workflow, tick *include data*, and DVC-track the `.knwf`.
  One file, versioned properly, instead of hundreds of churning caches.

## Everyday use

**Activate the virtual environment first, every time.** Nothing below works
without it, and forgetting is the single most common cause of confusing errors.

```bash
source .venv/bin/activate      # Windows: .venv\Scripts\activate
```

### Starting work

Two commands, and you need both. Git brings the code; DVC brings the data those
commits refer to.

```bash
git pull
dvc pull
```

`git pull` on its own leaves you with new code and old data, which usually looks
like the pipeline behaving strangely rather than an obvious error.

### Finishing work

```bash
dvc repro                      # rerun whatever your change affected
git add -A
git commit -m "what you changed and why"
dvc push                       # upload data and models FIRST
git push                       # then the code that points at them
```

**Push DVC before Git.** If the code lands on GitHub before the data reaches S3,
a teammate can pull a commit whose data does not exist yet, and their `dvc pull`
fails for reasons that have nothing to do with anything they did.

Commit the small files `dvc repro` updates — `dvc.lock`, `metrics/`, `reports/`
— alongside your code changes. They are how teammates see what your run produced
without having to rerun it.

## The pipeline

Data preparation happens in **KNIME**, which is a desktop application and cannot
be driven by `dvc repro`. So the prepared CSV is tracked as an *input* rather
than generated by the pipeline, and the pipeline's first job is to check it.

```
KNIME workflow (run by hand)
        |
        v
data/processed/cleaned_student_data.csv   <- dvc add
        |
        v
  verify_prep    contract checks + drift check   -> reports/prep_verification.json
        |
        v
  experiments    every model x every feature set -> models/
                                                    metrics/experiment_results.json
                                                    reports/experiment_comparison.md
```

After re-running the KNIME workflow:

```bash
dvc add data/processed/cleaned_student_data.csv
dvc repro
dvc push
```

`dvc dag` draws it. `dvc metrics show` prints the headline numbers, and
`reports/experiment_comparison.md` has the full table and confusion matrices.

### verify_prep

KNIME's output is produced by a human on a desktop, so the pipeline checks it
instead of trusting it. Two kinds of check, and either one failing stops
`dvc repro`:

- **Contract checks** against `data_contract.yaml` -- the validation Section 5
  of the proposal promises: required columns and types, missing values,
  duplicates, unexpected target categories, values outside known ranges, and
  drift in the target distribution.
- **A reproduction check.** `src/clean_data.py` is a Python port of the KNIME
  workflow, so re-running it on the raw data should reproduce the prepared file
  byte for byte. A mismatch means the workflow and the port have diverged --
  normally because someone edited the KNIME nodes without updating the port.

Out-of-range values are a warning, not a failure: the contract records what was
normal in the reference data, and genuinely new data may exceed it.

### experiments

Two models against three feature sets, nine runs' worth of questions answered
in six. Every run shares one stratified train/test split, drawn once and reused,
so differences come from the model and the feature set rather than the luck of
the split.

The feature sets are grouped by **when the information becomes available**:

| Feature set | Features | What it assumes you know |
|---|---:|---|
| `enrollment_only` | 24 | Only what is on file at admission |
| `through_sem1` | 30 | Plus first-semester results |
| `all_features` | 36 | Plus second-semester results |

That axis is the point. Second-semester results are the strongest predictors in
this dataset, but a model that needs them cannot raise the alarm until the year
is effectively over -- which is too late for the intervention the project is
built around.

Building the same comparison in KNIME? See
[docs/knime-modelling-guide.md](docs/knime-modelling-guide.md) -- node by node.
Its Scorer results reach MLflow through a CSV Writer on each Scorer plus
`python src/log_knime_runs.py`, which needs no KNIME extensions. Both sets of
runs land in one experiment, tagged `tool=KNIME` and `tool=python`, so the two
implementations can be compared directly.

Tune through `params.yaml` rather than by editing the scripts:

```bash
dvc exp run --set-param models.forest.n_estimators=800
dvc exp show
```

## Experiment tracking

Every run is logged to MLflow with the metadata the conceptual design calls
for: run name, feature set, preprocessing steps, dataset version and the
model's hyperparameters. The dataset version is the md5 DVC uses, so any result
can be traced back to the exact data that produced it.

MLflow writes to a local `sqlite:///mlflow.db` that only you can see. Comparing
runs across the team goes through DVC (`dvc metrics diff`, `dvc exp show`). If
the group later wants pooled MLflow runs, set `MLFLOW_TRACKING_URI` to a shared
server; the scripts already read it.

Do not commit `mlflow.db`. It stores **absolute** artifact paths, so a database
created on one machine points at directories that do not exist on any other --
the copy previously committed here pointed at `C:\Users\...\mlruns` and crashed
on macOS and Linux. It is gitignored for that reason.

## Local Prediction Application

The project includes a local prediction application for academic-risk assessment.

The application uses three services:

```text
MLflow Model Registry
        |
        v
FastAPI Prediction API
        |
        v
Streamlit User Interface
```

- MLflow stores experiment runs and registered model versions.
- FastAPI loads the deployed MLflow model and exposes prediction endpoints.
- Streamlit provides an advisor-facing user interface for batch and single-student predictions.

The deployed API uses the registered MLflow model:
student-risk-classifier

with the alias:
early-intervention

This alias should point to the selected Logistic Regression through-semester-1 model.
Application Features
The Streamlit interface supports:
- downloading an Excel prediction template;
- uploading an Excel file containing multiple students;
- generating predictions for all students in the file;
- displaying Dropout, Enrolled, and Graduate probabilities;
- sorting students by dropout probability;
- highlighting students above a configurable dropout-risk threshold;
- downloading prediction results as Excel;
- generating predictions for a single student;
- using readable dropdowns instead of numeric category codes; and
- displaying the active MLflow model version and feature set.

### Running the Local Application

Run all commands from the root of the repository.

You will normally need three terminal windows:

Terminal 1 -> MLflow    -> port 5000
Terminal 2 -> FastAPI   -> port 8000
Terminal 3 -> Streamlit -> port 8501

#### 1. Activate the Python Virtual Environment
##### Windows PowerShell
```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.venv\Scripts\Activate.ps1
```

The execution-policy command is only needed if PowerShell blocks the virtual-environment activation script.
##### macOS / Linux
```bash
source .venv/bin/activate
```

Install or update dependencies if necessary:
```bash
pip install -r requirements.txt
```

#### 2. Start MLflow
In the first terminal:
```powershell
mlflow server --backend-store-uri sqlite:///mlflow.db --host 127.0.0.1 --port 5000
```

Open the MLflow interface in a browser:
http://127.0.0.1:5000

Leave this terminal running.
Each developer has a local mlflow.db. This file should not be committed to Git.
If the local MLflow instance does not yet contain the project experiments and registered models, open another terminal, activate the virtual environment, and run the experiments.

##### Windows PowerShell
```powershell
$env:MLFLOW_TRACKING_URI="http://127.0.0.1:5000"
python src/run_experiments.py
```

##### macOS / Linux
```bash
export MLFLOW_TRACKING_URI=http://127.0.0.1:5000
python src/run_experiments.py
```

After the experiments complete, verify in MLflow that the registered model exists:
```text
student-risk-classifier
```

The model used by the API should have the alias:
```text
early-intervention
```

#### 3. Start the FastAPI Prediction Service
Open a second terminal and activate the virtual environment.
Set the MLflow tracking URI.

##### Windows PowerShell
```powershell
$env:MLFLOW_TRACKING_URI="http://127.0.0.1:5000"
```

##### macOS / Linux
```bash
export MLFLOW_TRACKING_URI=http://127.0.0.1:5000
```

Start FastAPI:
```bash
python -m uvicorn src.api:app --reload --host 127.0.0.1 --port 8000
```

The API is available at:
http://127.0.0.1:8000

Interactive API documentation is available at:
http://127.0.0.1:8000/docs

Useful endpoints include:
| Endpoint | Purpose |
|---|---|
| `GET /health` | Confirms the API is running |
| `GET /model-info` | Displays the deployed model and feature set |
| `GET /template` | Downloads the Excel prediction template |
| `POST /predict` | Generates a prediction for one student |
| `POST /predict-file` | Generates predictions for an uploaded Excel file |


A response of:
{"detail":"Not Found"}

at:
http://127.0.0.1:8000/

does not necessarily indicate an error. Use /health, /model-info, or /docs instead.
Leave this terminal running.

#### 4. Start the Streamlit User Interface
Open a third terminal and activate the virtual environment.
From the repository root, run:
```bash
python -m streamlit run ui/app.py
```

Streamlit should open automatically in the browser.
If it does not, open:
http://localhost:8501

Batch Predictions
The Batch Predictions tab allows a user to:
1. download the Excel input template;
2. enter one student per row;
3. upload the completed .xlsx file;
4. run predictions for all students;
5. view students ranked by dropout probability;
6. identify students above the selected risk threshold; and
7. download the prediction results.
Student ID is included in the template for identification purposes but is not used as a model feature.

The prediction output includes:
Student ID
Predicted Outcome
Probability Dropout
Probability Enrolled
Probability Graduate
Model Version
Model Alias
Feature Set

#### Single-Student Prediction
The Single Student tab allows a user to manually enter information for one student.

Fields are grouped into:
- Demographics
- Application & Academic Background
- Financial & Student Support
- Family Background
- Economic Environment
- First-Semester Performance

Categorical variables use readable dropdown options instead of the raw numeric category codes used by the dataset.

The Streamlit application converts the selected labels back into the numeric codes expected by the model before sending the request to FastAPI.

The result displays:
- predicted academic outcome;
- dropout probability;
- enrolled probability;
- graduate probability; and
- a dropout-risk indicator.

Predictions are intended to support human review and intervention planning and should not be treated as automatic academic decisions.

Required Python Packages for the Prediction Application

Make sure the following packages are included in requirements.txt:
fastapi
uvicorn[standard]
streamlit
requests
python-multipart
openpyxl

Then install them with:
pip install -r requirements.txt

Stopping the Application
Each local service can be stopped by returning to its terminal and pressing:
Ctrl + C

Troubleshooting
PowerShell will not activate .venv
Run:
```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.venv\Scripts\Activate.ps1
```

##### FastAPI cannot find the model
Confirm that:
1. MLflow is running at:
http://127.0.0.1:5000

2. MLFLOW_TRACKING_URI is set in the FastAPI terminal.
3. The registered model exists:
student-risk-classifier

4. The model has the alias:
early-intervention

##### FastAPI returns HTTP 422
The submitted student data is missing one or more features required by the deployed model.
Check the required features at:
http://127.0.0.1:8000/model-info

or download a new template from:
http://127.0.0.1:8000/template

##### Streamlit cannot connect to FastAPI
Verify that FastAPI is still running by opening:
http://127.0.0.1:8000/health

##### Streamlit cannot import category_mappings
The files should be structured like this:
student-academic-risk-prediction/
|
|-- src/
|   |-- api.py
|
|-- ui/
|   |-- app.py
|   |-- category_mappings.py
|
|-- requirements.txt
|-- data_contract.yaml

Inside ui/app.py, use:
```python
from category_mappings import CATEGORY_OPTIONS
```

Application Architecture
                     MODEL DEVELOPMENT

        KNIME Experiments        Python Experiments
                |                       |
                +----------+------------+
                           |
                           v
                        MLflow
                 Experiment Tracking
                  + Model Registry
                           |
                           v
             student-risk-classifier
               @ early-intervention
                           |
                           v

                     MODEL SERVING

                     FastAPI API
                  http://127.0.0.1:8000
                           |
                 +---------+---------+
                 |                   |
                 v                   v
          Single Prediction    Batch Prediction
                 |                   |
                 +---------+---------+
                           |
                           v

                    Streamlit UI
                 http://localhost:8501

## What goes where

| Kind of file | Tracked by | Example |
|---|---|---|
| Code, params, pipeline | Git | `src/`, `params.yaml`, `dvc.yaml` |
| Data contract | Git | `data_contract.yaml` |
| Metrics and reports | Git | `metrics/`, `reports/` |
| KNIME workflow | Git | `Student_Risk_DataOps/` |
| Pointers to data | Git | `*.dvc`, `dvc.lock` |
| Datasets and models | DVC | `data/`, `models/` |
| KNIME node caches | Neither | regenerated by Execute All |
| Credentials, local DBs | Neither | `.dvc/config.local`, `mlflow.db` |
| Prediction API | Git | `src/api.py` |
| Streamlit UI | Git | `ui/` |

## Documentation

| Guide | When you need it |
|---|---|
| [docs/troubleshooting.md](docs/troubleshooting.md) | Something broke. Start here |
| [docs/aws-s3-setup.md](docs/aws-s3-setup.md) | Getting S3 access, or adding a teammate |
| [docs/knime-modelling-guide.md](docs/knime-modelling-guide.md) | Building the model comparison in the KNIME GUI |
| [docs/streamlit-proposal.md](docs/streamlit-proposal.md) | Original design notes for the advisor-facing Streamlit interface |

## The pre-commit hook

`.githooks/pre-commit` blocks a commit when the staged changes contain an AWS
access key ID, a secret-looking credential value, uncommented credentials in
`.dvc/config`, or `.dvc/config.local` itself. It reads only what is staged, so
it does not care what is loose in your working tree.

It is a safety net, not a guarantee. It catches the common accident -- running
`dvc remote modify` without `--local` -- and it cannot catch everything.

If it stops you on something genuinely harmless, put `pragma: allowlist secret`
on that line. Reach for `git commit --no-verify` only when you are certain;
if you need it in order to commit a real credential, the credential is in the
wrong file.

## Local MacBook Pro machine reproduction and Review: 

I reproduced the project locally on an Intel Mac using GitHub Desktop, KNIME Analytics Platform 5.12.0, and Python 3.12.10.

## Work Completed

Set up the local repository through GitHub Desktop and retrieved the DVC-tracked project files using dvc pull.

Worked through local KNIME setup issues involving dataset paths, CSV reading, and the Domain Calculator node.

Ran the data preparation verification and reviewed the resulting dataset checks.

Reviewed twelve MLflow runs: six KNIME runs and six Python runs, comparing the two models across the three feature sets.

Reviewed registered model versions and the champion alias.

Reviewed the changes associated with Issue #3, submitted my review comment, and manually closed the issue after Anisa's pull request was merged.

## Local Data Verification Results: 

The prepared dataset verification reported: 

### Local Data Verification Results

| Check | Result |
| --- | --- |
| Rows | 4,424 |
| Columns, including the target | 37 |
| Missing values | 0 |
| Duplicate rows | 0 |
| Graduate proportion | 49.93% |
| Dropout proportion | 32.12% |
| Enrolled proportion | 17.95% |


These results document my local reproduction check. They provide an additional team-member verification of the prepared dataset used for the model comparisons.

