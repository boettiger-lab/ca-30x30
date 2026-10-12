-- Land characterization: share of the area's California land in 30x30
-- Conservation Areas (GAP 1-2), other conserved or public land (GAP 3-4),
-- and land outside any conserved-area unit. Res-10 land grid, area-weighted.
WITH land AS MATERIALIZED ({{LAND}}),
s AS (
  SELECT SUM(area_km2) AS land_km2,
         SUM(area_km2 * w12) AS gap12_km2,
         SUM(area_km2 * w34) AS gap34_km2
  FROM land
)
SELECT land_km2 * 247.105 AS land_acres,
       gap12_km2 * 247.105 AS gap12_acres,
       gap34_km2 * 247.105 AS gap34_acres,
       (land_km2 - gap12_km2 - gap34_km2) * 247.105 AS none_acres,
       gap12_km2 / land_km2 AS frac_gap12,
       gap34_km2 / land_km2 AS frac_gap34,
       1 - (gap12_km2 + gap34_km2) / land_km2 AS frac_none
FROM s
