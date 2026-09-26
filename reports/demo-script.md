# MVP demo script

Target **8 minutes** (limit is 5–10). Timings are generous; a first read-through
usually runs short.

Speakers are suggested from who wrote each section of the conceptual design —
swap freely. The assignment says everyone contributes but not everyone has to
talk.

**Have open before recording:** the KNIME workflow, a terminal in the repo with
the venv active, and MLflow at `http://127.0.0.1:5001`.

---

## 1. Problem and purpose — 1:00 — *Anisa*

> Universities lose students they could have kept. The warning signs exist in
> data they already hold — grades, attendance, whether tuition is paid — but
> they are scattered across departments, and nobody reviews them together early
> enough to act.
>
> We are building a system that flags students at risk of dropping out while
> there is still a semester left to help them. Three outcomes: dropout, still
> enrolled, or graduated. Our dataset is 4,424 undergraduates with 36 features
> covering demographics, finances and academic performance.
>
> The users are academic advisors, who have limited hours and need to know who
> to contact first.

**On screen:** title slide.

---

## 2. System diagram — 1:30 — *Sahin*

**On screen:** `Student_Risk_DataOps/workflow.svg`, then the README pipeline
diagram.

> Ingestion and preparation happen in KNIME. A CSV Reader pulls the raw file,
> then duplicate filtering, missing-value handling, type conversion and domain
> calculation. The prepared dataset is written out and versioned.
>
> One partitioning node produces a single stratified train/test split, and every
> model downstream shares it — so differences between results come from the
> model, not from a different set of students.
>
> Three column filters produce three feature sets, defined by *when* the
> university would actually have the data: at enrollment, after first semester,
> and the full year. Each feeds a logistic regression and a random forest. Six
> combinations, six scorers.
>
> Results go to MLflow. Deployment is not built — we have a design for an
> advisor-facing interface, which we will come back to.

---

## 3. Data pipeline — 2:00 — *Paul*

**On screen:** terminal.

> Code, parameters and metrics live in Git. Data and models live in DVC, backed
> by an S3 bucket, so the repository stays text-only and everyone pulls the same
> data.

Run: `dvc status -c`  → *"Cache and remote 'storage' are in sync."*

> Versioning is by content hash, so a result can always be traced to the exact
> data that produced it.

Run: `cat data/processed/cleaned_student_data.csv.dvc`

> Validation runs before anything trains.

Run: `dvc repro`  → *"Data and pipelines are up to date."*

> Nothing changed, so nothing re-ran. That is the point of a pipeline: it knows
> what each stage depends on, and only redoes what it has to.

Run: `python src/verify_prep.py`

> Here is the validation stage on its own. It checks the data against a
> contract — required columns and types, missing
> values, duplicates, unexpected categories, and drift in the outcome
> distribution. It also re-runs a Python port of the KNIME preparation and
> compares the result, which catches the workflow and the code drifting apart.
>
> This is not theoretical. It caught a real difference this week: the same
> workflow produces different line endings on Windows and macOS. The data was
> identical, so it now warns rather than failing — but it noticed.

---

## 4. Model development and experiment tracking — 2:30 — *Sirisha*

**On screen:** MLflow at `http://127.0.0.1:5001`.

> Twelve runs in one experiment. Six from KNIME, six from an independent Python
> implementation of the same design, on the same split.

*Add the `tool` column via the Columns button; sort by it.*

> Every run logs its hyperparameters, its metrics, the feature set, and the hash
> of the dataset version it used.
>
> Our primary metric is recall on the dropout class, because a false negative is
> a student who needed help and never got flagged.

*Open the Models tab.*

> Six registered model versions, each documented with its algorithm, feature set
> and scores. The best is tagged `champion`, and that alias resolves and loads —
> so a downstream system can request the current best model without knowing
> version numbers.

**The finding worth pausing on:**

> Dropout recall at enrollment is 0.63. After first-semester grades it is 0.80.
> With the full year it is 0.81.
>
> So a model that flags students in January gets essentially the same recall as
> one that waits until the year is over — and leaves an entire semester to
> intervene. That is the difference between a system that predicts dropout and
> one that prevents it.

---

## 5. Challenges and next steps — 1:30 — *Colton*

> Three honest problems.
>
> First, both implementations struggle with the "still enrolled" category, and
> our KNIME random forest never predicts it at all. The two algorithms agree
> closely on logistic regression, which gives us confidence in the pipeline, but
> the forest needs work — most likely our categorical encoding leaves it too
> many levels to split on.
>
> Second, these are single-split results. We have not cross-validated, so small
> differences between models should not be over-read.
>
> Third, this is one public dataset from one institution. Performance would need
> revalidating on real university data.
>
> Next: tune the forest, cross-validate, and build the advisor interface.

**On screen:** `docs/streamlit-proposal.md`.

> We designed it but did not build it. It takes an advisor's roster and returns
> a ranked list, with a threshold slider showing the trade-off between missing
> at-risk students and spending time on students who were never at risk.
> Ranking by probability rather than predicted class also works around the
> weakness we just described.

---

## 6. Close — 0:30

> To summarise: a versioned data pipeline with validation, two model families
> across three feature sets, twelve tracked experiments, six registered model
> versions — and a finding that changes the design, which is that we can predict
> early enough to matter.

---

## Notes

- **Show, don't narrate.** Let commands run and results appear; dead air while
  something executes is fine.
- **Don't hide the failures.** The random forest's Enrolled problem and the
  single-split caveat are worth more said plainly than glossed over.
- If a command misbehaves, keep going and mention it in next steps. A demo that
  admits a rough edge is better than a second take that hides one.
- **Disclosure:** the group used Claude Code for the pipeline infrastructure,
  the analysis that surfaced the timing finding, and drafting parts of the
  written documents. Say so, or include it on the closing slide.
