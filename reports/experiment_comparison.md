# Experiment comparison

Dataset version (md5): `fa8e869c1b2036558303a53f857ecb77`  
Primary metric: recall on **Dropout** -- a false negative is a student who needed help and did not get flagged.

| Model | Feature set | Features | Accuracy | Macro F1 | Recall Dropout | Recall Enrolled | Recall Graduate |
|---|---|---:|---:|---:|---:|---:|---:|
| logreg | enrollment_only | 24 | 0.625 | 0.473 | 0.588 | 0.044 | 0.857 |
| forest | enrollment_only | 24 | 0.627 | 0.519 | 0.616 | 0.145 | 0.808 |
| logreg | through_sem1 | 30 | 0.734 | 0.612 | 0.746 | 0.176 | 0.928 |
| forest | through_sem1 | 30 | 0.729 | 0.614 | 0.725 | 0.201 | 0.921 |
| logreg | all_features | 36 | 0.768 | 0.683 | 0.768 | 0.333 | 0.925 |
| forest | all_features | 36 | 0.765 | 0.687 | 0.732 | 0.365 | 0.930 |

## Confusion matrices

**logreg_enrollment_only_v1** (rows = actual, columns = predicted)

| | Dropout | Enrolled | Graduate |
|---|---:|---:|---:|
| **Dropout** | 167 | 6 | 111 |
| **Enrolled** | 38 | 7 | 114 |
| **Graduate** | 50 | 13 | 379 |

**forest_enrollment_only_v1** (rows = actual, columns = predicted)

| | Dropout | Enrolled | Graduate |
|---|---:|---:|---:|
| **Dropout** | 175 | 16 | 93 |
| **Enrolled** | 38 | 23 | 98 |
| **Graduate** | 61 | 24 | 357 |

**logreg_through_sem1_v1** (rows = actual, columns = predicted)

| | Dropout | Enrolled | Graduate |
|---|---:|---:|---:|
| **Dropout** | 212 | 23 | 49 |
| **Enrolled** | 52 | 28 | 79 |
| **Graduate** | 18 | 14 | 410 |

**forest_through_sem1_v1** (rows = actual, columns = predicted)

| | Dropout | Enrolled | Graduate |
|---|---:|---:|---:|
| **Dropout** | 206 | 26 | 52 |
| **Enrolled** | 53 | 32 | 74 |
| **Graduate** | 19 | 16 | 407 |

**logreg_all_features_v1** (rows = actual, columns = predicted)

| | Dropout | Enrolled | Graduate |
|---|---:|---:|---:|
| **Dropout** | 218 | 29 | 37 |
| **Enrolled** | 43 | 53 | 63 |
| **Graduate** | 14 | 19 | 409 |

**forest_all_features_v1** (rows = actual, columns = predicted)

| | Dropout | Enrolled | Graduate |
|---|---:|---:|---:|
| **Dropout** | 208 | 28 | 48 |
| **Enrolled** | 36 | 58 | 65 |
| **Graduate** | 10 | 21 | 411 |

