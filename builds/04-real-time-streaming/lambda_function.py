import base64, json, os, time

SLEEP = float(os.environ.get("SLEEP_SECONDS", "0"))

def lambda_handler(event, context):
    big = 0
    for record in event["Records"]:
        raw = base64.b64decode(record["kinesis"]["data"])   # Kinesis data arrives base64
        try:
            trip = json.loads(raw)
        except json.JSONDecodeError:
            print(f"BAD RECORD skipped: {raw[:60]}")         # never let one bad record block the shard
            continue
        if trip["fare"] > 200:
            big += 1
            print(f"BIG FARE ${trip['fare']} vehicle={trip['vehicle_id']} zone={trip['pickup_zone']}")
    time.sleep(SLEEP)
    print(f"batch={len(event['Records'])} big_fares={big}")
