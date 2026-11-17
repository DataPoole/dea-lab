-- Build 3: Schema Catalog and SQL Analytics (Glue + Athena)
-- Database: dea_db. Run analyst queries in workgroup dea-wg, CTAS in dea-etl-wg.
-- One statement per Athena tab.

-- ============ Analysis queries (CSV tables) ============

-- q1_trips_by_month
SELECT year, month, count(*) AS trips, round(avg(fare_amount), 2) AS avg_fare
FROM trips
GROUP BY year, month
ORDER BY year, month;

-- q2_top_pickup_zones
SELECT z.borough, z.zone, count(*) AS trips
FROM trips t
JOIN zones z ON t.pulocationid = z.locationid
GROUP BY z.borough, z.zone
ORDER BY trips DESC
LIMIT 10;

-- q3_tip_pct_by_payment
SELECT payment_type, count(*) AS trips,
       round(avg(tip_amount / fare_amount) * 100, 1) AS avg_tip_pct
FROM trips
WHERE fare_amount > 0
GROUP BY payment_type
ORDER BY payment_type;

-- q4_trips_by_hour (pickup time is a string in the CSV table)
SELECT hour(date_parse(tpep_pickup_datetime, '%Y-%m-%d %H:%i:%s')) AS pickup_hour,
       count(*) AS trips
FROM trips
GROUP BY 1
ORDER BY 1;

-- ============ CSV to Parquet (workgroup dea-etl-wg) ============

-- ctas_trips_parquet
CREATE TABLE dea_db.trips_parquet
WITH (
  format = 'PARQUET',
  write_compression = 'SNAPPY',
  external_location = 's3://dea-lake-ACCOUNT_ID/curated/trips_parquet/',
  partitioned_by = ARRAY['year', 'month']
) AS
SELECT * FROM trips;

-- ctas_zones_clean (removes literal quote marks left by the CSV SerDe)
CREATE TABLE dea_db.zones_clean
WITH (
  format = 'PARQUET',
  external_location = 's3://dea-lake-ACCOUNT_ID/curated/zones/'
) AS
SELECT locationid,
       replace(borough, '"', '')      AS borough,
       replace(zone, '"', '')         AS zone,
       replace(service_zone, '"', '') AS service_zone
FROM zones;

-- ============ Parquet versions (workgroup dea-wg) ============

-- q1p_trips_by_month
SELECT year, month, count(*) AS trips, round(avg(fare_amount), 2) AS avg_fare
FROM trips_parquet
GROUP BY year, month
ORDER BY year, month;

-- q2p_top_pickup_zones
SELECT z.borough, z.zone, count(*) AS trips
FROM trips_parquet t
JOIN zones_clean z ON t.pulocationid = z.locationid
GROUP BY z.borough, z.zone
ORDER BY trips DESC
LIMIT 10;

-- q3p_tip_pct_by_payment
SELECT payment_type, count(*) AS trips,
       round(avg(tip_amount / fare_amount) * 100, 1) AS avg_tip_pct
FROM trips_parquet
WHERE fare_amount > 0
GROUP BY payment_type
ORDER BY payment_type;

-- q4p_trips_by_hour
SELECT hour(date_parse(tpep_pickup_datetime, '%Y-%m-%d %H:%i:%s')) AS pickup_hour,
       count(*) AS trips
FROM trips_parquet
GROUP BY 1
ORDER BY 1;

-- ============ Partition management ============

-- MSCK: register Hive-style folders found in S3 (adds only, never removes)
MSCK REPAIR TABLE trips;

-- Remove a partition from the catalog (data in S3 is untouched)
ALTER TABLE trips DROP IF EXISTS PARTITION (year='2024', month='03');

-- ddl_partition_projection
ALTER TABLE trips SET TBLPROPERTIES (
  'projection.enabled'        = 'true',
  'projection.year.type'      = 'integer',
  'projection.year.range'     = '2024,2026',
  'projection.month.type'     = 'integer',
  'projection.month.range'    = '1,12',
  'projection.month.digits'   = '2',
  'storage.location.template' = 's3://dea-lake-ACCOUNT_ID/clean/trips/year=${year}/month=${month}/'
);

-- Check
SHOW TBLPROPERTIES trips;
SELECT month, count(*) AS trips FROM trips GROUP BY month ORDER BY month;
