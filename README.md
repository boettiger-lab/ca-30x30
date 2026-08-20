# California 30×30 Explorer

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.21284132.svg)](https://doi.org/10.5281/zenodo.21284132)

Configuration for the **California 30×30 Explorer**, an interactive map app and natural-language data agent for California's goal of conserving 30% of its lands and coastal waters by 2030. **Now updated to the 2025 CA 30×30 data. Live:** <https://ca-30x30.nrp-nautilus.io>

## The report this app accompanies

This app is the interactive companion appendix to the California Biodiversity Network's assessment, **published August 2026**:

> Schloss, C., Howard, J., Olliff Yang, R., Roth, N., Dickison, C., Canales, A., Stanley, C. K., Webb, M., Ackerly, D., Boettiger, C., Buhler, C., Monfort, S., Bucciarelli, G., Meyer, R., Levi Simons, A., Bando, J., Chamberlin, L., Veloz, S., Hill, A., Johnson, R., Hill, R., Kochanek, A., Rademacher, D., Micheli, L., Penrod, K., Rapacciuolo, G., Spatz, D., & Gluesenkamp, D. (2026). *California's 30x30 Initiative in 2025: A Biodiversity Assessment of the State's 30x30 Conservation Areas.* California Biodiversity Network.
> **[Read the report (PDF)](https://cabiodiversitynetwork.org/wp-content/uploads/2026/08/CBN-Biodiversity-Assessment-2025-Final-Report.pdf)**

DSE is among the report's authors; the app follows its conventions (the same conserved-areas inventory, feature definitions, and representation measure) but computes every figure live from the source data.

## Repository contents

The map, chat, and agent code live in the [GLEN](https://github.com/boettiger-lab/geo-agent) library (loaded from CDN); this repo only carries the configuration — `index.html`, `layers-input.json`, `system-prompt.md`, and `k8s/`. See [AGENTS.md](AGENTS.md) to configure or deploy, and the [About page](https://ca-30x30.nrp-nautilus.io/docs.html) for data sources.

A project of [Berkeley DSE](https://dse.berkeley.edu) with the California Biodiversity Network.

## Citation

If you use this tool, please cite it via its Zenodo concept DOI, which always resolves to the latest version:

> Buhler, C. K., & Boettiger, C. *California 30x30 Explorer.* Zenodo. https://doi.org/10.5281/zenodo.21284132

It is built on the GLEN framework ([10.5281/zenodo.20673849](https://doi.org/10.5281/zenodo.20673849)).

## Acknowledgements

Developed by DSE at UC Berkeley in collaboration with the California Biodiversity Network. Supported in part by NSF award [2153040](https://www.nsf.gov/awardsearch/showAward?AWD_ID=2153040). Feedback welcome via [GitHub issues](https://github.com/boettiger-lab/ca-30x30/issues).

## License

[BSD 2-Clause](LICENSE) © Boettiger Lab, UC Berkeley.
