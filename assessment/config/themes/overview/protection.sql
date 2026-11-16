-- Land characterization: share of the area's California land in 30x30
-- Conservation Areas (GAP 1-2), other conserved or public land (GAP 3-4),
-- and land outside any conserved-area unit. Res-10 land grid, area-weighted.
-- With a manager selected, GAP 1-2 and GAP 3-4 count only that manager's
-- units, and other managers' conserved land is `other`.
WITH land AS MATERIALIZED ({{LAND}}),
s AS (
  SELECT SUM(area_km2) AS land_km2,
         SUM(area_km2 * w12) AS gap12_km2,
         SUM(area_km2 * w34) AS gap34_km2,
         SUM(area_km2 * wc) AS conserved_km2
  FROM land
)
SELECT land_km2 * 247.105 AS land_acres,
       gap12_km2 * 247.105 AS gap12_acres,
       gap34_km2 * 247.105 AS gap34_acres,
       (conserved_km2 - gap12_km2 - gap34_km2) * 247.105 AS other_acres,
       (land_km2 - conserved_km2) * 247.105 AS none_acres,
       gap12_km2 / land_km2 AS frac_gap12,
       gap34_km2 / land_km2 AS frac_gap34,
       (conserved_km2 - gap12_km2 - gap34_km2) / land_km2 AS frac_other,
       1 - conserved_km2 / land_km2 AS frac_none,
       -- with a manager selected: the manager's land as a share of the area,
       -- and the split of that land between 30x30 and GAP 3-4
       (gap12_km2 + gap34_km2) * 247.105 AS own_acres,
       (gap12_km2 + gap34_km2) / land_km2 AS frac_own,
       gap12_km2 / NULLIF(gap12_km2 + gap34_km2, 0) AS own_frac_gap12,
       gap34_km2 / NULLIF(gap12_km2 + gap34_km2, 0) AS own_frac_gap34,
       -- the area's share of California: this query's statewide land_acres
       land_km2 * 247.105 / 101471550.0 AS frac_of_state
FROM s
