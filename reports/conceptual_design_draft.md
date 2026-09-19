# Conceptual Design: Experiment Tracking

BANA 7075 – Machine Learning Systems Design
Group 7: Anisa Longe, Colton Warren, Sahin Lokman, Paul Thaden, Sirisha Brandenburg

## Experiment Objectives

The purpose of the project is to harness the power of AI to build an ML system
for early intervention, identifying and predicting university student dropouts
using three classifications (dropout, remained enrolled, or graduate). Our
experiments are designed to determine which modeling approach best supports
that goal. Our first objective is to compare a multinomial logistic regression
model against a random forest classifier, since logistic regression offers interpretable
coefficients that build advisor trust while random forest handles the mixed
variable types in our dataset and produces feature importance scores. Our
second objective addresses a constraint we identified while preparing the data.
The strongest predictors in the dataset are the second-semester curricular
unit variables, but those values do not exist until the academic year is
nearly complete, which is too late for the intervention our system is designed
to enable. We therefore treat the timing of available information as an
experimental variable rather than an assumption. Each model is trained against
three feature sets defined by when the institution would actually possess the
data: enrollment-only (24 features available at admission), through-semester-1
(30 features), and all features (36). This produces a six-run grid of two
models against three feature sets, and it lets us quantify what predictive
performance we give up in exchange for being able to act in time. Within each
of these six configurations we will also tune the hyperparameters listed below,
to establish how much of any difference between models is attributable to
configuration rather than to the algorithm itself.

## Key Components to Track

Every run is logged to MLflow, which records the parameters, metrics, and
artifacts for each experiment so that results can be reproduced and compared.
Run names follow the convention `{model}_{feature_set}_{trial}`, for example
`Logistic_Semester1_v1` or `RandomForest_EnrollmentOnly_v2`, with the trial
suffix incremented for each run and the run description recording what changed
relative to the previous trial. The group expects a minimum of two experiment
trials per configuration before building the MVP. For training data we log the dataset
version as the MD5 hash tracked by DVC, which ties every result to the exact
file that produced it, along with the feature set used, the preprocessing
applied, and the date of the experiment. Our preparation is deliberately conservative: the KNIME workflow reads
the raw file, removes duplicate rows, and applies a missing-value policy, and
we verified that the source data contains no duplicate records and no missing
cells. The preparation stage therefore functions as validation rather than
imputation, and we log the validation results (row count, missing cells,
duplicate count, and target class distribution) so that any future change in
the incoming data is visible rather than silent. For each model we track the
hyperparameters listed below, and we retain the fitted model artifact for each
run so that any result can be re-examined without retraining.

## Evaluation Metrics

We assess accuracy, macro-averaged precision, recall, and F1-score, per-class
recall, and the full confusion matrix. Accuracy alone is insufficient because
the three outcomes are unevenly represented in our data: of 4,424 students,
2,209 graduated, 1,421 dropped out, and 794 remained enrolled. A model could
score reasonably on accuracy while performing poorly on the minority classes,
so we use macro-averaged F1 to weight the three outcomes equally and we report
recall for each class separately. Our primary metric is recall on the Dropout
class, because a false negative in this system is a student who needed
intervention and was never flagged, which is the failure the project exists to
prevent. Precision remains relevant as a secondary constraint, since advisors
have limited time and a system that floods them with false positives will not
be used, but we accept a precision cost in exchange for dropout recall. The
confusion matrix is tracked for every run because it reveals which outcomes the
model confuses with each other, and that distinction matters operationally:
misclassifying a dropout as enrolled is a missed intervention, while
misclassifying a graduate as a dropout is a wasted advisor contact.

## Outcome Goals and Comparison Method

The best model is the one that achieves the highest Dropout recall at the
earliest point in the academic year at which it could be deployed, subject to
macro F1 remaining competitive. Comparing runs is only meaningful if they are
measured on the same students, so all six runs share a single stratified 80/20
train/test split drawn once with a fixed random seed and reused across every
model and feature set; stratification keeps the class proportions stable
between the training and test sets. Runs are compared in the MLflow UI, where
the naming convention groups them by model and feature set, and the metrics are
additionally versioned in Git through DVC so that we can see how results change
across commits rather than only within a single session. We will consider the
experiments successful if they establish a baseline for each feature set,
identify the earliest point in the academic year at which a model performs well
enough to act on, and document the trade-off between predictive performance and
intervention time. Within that, a model is preferred if it improves Dropout
recall without a substantial loss in macro F1, and a model requiring end-of-year
data must outperform an earlier-available model by a wide margin to justify the
loss of intervention time. A defensible negative result would also count as
success, since establishing that two algorithms perform equivalently is itself a
finding that informs the design.

## Experiment Design

```
   Raw student data (Kaggle, 4,424 records)
                  |
        KNIME preparation workflow
        (read -> duplicate filter -> missing-value policy)
                  |
          Validation checks logged
                  |
        Single stratified 80/20 split (seed fixed)
                  |
     +------------+------------+------------+
     |                         |            |
 enrollment_only         through_sem1   all_features
   24 features            30 features    36 features
     |                         |            |
  logreg + forest        logreg + forest  logreg + forest
     |                         |            |
     +------------+------------+------------+
                  |
        6 runs logged to MLflow
   (parameters, metrics, confusion matrix, model artifact)
```

### Hyperparameters tracked

| Model | Hyperparameters |
|---|---|
| Multinomial logistic regression | Regularization strength, penalty type, solver, maximum iterations |
| Random forest | Number of trees, maximum tree depth, minimum samples per split, maximum features sampled |

Hyperparameters are stored in a configuration file rather than edited inside
the model code, so a tuning run changes one recorded value and the resulting
comparison remains traceable to it.

## Preliminary Results

We implemented the tracking described above and executed the full six-run grid.
The table reports held-out test performance.

These results are deliberately held back from the submitted conceptual design,
which states only that a first pass has been run and that the results will be
presented with the MVP. This file is the detailed internal version.

| Model | Feature set | Features | Accuracy | Macro F1 | Recall Dropout | Recall Enrolled | Recall Graduate |
|---|---|---:|---:|---:|---:|---:|---:|
| logreg | enrollment_only | 24 | 0.625 | 0.473 | 0.588 | 0.044 | 0.857 |
| forest | enrollment_only | 24 | 0.627 | 0.519 | 0.616 | 0.145 | 0.808 |
| logreg | through_sem1 | 30 | 0.734 | 0.612 | 0.746 | 0.176 | 0.928 |
| forest | through_sem1 | 30 | 0.729 | 0.614 | 0.725 | 0.201 | 0.921 |
| logreg | all_features | 36 | 0.768 | 0.683 | 0.768 | 0.333 | 0.925 |
| forest | all_features | 36 | 0.765 | 0.687 | 0.732 | 0.365 | 0.930 |

Three findings follow from these runs.

First, the two algorithms perform equivalently. Logistic regression reaches
0.768 accuracy and random forest 0.765, and the two remain within a few
thousandths of each other at every feature set. The choice between them should
therefore be made on interpretability and operational fit rather than on
predictive performance, which favors logistic regression for advisor-facing
explanations and random forest for the feature importance scores that help
identify which factors drive risk.

Second, and more consequentially, most of the achievable performance arrives
with first-semester results rather than second. Dropout recall rises from 0.588
using only enrollment data to 0.746 once first-semester grades are available,
and reaches just 0.768 with the full set. A model deployed after first-semester
grades post therefore retains roughly 97 percent of the dropout recall of a
model that waits for end-of-year data, while preserving an entire semester in
which an advisor can intervene. This directly supports the early-intervention
premise of our proposal, and it means our recommended configuration is the
through-semester-1 feature set rather than the highest-scoring one.

Third, all six configurations predict the Enrolled class poorly, with recall
between 0.044 and 0.365. The confusion matrices show this clearly. Using
logistic regression on the through-semester-1 feature set:

| Actual \ Predicted | Dropout | Enrolled | Graduate |
|---|---:|---:|---:|
| **Dropout** | 212 | 23 | 49 |
| **Enrolled** | 52 | 28 | 79 |
| **Graduate** | 18 | 14 | 410 |

Students who remain enrolled are most often predicted as graduating, which is
intuitive given that continued enrollment resembles progress toward a degree
more than it resembles withdrawal. For our use case this is a tolerable
weakness, since the operational decision is whether to flag a student for
outreach and the Enrolled category is the least urgent of the three. We report
it as a known limitation rather than treating the macro average as the whole
picture.

## Limitations and Next Steps

These results come from a single train/test split rather than
cross-validation, so the individual figures carry sampling uncertainty and
small differences between models should not be over-interpreted. The dataset is
a public Kaggle dataset describing one institution, so performance would need
revalidation on institutional data before deployment. Our next steps are to
tune the hyperparameters above and measure whether tuning changes the ranking,
to evaluate whether adjusting the decision threshold improves Dropout recall at
an acceptable precision cost, and to rebuild the comparison inside the KNIME
workflow so that the modeling remains visible and maintainable for the whole
team.

## Disclosure

Claude Code was used to "vibe code" a shared pipeline using GitHub, DVC, KNIME
and MLflow, and aided in uncovering the timing issues using Python's scikit
libraries. Claude Code also drafted and edited portions of this document's
text, which the group reviewed and revised.
