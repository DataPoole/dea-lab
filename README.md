# NYC Taxi Data Lake on AWS

A serverless data pipeline on AWS that ingests, validates, catalogs and serves NYC taxi trip data.
Built hands-on, one layer at a time, while preparing for the AWS Certified Data Engineer – Associate (DEA-C01) exam.

**Status:** in progress · 6 of 16 builds complete · Region `us-east-1`

## Architecture

```mermaid
flowchart LR
  U[CSV upload] --> R[(S3 raw/)]
  R -->|S3 event| L[Lambda: validate]
  L -->|valid| C[(S3 clean/)]
  L -->|invalid| Q[(S3 quarantine/)]
  L -.->|failed after retries| D[SQS failure queue]
  L -.->|errors| A[CloudWatch alarm] --> S[SNS email]
  C --> K[Glue crawler] --> G[Glue Data Catalog]
  G --> AT[Athena workgroups]
  AT -->|CTAS| P[(S3 curated/ Parquet)]
  PR[Trip event producer] --> KS[Kinesis Data Streams]
  KS --> LB[Lambda: real-time alerts]
  KS --> FH[Firehose: JSON to Parquet] --> RS[(S3 raw/stream/)]
  RS --> AT
  DB[(RDS MySQL)] -->|DMS full load + CDC| DM[(S3 raw/dms/)]
  DM --> AT
  C --> GJ[Glue ETL job<br/>join + DQ gate] --> E[(S3 curated/trips_enriched<br/>Parquet, partitioned)]
  E --> AT
  DM --> MG[Athena MERGE INTO] --> IC[(Iceberg zones_current)]
```

## Builds

| # | Build | Services | Result |
|---|---|---|---|
| 1 | [Data Lake Zones and Tiering](builds/01-data-lake-zones/) | S3 | Zoned, partitioned, versioned lake with lifecycle tiering |
| 2 | [Event-Driven File Validation](builds/02-event-driven-validation/) | S3, Lambda, SQS, CloudWatch, SNS | Files validated on arrival; failures captured and alerted |
| 3 | [Schema Catalog and SQL Analytics](builds/03-schema-catalog-sql/) | Glue, Athena | Cataloged lake; Parquet cut data scanned up to 100x; partition projection |
| 4 | [Real-Time Trip Streaming](builds/04-real-time-streaming/) | Kinesis, Firehose, Lambda | Events queryable as Parquet within a minute; bad records isolated |
| 5 | [Database Change Capture](builds/05-database-cdc/) | RDS MySQL, DMS, VPC endpoint | Inserts, updates and deletes replicated to S3; survived a paused task |
| 6 | [ETL with Data Quality Gates](builds/06-etl-data-quality/) | Glue ETL, Glue Data Quality, Athena, Iceberg | 578,642 trips cleaned and enriched behind a DQ gate; CDC merged into a current-state Iceberg table |

**Coming next:**
Orchestration (Step Functions) ·
data warehouse (Redshift Serverless) · pipeline as code (SAM) · governance and PII (Lake Formation).

## Skills shown

- **Data lake design:** zones, Hive-style partitions, storage tiering based on access patterns
- **Event-driven pipelines:** S3 notifications, Lambda, async retries, failure destinations
- **Streaming:** Kinesis Data Streams, Firehose format conversion, stream consumers, poison-record handling
- **Database replication:** DMS full load + CDC, MySQL binlog setup, private networking with VPC endpoints, Secrets Manager
- **ETL:** Glue Studio visual jobs, Spark SQL joins, job bookmarks, catalog updates from the job
- **Data quality:** schema and row-count checks with a quarantine path; Glue Data Quality (DQDL) gate that fails the job before loading
- **Lakehouse tables:** Apache Iceberg with idempotent `MERGE INTO` for CDC upserts and deletes
- **Security:** least-privilege IAM roles scoped to S3 prefixes; encryption at rest; no access keys
- **Operations:** CloudWatch alarms, SNS alerts, debugging timeouts and memory starvation
- **Query optimization:** columnar formats, partitioning, partition projection, workgroup scan limits
- **Cost control:** lifecycle rules, right-sized Lambda memory, budgets, teardown after each build

## Repo layout

```
builds/     one folder per build: README, code, IAM policies, screenshots
scripts/    helpers (sample data generator)
```

## Reproduce

1. AWS account with an admin role, AWS CLI v2, Python 3.12 with `pandas` and `pyarrow`.
2. Download sample data from the [NYC TLC trip record page](https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page) into `data/`.
3. `python scripts/make_csv_sample.py 2024-01` makes a 200,000-row CSV sample.
4. Follow each build's README in order. Hourly resources are torn down at the end of each build.
