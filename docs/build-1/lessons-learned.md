# Build 1 — Lessons Learned

**Data lake layout and lifecycle**  
*Friday 13 November 2026 · Exam tasks 2.3, 2.4, 4.1, 4.4*

## Summary

| # | Area | Takeaway |
|---|---|---|
| 1 | Decide before you click | Reasoned through each with analogies (filing cabinet, storage shelves) before building. |
| 2 | Partitions | Hive-style `key=value`, zero-padded. Glue crawlers name columns `year`, `month`; Athena skips non-matching folders. |
| 3 | Storage classes and lifecycle | `raw-tiering`: Standard-IA at 30 days, Glacier Flexible at 90, noncurrent delete at 30. |
| 4 | Minimum charges | Small or short-lived files stay in Standard. Console confirms the 128 KB transition minimum. |
| 5 | CSV sample script | `import pandas as pd`. Also `index=False` (no pandas index column) and `random_state=42` (same rows with same `n` and input). |
| 6 | Data types | Convert to Parquet with explicit types (Build 3 CTAS, Build 6 Glue). Parquet was about 6x smaller per row. |
| 7 | Break it: delete and recover | Deleted only the marker; original restored with the same version ID. |
| 8 | Environment | `cd ~/dea-lab` first; `setopt interactivecomments`; check `git log` and `git ls-files`. |
| 9 | Budget filter | Open item. Retry after hourly builds start billing; check Bills daily meanwhile. |

> **Top three for review**
>
> 1. Partition on the column you filter by; `key=value` names enable pruning.
> 2. Known access pattern → lifecycle rule; unknown → Intelligent-Tiering.
> 3. Small or short-lived objects stay in Standard (128 KB and 30-day minimums).

## Entries

### 1. Decide before you click

| Field | Detail |
|---|---|
| What happened | Could not answer the three decide questions cold (first time with AWS). |
| Root cause | No prior S3 cost or storage background. |
| Fix | Reasoned through each with analogies (filing cabinet, storage shelves) before building. |
| Exam angle | 2.3, 2.4. Reasoning beats memorizing; the build corrects the guess. |

### 2. Partitions

| Field | Detail |
|---|---|
| What happened | Learned why `year=2024/month=01/` beats `2024/01/`. |
| Root cause | Plain folders do not tell engines which column a value belongs to. |
| Fix | Hive-style `key=value`, zero-padded. Glue crawlers name columns `year`, `month`; Athena skips non-matching folders. |
| Exam angle | "Reduce Athena cost", "queries filter by date" → partition on the filter column + Parquet. Pays off only when queries filter on it. |

### 3. Storage classes and lifecycle

| Field | Detail |
|---|---|
| What happened | Chose a lifecycle rule over Intelligent-Tiering for `raw/`. |
| Root cause | Access pattern is known: hot 30 days, then cold. |
| Fix | `raw-tiering`: Standard-IA at 30 days, Glacier Flexible at 90, noncurrent delete at 30. |
| Exam angle | Known pattern → lifecycle (free). Unknown or changing → Intelligent-Tiering (monitoring fee). |

### 4. Minimum charges

| Field | Detail |
|---|---|
| What happened | Worked the 10,000 × 5 KB example: about 75x the real usage in Standard-IA. |
| Root cause | IA bills a 128 KB minimum size and 30-day minimum duration; Glacier 90 days. |
| Fix | Small or short-lived files stay in Standard. Console confirms the 128 KB transition minimum. |
| Exam angle | "Many small objects" + "move to IA to save money" is a trap answer. |

### 5. CSV sample script

| Field | Detail |
|---|---|
| What happened | First draft had `import pandas as pandas` but used `pd`. |
| Root cause | Alias mismatch would raise a NameError. |
| Fix | `import pandas as pd`. Also `index=False` (no pandas index column) and `random_state=42` (same rows with same `n` and input). |
| Exam angle | Repeatable samples make pipelines testable. |

### 6. Data types

| Field | Detail |
|---|---|
| What happened | CSV timestamps became plain text; `passenger_count` became `2.0`. |
| Root cause | CSV carries no types; pandas turns integer columns with blanks into floats. |
| Fix | Convert to Parquet with explicit types (Build 3 CTAS, Build 6 Glue). Parquet was about 6x smaller per row. |
| Exam angle | "CSV in S3, slow and costly queries" → Parquet + partitions. |

### 7. Break it: delete and recover

| Field | Detail |
|---|---|
| What happened | Deleted the zones file; Show versions revealed a delete marker over the original. |
| Root cause | Versioning on: a delete adds a marker and keeps the data as a noncurrent version. |
| Fix | Deleted only the marker; original restored with the same version ID. |
| Exam angle | "Protect against accidental delete or overwrite" → versioning (+ MFA Delete, Object Lock). Off by default; can only be suspended once on. |

### 8. Environment

| Field | Detail |
|---|---|
| What happened | Kiro terminal opened in `~` (no `.venv`); zsh rejected `#` comments; commit said "nothing to commit". |
| Root cause | Wrong working directory; zsh default setting; file already committed. |
| Fix | `cd ~/dea-lab` first; `setopt interactivecomments`; check `git log` and `git ls-files`. |
| Exam angle | None. Workflow hygiene. |

### 9. Budget filter

| Field | Detail |
|---|---|
| What happened | Charge type → Credit value unavailable. |
| Root cause | No credits applied yet (usage near $0), so no Credit charge type exists in Cost Explorer. |
| Fix | Open item. Retry after hourly builds start billing; check Bills daily meanwhile. |
| Exam angle | Budgets alert; they do not stop spend. Credits can hide real usage. |
