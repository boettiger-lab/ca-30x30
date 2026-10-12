-- Conservation status within each ecoregion that overlaps the area, and each
-- ecoregion's share of the area's 30x30 network (GAP 1-2 acres).
-- A cell on an ecoregion boundary is assigned to one ecoregion.
WITH land AS MATERIALIZED ({{LAND}}),
eco AS (
  SELECT l.h10, any_value(l.area_km2) AS area_km2, any_value(l.w12) AS w12, any_value(l.w34) AS w34,
         min(e.CA_Ecoregi) AS ecoregion
  FROM read_parquet('s3://public-ca30x30/ecoregion/hex/h0=*/data_0.parquet') e
  JOIN land l ON e.h0 = l.h0 AND e.h10 = l.h10
  GROUP BY l.h10
)
SELECT ecoregion AS feature, ecoregion AS label,
       SUM(area_km2) * 247.105 AS acres,
       SUM(area_km2 * w12) * 247.105 AS gap12_acres,
       SUM(area_km2 * w34) * 247.105 AS gap34_acres,
       SUM(area_km2 * w12) / SUM(area_km2) AS frac_gap12,
       SUM(area_km2 * w34) / SUM(area_km2) AS frac_gap34,
       1 - SUM(area_km2 * (w12 + w34)) / SUM(area_km2) AS frac_none,
       SUM(area_km2 * w12) / SUM(SUM(area_km2 * w12)) OVER () AS share_of_network
FROM eco
GROUP BY ecoregion
ORDER BY gap12_acres DESC
