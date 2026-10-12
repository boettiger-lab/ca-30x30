-- Freshwater features as in the 2025 Biodiversity Assessment (Table 13).
--   Wetlands: NWI (California) freshwater emergent, freshwater forested/shrub,
--     and estuarine & marine wetland types; res-10 presence.
--   Groundwater-dependent ecosystems: GDE vegetation or wetlands; res-10 presence.
--   100-year floodplain: FEMA NFHL Special Flood Hazard Areas; res-10 presence.
--     NOTE: the assessment used First Street Foundation flood zones, which this
--     catalog does not carry, so this row is not the assessment's feature.
--   Freshwater species richness: HUC12 watersheds in the statewide top 20% of
--     freshwater species count; res-8 presence.
-- Presence cells are the area's res-10 California land cells; area-weighted.
WITH land AS MATERIALIZED ({{LAND}}),
cells AS (SELECT DISTINCT h0, h10 FROM land),
wet AS (
  SELECT DISTINCT 'wetlands' AS code, h0, h10 FROM read_parquet('s3://public-wetlands/nwi-v2/hex/h0=*/data_0.parquet')
  WHERE state_code = 'CA' AND WETLAND_TYPE IN ('Freshwater Emergent Wetland', 'Freshwater Forested/Shrub Wetland', 'Estuarine and Marine Wetland')
    AND (h0, h10) IN (SELECT * FROM cells)
),
gde AS (
  SELECT DISTINCT 'gde' AS code, h0, h10 FROM (
    SELECT h0, h10 FROM read_parquet('s3://public-ca30x30/groundwater-dependent-ecosystems/vegetation/hex/h0=*/data_0.parquet')
    WHERE (h0, h10) IN (SELECT * FROM cells)
    UNION ALL
    SELECT h0, h10 FROM read_parquet('s3://public-ca30x30/groundwater-dependent-ecosystems/wetlands/hex/h0=*/data_0.parquet')
    WHERE (h0, h10) IN (SELECT * FROM cells))
),
fld AS (
  SELECT DISTINCT 'floodplain' AS code, h0, h10 FROM read_parquet('s3://public-hazard/flood-hazard/hex/h0=*/data_0.parquet')
  WHERE SFHA_TF = 'T' AND (h0, h10) IN (SELECT * FROM cells)
),
fwq AS (
  SELECT quantile_cont(Freshwater_Species_Count, 0.8) AS q
  FROM (SELECT DISTINCT Watershed_ID, Freshwater_Species_Count FROM read_parquet('s3://public-ca30x30/freshwater-species-richness.parquet'))
),
fw AS (
  SELECT DISTINCT h.h0, h.h8 FROM read_parquet('s3://public-ca30x30/freshwater-species-richness/hex/h0=*/data_0.parquet') h, fwq
  WHERE h.Freshwater_Species_Count >= fwq.q AND (h.h0, h.h8) IN (SELECT DISTINCT h0, h8 FROM land)
),
f AS (
  SELECT x.code, l.area_km2 AS a, l.w12, l.w34
  FROM (SELECT * FROM wet UNION ALL SELECT * FROM gde UNION ALL SELECT * FROM fld) x
  JOIN land l ON l.h0 = x.h0 AND l.h10 = x.h10
  UNION ALL
  SELECT 'fwrich', l.area_km2, l.w12, l.w34 FROM fw JOIN land l ON l.h0 = fw.h0 AND l.h8 = fw.h8
),
names(code, feature, label, ord) AS (VALUES
  ('wetlands', 'fw:wetlands', 'Remaining wetlands', 1),
  ('gde', 'fw:gde', 'Groundwater-dependent ecosystems', 2),
  ('floodplain', 'fw:floodplain', '100-year floodplain (FEMA; assessment used First Street)', 6),
  ('fwrich', 'fw:fwrich', 'Watersheds with top 20% freshwater species richness', 7))
SELECT n.feature, n.label, 'acres' AS measure,
       COALESCE(SUM(a), 0) * 247.105 AS acres,
       SUM(a * w12) * 247.105 AS gap12_acres,
       SUM(a * w34) * 247.105 AS gap34_acres,
       SUM(a * w12) / SUM(a) AS frac_gap12,
       SUM(a * w34) / SUM(a) AS frac_gap34,
       1 - SUM(a * (w12 + w34)) / SUM(a) AS frac_none,
       n.ord
FROM names n LEFT JOIN f USING (code)
GROUP BY n.feature, n.label, n.ord
ORDER BY n.ord
