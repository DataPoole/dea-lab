import json, random, sys, time, uuid
from datetime import datetime, timezone
import boto3

kinesis = boto3.client("kinesis", region_name="us-east-1")
STREAM = "dea-trip-events"

def make_trip():
    return {
        "event_id": str(uuid.uuid4()),
        "vehicle_id": f"V{random.randint(1, 50):03d}",
        "pickup_zone": random.randint(1, 263),
        "dropoff_zone": random.randint(1, 263),
        "fare": round(random.uniform(5, 250), 2),
        "passengers": random.randint(1, 4),
        "event_ts": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
    }

eps, seconds = int(sys.argv[1]), int(sys.argv[2])    # events per second, run time
hot = len(sys.argv) > 3 and sys.argv[3] == "hot"     # one fixed key for Break it

for _ in range(seconds):
    trips = [make_trip() for _ in range(eps)]
    records = [{"Data": json.dumps(t), "PartitionKey": "V001" if hot else t["vehicle_id"]} for t in trips]
    failed = 0
    for i in range(0, len(records), 500):
        resp = kinesis.put_records(StreamName=STREAM, Records=records[i:i + 500])
        failed += resp["FailedRecordCount"]
    print(f"sent={len(records)} failed={failed}")
    time.sleep(1)
