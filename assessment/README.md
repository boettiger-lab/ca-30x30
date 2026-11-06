# 30x30 Biodiversity Assessment Explorer

A map + dashboard companion to California's 2025 30x30 Biodiversity Assessment
([Schloss et al. 2026, California Biodiversity Network](https://cabiodiversitynetwork.org/wp-content/uploads/2026/08/CBN-Biodiversity-Assessment-2025-Final-Report.pdf)).
Pick **California**, an **ecoregion**, **county**, **congressional or legislative district**, or **draw / upload a polygon**, and see the report's
analyses for that area: land by conservation status, network composition, and the representation tables for habitats, species
richness, connectivity, freshwater and climate features. Each table splits a feature between 30x30 Conservation Areas (GAP 1–2), other conserved or
public land (GAP 3–4) and non-conserved land, with the report's need classes and pathway pies. **Managed by** narrows the conserved
land to one kind of manager (federal, state, local, non-profit or other) while keeping every share a share of the whole area; see
[Manager filter](#manager-filter).

**Live:** <https://boettiger-lab.github.io/ca-30x30/assessment/>

There is **no LLM** in the loop. Every number comes from a fixed, reviewable SQL template run on the public
[duckdb-geo MCP server](https://duckdb-mcp.nrp-nautilus.io/mcp) over H3-indexed GeoParquet. "Method & SQL" under each section shows the exact
SQL for the selected area, and **Export** downloads a self-contained report with every query as SQL / R / Python, its output, and data citations.
It accompanies, and does not replace, the open-ended [AI data explorer](https://ca-30x30.nrp-nautilus.io/) at the root of this repo.

The app is built on [glen-charts](https://github.com/SchmidtDSE/glen-charts) (v0.11.0), the shared library for no-LLM area explorers,
loaded from jsDelivr at a pinned tag. This folder holds only the configuration, the SQL, the precomputed data and what is specific to the
assessment.

## Reproducing the report

On the statewide view, every table row shows the report's published value beside this app's, compared at the precision the report printed.
Of the 85 values in Tables 3–13, 75 agree within 0.5 percentage points, 80 within 1 point, and 84 within 2. The need class matches on all 85
rows. Every pathway pie but one, for rivers, is within 0.1 of the published pie.

`scripts/validate.py` checks every number the app shows against the authors' result tables (`featureGAPSummary_*_wTotals.csv`, shared
by the report's authors, not distributed here). For each feature it compares the extent, the shares in GAP 1–2, GAP 3–4 and non-conserved land,
the share of the 30x30 network, the need class and the pathway pie. It also checks the ecoregion table and each ecoregion's own page.

```sh
python3 scripts/validate.py <dir with the CSVs>
```

What agrees:

- **Land characterization.** The app gives 26.1 / 25.6 / 48.2% against the report's 26.1 / 25.5 / 48.4%.
- **The 20 ecoregions.** Every ecoregion's shares, in the statewide table and on its own page, are within 0.8 points of the authors' tables, and
  its area is within 0.2%.
- **Network composition.** Ecoregion and habitat shares of the network are within 0.1 point of the authors' tables. The report's prose
  rounds three habitat figures down (Conifer Forest 15%, Shrub 13%; the tables give 16.0 and 14.0).
- **Climate.** About 32% of the network is projected to be climate-stressed: 31.4% (MIROC5) and 31.6% (CNRM-CM5) here, against 32.0 and
  32.1. A burned share of 13.9% matches the report's 14%.

Known differences, all from source data:

| Feature | App | Report | Why |
|---|---:|---:|---|
| Streams (order 3–5) / Rivers (6+) | 26.0 / 20.0 | 24 / 22 | NHDPlus HR network, ~3× the channel length of the report's medium-resolution network; GAP 3–4 shares differ by 4–8 points |
| 100-year floodplain | 16.3 | 14 | FEMA flood zones; the report used First Street Foundation, which the catalog does not carry |
| Watersheds, top 20% freshwater richness | 20.4 | 22 | GAP 3–4 share 29 vs 34%, not explained by the richness cutoff; likely a different edition of the richness data |
| Riverine (CWHR) | 18.7 | 17.6 | a small, linear class, so it is sensitive to the cell grid |
| Groundwater-dependent ecosystems (extent) | 2.5M ac | 4.3M ac | the catalog's layer totals 2.4M ac as mapped; the shares agree within 1 point (2.5 for non-conserved) |
| South Coast Missing Linkages (extent) | 1.96M ac | 1.78M ac | the 11 linkage polygons sum to 1.94M ac; shares agree within 2 points |
| Sea-level rise, 5 ft (extent) | 0.89M ac | 0.64M ac | NOAA's layer includes existing open water ([#104](https://github.com/boettiger-lab/ca-30x30/issues/104)) |

The transcribed report values are in `data/report.json`.

## How it works

```
index.html               header + glen-charts (MapLibre, PMTiles and glen-charts from CDN, no build step)
app/
  extensions.js          what glen-charts does not provide: the representation chart type, the
                         conserved-areas layer, polygon drawing, the "How to read this" note
  represent.js           the representation table (report Tables 3–13) + its CSS
  tokens.js              the {{LAND}} template token
  style.css              palette overrides on glen-charts' stylesheet
config/
  app.json               area types (AOI SQL, pick lists, boundary tiles), the land grid, sections,
                         the report as reference values
  themes/<id>/           theme.json (tiles, charts, method) + *.sql templates
data/
  statewide/manager-<m>.json   every section's SQL run over California, for each manager setting
  areas/<type>/manager-all/<id>.json   the same for each ecoregion, county and district (all managers;
                         other settings run live)
  lists/*.json           pick lists (id, name, bbox)
  report.json            the report's published values, transcribed from its tables
  sources.json           STAC records of every dataset read (export citations)
scripts/
  run.mjs                run one section query for one area (for writing templates)
  validate.py            compare every shown value with the report and its result tables
```

To move to a newer glen-charts, change the tag in `index.html`, `app/extensions.js`, `app/represent.js` and `scripts/run.mjs`, and
check that the generated SQL is unchanged, so `data/` stays valid.

### SQL template contract

`{{LAND}}` expands to the selected area's **California land cells at H3 resolution 10**, as `(h0, h8, h9, h10, area_km2, w12, w34, wc)`.
`w12` and `w34` are the cell's GAP 1–2 and GAP 3–4 shares from the 2025 Conserved Areas per-cell weights, and `wc` its whole conserved share,
all 0 for land outside every conserved unit. With a manager selected, `w12` and `w34` count only that manager's land and `wc` still counts
every manager's.
The grid is the CA ecoregion land grid, the 30x30 denominator. A feature's share in 30x30 is then always

```sql
SUM(a * w12) / SUM(a)        -- a = feature area (or length) in the cell
```

Representation queries also return `frac_other = SUM(a * (wc - w12 - w34)) / SUM(a)`, other managers' conserved land, and compute
`frac_none` from `wc`. With all managers `frac_other` is 0 and `frac_none` is unchanged.

Features join `{{LAND}}` at their own resolution (`h10`, `h9` or `h8`), so every metric is masked to California and to the area, area-weighted,
and uses the report's proportional estimate. Value thresholds (ACE top 20% / 5%, freshwater richness) are computed over **all of California**
before restricting to the area, so a feature means the same thing everywhere. Representation queries return
`feature, label, acres|miles, frac_gap12, frac_gap34, frac_none`. `feature` is the key into `data/report.json`.

Need classes are always measured against California's current share in 30x30, which is computed rather than hard-coded. For a sub-state area,
the area's own share is drawn as a second reference tick.

### Adding a metric

1. Add a `.sql` file to a theme under `config/themes/<id>/`, following the contract above. Check it with
   `node scripts/run.mjs <theme> <query> [ecoregion Mono]`.
2. Reference it in that theme's `theme.json`: a `"type": "representation"` chart, a bar chart, or a headline.
3. Regenerate the data with the glen-charts precompute CLI, from this folder:
   `npx github:SchmidtDSE/glen-charts#v0.11.0 precompute statewide --param manager=all`, then `... precompute areas ecoregion --theme <id>`
   and the same for `county`, `cd`, `sldu` and `sldl`, which re-run only that theme (`--force` re-runs every theme, which takes
   hours).
4. Check the result against the report with `python3 scripts/validate.py`.

## Manager filter

The `manager` param (app.json `params`, shown as **Managed by**) groups each conserved unit's `MNG_AG_LEV` from the 2025 Conserved
Areas inventory:

| Option | Levels | GAP 1–2 | GAP 3–4 |
|---|---|---:|---:|
| Federal | Federal | 21.29M ac | 22.87M ac |
| State | State | 2.67M ac | 0.69M ac |
| Local | City, County, Special District, Joint, JPA, Local Government | 0.67M ac | 1.47M ac |
| Non-profit | Non Profit | 1.89M ac | 0.94M ac |
| Other | Private, Tribal, Home Owners Association, Unknown, Government | 0.003M ac | 0.05M ac |

The five options partition the network: they sum to the statewide 26.52M ac in GAP 1–2 and 26.01M ac in GAP 3–4. The manager is the
managing agency, not the owner; for an easement (CCED) it is the easement holder.

Under Federal, the `agency` param (**Federal agency**, shown only when Federal is chosen) narrows to one agency by `MNG_AGENCY`,
with the inventory's abbreviations folded in:

| Option | Agencies | GAP 1–2 | GAP 3–4 |
|---|---|---:|---:|
| Forest Service | United States Forest Service, USFS | 6.42M ac | 14.39M ac |
| BLM | United States Bureau of Land Management, BLM | 6.73M ac | 8.18M ac |
| National Park Service | United States National Park Service, National Park Service, NPS, Golden Gate National Recreation Area | 7.54M ac | 0.07M ac |
| Fish and Wildlife Service | United States Fish and Wildlife Service | 0.46M ac | 0.02M ac |
| Other federal | every other federal unit (Bureau of Reclamation, NRCS, Army Corps, multi-agency units …) | 0.14M ac | 0.21M ac |

These sum to the Federal row. The agency param carries `"when": { "manager": "federal" }` (glen-charts ≥ 0.10), so it is left out of the
file key elsewhere: `manager-state.json`, but `agency-usfs_manager-federal.json`.

`app.land_manager` builds the filtered `{{LAND}}`, with `{{UNITS}}` the unit predicate from `app/tokens.js`. Each cell's GAP 1–2 weight goes to the selected manager in proportion to its units'
GAP 1–2 percentages among all units in that cell (GAP 3–4 alike), from the unit-level hex asset. 99.6% of conserved land lies in cells
with a single unit, where the split is exact.

The denominator does not change: a feature's share in a manager's 30x30 land is a share of the feature's whole extent in the area.
The representation table then drops the need classes and the report's values, which describe all managers together, and shows each
manager's share of the feature's 30x30 acres in their place. Theme items that change meaning carry `"when": { "manager": ... }`
(glen-charts ≥ 0.9), and the report comparison is limited to `manager: all`.

Statewide results are precomputed for every option (`--param manager=all`, then `--param manager=federal --param agency=all`). Named areas are precomputed for all managers only, so a
county or ecoregion with a manager selected runs live.

## Run locally

```sh
python3 -m http.server 8000      # from this folder, then open http://localhost:8000
```

## Deploy

`.github/workflows/gh-pages.yml` copies this folder to `assessment/` on the `gh-pages` branch on every push to `main` that touches it.
The site is fully static, with no secrets, and the browser calls the public MCP endpoint in `config/app.json` directly.
