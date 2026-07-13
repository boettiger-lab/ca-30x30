# Canonical duckdb-geo queries

All run through the `duckdb-geo` MCP `query` tool over NRP S3 GeoParquet / H3 hex.
Method: the report's **proportional estimate** — for each conserved-area unit,
`feature_area_in_unit × (Final_g1_p + Final_g2_p)/100`, summed statewide ÷ statewide
feature extent — implemented as an H3 hex overlay at each feature's native resolution.
Constant cell area cancels in the ratio; the statewide baseline calibrates to ~25.4–26.1%.

## 1. Land characterization (flat GeoParquet, direct acre columns)

```sql
SELECT
  ROUND(100.0*SUM(Acres)/101.5e6, 2)                        AS pct_CA_gap12,      -- 26.08 (report 26.1)
  ROUND(100.0*SUM(Gap3_acres+Gap4_acres)/101.5e6, 2)        AS pct_CA_gap34,      -- 25.52 (report 25.5)
  ROUND(100.0 - 100.0*SUM(Acres+Gap3_acres+Gap4_acres)/101.5e6, 2) AS pct_nonconserved, -- 48.40
  SUM(Acres)                                                AS gap12_acres        -- 26,471,461
FROM read_parquet('s3://public-ca30x30/conserved-areas-terrestrial-2025.parquet');
```
Denominator = the hardwired official CA land area (101.5M ac).

## 2. Ecoregion network composition (%network) — all 20 exact

```sql
WITH t AS (SELECT CA_Ecoregi, SUM(Acres) g
           FROM read_parquet('s3://public-ca30x30/conserved-areas-terrestrial-2025.parquet')
           GROUP BY CA_Ecoregi)
SELECT CA_Ecoregi, ROUND(100.0*g/SUM(g) OVER (),2) pct FROM t ORDER BY pct DESC;
```

## 3. CWHR13 / CWHR-60 habitat representation (%feature) — res-10 fractional overlay

```sql
WITH cons AS (   -- per res-10 cell, the GAP1+2 weight (fraction of cell that is 30x30)
  SELECT h0, h10, SUM((Final_g1_p+Final_g2_p)/100.0) AS w
  FROM read_parquet('s3://public-ca30x30/conserved-areas-terrestrial-2025/hex/h0=*/data_0.parquet')
  GROUP BY h0, h10),
feat AS (
  SELECT h0, h10, whr13num, frac
  FROM read_parquet('s3://public-ca30x30/cwhr13/hex-fractions/h0=*/data_0.parquet')
  WHERE whr13num <> 0),
num AS (SELECT f.whr13num, SUM(f.frac*c.w) num FROM feat f JOIN cons c USING(h0,h10) GROUP BY 1),
den AS (SELECT whr13num, SUM(frac) den FROM feat GROUP BY 1)
SELECT d.whr13num, ROUND(100.0*n.num/d.den,2) pct_in_30x30
FROM den d LEFT JOIN num n USING(whr13num) ORDER BY d.whr13num;
```
Swap `cwhr13/hex-fractions` → `cwhr/hex-fractions` (col `whrnum`) for the 62 finer classes.
Network **composition** = renormalize `num` by `SUM(num) OVER ()` instead of by `den`.

## 4. Connectivity + climate migration (%feature) — res-9 fractional overlay

```sql
WITH cons9 AS (
  SELECT h0, h9, SUM((Final_g1_p+Final_g2_p)/100.0)/7.0 AS w   -- ÷7 res-10 children per res-9
  FROM read_parquet('s3://public-ca30x30/conserved-areas-terrestrial-2025/hex/h0=*/data_0.parquet')
  GROUP BY h0, h9),
feat AS (
  SELECT h0, h9,
    CASE WHEN connectivity_category IN (25,29) THEN 'diff'
         WHEN connectivity_category IN (31,35,39) THEN 'int'
         WHEN connectivity_category IN (41,45,49) THEN 'chn' END AS cat, frac
  FROM read_parquet('s3://public-connectivity/present-day-connectivity-categories/hex-fractions/h0=*/data_0.parquet')
  WHERE connectivity_category IN (25,29,31,35,39,41,45,49))
SELECT f.cat, ROUND(100.0*SUM(f.frac*LEAST(c.w,1.0))/SUM(f.frac),2) pct
FROM feat f JOIN cons9 c USING(h0,h9) GROUP BY f.cat;
```

## 5. res-8 features (ACE ranks/richness, Kling plant p80, regional linkages, freshwater richness)

Key: divide the conserved weight-sum by each h8's **actual** res-10 land-cell count
(`nland`), NOT a flat 49. And guard NULLs explicitly — DuckDB `LEAST(NULL,1)` returns 1.

```sql
WITH cons8 AS (
  SELECT h0,h8,SUM((Final_g1_p+Final_g2_p)/100.0) wsum
  FROM read_parquet('s3://public-ca30x30/conserved-areas-terrestrial-2025/hex/h0=*/data_0.parquet') GROUP BY h0,h8),
land8 AS (
  SELECT h0,h8,COUNT(DISTINCT h10) nland
  FROM read_parquet('s3://public-ca30x30/cwhr13/hex-fractions/h0=*/data_0.parquet')
  WHERE whr13num<>0 GROUP BY h0,h8),
feat AS (SELECT DISTINCT h0,h8 FROM read_parquet('s3://public-ca30x30/plant-richness/p80-hex/h0=*/data_0.parquet'))
SELECT ROUND(100.0*SUM(COALESCE(c.wsum,0))/SUM(COALESCE(l.nland,0)),2) pct   -- plant: 41.12 (report 40.59)
FROM feat f LEFT JOIN cons8 c USING(h0,h8) LEFT JOIN land8 l USING(h0,h8);
```
For ACE, `feat` = ACE hexagons meeting the threshold (rank=5, or top-20%/top-5% of the
count via `quantile_cont`). For `fwa_rich`, top-20% HUC12 by `Freshwater_Species_Count`.

## 6. res-10 presence features (NWI wetlands, GDE, sea-level-rise)

```sql
WITH cons AS (
  SELECT h0,h10,SUM((Final_g1_p+Final_g2_p)/100.0) w
  FROM read_parquet('s3://public-ca30x30/conserved-areas-terrestrial-2025/hex/h0=*/data_0.parquet') GROUP BY h0,h10),
wet AS (SELECT DISTINCT h0,h10 FROM read_parquet('s3://public-wetlands/nwi-v2/hex/h0=*/data_0.parquet')
        WHERE state_code='CA' AND WETLAND_TYPE IN
          ('Freshwater Emergent Wetland','Freshwater Forested/Shrub Wetland','Estuarine and Marine Wetland'))
SELECT ROUND(100.0*SUM(CASE WHEN c.w IS NULL THEN 0 ELSE LEAST(c.w,1.0) END)/COUNT(*),2) pct  -- wetlands 30.08
FROM wet f LEFT JOIN cons c USING(h0,h10);
```
**Gotcha:** never write `SUM(LEAST(c.w,1.0))` on a LEFT JOIN — DuckDB's `LEAST` skips NULLs,
so unconserved cells score as 1.0 and the baseline blows up to ~74%. Use the explicit
`CASE WHEN c.w IS NULL THEN 0 …` guard (or plain `SUM(c.w)`, which ignores NULLs).
