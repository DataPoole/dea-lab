import os
from urllib.parse import unquote_plus

import boto3
import pandas as pd

s3 = boto3.client("s3")
MIN_ROWS = int(os.environ["MIN_ROWS"])
DEST = os.environ["BUCKET"]
EXPECTED = {"VendorID", "tpep_pickup_datetime", "tpep_dropoff_datetime",
            "passenger_count", "trip_distance", "RatecodeID",
            "store_and_fwd_flag", "PULocationID", "DOLocationID",
            "payment_type", "fare_amount", "extra", "mta_tax", "tip_amount",
            "tolls_amount", "improvement_surcharge", "total_amount",
            "congestion_surcharge", "Airport_fee"}

def lambda_handler(event, context):
    # 1. Find the file
    record = event["Records"][0]
    bucket = record["s3"]["bucket"]['name']
    key = unquote_plus(record["s3"]["object"]["key"])

    # 2. Read it
    obj =s3.get_object(Bucket=bucket, Key=key)
    df = pd.read_csv(obj["Body"])
    # 3. Check it
    missing = EXPECTED - set(df.columns)
    enough_rows = len(df) >= MIN_ROWS
    good = not missing and enough_rows
    # 4. Route it
    zone = "clean/" if good else "quarantine/"
    dest_key = key.replace("raw/", zone, 1)
    s3.copy_object(
        Bucket=DEST,
        Key=dest_key,
        CopySource={"Bucket": bucket, "Key": key},
    )
    # 5. Report
    print(f"{key} -> {dest_key} | rows={len(df)} | missing={sorted(missing)}")
    return {"status": "clean" if good else "quarantine", "dest": dest_key}