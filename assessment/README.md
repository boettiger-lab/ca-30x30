# 30x30 Biodiversity Assessment Explorer

A map + dashboard companion to California's 2025 30x30 Biodiversity Assessment
([Schloss et al. 2026, California Biodiversity Network](https://cabiodiversitynetwork.org/wp-content/uploads/2026/08/CBN-Biodiversity-Assessment-2025-Final-Report.pdf)).
Pick **California**, an **ecoregion**, **county**, **congressional or legislative district**, or **draw / upload a polygon**, and see the report's
analyses for that area: land by conservation status, network composition, and the representation tables for habitats, species
richness, connectivity, freshwater and climate features. Each table splits a feature between 30x30 Conservation Areas (GAP 1–2), other conserved or
public land (GAP 3–4) and non-conserved land, with the report's need classes and pathway pies.

**Live:** <https://boettiger-lab.github.io/ca-30x30/assessment/>

There is **no LLM** in the loop. Every number comes from a fixed, reviewable SQL template run on the public
[duckdb-geo MCP server](https://duckdb-mcp.nrp-nautilus.io/mcp) over H3-indexed GeoParquet. "Method & SQL" under each section shows the exact
SQL for the selected area, and **Export** downloads a self-contained report with every query as SQL / R / Python, its output, and data citations.
It accompanies, and does not replace, the open-ended [AI data explorer](https://ca-30x30.nrp-nautilus.io/) at the root of this repo.

The architecture is forked from [tpl-cities](https://github.com/boettiger-lab/tpl-cities) (`app/`, at `ca2ee19`), and the shared parts are
candidates for a common library.

## Reproducing the report

On the statewide view, every table row shows the report's published value beside this app's, compared at the precision the report printed.
Of the 85 values in Tables 3–13, 74 agree within 0.5 percentage points, 80 within 1 point, and all within 2. The five beyond one point come from
known data differences:

| Feature | App | Report | Why |
|---|---:|---:|---|
| Streams (order 3–5) / Rivers (6+) | 26.0 / 20.0 | 24 / 22 | NHDPlus HR network, ~3× the channel length of the report's medium-resolution network |
| 100-year floodplain | 16.0 | 14 | FEMA flood zones; the report used First Street Foundation, which the catalog does not carry |
| Watersheds, top 20% freshwater richness | 20.0 | 22 | under investigation |
| Riverine (CWHR) | 18.7 | 17.6 | under investigation |

Land characterization reproduces 26.1 / 25.5 / 48.4% as 26.1 / 25.6 / 48.2%. The report's prose figure that 32% of the network is projected to
be climate-stressed is not reproduced (this app computes about 22% for either climate model); the report's own MIROC5 representation value,
31.7%, is close to that 32%. The transcribed report values are in `data/report.json`.

## How it works

```
index.html               static shell (MapLibre + PMTiles from CDN, no build step)
app/
  mcp.js                 MCP client: one stateless POST per query, results as one JSON cell
  engine.js              loads config, expands SQL templates, caches; precomputed results first
  main.js                UI: area → sections → report; URL hash state
  report.js              section card: headline tiles, charts, "Method & SQL"
  represent.js           the representation table (report Tables 3–13) + its CSS
  charts.js, format.js   SVG bar charts, number formats
  map.js                 basemap, conserved areas, boundaries, selection, drawn shapes
  draw.js, polygon.js    draw / upload a polygon → H3-polyfill AOI
  export.js, sources.js  self-contained HTML report with code and citations
config/
  app.json               area types (AOI SQL, pick lists, boundary tiles), the land grid, sections
  themes/<id>/           theme.json (tiles, charts, method) + *.sql templates
data/
  statewide.json         every section's SQL run over California
  areas/<type>/<id>.json the same for each ecoregion and county
  lists/*.json           pick lists (id, name, bbox)
  report.json            the report's published values, transcribed from its tables
  sources.json           STAC records of every dataset read (export citations)
scripts/
  precompute.mjs         regenerates data/ with the same engine
  run.mjs                run one section query for one area (for writing templates)
```

### SQL template contract

`{{LAND}}` expands to the selected area's **California land cells at H3 resolution 10**, as `(h0, h8, h9, h10, area_km2, w12, w34)`.
`w12` and `w34` are the cell's GAP 1–2 and GAP 3–4 shares from the 2025 Conserved Areas per-cell weights, and 0 for land outside every conserved unit.
The grid is the CA ecoregion land grid, the 30x30 denominator. A feature's share in 30x30 is then always

```sql
SUM(a * w12) / SUM(a)        -- a = feature area (or length) in the cell
```

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
3. Regenerate the data: `node scripts/precompute.mjs statewide` and `node scripts/precompute.mjs sources`, then
   `node scripts/precompute.mjs areas ecoregion --force` and `areas county --force`, which take about an hour.

## Run locally

```sh
python3 -m http.server 8000      # from this folder, then open http://localhost:8000
```

## Deploy

`.github/workflows/gh-pages.yml` copies this folder to `assessment/` on the `gh-pages` branch on every push to `main` that touches it.
The site is fully static, with no secrets, and the browser calls the public MCP endpoint in `config/app.json` directly.
