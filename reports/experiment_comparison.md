# Experiment comparison

Dataset version (md5): `7cf4df354c28983ba4ae5c2587e9e8c3`  
Primary metric: recall on **Dropout** -- a false negative is a student who needed help and did not get flagged.

| Model | Feature set | Features | Accuracy | Macro F1 | Recall Dropout | Recall Enrolled | Recall Graduate |
|---|---|---:|---:|---:|---:|---:|---:|
| logreg | enrollment_only | 24 | 0.625 | 0.473 | 0.588 | 0.044 | 0.857 |
| forest | enrollment_only | 24 | 0.629 | 0.517 | 0.616 | 0.138 | 0.814 |
| logreg | through_sem1 | 30 | 0.734 | 0.612 | 0.746 | 0.176 | 0.928 |
| forest | through_sem1 | 30 | 0.728 | 0.618 | 0.725 | 0.214 | 0.914 |
| logreg | all_features | 36 | 0.768 | 0.683 | 0.768 | 0.333 | 0.925 |
| forest | all_features | 36 | 0.768 | 0.691 | 0.732 | 0.371 | 0.934 |

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
| **Enrolled** | 42 | 22 | 95 |
| **Graduate** | 60 | 22 | 360 |

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
| **Enrolled** | 51 | 34 | 74 |
| **Graduate** | 20 | 18 | 404 |

**logreg_all_features_v1** (rows = actual, columns = predicted)

| | Dropout | Enrolled | Graduate |
|---|---:|---:|---:|
| **Dropout** | 218 | 29 | 37 |
| **Enrolled** | 43 | 53 | 63 |
| **Graduate** | 14 | 19 | 409 |

**forest_all_features_v1** (rows = actual, columns = predicted)

| | Dropout | Enrolled | Graduate |
|---|---:|---:|---:|
| **Dropout** | 208 | 27 | 49 |
| **Enrolled** | 36 | 59 | 64 |
| **Graduate** | 10 | 19 | 413 |

