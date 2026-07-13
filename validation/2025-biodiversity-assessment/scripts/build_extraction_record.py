#!/usr/bin/env python3
"""Build extraction_record.json (record #1) and reproduction_record.json (record #2)
for the CBN 2025 Biodiversity Assessment draft report."""
import csv, json, os

CSVDIR = "csvs/Result_CSVs_2025data"

def load(name):
    """Return dict feature_key -> row dict from a featureGAPSummary CSV."""
    path = os.path.join(CSVDIR, f"featureGAPSummary_{name}.csv")
    out = {}
    with open(path) as f:
        r = csv.DictReader(f)
        first = r.fieldnames[0]
        for row in r:
            key = row[first]
            out[key] = row
    return out

def f2(x):
    try: return round(float(x), 2)
    except: return None

# ---- Definitions ---------------------------------------------------------
# metric semantics:
#  percentFeature: proportional (Disc) % of that feature's STATEWIDE extent that falls
#                  within 30x30 Conservation Areas (GAP 1+2). Lower80/Upper20 = uncertainty band.
#  percentNetwork: proportional % of the 30x30 network's area composed of that feature/class.

# Human-readable definitions for non-habitat feature keys
FEATURE_DEFS = {
 "slr5ft": "Sea-level-rise inundation zone (NOAA, 5 ft): % of the SLR-exposed area within 30x30 (representation); as %network it is the network's SLR-at-risk share.",
 "fire_perimeter": "Historic fire perimeters (CAL FIRE, past decade): % of burned-area extent within 30x30; as %network the share of the network burned in the past decade.",
 "scmlinkage": "Regional connectivity linkages (South Coast Missing Linkages, Beier et al. 2006): % of linkage extent within 30x30.",
 "gde": "Groundwater-dependent ecosystems (Klausmeyer et al. 2018): % of GDE extent within 30x30. KEY FEATURE.",
 "wetlands": "Wetlands = freshwater emergent + freshwater forested/shrub + estuarine & marine wetland (NWI 2019, 3 WETLAND_TYPE classes): % of wetland extent within 30x30. KEY FEATURE. NOTE: distinct from the FVEG CWHR13 'Wetland' habitat class.",
 "fwa_rich": "Watersheds with the highest freshwater species richness (top, Howard et al. 2015): % of extent within 30x30.",
 "BioRankSW": "ACE top-ranked biodiversity, statewide (Rank 5), CDFW 2018: % of extent within 30x30. Threshold feature (top quintile) - CA-level comparison N/A.",
 "BioRankEco": "ACE top-ranked biodiversity, per-ecoregion (Rank 5): % of extent within 30x30. Threshold feature.",
 "RarRankSW": "ACE top-ranked RARE biodiversity, statewide (Rank 5): % within 30x30. Threshold feature.",
 "RarRankEco": "ACE top-ranked RARE biodiversity, per-ecoregion (Rank 5): % within 30x30. Threshold feature.",
 "NtvRept": "Reptile richness, all native (top 20%), ACE/CDFW: % within 30x30.",
 "NtvAmph": "Amphibian richness, all native (top 20%): % within 30x30.",
 "NtvMamm": "Mammal richness, all native (top 20%): % within 30x30.",
 "NtvBird": "Bird richness, all native (top 20%): % within 30x30.",
 "NtvPlnt": "Plant richness, all native (top 20%), ACE: % within 30x30.",
 "RarRept": "Reptile richness, rare subset (top 5%): % within 30x30.",
 "RarAmph": "Amphibian richness, rare subset (top 5%): % within 30x30.",
 "RarMamm": "Mammal richness, rare subset (top 5%): % within 30x30.",
 "RarBird": "Bird richness, rare subset (top 5%): % within 30x30.",
 "RarPlnt": "Plant richness, rare subset (top 5%): % within 30x30.",
 "ReptEndem": "Reptile richness, endemic subset (top 5%): % within 30x30.",
 "AmphEndem": "Amphibian richness, endemic subset (top 5%): % within 30x30.",
 "MammEndem": "Mammal richness, endemic subset (top 5%): % within 30x30.",
 "BirdEndem": "Bird richness, endemic subset (top 5%): % within 30x30.",
 "PlntEndem": "Plant richness, endemic subset (top 5%): % within 30x30.",
 "stream_1_2": "Headwater streams (NHD order 1-2, USGS 2020): % of stream length within 30x30.",
 "stream_3_5": "Mid-sized streams (NHD order 3-5): % of length within 30x30.",
 "stream_6_9": "Major rivers (NHD order 6-9): % of length within 30x30.",
 "stream_peren": "Perennial streams (NHD): % of length within 30x30.",
 "chn": "Channelized connectivity (Cameron et al. 2022): % of extent within 30x30.",
 "int": "Intensified connectivity (Cameron et al. 2022): % within 30x30.",
 "diff": "Diffuse (well-connected) connectivity (Cameron et al. 2022): % within 30x30.",
 "clink": "Climate migration routes / climate linkages (Schloss et al. 2022): % within 30x30.",
 "flood": "100-year floodplain / flood hazard zone (First Street Foundation 2020): % within 30x30. KEY FEATURE.",
 "plant": "Plant species richness, top 20% (Kling et al. 2019): % within 30x30.",
 "endp": "Rarity-weighted endemic plant richness, top 20% (Kling et al. 2019): % within 30x30.",
 "miroc": "Mid-century habitat climate exposure / projected climate stress (Thorne et al. 2016, MIROC): % of climate-stressed extent within 30x30; as %network the network share projected to be climate-stressed.",
}

WHR13_LABEL = {
 "CONIFER_FO":"Conifer Forest","HARDWOOD_F":"Hardwood Forest","HERBACEOUS":"Herbaceous",
 "SHRUB":"Shrub","WETLAND":"Wetland (FVEG)","BARREN_OTH":"Barren/Other","URBAN":"Urban",
 "WATER":"Water","AGRICULTUR":"Agriculture","HARDWOOD_W":"Hardwood Woodland",
 "CONIFER_WO":"Conifer Woodland","DESERT_SHR":"Desert Shrub","DESERT_WOO":"Desert Woodland"}

stats = []
sid = 0
def add(**kw):
    global sid; sid += 1
    kw = {"id": f"S{sid:03d}", **kw}
    stats.append(kw)

# ---- A. Headline / land characterization (prose) ------------------------
add(group="Land characterization", label="% of California in 30x30 Conservation Areas",
    definition="Percent of California's land area classified GAP 1+2 (durably protected for biodiversity), proportional estimate. Denominator = official CA area (~101.5M ac).",
    metric="percent_of_CA", reported_value=26.1, uncertainty=None,
    source="Exec summary / p.'Where Do We Stand' / Land Characterization; = CNRA 2025 progress report")
add(group="Land characterization", label="% of California in other conserved/public/unknown lands (GAP 3+4)",
    definition="Percent of CA land classified GAP 3 or GAP 4 (other conservation, public, or unknown status).",
    metric="percent_of_CA", reported_value=25.5, uncertainty=None, source="Land Characterization")
add(group="Land characterization", label="% of California non-conserved",
    definition="Percent of CA land outside any conservation-area unit (private unmanaged + DOD).",
    metric="percent_of_CA", reported_value=48.4, uncertainty=None, source="Land Characterization")
add(group="Land characterization", label="Official 2025 30x30 Conservation Area acreage (GAP 1+2)",
    definition="Total statewide GAP 1+2 conserved acres in the 2025 Conserved Areas dataset.",
    metric="acres", reported_value=26471461, uncertainty=None, source="Appendix B (Table S2 denominator)")
add(group="Land characterization", label="Acreage increase since 2022",
    definition="Net new GAP 1+2 acreage added 2022->2025.",
    metric="acres", reported_value=2400000, uncertainty="stated as '2.4M' (exec) and 'roughly 2.5M' (conclusion)",
    source="Exec summary / Conclusion")
add(group="Land characterization", label="Acreage still needed to reach 30%",
    definition="Additional GAP 1+2 acres required to hit 30% of CA.",
    metric="acres", reported_value=4000000, uncertainty="stated as 'over 4M' / 'nearly 4M'", source="Exec summary / Conclusion")

# ---- D. Climate & disturbance of the network (prose, %network) ----------
add(group="Network climate/disturbance", label="Network projected climate-stressed by mid-century",
    definition="% of the 30x30 network's natural vegetation projected to be stressed by mid-century climate change (Thorne et al. 2016).",
    metric="percent_of_network", reported_value=32.0, uncertainty=None, source="Network Composition (prose); miroc %network")
add(group="Network climate/disturbance", label="Network at risk from sea-level rise",
    definition="% of the 30x30 network at risk from sea-level rise (NOAA 5 ft).",
    metric="percent_of_network", reported_value=0.5, uncertainty=None, source="Network Composition (prose); slr %network")
add(group="Network climate/disturbance", label="Network burned in past decade",
    definition="% of the 30x30 network burned by wildfire in the past decade (CAL FIRE).",
    metric="percent_of_network", reported_value=14.0, uncertainty=None, source="Network Composition (prose); fire %network")

# ---- B. Ecoregion network composition (Table/Fig 6, %network) -----------
eco = load("ecoregion_percentNetwork")
for k,row in eco.items():
    if k in ("Network Total",): continue
    add(group="Network composition: ecoregion", feature_key=k, label=f"{k} share of 30x30 network",
        definition=f"Proportional % of the 30x30 network composed of the {k} ecoregion.",
        metric="percent_of_network", reported_value=f2(row["Disc"]),
        uncertainty=[f2(row["Lower80"]), f2(row["Upper20"])], source="Figure 6b / ecoregion %network")

# ---- C. Habitat network composition (Fig 7, %network) -------------------
h13n = load("WHR13NAME_percentNetwork")
for k,row in h13n.items():
    if k=="Network Total": continue
    add(group="Network composition: major habitat", feature_key=k, label=f"{WHR13_LABEL[k]} share of 30x30 network",
        definition=f"Proportional % of the 30x30 network composed of FVEG CWHR13 major habitat '{WHR13_LABEL[k]}'.",
        metric="percent_of_network", reported_value=f2(row["Disc"]),
        uncertainty=[f2(row["Lower80"]), f2(row["Upper20"])], source="Figure 7b / WHR13 %network")

# ---- E. Major habitat representation (Table 3, %feature) ----------------
h13f = load("WHR13NAME_percentFeature")
for k,row in h13f.items():
    if k=="Network Total": continue
    add(group="Representation: major habitat", feature_key=k, label=f"{WHR13_LABEL[k]} conserved in 30x30",
        definition=f"Proportional % of the statewide extent of FVEG CWHR13 '{WHR13_LABEL[k]}' within 30x30 Conservation Areas.",
        metric="percent_of_feature", reported_value=f2(row["Disc"]),
        uncertainty=[f2(row["Lower80"]), f2(row["Upper20"])],
        gap34_pct=f2(row["g34"]), nonconserved_pct=f2(row["nonconserved"]), source="Table 3 / WHR13 %feature")

# ---- F. Finer habitat representation (Tables 4-8, %feature) -------------
whrt = load("WHRTYPE_percentFeature")
for k,row in whrt.items():
    if k=="Network Total": continue
    lbl = row.get("WHRNAME_first", k)
    add(group="Representation: finer habitat (CWHR 60-class)", feature_key=k, label=f"{lbl} conserved in 30x30",
        definition=f"Proportional % of the statewide extent of CWHR habitat '{lbl}' ({k}) within 30x30 Conservation Areas.",
        metric="percent_of_feature", reported_value=f2(row["Disc"]),
        uncertainty=[f2(row["Lower80"]), f2(row["Upper20"])],
        gap34_pct=f2(row["g34"]), nonconserved_pct=f2(row["nonconserved"]), source="Tables 4-8 / WHRTYPE %feature")

# ---- G. Richness / ranked biodiversity (Tables 9-11, %feature) ----------
allf = load("all_percentFeature")
richness_keys = ["BioRankSW","BioRankEco","RarRankSW","RarRankEco",
 "NtvRept","NtvAmph","NtvMamm","NtvBird","NtvPlnt","RarRept","RarAmph","RarMamm","RarBird","RarPlnt",
 "ReptEndem","AmphEndem","MammEndem","BirdEndem","PlntEndem"]
for k in richness_keys:
    row = allf[k]
    add(group="Representation: richness/ranked biodiversity", feature_key=k, label=k,
        definition=FEATURE_DEFS[k], metric="percent_of_feature", reported_value=f2(row["Disc"]),
        uncertainty=[f2(row["Lower80"]), f2(row["Upper20"])],
        gap34_pct=f2(row["g34"]), nonconserved_pct=f2(row["nonconserved"]), source="Tables 9-10 / ACE %feature")
for name,src in [("plant","plant"),("endp","endp")]:
    row = load(f"{src}_percentFeature")[name]
    add(group="Representation: richness/ranked biodiversity", feature_key=name, label=name,
        definition=FEATURE_DEFS[name], metric="percent_of_feature", reported_value=f2(row["Disc"]),
        uncertainty=[f2(row["Lower80"]), f2(row["Upper20"])],
        gap34_pct=f2(row["g34"]), nonconserved_pct=f2(row["nonconserved"]), source="Table 11 / Kling %feature")

# ---- H. Connectivity (Table 12, %feature) -------------------------------
conn = load("connectivity_percentFeature")
for k in ["chn","int","diff","clink"]:
    row = conn[k]
    add(group="Representation: connectivity", feature_key=k, label=k, definition=FEATURE_DEFS[k],
        metric="percent_of_feature", reported_value=f2(row["Disc"]),
        uncertainty=[f2(row["Lower80"]), f2(row["Upper20"])],
        gap34_pct=f2(row["g34"]), nonconserved_pct=f2(row["nonconserved"]), source="Table 12 / connectivity %feature")
row = allf["scmlinkage"]
add(group="Representation: connectivity", feature_key="scmlinkage", label="scmlinkage", definition=FEATURE_DEFS["scmlinkage"],
    metric="percent_of_feature", reported_value=f2(row["Disc"]),
    uncertainty=[f2(row["Lower80"]), f2(row["Upper20"])],
    gap34_pct=f2(row["g34"]), nonconserved_pct=f2(row["nonconserved"]), source="Table 12 / connectivity %feature")

# ---- I. Freshwater (Table 13, %feature) ---------------------------------
for k in ["gde","wetlands","fwa_rich","stream_1_2","stream_3_5","stream_6_9","stream_peren"]:
    row = allf[k]
    add(group="Representation: freshwater", feature_key=k, label=k, definition=FEATURE_DEFS[k],
        metric="percent_of_feature", reported_value=f2(row["Disc"]),
        uncertainty=[f2(row["Lower80"]), f2(row["Upper20"])],
        gap34_pct=f2(row["g34"]), nonconserved_pct=f2(row["nonconserved"]), source="Table 13 / freshwater %feature")
row = load("flood_percentFeature")["flood"]
add(group="Representation: freshwater", feature_key="flood", label="flood", definition=FEATURE_DEFS["flood"],
    metric="percent_of_feature", reported_value=f2(row["Disc"]),
    uncertainty=[f2(row["Lower80"]), f2(row["Upper20"])],
    gap34_pct=f2(row["g34"]), nonconserved_pct=f2(row["nonconserved"]), source="Table 13 / flood %feature")

# ---- climate/disturbance representation (%feature) ----------------------
for k,src in [("miroc","miroc_percentFeature"),("slr5ft","all_percentFeature"),("fire_perimeter","all_percentFeature")]:
    row = load(src)[k] if src!="all_percentFeature" else allf[k]
    add(group="Representation: climate/disturbance", feature_key=k, label=k, definition=FEATURE_DEFS[k],
        metric="percent_of_feature", reported_value=f2(row["Disc"]),
        uncertainty=[f2(row["Lower80"]), f2(row["Upper20"])],
        gap34_pct=f2(row["g34"]), nonconserved_pct=f2(row["nonconserved"]), source="Richness/Tables / %feature")

record1 = {
 "record_type": "extraction",
 "report": "V2025_WORKING_MASTER_DRAFT_Biodiversity_Assessment_Report_2025Update (CBN, draft, pub. date tag 2026-07-08)",
 "note": ("Reported values are the report's PROPORTIONAL ('Disc') estimate. Tables 3-13 in the docx are embedded "
          "raster images; their numeric values were recovered from the authors' shipped result CSVs "
          "(Result_CSVs_2025data.zip), which are the digital source of those image tables and match every prose "
          "figure spot-checked (26.1/25.5/48.4, ecoregion & habitat composition, freshwater, finer habitats). "
          "Lower80/Upper20 = the report's lower/upper uncertainty band."),
 "metric_definitions": {
   "percent_of_CA": "share of California's official land area (~101.5M ac denominator)",
   "percent_of_feature": "share of that feature's STATEWIDE extent lying within 30x30 (GAP 1+2), proportional estimate",
   "percent_of_network": "share of the 30x30 network's area composed of that feature/ecoregion, proportional estimate"},
 "n_statistics": len(stats),
 "statistics": stats,
}
with open("extraction_record.json","w") as f:
    json.dump(record1, f, indent=2)

# group counts
from collections import Counter
gc = Counter(s["group"] for s in stats)
print("Extraction record: %d unique statistics" % len(stats))
for g,c in gc.items():
    print(f"  {c:3d}  {g}")
