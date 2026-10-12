-- ACE (CDFW Areas of Conservation Emphasis v3) biodiversity features, defined
-- as in the 2025 Biodiversity Assessment: rank 5 for the BioRank and Rare Rank
-- indices; for per-taxon richness, hexagons at or above the STATEWIDE 80th
-- percentile (native) or 95th percentile (rare, endemic). Thresholds are taken
-- over every ACE hexagon in California, so a feature means the same thing in
-- any area. ACE res-8 cells are applied to the area's res-10 land cells.
WITH land AS MATERIALIZED ({{LAND}}),
ace AS (
  SELECT * FROM read_parquet('s3://public-cdfw/ace/terrestrial-biodiversity-summary/hex/h0=*/data_0.parquet')
),
th AS (
  SELECT quantile_cont(NtvAmph, 0.8) AS NtvAmph, quantile_cont(NtvRept, 0.8) AS NtvRept,
         quantile_cont(NtvBird, 0.8) AS NtvBird, quantile_cont(NtvMamm, 0.8) AS NtvMamm,
         quantile_cont(NtvPlnt, 0.8) AS NtvPlnt,
         quantile_cont(RarAmph, 0.95) AS RarAmph, quantile_cont(RarRept, 0.95) AS RarRept,
         quantile_cont(RarBird, 0.95) AS RarBird, quantile_cont(RarMamm, 0.95) AS RarMamm,
         quantile_cont(RarPlnt, 0.95) AS RarPlnt,
         quantile_cont(AmphEndem, 0.95) AS AmphEndem, quantile_cont(ReptEndem, 0.95) AS ReptEndem,
         quantile_cont(BirdEndem, 0.95) AS BirdEndem, quantile_cont(MammEndem, 0.95) AS MammEndem,
         quantile_cont(PlntEndem, 0.95) AS PlntEndem
  FROM (SELECT DISTINCT Hex_ID, NtvAmph, NtvRept, NtvBird, NtvMamm, NtvPlnt, RarAmph, RarRept, RarBird, RarMamm, RarPlnt,
                        AmphEndem, ReptEndem, BirdEndem, MammEndem, PlntEndem FROM ace)
),
cell AS (
  SELECT a.h0, a.h8,
    bool_or(a.BioRankSW = 5) AS BioRankSW, bool_or(a.BioRankEco = 5) AS BioRankEco,
    bool_or(a.RarRankSW = 5) AS RarRankSW, bool_or(a.RarRankEco = 5) AS RarRankEco,
    bool_or(a.NtvAmph >= th.NtvAmph) AS NtvAmph, bool_or(a.NtvRept >= th.NtvRept) AS NtvRept,
    bool_or(a.NtvBird >= th.NtvBird) AS NtvBird, bool_or(a.NtvMamm >= th.NtvMamm) AS NtvMamm,
    bool_or(a.NtvPlnt >= th.NtvPlnt) AS NtvPlnt,
    bool_or(a.RarAmph >= th.RarAmph) AS RarAmph, bool_or(a.RarRept >= th.RarRept) AS RarRept,
    bool_or(a.RarBird >= th.RarBird) AS RarBird, bool_or(a.RarMamm >= th.RarMamm) AS RarMamm,
    bool_or(a.RarPlnt >= th.RarPlnt) AS RarPlnt,
    bool_or(a.AmphEndem >= th.AmphEndem) AS AmphEndem, bool_or(a.ReptEndem >= th.ReptEndem) AS ReptEndem,
    bool_or(a.BirdEndem >= th.BirdEndem) AS BirdEndem, bool_or(a.MammEndem >= th.MammEndem) AS MammEndem,
    bool_or(a.PlntEndem >= th.PlntEndem) AS PlntEndem
  FROM ace a CROSS JOIN th
  WHERE (a.h0, a.h8) IN (SELECT DISTINCT h0, h8 FROM land)
  GROUP BY a.h0, a.h8
),
long AS (UNPIVOT cell ON COLUMNS(* EXCLUDE (h0, h8)) INTO NAME code VALUE present),
names(code, label, grp, ord) AS (VALUES
  ('BioRankSW', 'Top-ranked biodiversity, statewide (rank 5)', 'Top-ranked biodiversity', 1),
  ('BioRankEco', 'Top-ranked biodiversity, by ecoregion (rank 5)', 'Top-ranked biodiversity', 2),
  ('RarRankSW', 'Top-ranked rare species, statewide (rank 5)', 'Top-ranked biodiversity', 3),
  ('RarRankEco', 'Top-ranked rare species, by ecoregion (rank 5)', 'Top-ranked biodiversity', 4),
  ('NtvAmph', 'Amphibians: native richness (top 20%)', 'Richness by taxon', 10),
  ('RarAmph', 'Amphibians: rare richness (top 5%)', 'Richness by taxon', 11),
  ('AmphEndem', 'Amphibians: endemic richness (top 5%)', 'Richness by taxon', 12),
  ('NtvRept', 'Reptiles: native richness (top 20%)', 'Richness by taxon', 20),
  ('RarRept', 'Reptiles: rare richness (top 5%)', 'Richness by taxon', 21),
  ('ReptEndem', 'Reptiles: endemic richness (top 5%)', 'Richness by taxon', 22),
  ('NtvBird', 'Birds: native richness (top 20%)', 'Richness by taxon', 30),
  ('RarBird', 'Birds: rare richness (top 5%)', 'Richness by taxon', 31),
  ('BirdEndem', 'Birds: endemic richness (top 5%)', 'Richness by taxon', 32),
  ('NtvMamm', 'Mammals: native richness (top 20%)', 'Richness by taxon', 40),
  ('RarMamm', 'Mammals: rare richness (top 5%)', 'Richness by taxon', 41),
  ('MammEndem', 'Mammals: endemic richness (top 5%)', 'Richness by taxon', 42),
  ('NtvPlnt', 'Plants: native richness (top 20%)', 'Richness by taxon', 50),
  ('RarPlnt', 'Plants: rare richness (top 5%)', 'Richness by taxon', 51),
  ('PlntEndem', 'Plants: endemic richness (top 5%)', 'Richness by taxon', 52)),
f AS (
  SELECT long.code, l.area_km2 AS a, l.w12, l.w34
  FROM long JOIN land l ON l.h0 = long.h0 AND l.h8 = long.h8
  WHERE long.present
)
SELECT 'ace:' || n.code AS feature, n.label, n.grp,
       COALESCE(SUM(a), 0) * 247.105 AS acres,
       SUM(a * w12) * 247.105 AS gap12_acres,
       SUM(a * w34) * 247.105 AS gap34_acres,
       SUM(a * w12) / SUM(a) AS frac_gap12,
       SUM(a * w34) / SUM(a) AS frac_gap34,
       1 - SUM(a * (w12 + w34)) / SUM(a) AS frac_none
FROM names n LEFT JOIN f USING (code)
GROUP BY n.code, n.label, n.grp, n.ord
ORDER BY n.ord
