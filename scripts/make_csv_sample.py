import sys
import pandas as pd

# 1. get month from cmd line
month = sys.argv[1]
src = f"data/yellow_tripdata_{month}.parquet"

# 2. read the Parquet file into dataframe
df = pd.read_parquet(src)

# 3. take a random sample
sample = df.sample(n=200_000, random_state=42)

# 4. build output path/write the CSV
dst = f"data/trips_{month.replace('-', '_')}.csv"
sample.to_csv(dst, index=False)

# 5. Print Summary
print(f"Wrote {len(sample):,} rows to {dst}")
print("Columns:", list(sample.columns))


