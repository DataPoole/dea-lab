# Build 1 — As Built

**Data lake layout and lifecycle: only what worked**  
*Friday 13 November 2026 · Exam tasks 2.3, 2.4, 4.1, 4.4*

| Thing | Value |
|---|---|
| Lake bucket | `dea-lake-124118675794`: versioning on, SSE-S3 + Bucket Key, public access blocked, tag `project=dea` |
| Athena results bucket | `dea-athena-124118675794`: versioning off |
| Prefixes | `raw/` · `clean/` · `quarantine/` · `curated/` · `ref/` |
| Lifecycle rules | `raw-tiering` (IA 30d → Glacier Flexible 90d, noncurrent delete 30d) · `quarantine-expire` (expire 14d, noncurrent 7d) |
| Objects | `raw/trips/year=2024/month=01/trips_2024_01.csv` (20 MiB, 200,000 rows) · `ref/zones/taxi_zone_lookup.csv` (12 KiB) |
| Local only | `data/trips_2024_02.csv` held back for Build 2 · repo commit `df2f5a0` |

## 1. Start of Day

```
cd ~/dea-lab && conda deactivate && source .venv/bin/activate
aws login --profile dea
aws sts get-caller-identity          # 124118675794
```

## 2. Data and Sample Script

```
mkdir -p data && cd data
curl -O https://d37ci6vzurychx.cloudfront.net/trip-data/yellow_tripdata_2024-01.parquet
curl -O https://d37ci6vzurychx.cloudfront.net/trip-data/yellow_tripdata_2024-02.parquet
curl -O https://d37ci6vzurychx.cloudfront.net/misc/taxi_zone_lookup.csv
cd ..
```

`make_csv_sample.py` (built step by step):

```
import sys
import pandas as pd

month = sys.argv[1]                                    # 2024-01
src = f"data/yellow_tripdata_{month}.parquet"
df = pd.read_parquet(src)
sample = df.sample(n=200_000, random_state=42)         # same rows every run
dst = f"data/trips_{month.replace('-', '_')}.csv"
sample.to_csv(dst, index=False)                        # no pandas index column
print(f"Wrote {len(sample):,} rows to {dst}")
print("Columns:", list(sample.columns))
```

Run: `python make_csv_sample.py 2024-01` and `2024-02`. Output: 200,000 rows, 19 columns.

## 3. Buckets and Folders (console)

1. **S3 → Create bucket** `dea-lake-124118675794`: General purpose, ACLs disabled, Block all public access, **Versioning: Enable**, **SSE-S3 + Bucket Key**, tag `project=dea`.
2. Same for `dea-athena-124118675794`, versioning off.
3. Lake bucket → **Create folder** ×5: `raw`, `clean`, `quarantine`, `curated`, `ref` (encryption: use bucket default).

## 4. Lifecycle Rules (console)

1. **Management → Create lifecycle rule** `raw-tiering`, prefix `raw/`: transition current versions to Standard-IA at 30 days and Glacier Flexible Retrieval at 90; permanently delete noncurrent versions after 30 days.
2. `quarantine-expire`, prefix `quarantine/`: expire current versions at 14 days; permanently delete noncurrent versions after 7 days.
3. Console confirmed: default minimum object size for transitions is 128 KB.

## 5. Upload with Hive Partitions

```
B=dea-lake-124118675794
aws s3 cp data/trips_2024_01.csv s3://$B/raw/trips/year=2024/month=01/trips_2024_01.csv
aws s3 cp data/taxi_zone_lookup.csv s3://$B/ref/zones/taxi_zone_lookup.csv
aws s3 ls s3://$B/ --recursive --human-readable
```

## 6. Break It: Delete and Recover

1. Deleted `ref/zones/taxi_zone_lookup.csv` with **Show versions** off: file appeared gone.
2. **Show versions** on: a **Delete marker** (0 B) on top of the original version (12 KB, Standard).
3. Deleted only the delete marker (`permanently delete`). Original returned with the same version ID.

> **Lessons learned**
>
> - `key=value` partitions tell Athena and Glue which column a folder represents; queries that filter on it skip the rest (pruning). Glue crawlers name the columns `year`, `month` instead of `partition_0`.
> - Known access pattern → lifecycle rule (free). Unknown → Intelligent-Tiering (monitoring fee).
> - IA and Glacier have minimum duration (30/90 days) and IA a 128 KB minimum size: small or short-lived files cost more there.
> - CSV loses data types (timestamps become text; integer columns with blanks become floats). Parquet keeps types and was about 6x smaller per row.
> - S3 folders are just key prefixes. Versioning is off by default; with it on, a delete is a marker and is reversible.
> - Kiro terminal opens in `~`; `cd ~/dea-lab` first. zsh needs `setopt interactivecomments` for `#` comments.

> **Open items**
>
> - Budget Credit filter: no Credit charge type yet (usage near $0). Retry once credits start applying.
> - Upload `trips_2024_02.csv` in Build 2 to trigger the Lambda.
