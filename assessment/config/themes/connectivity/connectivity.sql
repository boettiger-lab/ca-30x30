-- Connectivity features as in the 2025 Biodiversity Assessment (Table 12):
--   present-day connectivity (Cameron et al. 2022): channelized (41, 45, 49),
--     intensified (31, 35, 39) and diffuse (25, 29) categories;
--   climate linkages (Schloss et al. 2022): every class that is also a
--     climate-change linkage under either climate model (x01-x03);
--   South Coast Missing Linkages (Beier et al. 2006).
-- Res-9 fractional cells (connectivity) and res-8 presence (linkages), applied
-- to the area's res-10 land cells; area-weighted.
WITH land AS MATERIALIZED ({{LAND}}),
pd AS (
  SELECT CASE WHEN c.connectivity_category IN (41, 45, 49) THEN 'chn'
              WHEN c.connectivity_category IN (31, 35, 39) THEN 'int'
              ELSE 'diff' END AS code, c.h0, c.h9, c.frac
  FROM read_parquet('s3://public-connectivity/present-day-connectivity-categories/hex-fractions/h0=*/data_0.parquet') c
  WHERE c.connectivity_category IN (25, 29, 31, 35, 39, 41, 45, 49)
    AND (c.h0, c.h9) IN (SELECT DISTINCT h0, h9 FROM land)
),
cl AS (
  SELECT 'clink' AS code, c.h0, c.h9, SUM(c.frac) AS frac
  FROM read_parquet('s3://public-connectivity/climate-migration-routes/hex-fractions/h0=*/data_0.parquet') c
  WHERE c.connectivity_class IN (101, 102, 103, 201, 202, 203, 301, 302, 303)
    AND (c.h0, c.h9) IN (SELECT DISTINCT h0, h9 FROM land)
  GROUP BY c.h0, c.h9
),
lk AS (
  SELECT DISTINCT h0, h8
  FROM read_parquet('s3://public-connectivity/regional-connectivity-linkages/hex/h0=*/data_0.parquet')
  WHERE (h0, h8) IN (SELECT DISTINCT h0, h8 FROM land)
),
f AS (
  SELECT x.code, l.area_km2 * x.frac AS a, l.w12, l.w34
  FROM (SELECT * FROM pd UNION ALL SELECT * FROM cl) x JOIN land l ON l.h0 = x.h0 AND l.h9 = x.h9
  UNION ALL
  SELECT 'scml', l.area_km2, l.w12, l.w34 FROM lk JOIN land l ON l.h0 = lk.h0 AND l.h8 = lk.h8
),
names(code, feature, label, ord) AS (VALUES
  ('chn', 'conn:chn', 'Channelized connectivity', 1),
  ('int', 'conn:int', 'Intensified connectivity', 2),
  ('diff', 'conn:diff', 'Diffuse connectivity', 3),
  ('clink', 'conn:clink', 'Climate linkages', 4),
  ('scml', 'link:scml', 'South Coast Missing Linkages', 5))
SELECT n.feature, n.label,
       COALESCE(SUM(a), 0) * 247.105 AS acres,
       SUM(a * w12) * 247.105 AS gap12_acres,
       SUM(a * w34) * 247.105 AS gap34_acres,
       SUM(a * w12) / SUM(a) AS frac_gap12,
       SUM(a * w34) / SUM(a) AS frac_gap34,
       1 - SUM(a * (w12 + w34)) / SUM(a) AS frac_none
FROM names n LEFT JOIN f USING (code)
GROUP BY n.feature, n.label, n.ord
ORDER BY n.ord
