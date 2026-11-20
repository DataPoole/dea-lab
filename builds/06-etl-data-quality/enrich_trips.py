import sys
from awsglue.transforms import *
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from awsglue.context import GlueContext
from awsglue.job import Job
from awsgluedq.transforms import EvaluateDataQuality
from awsglue import DynamicFrame

def sparkSqlQuery(glueContext, query, mapping, transformation_ctx) -> DynamicFrame:
    for alias, frame in mapping.items():
        frame.toDF().createOrReplaceTempView(alias)
    result = spark.sql(query)
    return DynamicFrame.fromDF(result, glueContext, transformation_ctx)
args = getResolvedOptions(sys.argv, ['JOB_NAME'])
sc = SparkContext()
glueContext = GlueContext(sc)
spark = glueContext.spark_session
job = Job(glueContext)
job.init(args['JOB_NAME'], args)

# Script generated for node trips_csv
trips_csv_node1795178575346 = glueContext.create_dynamic_frame.from_options(format_options={"quoteChar": "\"", "withHeader": True, "separator": ",", "optimizePerformance": False}, connection_type="s3", format="csv", connection_options={"paths": ["s3://dea-lake-124118675794/clean/trips/"], "recurse": True}, transformation_ctx="trips_csv_node1795178575346")

# Script generated for node zones
zones_node1795178857749 = glueContext.create_dynamic_frame.from_catalog(database="dea_db", table_name="zones_clean", transformation_ctx="zones_node1795178857749")

# Script generated for node enrich
SqlQuery0 = '''
SELECT
  CAST(t.VendorID AS int) AS vendor_id,
  to_timestamp(t.tpep_pickup_datetime) AS pickup_ts,
  to_timestamp(t.tpep_dropoff_datetime) AS dropoff_ts,
  CAST(t.passenger_count AS double) AS passenger_count,
  CAST(t.trip_distance AS double) AS trip_distance,
  CAST(t.PULocationID AS int) AS pu_location_id,
  CAST(t.DOLocationID AS int) AS do_location_id,
  CAST(t.payment_type AS int) AS payment_type,
  CAST(t.fare_amount AS double) AS fare_amount,
  CAST(t.tip_amount AS double) AS tip_amount,
  CAST(t.total_amount AS double) AS total_amount,
  z.borough AS pickup_borough,
  z.zone AS pickup_zone,
  year(to_timestamp(t.tpep_pickup_datetime)) AS year,
  month(to_timestamp(t.tpep_pickup_datetime)) AS month
FROM trips t
LEFT JOIN zones z ON CAST(t.PULocationID AS int) = z.locationid
WHERE t.tpep_pickup_datetime IS NOT NULL
  AND CAST(t.fare_amount AS double) >= 0
  AND CAST(t.trip_distance AS double) > 0
  AND year(to_timestamp(t.tpep_pickup_datetime)) = 2024
'''
enrich_node1795178949086 = sparkSqlQuery(glueContext, query = SqlQuery0, mapping = {"zones":zones_node1795178857749, "trips":trips_csv_node1795178575346}, transformation_ctx = "enrich_node1795178949086")

# Script generated for node dq_gate
dq_gate_node1795179894676_ruleset = """
    Rules = [ RowCount > 100000, IsComplete "pickup_ts", IsComplete "pickup_borough", ColumnValues "fare_amount" >= 0 ]
"""

dq_gate_node1795179894676 = EvaluateDataQuality().process_rows(frame=enrich_node1795178949086, ruleset=dq_gate_node1795179894676_ruleset, publishing_options={"dataQualityEvaluationContext": "dq_gate_node1795179894676", "enableDataQualityCloudWatchMetrics": True, "enableDataQualityResultsPublishing": True}, additional_options={"observations.scope":"ALL","performanceTuning.caching":"CACHE_NOTHING"})

assert dq_gate_node1795179894676[EvaluateDataQuality.DATA_QUALITY_RULE_OUTCOMES_KEY].filter(lambda x: x["Outcome"] == "Failed").count() == 0, "The job failed due to failing DQ rules for node: enrich_node1795178949086"

# Script generated for node originalData
originalData_node1795179945993 = SelectFromCollection.apply(dfc=dq_gate_node1795179894676, key="originalData", transformation_ctx="originalData_node1795179945993")

# Script generated for node curated_parquet
curated_parquet_node1795180087482 = glueContext.getSink(path="s3://dea-lake-124118675794/curated/trips_enriched/", connection_type="s3", updateBehavior="UPDATE_IN_DATABASE", partitionKeys=[], enableUpdateCatalog=True, transformation_ctx="curated_parquet_node1795180087482")
curated_parquet_node1795180087482.setCatalogInfo(catalogDatabase="dea_db",catalogTableName="trips_enriched")
curated_parquet_node1795180087482.setFormat("glueparquet", compression="snappy")
curated_parquet_node1795180087482.writeFrame(originalData_node1795179945993)
job.commit()