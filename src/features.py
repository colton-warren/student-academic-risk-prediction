"""Feature groupings, defined by *when the information becomes available*.

The project's premise is early intervention: flagging a student while there is
still time to help. That makes timing a modelling constraint, not a detail.
Second-semester results are the strongest predictors in this dataset, but a
model that needs them can only raise the alarm once the year is effectively
over, which is too late to act on.

Keeping the groups here means the experiment grid and the validation checks
agree on what "enrollment only" means.
"""

TARGET = "target"


def semester_columns(columns, which):
    """Columns holding results for the given semester, e.g. '1st' or '2nd'."""
    return [c for c in columns if f"{which} sem" in c]


def enrollment_columns(columns):
    """What the university knows on day one.

    Demographics, prior schooling, financial status and the macroeconomic
    indicators -- everything except per-semester performance.
    """
    later = semester_columns(columns, "1st") + semester_columns(columns, "2nd")
    return [c for c in columns if c not in later and c != TARGET]


def feature_sets(columns):
    """The three feature sets the experiment grid sweeps over.

    Ordered by how early a prediction could be made, which is also the order
    of increasing predictive power -- that trade-off is the point.
    """
    enroll = enrollment_columns(columns)
    sem1 = semester_columns(columns, "1st")
    sem2 = semester_columns(columns, "2nd")
    return {
        "enrollment_only": enroll,
        "through_sem1": enroll + sem1,
        "all_features": enroll + sem1 + sem2,
    }
