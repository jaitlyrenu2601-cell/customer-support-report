"""Sequential delta-processing pipeline for the customer support challenge."""
from __future__ import annotations
import argparse
import logging
from pathlib import Path
from typing import Dict
import pandas as pd

TABLE_KEYS = {
    "agents": "agent_id",
    "contact_centers": "contact_center_id",
    "service_categories": "category_id",
    "interactions": "interaction_id",
}
TABLES = tuple(TABLE_KEYS)

def configure_logging() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")

def clean_strings(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for col in df.select_dtypes(include=["object"]).columns:
        df[col] = df[col].where(df[col].isna(), df[col].astype(str).str.strip())
    return df

def apply_delta(state: pd.DataFrame, delta: pd.DataFrame, key: str) -> pd.DataFrame:
    state = state.copy()
    delta = clean_strings(delta)
    if "action" not in delta.columns:
        raise ValueError("Delta file is missing required action column.")
    delta["action"] = delta["action"].str.lower()
    for _, row in delta.iterrows():
        record_id, action = row[key], row["action"]
        if action == "delete":
            state = state[state[key] != record_id].copy()
        elif action in {"add", "update"}:
            exists = (state[key] == record_id).any()
            if action == "add" and exists:
                raise ValueError(f"Add for existing {key}={record_id}")
            if action == "update" and not exists:
                raise ValueError(f"Update for missing {key}={record_id}")
            state = state[state[key] != record_id].copy()
            record = {c: row[c] for c in state.columns if c in row.index}
            state = pd.concat([state, pd.DataFrame([record])], ignore_index=True)
        else:
            raise ValueError(f"Unsupported action: {action!r}")
    return state

def load_state(data_dir: Path, months: list[str]) -> Dict[str, pd.DataFrame]:
    initial, delta_dir = data_dir / "initial", data_dir / "delta"
    states = {t: clean_strings(pd.read_csv(initial / f"{t}.csv")) for t in TABLES}
    for month in sorted(months):
        logging.info("Applying delta month %s", month)
        for table, key in TABLE_KEYS.items():
            path = delta_dir / f"{table}_delta_{month}.csv"
            if path.exists():
                states[table] = apply_delta(states[table], pd.read_csv(path), key)
    return states

def persist_state(states: Dict[str, pd.DataFrame], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    for table, df in states.items():
        df.to_csv(output_dir / f"{table}.csv", index=False)

def build_report(states: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    interactions = states["interactions"].copy()
    interactions["interaction_start"] = pd.to_datetime(
        interactions["interaction_start"], utc=True, errors="coerce"
    )
    if interactions["interaction_start"].isna().any():
        raise ValueError("Interactions contain invalid interaction_start values.")
    interactions["month"] = (
        interactions["interaction_start"]
        .dt.tz_convert("America/New_York")
        .dt.strftime("%Y-%m")
    )
    interactions["channel"] = interactions["channel"].astype(str).str.strip().str.lower()
    interactions["call_duration_minutes"] = pd.to_numeric(
        interactions["call_duration_minutes"], errors="coerce"
    ).fillna(0)
    enriched = (
        interactions
        .merge(states["contact_centers"], on="contact_center_id", how="left")
        .merge(states["service_categories"][["category_id", "department"]],
               on="category_id", how="left")
    )
    enriched["contact_center_name"] = enriched["contact_center_name"].fillna("Unknown")
    enriched["department"] = enriched["department"].fillna("Unknown")
    return (
        enriched.groupby(["month", "contact_center_name", "department"],
                         as_index=False, dropna=False)
        .agg(
            total_interactions=("interaction_id", "nunique"),
            total_calls=("channel", lambda s: int((s == "phone").sum())),
            total_call_duration=("call_duration_minutes", "sum"),
        )
        .sort_values(["month", "contact_center_name", "department"])
    )

def persist_report(report: pd.DataFrame, output_dir: Path, fmt: str) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"support_report.{fmt}"
    if fmt == "csv":
        report.to_csv(path, index=False)
    elif fmt == "json":
        report.to_json(path, orient="records", indent=2)
    elif fmt == "parquet":
        report.to_parquet(path, index=False)
    return path

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, default=Path("data"))
    parser.add_argument("--output-dir", type=Path, default=Path("output"))
    parser.add_argument("--months", default=None)
    parser.add_argument("--format", choices=["csv", "json", "parquet"], default="csv")
    args = parser.parse_args()
    configure_logging()
    months = ([m.strip() for m in args.months.split(",") if m.strip()]
              if args.months else sorted({
                  p.name.split("_delta_")[1].split(".csv")[0]
                  for p in (args.data_dir / "delta").glob("*_delta_*.csv")
              }))
    if not months:
        raise ValueError("No delta months found.")
    states = load_state(args.data_dir, months)
    persist_state(states, args.output_dir)
    report_path = persist_report(build_report(states), args.output_dir, args.format)
    logging.info("Wrote %s", report_path)

if __name__ == "__main__":
    main()
