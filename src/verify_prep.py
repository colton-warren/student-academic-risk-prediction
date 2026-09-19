"""Validate the KNIME-prepared dataset before anything trains on it.

KNIME does the preparation, which means a human runs it and commits the
result. Nothing stops that result from being produced by an edited workflow,
a different input file, or an accidental manual tweak -- so the pipeline
checks it rather than trusting it.

Two kinds of check run here:

1. Contract checks, from data_contract.yaml -- the validation Section 5 of the
   proposal promises: required columns and types, missing values, duplicates,
   unexpected target categories, values outside known ranges, and drift in the
   target distribution.

2. A reproduction check. src/clean_data.py is a Python port of the KNIME
   workflow, so re-running it on the raw data should reproduce the committed
   file exactly. A mismatch means the workflow and the port have diverged --
   usually because someone changed the KNIME nodes without updating the port.

Exit status is non-zero when a check fails, which stops `dvc repro`.
"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

import pandas as pd
import yaml

RAW = "data/raw/student_data.csv"
PREPARED = "data/processed/cleaned_student_data.csv"
CONTRACT = "data_contract.yaml"
REPORT = "reports/prep_verification.json"


def contract_checks(df, contract):
    """Run the data-contract checks, returning (failures, warnings, summary)."""
    failures, warnings = [], []
    spec = contract["columns"]

    missing_cols = [c for c in spec if c not in df.columns]
    extra_cols = [c for c in df.columns if c not in spec]
    if missing_cols:
        failures.append(f"missing required columns: {missing_cols}")
    if extra_cols:
        warnings.append(f"columns not in the contract: {extra_cols}")

    if len(df) < contract["row_count"]["min"]:
        failures.append(f"only {len(df)} rows, contract requires at least "
                        f"{contract['row_count']['min']}")

    missing_cells = int(df.isna().sum().sum())
    if missing_cells:
        by_col = {c: int(n) for c, n in df.isna().sum().items() if n}
        failures.append(f"{missing_cells} missing cells: {by_col}")

    duplicates = int(df.duplicated().sum())
    if duplicates:
        failures.append(f"{duplicates} duplicate rows survived preparation")

    out_of_range = {}
    for col, rules in spec.items():
        if col not in df.columns or rules["type"] == "string":
            continue
        series = pd.to_numeric(df[col], errors="coerce")
        outside = int(((series < rules["min"]) | (series > rules["max"])).sum())
        if outside:
            out_of_range[col] = outside
    if out_of_range:
        # Out-of-range is a warning: the contract records what was normal in
        # the reference data, and genuinely new data may legitimately exceed it.
        warnings.append(f"values outside contract ranges: {out_of_range}")

    target_spec = spec.get("target", {})
    if "target" in df.columns and "allowed" in target_spec:
        unexpected = sorted(set(df["target"].unique()) - set(target_spec["allowed"]))
        if unexpected:
            failures.append(f"unexpected target categories: {unexpected}")

    balance = {k: round(float(v), 4)
               for k, v in df["target"].value_counts(normalize=True).items()}
    tolerance = contract["target_balance_tolerance"]
    drifted = {
        cls: {"expected": exp, "actual": balance.get(cls, 0.0)}
        for cls, exp in contract["target_balance"].items()
        if abs(balance.get(cls, 0.0) - exp) > tolerance
    }
    if drifted:
        failures.append(f"target distribution drifted beyond {tolerance}: {drifted}")

    return failures, warnings, {
        "rows": len(df),
        "columns": len(df.columns),
        "missing_cells": missing_cells,
        "duplicate_rows": duplicates,
        "target_balance": balance,
    }


def reproduction_check(failures):
    """Re-run the KNIME port on the raw data and compare to the committed file."""
    with tempfile.TemporaryDirectory() as tmp:
        regenerated = Path(tmp) / "regenerated.csv"
        result = subprocess.run(
            [sys.executable, "src/clean_data.py",
             "--input", RAW,
             "--output", str(regenerated),
             "--report", str(Path(tmp) / "report.json")],
            capture_output=True, text=True,
        )
        if result.returncode != 0:
            failures.append(f"could not re-run src/clean_data.py: {result.stderr.strip()}")
            return {"status": "error"}

        committed = Path(PREPARED).read_bytes()
        rebuilt = regenerated.read_bytes()
        if committed == rebuilt:
            return {"status": "match",
                    "detail": "KNIME output matches the Python port byte for byte"}

        # Bytes differ; say whether the *data* differs, which is what matters.
        same_data = pd.read_csv(PREPARED).equals(pd.read_csv(regenerated))
        detail = ("same data, different formatting -- check line endings or "
                  "number formatting in the CSV Writer node"
                  if same_data else
                  "the prepared data itself differs from what the workflow port produces")
        failures.append(f"KNIME output does not match src/clean_data.py: {detail}")
        return {"status": "same_data_different_bytes" if same_data else "mismatch",
                "detail": detail}


def main():
    contract = yaml.safe_load(Path(CONTRACT).read_text())
    df = pd.read_csv(PREPARED)

    failures, warnings, summary = contract_checks(df, contract)
    summary["reproduction"] = reproduction_check(failures)

    report = {
        "passed": not failures,
        "failures": failures,
        "warnings": warnings,
        **summary,
    }
    Path(REPORT).parent.mkdir(parents=True, exist_ok=True)
    Path(REPORT).write_text(json.dumps(report, indent=2) + "\n")

    for warning in warnings:
        print(f"WARNING: {warning}")
    if failures:
        print("\nPreparation checks FAILED:")
        for failure in failures:
            print(f"  - {failure}")
        print(f"\nFull report: {REPORT}")
        return 1

    print(f"All preparation checks passed: {summary['rows']} rows, "
          f"{summary['columns']} columns, no missing cells, no duplicates")
    print(f"KNIME reproduction: {summary['reproduction']['detail']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
