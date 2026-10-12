-- Rivers and streams by order (Table 13), from the NHDPlus HR network
-- (innetwork = 1, streamorde > 0): headwaters (order 1-2), streams (3-5),
-- rivers (6+). A length measure: each flowline's length is spread evenly over
-- the res-8 cells it crosses, and only cells on the area's California land
-- grid count (the network is national). A cell's conservation status is the
-- area-weighted GAP share of its res-10 land cells in the area.
-- Our high-resolution network carries ~3x the channel length of the
-- medium-resolution network the assessment used; shares compare, lengths do not.
WITH land AS MATERIALIZED ({{LAND}}),
c8 AS MATERIALIZED (
  SELECT h0, h8, SUM(area_km2 * w12) / SUM(area_km2) AS w12, SUM(area_km2 * w34) / SUM(area_km2) AS w34
  FROM land GROUP BY h0, h8
),
fl AS MATERIALIZED (
  SELECT nhdplusid, any_value(lengthkm) AS lengthkm, any_value(streamorde) AS ord, h0, h8
  FROM read_parquet('s3://public-usgs-nhd/nhdplus-hr/flowline/hex/h0=*/data_0.parquet')
  WHERE innetwork = 1 AND streamorde > 0 AND h0 IN (SELECT DISTINCT h0 FROM c8)
  GROUP BY nhdplusid, h0, h8
),
per AS (  -- each flowline's share of length per cell
  SELECT nhdplusid, ord, h0, h8, lengthkm / COUNT(*) OVER (PARTITION BY nhdplusid) AS km FROM fl
),
f AS (
  SELECT CASE WHEN ord <= 2 THEN 'headwaters' WHEN ord <= 5 THEN 'streams' ELSE 'rivers' END AS code,
         p.km AS a, c.w12, c.w34
  FROM per p JOIN c8 c ON c.h0 = p.h0 AND c.h8 = p.h8
),
names(code, feature, label, ord) AS (VALUES
  ('rivers', 'fw:rivers', 'Rivers (order 6+)', 3),
  ('streams', 'fw:streams', 'Streams (order 3-5)', 4),
  ('headwaters', 'fw:headwaters', 'Headwaters (order 1-2)', 5))
SELECT n.feature, n.label, 'miles' AS measure,
       COALESCE(SUM(a), 0) * 0.621371 AS miles,
       SUM(a * w12) / SUM(a) AS frac_gap12,
       SUM(a * w34) / SUM(a) AS frac_gap34,
       1 - SUM(a * (w12 + w34)) / SUM(a) AS frac_none,
       n.ord
FROM names n LEFT JOIN f USING (code)
GROUP BY n.feature, n.label, n.ord
ORDER BY n.ord
