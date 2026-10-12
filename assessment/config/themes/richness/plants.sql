-- Plant richness (Kling et al. 2019): the statewide top 20% of plant species
-- richness and of rarity-weighted endemic plant richness, as published (the
-- p80 assets are already thresholded statewide). Res-8 cells applied to the
-- area's res-10 land cells.
WITH land AS MATERIALIZED ({{LAND}}),
feat AS (
  SELECT DISTINCT 'plant' AS code, h0, h8 FROM read_parquet('s3://public-ca30x30/plant-richness/p80-hex/h0=*/data_0.parquet')
  WHERE (h0, h8) IN (SELECT DISTINCT h0, h8 FROM land)
  UNION ALL
  SELECT DISTINCT 'endp' AS code, h0, h8 FROM read_parquet('s3://public-ca30x30/rarity-weighted-endemic-plant-richness/p80-hex/h0=*/data_0.parquet')
  WHERE (h0, h8) IN (SELECT DISTINCT h0, h8 FROM land)
),
names(code, label, ord) AS (VALUES
  ('plant', 'Plant species richness (top 20%)', 1),
  ('endp', 'Rarity-weighted endemic plant richness (top 20%)', 2)),
f AS (SELECT feat.code, l.area_km2 AS a, l.w12, l.w34 FROM feat JOIN land l ON l.h0 = feat.h0 AND l.h8 = feat.h8)
SELECT 'kling:' || n.code AS feature, n.label, 'Plant richness' AS grp,
       COALESCE(SUM(a), 0) * 247.105 AS acres,
       SUM(a * w12) * 247.105 AS gap12_acres,
       SUM(a * w34) * 247.105 AS gap34_acres,
       SUM(a * w12) / SUM(a) AS frac_gap12,
       SUM(a * w34) / SUM(a) AS frac_gap34,
       1 - SUM(a * (w12 + w34)) / SUM(a) AS frac_none
FROM names n LEFT JOIN f USING (code)
GROUP BY n.code, n.label, n.ord
ORDER BY n.ord
