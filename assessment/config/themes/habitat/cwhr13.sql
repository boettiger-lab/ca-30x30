-- Major habitats (CWHR 13-class, CAL FIRE FVEG 2022): each class's extent in
-- the area and the share in 30x30 Conservation Areas (GAP 1-2), other conserved
-- or public land (GAP 3-4), and non-conserved land. Fractional res-10 cells,
-- masked to California's land grid; area-weighted.
WITH land AS MATERIALIZED ({{LAND}}),
names(code, label) AS (VALUES
  (10, 'Agriculture'), (20, 'Barren/Other'), (31, 'Conifer Forest'), (32, 'Conifer Woodland'),
  (41, 'Desert Shrub'), (42, 'Desert Woodland'), (51, 'Hardwood Forest'), (52, 'Hardwood Woodland'),
  (60, 'Grassland'), (70, 'Shrub'), (80, 'Urban'), (90, 'Water'), (100, 'Wetland')),
f AS (
  SELECT h.whr13num AS code, l.area_km2 * h.frac AS a, l.w12, l.w34
  FROM read_parquet('s3://public-ca30x30/cwhr13/hex-fractions/h0=*/data_0.parquet') h
  JOIN land l ON h.h0 = l.h0 AND h.h10 = l.h10
  WHERE h.whr13num <> 0
)
SELECT 'cwhr13:' || f.code AS feature, n.label,
       f.code IN (31, 32, 41, 42, 51, 52, 60, 70) AS natural,
       SUM(a) * 247.105 AS acres,
       SUM(a * w12) * 247.105 AS gap12_acres,
       SUM(a * w34) * 247.105 AS gap34_acres,
       SUM(a * w12) / SUM(a) AS frac_gap12,
       SUM(a * w34) / SUM(a) AS frac_gap34,
       1 - SUM(a * (w12 + w34)) / SUM(a) AS frac_none,
       SUM(a * w12) / NULLIF(SUM(SUM(a * w12)) OVER (), 0) AS share_of_network
FROM f JOIN names n USING (code)
GROUP BY f.code, n.label
ORDER BY frac_gap12
