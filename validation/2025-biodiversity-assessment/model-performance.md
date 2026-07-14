# Model performance, cost & 30-question scorecard

Blind headless runs of the 30-question report set (`headless-questions.txt`), **2 trials each = 60 cells per model**, on the current deployed layer (mcp-data-server v0.8.5). The models never see the report value — this measures deployed behavior, unlike the answer-key-supervised reproduction in `reproduction_record.json`. `qwen` = DSE-Nimbus (self-hosted, no per-call $); `nemotron-ultra` + `glm-5.2` via OpenRouter.

## Why glm-5.2 is the default

glm-5.2 is the most **accurate and most deterministic** of the three at essentially the **same cost and reasonable wall-time** — and it's the only open model that reproduces *both* the res-8 ACE/richness features and the 3-bucket land-status without an answer key.

| | **glm-5.2** ⭐ | nemotron-ultra | qwen (Nimbus) |
|---|--:|--:|--:|
| Questions ✓ both trials | **~22 / 27** | ~15 / 27 | ~8 / 27 |
| Numeric cells ✓/~ (of 54) | **~44 (81%)** | ~32 (59%) | ~20 (37%) |
| Non-deterministic Qs | **~2** | ~8 | ~10 |
| API calls | 221 | 263 | ≈250 |
| Tool calls | 224 | 245 | — |
| Input tokens | 6.24 M | 7.70 M | — |
| — cached | **85%** | 47% | — |
| Output tokens | 397 k | 261 k | — |
| — reasoning | 305 k | 173 k | — |
| Job wall-clock | 171 min | 120 min | 214 min |
| Timed-out cells | 1 | 3 | ≈10 |
| **Cost (USD, 60 cells)** | **$2.98** | $3.32 | n/a (self-hosted) |
| — input / output split | $1.81 / $1.17 | $2.57 / $0.74 | — |

- **Cost is input-dominated** (61% glm, 78% nemotron): the agent resends growing context each turn, so input volume (6–8 M tok) dwarfs output (0.26–0.40 M) even though output bills ~9–10× more per token. glm's **85% prompt-cache hit** (vs nemotron 47%) is why it's cheaper despite emitting more reasoning.
- nemotron is fastest wall-clock but least accurate and least stable (3 timeouts, ~8 non-deterministic). qwen is slowest and weakest.

## 30-question scorecard

Per cell: `T1T2 value` — ✓ match · ~ close · ✗ mismatch · ⏱ timeout/no-answer · ⚠ trials disagree. Values are the extracted headline (heuristic).

| # | question | report | glm-5.2 | nemotron-ultra | qwen |
|--|--|--|--|--|--|
| 1 | % CA in 30x30 | 26.1 | ✓✓ 26.08 | ✓✓ 26.08/26.1 | ✓✓ 26.1 |
| 2 | % GAP3+4 | 25.5 | ✓✓ 25.5 | ✓✓ 25.5 | ·· — |
| 3 | % non-conserved | 48.4 | ✓✓ 48.4 | ✗✗ 25.8/74.2⚠ | ✗✗ 73.9 |
| 4 | acres conserved | 26,471,461 | ·✗ —/101,498,000 | ✓✗ 26,144,800/101,498,000⚠ | ✓✓ 26,470,000 |
| 5 | acres to 30% | 4,000,000 | ✓✗ 4,000,000/26,470,000⚠ | ✗✓ 101,498,000/3,980,000⚠ | ✓· 3,980,000 |
| 6 | top ecoregion % | Mojave Desert, 27.9% | — | — | — |
| 7 | Sierra % | 17.5 | ✓✓ 17.5 | ✓✓ 17.4/17.5 | ✓✓ 17.52/17.5 |
| 8 | top habitat % | Desert shrub, 39% | — | — | — |
| 9 | desert shrub | 48.2 | ✓✓ 48.2 | ✓✓ 48.2/48.6 | ✓⏱ 48.6 |
| 10 | desert woodland | 56.6 | ✓✓ 56.6 | ✓✓ 56.9/56.6 | ✓✓ 56.59/56.9 |
| 11 | hardwood woodland | 13.6 | ✓✓ 13.6 | ✓✓ 13.95/13.6 | ✗✓ 17.3/13.9⚠ |
| 12 | herbaceous | 15.9 | ✓✓ 15.9 | ✓✓ 15.9 | ⏱✗ —/30 |
| 13 | conifer forest | 24.1 | ✓✓ 24 | ✓✓ 23.2/25 | ✓✗ 24/67.5⚠ |
| 14 | shrub | 27.8 | ✗✗ 48.2 | ✓✓ 26.8/26.96 | ⏱· — |
| 15 | blue oak wood | 10.3 | ✓✓ 10.3 | ✓✓ 10.3/10.33 | ✓✓ 10.3 |
| 16 | eastside pine | 8.5 | ✓✓ 8.3 | ✓✓ 8.07/8.28 | ✓✗ 8.31/16.2⚠ |
| 17 | subalpine conifer | 85.8 | ~✓ 84.2/84.5 | ✓✓ 84.5 | ✓✗ 84.9/35.74⚠ |
| 18 | least-protected | Urban (0.7%) and Agriculture (2.3%); among natural habitats, hardwood woodland (13.6%) and herbaceous/grassland (15.9%) | — | — | — |
| 19 | ACE BioRankSW | 21.1 | ✓✓ 21.2 | ✗✗ 38.3/52.2⚠ | ·✗ —/32.6 |
| 20 | native bird | 11.9 | ✓✓ 11.9 | ✗✗ 22.3/22.21 | ✗✗ 49/42⚠ |
| 21 | native reptile | 40.9 | ✗⏱ 47.3 | ✗✗ 46.95/55.43⚠ | ✗✗ 55.4/47⚠ |
| 22 | plant top20 | 40.6 | ✓✓ 41.2 | ✗✗ 48.05/48.1 | ✗⏱ 47.8 |
| 23 | channelized | 22.7 | ✓✓ 22.5 | ✓✗ 22.55/36.2⚠ | ✗✗ 48.35/32.1⚠ |
| 24 | diffuse | 36.8 | ✓✓ 36.9 | ~✗ 38.7/80.5⚠ | ✗✗ 47.99/47.46 |
| 25 | wetlands | 32.2 | ~~ 30.1 | ~✗ 34.2/15.95⚠ | ✗✗ 81.6/17.2⚠ |
| 26 | GDE | 33.5 | ✓✓ 33/33.4 | ✓✓ 32.2/32.43 | ✓✗ 33.5/58.4⚠ |
| 27 | floodplain | 14.3 | ~~ 16.1 | ~✗ 15.87/4.79⚠ | ✗~ 29.2/16.4⚠ |
| 28 | headwater strm | 27 | ~✗ 29.46/23.94⚠ | ⏱⏱ — | ⏱⏱ — |
| 29 | major rivers | 21.8 | ✗⏱ 62.1 | ✗⏱ 64.4 | ⏱✗ —/5.8 |
| 30 | fwa richness | 21.7 | ✓✓ 20.4 | ✗✗ 87.89/94.7⚠ | ✓✓ 20.6/20.3 |

**Caveats.** Headline figures extracted heuristically from transcripts (a few cells may misparse); 30 Q is a subset of the partner's 149-bank; ranking/name questions (8, 18) aren't numerically scored. Cost = OpenRouter's per-call `cost` summed (pass-through). Streams questions (28–29) fail for all three via the `public-usgs-nhd` bucket listing issue (data-workflows#411).
