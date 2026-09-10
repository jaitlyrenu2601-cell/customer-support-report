# Customer Support Interaction Data Engineering Challenge

## Overview

This is a sequential ETL solution for the January 2025 initial extract plus
February and March 2025 deltas.

It produces the March-end state of all four tables, a `support_report`, and
reproducible queries for the three business questions.

## Key implementation decisions

### Sequential deltas
January is loaded first, then February changes, then March changes. `add`,
`update`, and `delete` are normalized for whitespace/case.

### Reporting month
`interactions.timestamp` is the time the record was generated into a delta,
not when the interaction occurred. Therefore the reporting month is derived
from `interaction_start`, converted from UTC to `America/New_York`.

### Deleted dimensions
The final interaction fact is left-joined to final dimensions. Missing
dimension attributes are replaced with `Unknown`. This preserves historical
interactions even when a category is later deleted.

### Average phone duration
Average duration by center is:
`sum(total_call_duration) / sum(total_calls)`.

## Run

Python 3.10+:

```bash
python -m pip install -r requirements.txt
python -m src.pipeline
python -m src.report
pytest
```

Optional:

```bash
python -m src.pipeline --months 202502,202503
python -m src.pipeline --format json
python -m src.pipeline --format parquet
```

## Results

### Q1 — Q1 2025 interactions by contact center

| Contact center | Interactions |
|---|---:|
| Boston MA NE | 13 |
| Atlanta GA SE | 8 |
| Richmond VA E | 7 |

### Q2 — highest-volume month

**February 2025 — 10 interactions.**

January: 9  
February: 10  
March: 9

### Q3 — longest average phone call

**Boston MA NE — 12.73 minutes per phone call.**

| Contact center | Total calls | Total duration | Average |
|---|---:|---:|---:|
| Boston MA NE | 11 | 140 | **12.73** |
| Richmond VA E | 5 | 62 | 12.40 |
| Atlanta GA SE | 5 | 54 | 10.80 |

Boston's average is likely influenced by several longer calls (17, 19, 19,
21, and 14 minutes) and its larger volume. Call duration is not, however, a
complete measure of agent work.

For better work-time measurement, instrument agent-state events covering
available, on-call, hold/transfer, after-call work, and return-to-available.
This captures work performed outside connected talk time.

## Final March state

- Agents: 10
- Contact centers: 3
- Service categories: 9
- Interactions: 28

The final state and `support_report.csv` are included under `output/`.
