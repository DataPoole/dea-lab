-- Build 6 checks (workgroup dea-wg)
SELECT year, month, count(*) AS trips
FROM trips_enriched
GROUP BY year, month
ORDER BY year, month;

SELECT pickup_borough, count(*) AS trips, round(avg(fare_amount), 2) AS avg_fare
FROM trips_enriched
GROUP BY pickup_borough
ORDER BY trips DESC;

-- Iceberg current state from the DMS change log (workgroup dea-etl-wg)
SELECT op, count(*) AS rows
FROM dms_zones
GROUP BY op
ORDER BY op;

CREATE TABLE dea_db.zones_current (
  location_id int,
  borough string,
  zone string,
  service_zone string,
  updated_at timestamp)
LOCATION 's3://dea-lake-124118675794/curated/zones_current/'
TBLPROPERTIES ('table_type' = 'ICEBERG');

MERGE INTO dea_db.zones_current t
USING (
  SELECT location_id, borough, zone, service_zone, updated_at, op
  FROM (
    SELECT *,
      row_number() OVER (
        PARTITION BY location_id
        ORDER BY dms_ts DESC,
          CASE op WHEN 'D' THEN 3 WHEN 'U' THEN 2 ELSE 1 END DESC
      ) AS rn
    FROM dea_db.dms_zones
  ) x
  WHERE rn = 1
) s
ON t.location_id = s.location_id
WHEN MATCHED AND s.op = 'D' THEN DELETE
WHEN MATCHED THEN UPDATE SET
  borough = s.borough,
  zone = s.zone,
  service_zone = s.service_zone,
  updated_at = CAST(s.updated_at AS timestamp)
WHEN NOT MATCHED AND s.op <> 'D' THEN INSERT
  (location_id, borough, zone, service_zone, updated_at)
  VALUES (CAST(s.location_id AS int), s.borough, s.zone, s.service_zone, CAST(s.updated_at AS timestamp));

SELECT count(*) AS zones,
       count_if(zone LIKE '%(test)%') AS test_edits,
       count_if(location_id = 999) AS zone_999
FROM dea_db.zones_current;
