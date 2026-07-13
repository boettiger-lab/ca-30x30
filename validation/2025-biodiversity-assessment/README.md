# 2025 Biodiversity Assessment — statistic extraction & independent reproduction

Independent validation of the quantitative claims in the California Biodiversity
Network draft report *"California's 30x30 Initiative in 2025: A Biodiversity
Assessment of the State's 30x30 Conservation Areas."* This app is built to
accompany that report, so every headline number it might be asked about is
extracted, defined precisely, and re-derived from scratch against our own
`duckdb-geo` catalog.

## Contents

| File | What it is |
|---|---|
| `extraction_record.json` | **Record #1** — all 154 quantitative "what-is-protected" statistics from the report, each with a precise definition, the reported (proportional / "Disc") value, and the report's own lower/upper uncertainty band. |
| `reproduction_record.json` | **Record #2** — our independent duckdb-geo reproduction of each statistic, with the dataset used, method note, reproduced value, absolute difference, and match class. |
| `QUERIES.md` | The canonical SQL for each overlay family, copy-paste runnable. |
| `report_qa_answer_key.json` | Validated answer key (value + tolerance) for grading LLM answers. |
| `headless-questions.txt` | 30 natural-language questions (one per category) for the headless model test. |
| `scripts/` | Generators that build the two JSON records from the report's shipped result CSVs + our reproduced values. |

## Source of the reported numbers

The report's **Tables 3–13 are embedded as raster images (TIFF)**, not text tables.
Their numeric content was recovered from the authors' shipped result CSVs
(`Result_CSVs_2025data.zip`, the digital source of those images), whose `Disc`
column is the report's **proportional estimate**. Every prose figure that could be
spot-checked (26.1 / 25.5 / 48.4 %, ecoregion & habitat composition, wetlands 32 %,
floodplain 14 %, "8–10 %" oak/pine) matches the CSVs exactly, so they are treated as
the report's authoritative reported values. (The source docx and CSV zip are not
committed — they are a working draft and the authors' data.)

## Method

The report's proportional estimate = for each conserved-area unit,
`feature_area_in_unit × (Final_g1_p + Final_g2_p)/100`, summed statewide ÷ the
feature's statewide extent. We reproduce this as an **H3 hex overlay** at each
feature's native resolution (res-10 fractional, res-9 fractional, res-8
presence/threshold). Constant cell area cancels in the ratio; the statewide baseline
calibrates to 25.4–26.1 %. See `QUERIES.md`.

## Results

**154 statistics extracted · 143 reproduced with a value · 7 not reproduced.**

| Match vs. report's proportional value | Count |
|---|---:|
| **Exact** (≤ 0.1 pp, or exact acreage) | 51 |
| **Near** (≤ 1.0 pp — inside the report's own uncertainty band) | 63 |
| **Moderate** (1–3 pp) | 22 |
| **Far** (> 3 pp) | 7 |
| **Not reproduced** | 7 |

80 % land within 1 pp of the report; 95 % within 3 pp.

**Exact backbone:** 26.1 % / 25.5 % / 48.4 % of California and 26,471,461 conserved
acres reproduce to the decimal; all 20 ecoregion composition shares are exact.

**The 7 "far" cases** (cause identified in the record): Conifer Woodland and three
small finer-habitat classes (H3 quantization on small extents), BirdEndem & AmphEndem
(top-5 % threshold sensitivity on small integer counts), and `slr5ft` (the terrestrial
conserved layer excludes bay/coastal-water sea-level-rise cells).

**The 7 not reproduced**, with reasons recorded:
- `miroc` — needs the report's climate-stress threshold on the continuous Thorne exposure index.
- `fire_perimeter` — needs a "past-decade" year filter + overlapping-perimeter dedup.
- `flood` — **source mismatch**: report uses First Street Foundation; our catalog has FEMA NFHL only.
- `stream_1_2`, `stream_3_5`, `stream_6_9`, `stream_peren` — line-length metric (hex-area overlap is a poor proxy) + an S3 403 on the `public-usgs-nhd` bucket glob.

Two real methodology bugs were found and fixed during reproduction (documented in
`QUERIES.md`): a res-8 rollup that must divide by each cell's actual land-cell count
(not a flat 49), and DuckDB's `LEAST(NULL,1) → 1` silently scoring unconserved cells
as fully conserved.

## Headless model test

`headless-questions.txt` (30 questions) + `report_qa_answer_key.json` drive a matrix
run through the geo-agent headless runner (`open-llm-proxy/headless/run-matrix-k8s.sh`)
on three models: `qwen` (DSE-Nimbus), `nvidia/nemotron-3-ultra-550b-a55b` and
`z-ai/glm-5.2` (OpenRouter). Grading compares each model's answer to the validated key.
