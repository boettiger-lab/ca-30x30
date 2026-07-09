# CA 30×30 Planning & Assessment Tool

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.14933817.svg)](https://doi.org/10.5281/zenodo.14933817)

**[🗺️ Open the app → ca-30x30.nrp-nautilus.io](https://ca-30x30.nrp-nautilus.io)** · **[About & data sources](https://ca-30x30.nrp-nautilus.io/docs.html)**

An interactive map and AI assistant for exploring California's conserved lands, biodiversity, habitat connectivity, and climate data — and tracking progress toward the state's goal of conserving **30% of its lands and coastal waters by 2030** (the "30×30" goal).

A project of the [Eric and Wendy Schmidt Center for Data Science & Environment (DSE)](https://dse.berkeley.edu) at UC Berkeley, developed in collaboration with the California Biodiversity Network to align with the CA 30×30 Biodiversity Assessment. It answers complex, real-world natural-language queries from conservation partners with reproducible, verifiable data summaries, charts, maps, and text — integrating open-weights language models with cloud-optimized ecological and socio-environmental data.

> **Now updated to the 2025 CA 30×30 conservation data.** This tool runs on the 2025 statewide conservation inventory and refreshed supporting layers. It is a **work in progress** — layers, models, and capabilities are being added and refined.

## What you can do

The Data Assistant understands plain English and does two kinds of things — it can **drive the map** and it can **answer analytical questions** about the underlying data.

**Map operations** act on the layers already loaded:
- *"Show only GAP status 1 and 2 conserved lands."*
- *"Color conserved areas by managing agency."* · *"Make the habitat layer 50% transparent."*
- *"Fly to the Sierra Nevada."* · *"Turn on bird species richness."*

**Analytical questions** are answered by writing live spatial queries over the data, returning a number or a downloadable table:
- *"How many acres of California are conserved at GAP status 1 or 2?"*
- *"Which ecoregion has the most conserved acreage?"*
- *"Where is rare-species biodiversity highest relative to its ecoregion?"*

**Draw to ask about an area.** Sketch a polygon on the map — a watershed, a proposed acquisition, a county — and ask about it: *"How many acres inside the area I drew are already conserved?"* Your shape becomes a live spatial filter for any query.

## Data layers

Every layer draws from a public, primary source, with full machine-readable metadata (schema, license, lineage) available via its STAC entry. Groups include:

- **Progress & Protections** — Conserved Areas Terrestrial (2025), Disadvantaged Communities (DAC), CalEnviroScreen 5.0
- **Ecoregions** — CNRA/ACE Bailey-derived ecoregions (20-class)
- **Habitat Types** — CWHR major (13-class) and full (60+ class) vegetation types
- **ACE Biodiversity** — CDFW Areas of Conservation Emphasis (BioRank, Rare Rank, species richness)
- **Biodiversity, Freshwater & Connectivity** — plant richness, freshwater species richness (HUC12), NWI wetlands, groundwater-dependent ecosystems, NHD streams, connectivity & climate-migration routes
- **Climate-Related Risks** — sea-level-rise inundation, mid-century habitat climate exposure, historic fire perimeters (1878–2025)
- **Reference Boundaries** — Census TIGER/Line 2024 county / state / tract

See the **[About page](https://ca-30x30.nrp-nautilus.io/docs.html)** for the full annotated catalog, or browse the complete [STAC catalog](https://radiantearth.github.io/stac-browser/#/external/s3-west.nrp-nautilus.io/public-data/stac/catalog.json).

## How it works

The app is powered by **[GLEN (Geospatial LLM-Enabled Navigator)](https://github.com/boettiger-lab/geo-agent)**, DSE's open-source framework for AI-assisted geospatial exploration. Open datasets stream straight to the browser from cloud-native formats (PMTiles/COG for the map, H3-indexed Parquet for analytics) — no tile server in between — and the AI assistant answers questions by writing live SQL against the same data through a DuckDB [MCP](https://modelcontextprotocol.io) server. The map is built on [MapLibre GL](https://maplibre.org).

**There is no application code in this repository.** The map, chat, agent loop, and tools are loaded from GLEN via CDN. This repo only holds configuration:

```
index.html          ← HTML shell — loads GLEN core JS/CSS from CDN
layers-input.json   ← which STAC collections to show + map/LLM settings
system-prompt.md    ← the agent's persona and CA 30×30 domain conventions
docs.html           ← the public About page
k8s/                ← Kubernetes deployment manifests
```

Full framework documentation: [boettiger-lab.github.io/geo-agent/docs](https://boettiger-lab.github.io/geo-agent/docs/). Contributor and deployment notes for this repo are in [AGENTS.md](AGENTS.md).

## Local development

```bash
python -m http.server 8000
# Open http://localhost:8000
```

## Citation

If you use this tool, please cite it via its Zenodo concept DOI, which always resolves to the latest version:

> Buhler, C. K., & Boettiger, C. *CA 30x30 Planning & Assessment Tool.* Zenodo. https://doi.org/10.5281/zenodo.14933817

It is built on the GLEN framework ([10.5281/zenodo.20673849](https://doi.org/10.5281/zenodo.20673849)).

## Acknowledgements

Developed by DSE at UC Berkeley in collaboration with the California Biodiversity Network. Supported in part by NSF award [2153040](https://www.nsf.gov/awardsearch/showAward?AWD_ID=2153040). Feedback welcome via [GitHub issues](https://github.com/boettiger-lab/ca-30x30/issues).

## License

[BSD 2-Clause](LICENSE) © Boettiger Lab, UC Berkeley.
