CALL mysql.rds_set_configuration('binlog retention hours', 24);

CREATE TABLE zones (
  location_id  INT PRIMARY KEY,
  borough      VARCHAR(40),
  zone         VARCHAR(80),
  service_zone VARCHAR(40),
  updated_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

LOAD DATA LOCAL INFILE 'data/taxi_zone_lookup.csv' INTO TABLE zones
  FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"'
  LINES TERMINATED BY '\r\n'
  IGNORE 1 LINES
  (location_id, borough, zone, service_zone);

SELECT COUNT(*) AS zones FROM zones;
SHOW VARIABLES LIKE 'binlog_format';
