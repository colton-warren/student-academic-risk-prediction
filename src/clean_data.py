"""Python port of the Student_Risk_DataOps KNIME workflow.

Mirrors the KNIME node chain so `dvc repro` can rebuild the processed CSV
without a KNIME install:

    CSV Reader (#1) -> Duplicate Row Filter (#2) -> Missing Value (#3) -> CSV Writer (#5)

Duplicate Row Filter (#2) is configured with an empty exclusion list and
EnforceExclusion, i.e. duplicates are judged across *all* columns, the first
occurrence is kept and the original row order is retained.

Missing Value (#3) maps IntCell, StringCell and DoubleCell to
DoNothingMissingCellHandlerFactory -- it is a deliberate no-op. The stage is
kept so the policy stays explicit and versioned, and the counts are reported
rather than silently imputed.
"""

import argparse
import csv
import json
import math
import numbers
from pathlib import Path

import pandas as pd


def knime_cell(value):
    """Convert one cell to the value KNIME's CSV Writer would emit.

    Two details matter for reproducing the existing processed CSV exactly:
    KNIME drops the decimal part of integral doubles (122, not pandas' 122.0),
    and numpy's integer types are not `int` subclasses, so they would be
    quoted as text by QUOTE_NONNUMERIC unless converted first.
    """
    if value is None or value is pd.NA:
        return None
    if isinstance(value, numbers.Integral) and not isinstance(value, bool):
        return int(value)
    if isinstance(value, numbers.Real):
        number = float(value)
        if not math.isfinite(number):
            return None
        return int(number) if number == int(number) else number
    return str(value)


def write_knime_csv(df, path):
    """Write `df` in the format produced by KNIME's CSV Writer (#5).

    CRLF matches the workflow's original Windows execution. It is no longer
    load-bearing: KNIME's CSV Writer emits whatever line ending the host OS
    uses, so a Mac run produces LF, and verify_prep compares the data rather
    than the bytes for exactly that reason.
    """
    with open(path, "w", newline="") as handle:
        writer = csv.writer(handle, quoting=csv.QUOTE_NONNUMERIC, lineterminator="\r\n")
        writer.writerow(list(df.columns))
        for row in df.itertuples(index=False, name=None):
            writer.writerow([knime_cell(cell) for cell in row])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default="data/raw/student_data.csv")
    parser.add_argument("--output", default="data/processed/cleaned_student_data.csv")
    parser.add_argument("--report", default="reports/cleaning_report.json")
    args = parser.parse_args()

    df = pd.read_csv(args.input)
    rows_in = len(df)

    # Duplicate Row Filter (#2): all columns, keep first, retain order.
    df = df.drop_duplicates(keep="first")
    duplicates_removed = rows_in - len(df)

    # Missing Value (#3): DoNothing for every type. Reported, never imputed.
    missing_by_column = {
        column: int(count) for column, count in df.isna().sum().items() if count
    }

    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    write_knime_csv(df, args.output)

    report = {
        "rows_in": rows_in,
        "rows_out": len(df),
        "duplicates_removed": duplicates_removed,
        "missing_cells": int(sum(missing_by_column.values())),
        "missing_by_column": missing_by_column,
        "missing_value_policy": "do_nothing",
    }
    Path(args.report).parent.mkdir(parents=True, exist_ok=True)
    Path(args.report).write_text(json.dumps(report, indent=2) + "\n")

    print(
        f"{rows_in} rows in, {len(df)} rows out, "
        f"{duplicates_removed} duplicates removed, "
        f"{report['missing_cells']} missing cells left as-is"
    )


if __name__ == "__main__":
    main()
