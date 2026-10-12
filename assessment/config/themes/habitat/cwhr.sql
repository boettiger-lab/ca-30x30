-- Finer habitat types (CWHR 60+ classes, CAL FIRE FVEG 2022), grouped as in
-- the 2025 Biodiversity Assessment's Tables 4-8, with each type's extent in
-- the area and its share by conservation status. Fractional res-10 cells,
-- masked to California's land grid; area-weighted. Agricultural, urban and
-- open-water types are omitted, as in the assessment.
WITH land AS MATERIALIZED ({{LAND}}),
types(code, label, grp) AS (VALUES
  (11, 'Closed-Cone Pine-Cypress', 'Conifer forest & woodland'), (14, 'Douglas Fir', 'Conifer forest & woodland'),
  (20, 'Eastside Pine', 'Conifer forest & woodland'), (24, 'Jeffrey Pine', 'Conifer forest & woodland'),
  (26, 'Juniper', 'Conifer forest & woodland'), (27, 'Klamath Mixed Conifer', 'Conifer forest & woodland'),
  (29, 'Lodgepole Pine', 'Conifer forest & woodland'), (40, 'Pinyon-Juniper', 'Conifer forest & woodland'),
  (42, 'Ponderosa Pine', 'Conifer forest & woodland'), (44, 'Redwood', 'Conifer forest & woodland'),
  (45, 'Red Fir', 'Conifer forest & woodland'), (48, 'Subalpine Conifer', 'Conifer forest & woodland'),
  (51, 'Sierran Mixed Conifer', 'Conifer forest & woodland'), (58, 'White Fir', 'Conifer forest & woodland'),
  (35, 'Montane Hardwood-Conifer', 'Conifer forest & woodland'),
  (5, 'Aspen', 'Hardwood woodland & forest'), (8, 'Blue Oak-Foothill Pine', 'Hardwood woodland & forest'),
  (9, 'Blue Oak Woodland', 'Hardwood woodland & forest'), (10, 'Coastal Oak Woodland', 'Hardwood woodland & forest'),
  (36, 'Montane Hardwood', 'Hardwood woodland & forest'), (55, 'Valley Oak Woodland', 'Hardwood woodland & forest'),
  (77, 'Eucalyptus', 'Hardwood woodland & forest'),
  (1, 'Alpine-Dwarf Shrub', 'Shrub & grassland'), (3, 'Annual Grassland', 'Shrub & grassland'),
  (7, 'Bitterbrush', 'Shrub & grassland'), (12, 'Chamise-Redshank Chaparral', 'Shrub & grassland'),
  (13, 'Coastal Scrub', 'Shrub & grassland'), (30, 'Low Sage', 'Shrub & grassland'),
  (32, 'Mixed Chaparral', 'Shrub & grassland'), (34, 'Montane Chaparral', 'Shrub & grassland'),
  (39, 'Perennial Grassland', 'Shrub & grassland'), (50, 'Sagebrush', 'Shrub & grassland'),
  (4, 'Alkali Desert Scrub', 'Desert'), (15, 'Desert Riparian', 'Desert'), (17, 'Desert Scrub', 'Desert'),
  (18, 'Desert Succulent Shrub', 'Desert'), (19, 'Desert Wash', 'Desert'), (25, 'Joshua Tree', 'Desert'),
  (41, 'Palm Oasis', 'Desert'),
  (21, 'Estuarine', 'Wetland & aquatic'), (22, 'Fresh Emergent Wetland', 'Wetland & aquatic'),
  (28, 'Lacustrine', 'Wetland & aquatic'), (37, 'Montane Riparian', 'Hardwood woodland & forest'),
  (43, 'Riverine', 'Wetland & aquatic'), (49, 'Saline Emergent Wetland', 'Wetland & aquatic'),
  (56, 'Valley Foothill Riparian', 'Hardwood woodland & forest'), (59, 'Wet Meadow', 'Wetland & aquatic')),
f AS (
  SELECT h.whrnum AS code, l.area_km2 * h.frac AS a, l.w12, l.w34
  FROM read_parquet('s3://public-ca30x30/cwhr/hex-fractions/h0=*/data_0.parquet') h
  JOIN land l ON h.h0 = l.h0 AND h.h10 = l.h10
  WHERE h.whrnum IN (SELECT code FROM types)
)
SELECT 'cwhr:' || f.code AS feature, t.label, t.grp,
       SUM(a) * 247.105 AS acres,
       SUM(a * w12) * 247.105 AS gap12_acres,
       SUM(a * w34) * 247.105 AS gap34_acres,
       SUM(a * w12) / SUM(a) AS frac_gap12,
       SUM(a * w34) / SUM(a) AS frac_gap34,
       1 - SUM(a * (w12 + w34)) / SUM(a) AS frac_none
FROM f JOIN types t USING (code)
GROUP BY f.code, t.label, t.grp
ORDER BY t.grp, frac_gap12
