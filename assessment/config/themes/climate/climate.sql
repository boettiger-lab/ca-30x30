-- Climate and disturbance features, with the share of each in 30x30 and the
-- share of the area's 30x30 network each covers.
--   Burned in the past decade: CAL FIRE fire perimeters, 2015 onward; res-10 presence.
--   Mid-century climate exposure (Thorne et al. 2016): natural vegetation
--     (CWHR13 classes other than agriculture and urban) with exposure >= 0.9,
--     separately for the MIROC5 (hot-dry) and CNRM-CM5 (warm-wet) models; res-9.
--     The report states no cutoff; 0.9 on the res-9 cell mean reproduces its
--     extents (MIROC5 25.5M vs 26.7M ac, CNRM-CM5 27.9M vs 28.5M) and its 32% of
--     the network climate-stressed.
--   Sea-level rise, 5 ft (NOAA): res-10 presence, California.
--     NOTE: NOAA's inundation layer includes existing open water, so its extent
--     differs from the report's (see ca-30x30#104).
WITH land AS MATERIALIZED ({{LAND}}),
cells AS (SELECT DISTINCT h0, h10 FROM land),
net AS (SELECT SUM(area_km2 * w12) AS n FROM land),
fire AS (
  SELECT DISTINCT 'fire' AS code, h0, h10 FROM read_parquet('s3://public-fire/calfire-2025/firep/hex/h0=*/data_0.parquet')
  WHERE YEAR_ >= 2015 AND (h0, h10) IN (SELECT * FROM cells)
),
slr AS (
  SELECT DISTINCT 'slr' AS code, h0, h10 FROM read_parquet('s3://public-hazard/sea-level-rise/hex/h0=*/data_0.parquet')
  WHERE slr_ft = 5 AND (h0, h10) IN (SELECT * FROM cells)
),
nat AS MATERIALIZED (
  SELECT l.* FROM land l
  JOIN read_parquet('s3://public-ca30x30/cwhr13/hex/h0=*/data_0.parquet') c ON c.h0 = l.h0 AND c.h10 = l.h10
  WHERE c.whr13num NOT IN (0, 10, 80)
),
expo AS (
  SELECT 'miroc' AS code, n.area_km2 AS a, n.w12, n.w34 FROM nat n
  JOIN read_parquet('s3://public-hazard/mid-century-habitat-climate-exposure/miroc/hex/h0=*/data_0.parquet') x ON x.h0 = n.h0 AND x.h9 = n.h9
  WHERE x.exposure >= 0.9
  UNION ALL
  SELECT 'cnrm', n.area_km2, n.w12, n.w34 FROM nat n
  JOIN read_parquet('s3://public-hazard/mid-century-habitat-climate-exposure/cnrm/hex/h0=*/data_0.parquet') x ON x.h0 = n.h0 AND x.h9 = n.h9
  WHERE x.exposure >= 0.9
),
f AS (
  SELECT x.code, l.area_km2 AS a, l.w12, l.w34
  FROM (SELECT * FROM fire UNION ALL SELECT * FROM slr) x JOIN land l ON l.h0 = x.h0 AND l.h10 = x.h10
  UNION ALL SELECT * FROM expo
),
names(code, feature, label, ord) AS (VALUES
  ('fire', 'clim:fire', 'Burned since 2015 (CAL FIRE perimeters)', 1),
  ('miroc', 'clim:miroc', 'Climate-exposed natural vegetation, mid-century (MIROC5, hot-dry)', 2),
  ('cnrm', 'clim:cnrm', 'Climate-exposed natural vegetation, mid-century (CNRM-CM5, warm-wet)', 3),
  ('slr', 'clim:slr', 'Sea-level rise, 5 ft (NOAA; extent differs from the report)', 4))
SELECT n.feature, n.label,
       COALESCE(SUM(a), 0) * 247.105 AS acres,
       SUM(a * w12) * 247.105 AS gap12_acres,
       SUM(a * w34) * 247.105 AS gap34_acres,
       SUM(a * w12) / SUM(a) AS frac_gap12,
       SUM(a * w34) / SUM(a) AS frac_gap34,
       1 - SUM(a * (w12 + w34)) / SUM(a) AS frac_none,
       COALESCE(SUM(a * w12), 0) / ANY_VALUE(net.n) AS share_of_network
FROM names n LEFT JOIN f USING (code) CROSS JOIN net
GROUP BY n.feature, n.label, n.ord
ORDER BY n.ord
