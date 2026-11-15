# Build 2 — As Built

**Event-driven ingestion with Lambda: only what worked**  
*Sunday 15 November 2026 · Exam tasks 1.1, 1.3, 1.4, 3.3*

| Thing | Value |
|---|---|
| Function | `dea-validate-trips` · us-east-1 · Python 3.12 · 1024 MB · ephemeral 1024 MB · timeout 1 min |
| Env vars · layer | `BUCKET=dea-lake-124118675794` · `MIN_ROWS=1000` · `AWSSDKPandas-Python312-Arm64` (us-east-1 ARN) |
| Execution role | `dea-validate-trips-role` (IAM, global): `AWSLambdaBasicExecutionRole` + `dea-validate-trips-role-s3` |
| Trigger | S3 **All object create events** on `dea-lake-124118675794`, prefix `raw/trips/`, suffix `.csv` |
| Failure path | Async: 2 retries, max age 1 hr → on-failure destination SQS `dea-ingest-dlq` (14-day retention) |
| Alarm | `dea-validate-errors`: Lambda Errors, Sum, 5 min, > 0, missing data = good → SNS `dea-alerts` |
| Results | `clean/trips/` Jan + Feb · `quarantine/trips/year=2024/month=02/bad.csv` · handler in repo `lambda/validate/` |

## 1. Queue (SQS)

1. **SQS → Create queue → Standard**, name `dea-ingest-dlq` (copy-paste; letter l, not digit 1), retention **14 days**, tag `project=dea`.

## 2. Function (Lambda, N. Virginia)

1. Check region **N. Virginia** first. **Lambda → Create function → Event function → Author from scratch**: `dea-validate-trips`, **Python 3.12**.
2. Additional settings: **ARM64 on**; **Custom execution role on → Create new role** `dea-validate-trips-role` with default `AWSLambdaBasicExecutionRole` + new policy `dea-validate-trips-role-s3` (JSON below). Tags off (form would not submit with an empty tag).
3. **Configuration → General configuration**: memory 1024 MB, ephemeral 1024 MB, timeout 1 min. **Environment variables**: `BUCKET`, `MIN_ROWS`. **Tags**: `project=dea`.
4. **Code → Layers → Add a layer → AWS layers** → `AWSSDKPandas-Python312-Arm64`; confirm the ARN says `us-east-1`.

```
{ "Version": "2012-10-17", "Statement": [
  { "Sid": "ReadRaw", "Effect": "Allow", "Action": "s3:GetObject",
    "Resource": "arn:aws:s3:::dea-lake-124118675794/raw/*" },
  { "Sid": "WriteCleanAndQuarantine", "Effect": "Allow", "Action": "s3:PutObject",
    "Resource": ["arn:aws:s3:::dea-lake-124118675794/clean/*",
                 "arn:aws:s3:::dea-lake-124118675794/quarantine/*"] },
  { "Sid": "SendFailuresToDLQ", "Effect": "Allow", "Action": "sqs:SendMessage",
    "Resource": "arn:aws:sqs:us-east-1:124118675794:dea-ingest-dlq" } ] }
```

## 3. Handler (lambda/validate/lambda_function.py)

```
import os
from urllib.parse import unquote_plus
import boto3
import pandas as pd

s3 = boto3.client("s3")
MIN_ROWS = int(os.environ["MIN_ROWS"])
DEST = os.environ["BUCKET"]
EXPECTED = {...19 TLC column names...}

def lambda_handler(event, context):
    record = event["Records"][0]                          # 1. find the file
    bucket = record["s3"]["bucket"]["name"]
    key = unquote_plus(record["s3"]["object"]["key"])    # %3D -> =
    obj = s3.get_object(Bucket=bucket, Key=key)            # 2. read it
    df = pd.read_csv(obj["Body"])
    missing = EXPECTED - set(df.columns)                   # 3. check it
    good = not missing and len(df) >= MIN_ROWS
    zone = "clean/" if good else "quarantine/"             # 4. route it
    dest_key = key.replace("raw/", zone, 1)
    s3.copy_object(Bucket=DEST, Key=dest_key, CopySource={"Bucket": bucket, "Key": key})
    print(f"{key} -> {dest_key} | rows={len(df)} | missing={sorted(missing)}")   # 5. report
    return {"status": "clean" if good else "quarantine", "dest": dest_key}
```

## 4. Trigger, Failure Path, Alarm

1. **Add trigger → S3**: bucket, **All object create events**, prefix `raw/trips/`, suffix `.csv`, acknowledge recursive invocation.
2. **Configuration → Asynchronous invocation**: retries 2, max event age 1 hour. **Destinations → On failure → SQS** `dea-ingest-dlq`.
3. **IAM role → Permissions policies**: removed the console-added `AWSLambdaSQSQueueDestinationExecutionRole-…`; own policy covers the queue.
4. **CloudWatch → Alarms → Create alarm** (after the first invocation, so Lambda metrics exist) → Lambda **By Function Name** → Errors, Sum, 5 min, > 0, missing data good → notify `dea-alerts`.

## 5. Test and Break It

```
B=dea-lake-124118675794
python make_csv_sample.py 2024-02
aws s3 cp data/trips_2024_02.csv s3://$B/raw/trips/year=2024/month=02/trips_2024_02.csv
K=raw/trips/year=2024/month=01/trips_2024_01.csv
aws s3 cp s3://$B/$K s3://$B/$K --metadata reprocess=1 --metadata-directive REPLACE
python -c "import pandas as pd; df=pd.read_csv('data/trips_2024_02.csv'); df.drop(columns=['fare_amount']).to_csv('data/bad.csv', index=False)"
aws s3 cp data/bad.csv s3://$B/raw/trips/year=2024/month=02/bad.csv
```

1. **Good files:** Jan and Feb → `clean/`. Log: `rows=200000 | missing=[]`. Cold start Init ~1.9 s; warm run ~0.6 s; max memory ~260 MB.
2. **Bad file:** `bad.csv` → `quarantine/`, log `missing=['fare_amount']`. No error, no alarm (handled by design).
3. **3 s timeout:** did not fail (warm environment, 0.6 s run).
4. **128 MB memory:** 3 attempts, each `Status: timeout` at 60 s with 127 MB used; retries ~1 min then ~2 min apart; same request ID.
5. **Queue message:** `condition: RetriesExhausted`, `approximateInvokeCount: 3`, original S3 event, `errorType: Sandbox.Timedout`.
6. **Alarm:** In alarm at 21:13:39 UTC, SNS action succeeded; email landed in spam. Memory restored to 1024 MB.

> **Open items**
>
> - Confirm **Architecture: arm64** in runtime settings (log runtime string shows x86).
> - Set log group `/aws/lambda/dea-validate-trips` retention to 1 week (default is never expire).
> - Optional: rerun the 128 MB test against the new `dea-ingest-dlq` to prove the own policy alone delivers failures.
> - Mark `no-reply@sns.amazonaws.com` as a safe sender.
