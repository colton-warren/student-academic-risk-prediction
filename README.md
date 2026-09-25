# student-academic-risk-prediction

Group 7 Student Academic Risk Prediction MVP.

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

## Documentation

| Guide | When you need it |
|---|---|
| [docs/troubleshooting.md](docs/troubleshooting.md) | Something broke. Start here |
| [docs/aws-s3-setup.md](docs/aws-s3-setup.md) | Getting S3 access, or adding a teammate |
| [docs/knime-modelling-guide.md](docs/knime-modelling-guide.md) | Building the model comparison in the KNIME GUI |
| [docs/streamlit-proposal.md](docs/streamlit-proposal.md) | Design proposal for an advisor-facing interface (not built) |

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

