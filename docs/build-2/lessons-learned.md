# Build 2 — Lessons Learned

**Event-driven ingestion with Lambda**  
*Sunday 15 November 2026 · Exam tasks 1.1, 1.3, 1.4, 3.3*

## Summary

| # | Area | Takeaway |
|---|---|---|
| 1 | Decide before you click | One service → S3 Event Notifications; many → EventBridge. Big or long jobs → not Lambda. Never write to the trigger prefix. Async failures are dropped unless a destination or DLQ is set. |
| 2 | Region drift | Deleted and rebuilt in N. Virginia; set Unified settings default region. IAM role reused: IAM is global ("policy already exists" error proved it). |
| 3 | Execution role | Created `dea-validate-trips-role`: read `raw/*`, write `clean/*` and `quarantine/*`, send to the queue. Analyzer: 0 findings. |
| 4 | Event shape and names | Read source from the event, destination from env vars. `Bucket=` is the boto3 parameter. Decode keys with `unquote_plus` (`=` arrives as `%3D`). |
| 5 | Code bugs | Fixed `Key=key`; indented 4 spaces; ran `make_csv_sample.py 2024-02`. |
| 6 | Metrics before alarms | Ran the test first, then created the alarm. |
| 7 | Cold vs warm starts | Timeouts must cover the cold start. Forced failure with memory instead. |
| 8 | Under-provisioned memory | Restored 1024 MB. A right-sized run is 0.6 s; starving it cost ~100x more. |
| 9 | Retries and destinations | Message held `RetriesExhausted`, invoke count 3, original event, `Sandbox.Timedout`. |
| 10 | Multipart upload event | Trigger set to All object create events catches both. |
| 11 | Queue typo and hidden policy | Recreated `dea-ingest-dlq` (copy-paste names), repointed destination, removed the auto policy. |
| 12 | Alarm email "missing" | Marked not spam; add `no-reply@sns.amazonaws.com` to safe senders. |

> **Top three for review**
>
> 1. Async Lambda failures are dropped unless an on-failure destination or DLQ catches them.
> 2. Timeouts and memory must cover the cold start; too little memory costs more, not less.
> 3. Check the Region before creating anything; IAM is global, almost everything else is regional.

## Entries

### 1. Decide before you click

| Field | Detail |
|---|---|
| What happened | Reasoned through all four questions with analogies. |
| Root cause | Lambda, events and async retries were new. |
| Fix | One service → S3 Event Notifications; many → EventBridge. Big or long jobs → not Lambda. Never write to the trigger prefix. Async failures are dropped unless a destination or DLQ is set. |
| Exam angle | 1.1, 1.3. "Multiple consumers", "fan out", "replay" → EventBridge. |

### 2. Region drift

| Field | Detail |
|---|---|
| What happened | Queue and function were created in Ohio; the layer ARN said `us-east-2`. |
| Root cause | Console fell back to the project account home region. |
| Fix | Deleted and rebuilt in N. Virginia; set Unified settings default region. IAM role reused: IAM is global ("policy already exists" error proved it). |
| Exam angle | S3 triggers and layers must be in the same Region as the function. IAM is global; most other resources are regional. |

### 3. Execution role

| Field | Detail |
|---|---|
| What happened | New console hides the role under Custom execution role; default grants automatic permissions. |
| Root cause | Least privilege needs an explicit role. |
| Fix | Created `dea-validate-trips-role`: read `raw/*`, write `clean/*` and `quarantine/*`, send to the queue. Analyzer: 0 findings. |
| Exam angle | Trust policy = who can assume the role; permissions policy = what it can do. Use roles, never keys in code. |

### 4. Event shape and names

| Field | Detail |
|---|---|
| What happened | Confused by `record["s3"]["bucket"]["name"]`, `Bucket=` vs `bucket` vs `BUCKET`. |
| Root cause | Nested dictionaries; parameter names vs variables vs env vars. |
| Fix | Read source from the event, destination from env vars. `Bucket=` is the boto3 parameter. Decode keys with `unquote_plus` (`=` arrives as `%3D`). |
| Exam angle | URL-encoded keys are a common Lambda bug. |

### 5. Code bugs

| Field | Detail |
|---|---|
| What happened | `Key-key` typo; unindented `print` before `return`; February CSV never created. |
| Root cause | Syntax error; IndentationError (Init error); missing input. |
| Fix | Fixed `Key=key`; indented 4 spaces; ran `make_csv_sample.py 2024-02`. |
| Exam angle | Workflow hygiene. An Init error means the code never loaded. |

### 6. Metrics before alarms

| Field | Detail |
|---|---|
| What happened | No Lambda tile in CloudWatch metrics when creating the alarm. |
| Root cause | Lambda metrics only appear after the first invocation (and only in the viewed Region). |
| Fix | Ran the test first, then created the alarm. |
| Exam angle | Check Region and invocation history when metrics are missing. |

### 7. Cold vs warm starts

| Field | Detail |
|---|---|
| What happened | 3 s timeout did not fail; run took 0.6 s. |
| Root cause | Environment was warm; the cold-start Init (~1.9 s) did not run. |
| Fix | Timeouts must cover the cold start. Forced failure with memory instead. |
| Exam angle | Cold start fixes: provisioned concurrency, SnapStart, smaller packages. Init time is billed. |

### 8. Under-provisioned memory

| Field | Detail |
|---|---|
| What happened | 128 MB → 127 MB used, `Status: timeout` at 60 s, billed 63 s. |
| Root cause | Too little memory also means too little CPU; pandas crawled. |
| Fix | Restored 1024 MB. A right-sized run is 0.6 s; starving it cost ~100x more. |
| Exam angle | "Lambda slow or out of memory" → raise memory (adds CPU). Right-size with Power Tuning. |

### 9. Retries and destinations

| Field | Detail |
|---|---|
| What happened | 3 attempts, ~1 then ~2 min apart, same request ID; message in the queue. |
| Root cause | Async invoke: 2 retries with exponential backoff, then on-failure destination. |
| Fix | Message held `RetriesExhausted`, invoke count 3, original event, `Sandbox.Timedout`. |
| Exam angle | Destinations carry error details; a DLQ keeps only the event. |

### 10. Multipart upload event

| Field | Detail |
|---|---|
| What happened | Event name was `ObjectCreated:CompleteMultipartUpload`, not `Put`. |
| Root cause | The CLI uses multipart for files over 8 MB. |
| Fix | Trigger set to All object create events catches both. |
| Exam angle | A Put-only trigger misses large uploads: classic gotcha. |

### 11. Queue typo and hidden policy

| Field | Detail |
|---|---|
| What happened | Queue named `dea-ingest-d1q` (digit 1); still worked. |
| Root cause | Console auto-attached `AWSLambdaSQSQueueDestinationExecutionRole-…` for that queue; own policy pointed elsewhere. |
| Fix | Recreated `dea-ingest-dlq` (copy-paste names), repointed destination, removed the auto policy. |
| Exam angle | Wizards add customer managed policies quietly; review role policies. AWS managed vs customer managed. |

### 12. Alarm email "missing"

| Field | Detail |
|---|---|
| What happened | No alarm email arrived. |
| Root cause | Alarm fired and SNS action succeeded (History tab); email went to spam. |
| Fix | Marked not spam; add `no-reply@sns.amazonaws.com` to safe senders. |
| Exam angle | Trace the chain: metric → alarm History → SNS action → subscription → inbox. |
