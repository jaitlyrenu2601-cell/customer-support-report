"""Business-question queries against generated support_report."""
from __future__ import annotations
import argparse
from pathlib import Path
import pandas as pd

def load_report(path: Path) -> pd.DataFrame:
    if path.suffix == ".csv": return pd.read_csv(path)
    if path.suffix == ".json": return pd.read_json(path)
    if path.suffix == ".parquet": return pd.read_parquet(path)
    raise ValueError(f"Unsupported report format: {path.suffix}")

def answer_questions(report: pd.DataFrame):
    q1 = (report.groupby("contact_center_name", as_index=False)
          .agg(total_interactions=("total_interactions", "sum"))
          .sort_values("total_interactions", ascending=False))
    q2 = (report.groupby("month", as_index=False)
          .agg(total_interactions=("total_interactions", "sum"))
          .sort_values("total_interactions", ascending=False))
    q3 = (report.groupby("contact_center_name", as_index=False)
          .agg(total_call_duration=("total_call_duration", "sum"),
               total_calls=("total_calls", "sum")))
    q3["avg_call_duration"] = q3["total_call_duration"] / q3["total_calls"]
    return q1, q2, q3.sort_values("avg_call_duration", ascending=False)

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--report", type=Path, default=Path("output/support_report.csv"))
    args = p.parse_args()
    q1, q2, q3 = answer_questions(load_report(args.report))
    print("\nQ1 - interactions by contact center\n", q1.to_string(index=False))
    print("\nQ2 - monthly interaction volume\n", q2.to_string(index=False))
    print("\nQ3 - average phone call duration\n", q3.to_string(index=False))

if __name__ == "__main__":
    main()
