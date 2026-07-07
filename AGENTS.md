# AI Agent Guide — geo-agent-template

## Repo relationship

This is a **template repo** for creating geo-agent map applications. The core library lives at [boettiger-lab/geo-agent](https://github.com/boettiger-lab/geo-agent) and is loaded from CDN — you never modify it here.

| Repo | Purpose |
|---|---|
| `geo-agent` | Core library (map, chat, agent, tools). Source of truth for all functionality. |
| `geo-agent-template` | Starter template. Users fork this and configure three files for their dataset. |

**Full docs:** [boettiger-lab.github.io/geo-agent](https://boettiger-lab.github.io/geo-agent/)
— includes the complete configuration reference, deployment guide, and agent loop internals.

The schema below is kept inline so you can work without a network fetch. If it conflicts with the docs, the docs are authoritative.

---

## What you configure (and what you don't)

**You configure:** `layers-input.json` (which datasets to show and how), `system-prompt.md` (LLM persona and guidelines), and `k8s/` manifests if deploying to Kubernetes.

**You do not write JavaScript.** The core map, chat, agent, and tool modules are loaded from the CDN. Do not create or modify JS files in a client app repo.

### Writing the system prompt

**Keep `system-prompt.md` lean.** The MCP query tool (`list_datasets`, `get_schema`) already provides the agent with dataset titles, descriptions, column schemas, coded values, and exact S3 parquet paths at runtime. Do not duplicate any of this in the system prompt — it drifts out of sync and can contradict the tools.

What **belongs** in `system-prompt.md`:
- Domain-specific context the tools cannot provide (e.g., "this dataset has one row per funding transaction, not per site — deduplicate acres before summing")
- Attribution and framing guidance (e.g., how to describe data sources to users)
- Cross-dataset pitfalls (e.g., "Dataset A uses state abbreviations, Dataset B uses full names")
- Map-vs-SQL decision guidance and interaction style
- "Data tool, not advisor" guardrails if the agent should avoid giving policy opinions

What **does not belong** in `system-prompt.md`:
- Column listings or S3 paths (use `get_schema` instead — direct the agent to call it)
- Multiple SQL examples with hardcoded paths (these go stale and may contradict the MCP tool's own query optimization rules)
- DuckDB configuration details (thread count, extensions)
- Dataset descriptions that repeat what's in the STAC catalog

Instead, add a "Discovering data" section directing the agent to verify against the dataset metadata (via `list_datasets` / `get_schema`) before writing any SQL.

---

## Training & evaluation workflow (regression fixes)

Partner-reported agent failures (wrong numbers, hallucinated codes, speculation) are diagnosed and fixed through a fixed loop: **observe logs → reproduce headless → trace each issue to the layer that owns it → fix in that layer → verify → deploy.** The canonical reference is the **`geo-agent-training` skill** in `boettiger-lab/open-llm-proxy` (`.claude/skills/geo-agent-training/SKILL.md`) — read it before working a batch of issues.

### Hard boundary — edit only this repo

The LLM's context is assembled from four layers, each owned by a different repo. **You make code/config edits *only* in this app repo. For a root cause in any other layer, open a GitHub issue on the owning repo** (with log evidence, root cause, exact proposed change, and how to verify) — never edit another repo's code, and never open a PR there. Their agents/maintainers action it. Reading sibling repos and their git history for diagnosis is encouraged.

| Layer | Owns | Repo | Symptom that points here |
|---|---|---|---|
| **STAC catalog metadata** | dataset paths, column schemas, coded values (code→name), dataset descriptions, per-dataset aggregation notes | `data-workflows` | model guesses a column/code, can't resolve a class name, wrong paths, missing dataset-specific aggregation rule |
| **MCP tool descriptions** | SQL construction, H3 join rules, partition pruning, dedup/area-aggregation patterns, raster-vs-vector guidance | `mcp-data-server` (`query-optimization.md`, `h3-guide.md`) | structurally wrong SQL, bad joins, generic aggregation/uncertainty caveats that apply across apps |
| **geo-agent framework** | tool orchestration, STAC-first enforcement, map-tool definitions, prompt assembly, LLM call params (e.g. temperature) | `geo-agent` | model skips STAC tools, wrong tool type, ListTools spam, sampling/determinism knobs |
| **App system prompt** (here) | app persona, domain interpretation, attribution/framing, cross-dataset disambiguation, "data tool not advisor" / no-speculation guardrails | **this repo** (`system-prompt.md`) | the issue is purely how *this* app interprets/presents results for its audience |

**Objective vs. subjective — the test for STAC vs. system prompt.** STAC metadata (incl. "per-dataset aggregation notes") holds only *application-independent* truths about a dataset: what a column means, coded values, that an ACE rank is a top quintile *by construction*. How to *use* a shared/national dataset for this app — which subset, threshold, or filter defines a "feature" — is a **subjective, app-specific choice and belongs in `system-prompt.md`**, even when an authoritative partner specifies it. Example: California 30x30 defines the "wetlands" feature as three NWI `WETLAND_TYPE` classes and ACE biodiversity features as rank 5; other apps interpret the same national layers differently, so those are app conventions (see `system-prompt.md` "Feature definitions"), **not** STAC notes. (Model SQL-handling failures — hex-count-vs-vector area, proportional GAP weighting — go to `mcp-data-server`, not the prompt.)

Prefer fixing the root cause in the correct layer over papering over it in `system-prompt.md`. Before adding anything to the system prompt, ask: *could STAC metadata, an MCP tool description, or the framework fix this instead?* If yes, file the issue there. After tracing a batch, the app repo gets the app-layer edits plus one summary issue linking all the cross-repo issues filed.

### Verify with the headless runner — don't close on faith

Before claiming an issue fixed, **reproduce it through the headless runner**, which replays the full geo-agent tool-use loop (catalog load, MCP connect, prompt assembly, tool calls) through the live proxy using *this repo's current `system-prompt.md` and `layers-input.json`*. It imports the framework from a sibling `geo-agent` checkout, so behavior matches the browser by construction.

- **Matrix sweeps (model × question × trial) run as a Kubernetes Job**, never locally — it mounts `PROXY_KEY` from the `open-llm-proxy-secrets` Secret in `biodiversity`:
  ```bash
  cd ../open-llm-proxy/headless
  TAG=ca30x30-regress QUESTIONS_FILE=runs/ca30x30-regression-q.txt \
    MODELS="qwen3" TRIALS=3 \
    ./run-matrix-k8s.sh boettiger-lab/ca-30x30
  kubectl -n biodiversity logs -f job/<JOB_NAME>      # printed on launch
  ```
  Re-running the *same* question with `TRIALS>1` is how determinism regressions are checked. The Job clones the app repo at `main` (override with `APP_BRANCH`), so it tests exactly what is deployed.
- Per-cell transcripts + `summary.tsv` print to the Job's stdout; the full request/response pairs land in the proxy logs. Analyze them per `open-llm-proxy/AGENTS.md` + `LOGGING.md` (`./sync-logs.sh` then DuckDB over the consolidated parquet, filtered by the `--origin` tag).
- Single ad-hoc repro of one failure: `node run.js "QUESTION" --config layers-input.json --system-prompt system-prompt.md --model qwen3` (see `headless/README.md`). Not for matrix work.

When testing SQL methodology directly (not the full agent loop), run it against the MCP `query` tool to confirm the numbers before encoding any guidance.

---

## Branch and deployment workflow

**`main` is the live branch.** The `ca-30x30` deployment on k8s (namespace `biodiversity`) clones from `main` at pod startup — whatever is on `main` is what runs in production. (The app's deployment is named **`ca-30x30`**, not `padus` — `padus` is a *different* app sharing the cluster. Always target `deployment/ca-30x30`.)

Workflow for testing CDN pin updates or config changes:
1. Create a `test/` branch, make changes, verify jsDelivr serves the new SHA.
2. Merge the `test/` branch to `main` (fast-forward is fine).
3. Restart the deployment: `kubectl rollout restart deployment/ca-30x30 -n biodiversity`

Do **not** merge to main before verifying the CDN SHA is live — jsDelivr can take up to an hour to index a new tag.

---

## Deployment

Full guide: [boettiger-lab.github.io/geo-agent/docs/guide/deployment](https://boettiger-lab.github.io/geo-agent/docs/guide/deployment)

**Read the sections below before fetching that URL** — they cover the two common k8s patterns. Fetch the docs only if you need details beyond what's here (e.g., GitHub Pages, Hugging Face Spaces, private data modules).

> **If you lack credentials or permissions** to run `kubectl` or `git push`, do not attempt to discover or work around credentials. Instead, provide the user with the exact commands to run.

### Public repo (k8s git-clone pattern)

The pod's init container clones the GitHub repo at startup. **Push to GitHub first, then restart.**

```bash
git add <files> && git commit -m "<message>" && git push
kubectl rollout restart deployment/<app-name> -n <namespace>
kubectl rollout status deployment/<app-name> -n <namespace>
```

Restarting without pushing first serves stale code.

### Private repo (ConfigMap pattern)

When the GitHub repo is private, the pod reads content from a k8s ConfigMap instead of git-cloning. **Never edit `k8s/content-configmap.yaml` directly** — it is generated from source files.

```bash
# 1. Edit source files (index.html, layers-input.json, system-prompt.md)
# 2. Regenerate the ConfigMap
bash scripts/generate-configmap.sh
# 3. Apply and restart
kubectl apply -f k8s/content-configmap.yaml -n <namespace>
kubectl rollout restart deployment/<app-name> -n <namespace>
kubectl rollout status deployment/<app-name> -n <namespace>
# 4. Commit and push source files (not just the generated configmap)
git add <source-files> k8s/content-configmap.yaml && git commit -m "<message>" && git push
```

The git push does **not** update running pods — step 3 does. Skipping `generate-configmap.sh` and re-applying serves the old ConfigMap.

For private data modules (rclone sidecar, oauth2-proxy, private parquet credentials): [docs/guide/private-deployment](https://boettiger-lab.github.io/geo-agent/docs/guide/private-deployment)

### CDN versioning

`index.html` tracks `@main` by default:

```html
<script type="module" src="https://cdn.jsdelivr.net/gh/boettiger-lab/geo-agent@main/app/main.js"></script>
```

**When testing a geo-agent PR:** pin to the PR's HEAD commit hash, verify jsDelivr serves it, then return to `@main` when done:

```bash
# Get latest SHA from a PR
gh pr view 166 --repo boettiger-lab/geo-agent --json headRefOid --jq '.headRefOid[:8]'

# Verify jsDelivr serves it before deploying
curl -sI https://cdn.jsdelivr.net/gh/boettiger-lab/geo-agent@<sha>/app/style.css | grep HTTP
# Must return HTTP/2 200
```

Replace all three occurrences of the SHA in `index.html` (style.css, chat.css, sidebar.css, main.js), commit to `main`, and restart.

---

## Full `layers-input.json` schema

### Top-level fields

| Field | Required | Type | Description |
|---|---|---|---|
| `catalog` | Yes | string | STAC catalog root URL |
| `collections` | Yes | array | Collection specs (see below) |
| `view` | No | object | `{ "center": [lon, lat], "zoom": z }` |
| `titiler_url` | No | string | TiTiler server for COG rasters (default: `https://titiler.nrp-nautilus.io`) |
| `mcp_url` | No | string | MCP/DuckDB server URL for SQL analytics |
| `llm` | No | object | LLM config for user-provided key mode (see below) |
| `welcome` | No | object | `{ "message": "...", "examples": ["...", "..."] }` |

> **Security note:** The public MCP server (`https://duckdb-mcp.nrp-nautilus.io/mcp`) is open — no auth token is required or set. The `mcp-data-server` supports optional bearer token auth: if `MCP_AUTH_TOKEN` is set in the server's environment it enforces auth on all requests; if unset, the server is open. The active deployment does not set `MCP_AUTH_TOKEN`, so no token is needed in client apps.

### Collection-level fields

Each `collections` entry is a bare string (loads all visual assets) or an object:

| Field | Type | Description |
|---|---|---|
| `collection_id` | string | **Must exactly match the `"id"` field in the STAC collection JSON** — not a label you invent. Verify before use (see below). |
| `collection_url` | string | Direct STAC collection JSON URL — bypasses root catalog traversal |
| `group` | string | Layer toggle group label |
| `assets` | array | Asset selector (see below). Omit to load all visual assets. |
| `display_name` | string | Override collection title in UI |

### Asset config — vector / PMTiles

Each `assets` entry is a bare string (the STAC asset key) or a config object:

| Field | Type | Description |
|---|---|---|
| `id` | string | **Required.** STAC asset key (e.g., `"pmtiles"`) |
| `alias` | string | Alternative layer ID — use to create two logical layers from one STAC asset with different filters |
| `display_name` | string | Layer toggle label |
| `visible` | boolean | Default visibility (default: `false`) |
| `default_style` | object | MapLibre fill paint properties |
| `outline_style` | object | MapLibre line paint for an auto-added outline layer |
| `layer_type` | `"line"` or `"circle"` | `"line"` for LineString features; `"circle"` for Point features — see warning below |
| `default_filter` | array | MapLibre filter expression at load time |
| `tooltip_fields` | array | Property names shown on feature hover |
| `group` | string | Override collection-level group for this layer |

### Asset config — raster / COG

| Field | Type | Description |
|---|---|---|
| `id` | string | **Required.** STAC asset key |
| `display_name` | string | Layer toggle label |
| `visible` | boolean | Default visibility (default: `false`) |
| `colormap` | string | TiTiler colormap name (e.g., `"reds"`, `"viridis"`) |
| `rescale` | string | TiTiler min,max range (e.g., `"0,150"`) |
| `legend_label` | string | Legend label |
| `legend_type` | string | `"categorical"` to use STAC `classification:classes` colors |

---

## Critical: `layer_type` vs `outline_style`

**Never use `"layer_type": "line"` to draw polygon outlines.** This tells the renderer the tile features are LineString geometries. On a polygon-feature PMTiles file, it causes MapLibre to silently render nothing.

**To draw polygon boundaries without a fill**, use `outline_style` and set `fill-opacity: 0`:

```json
{
    "id": "pmtiles",
    "display_name": "District Boundaries",
    "visible": true,
    "default_style": {
        "fill-color": "#000000",
        "fill-opacity": 0
    },
    "outline_style": {
        "line-color": "#1565C0",
        "line-width": 1.5
    }
}
```

Only set `layer_type` when the tile features match the geometry type:
- `"line"` — LineString/MultiLineString features (roads, rivers, transects)
- `"circle"` — Point/MultiPoint features (observations, stations, events)

---

## Finding collection IDs and asset IDs

**Always fetch the STAC collection JSON and verify — never guess.** The `collection_id` must match the STAC `"id"` field exactly; a mismatch causes layers to silently not appear. Run this one-liner when you have the collection URL:

### Nested / hierarchical collections

Some catalog entries are **parent collections** that contain sub-collections as `"child"` links, not assets of their own. The framework only traverses **direct children of the root catalog** — it does not recurse into parent collections to find nested sub-collections.

**Symptom:** you set a `collection_id` that exists in STAC but the layer never appears. The collection is a child of a parent collection, not of the root catalog.

**Fix:** always inspect the `links` array of every collection you encounter, and use `collection_url` to point directly to the sub-collection JSON URL:

```python
import urllib.request, json
url = "<parent_collection_url>"
d = json.loads(urllib.request.urlopen(url).read())
print("id:", d["id"])
for l in d.get("links", []):
    if l.get("rel") == "child":
        print("  child:", l["href"], "|", l.get("title",""))
```

Then in `layers-input.json`, set both `collection_id` (the exact STAC `"id"`) and `collection_url` (the direct URL) so the framework bypasses root-catalog traversal:

```json
{
    "collection_id": "pad-us-4.1-fee",
    "collection_url": "https://s3-west.nrp-nautilus.io/public-padus/padus-4-1/fee/stac-collection.json",
    "assets": [...]
}
```

```bash
curl -s <collection_url> | python3 -c "
import json, sys
d = json.load(sys.stdin)
print('collection_id:', d['id'])
for k, v in d.get('assets', {}).items():
    vl = v.get('vector:layers', 'MISSING')
    print(f'  asset: {k}  type: {v.get(\"type\",\"\")}  vector:layers: {vl}')
"
```

This also checks `vector:layers` on each PMTiles asset. If it shows `MISSING`, the STAC collection needs to be patched before the layer will render — the app falls back to the asset key as the source-layer name, which is almost always wrong.

Alternatively, browse the catalog in STAC Browser:

```
https://radiantearth.github.io/stac-browser/#/external/s3-west.nrp-nautilus.io/public-data/stac/catalog.json
```

Open a collection → the collection `id` is shown at the top. Under **Assets**, the keys (e.g., `"pmtiles"`, `"v2-total-2024-cog"`) are the `id` values for asset entries. For PMTiles, the asset's `vector:layers` field lists internal layer names — the app reads this automatically, no manual config needed.

### Verifying PMTiles fields for `tooltip_fields` and `default_filter`

PMTiles tiles contain only a subset of the parquet columns — tippecanoe selects fields at tile-build time. **Do not assume field names from the STAC `table:columns` schema are available in the tiles.** Before setting `tooltip_fields` or `default_filter`, inspect the PMTiles metadata directly:

```bash
python3 -c "
import urllib.request, struct, json
url = '<pmtiles_url>'
req = urllib.request.Request(url, headers={'Range': 'bytes=0-16383'})
data = urllib.request.urlopen(req).read()
off = struct.unpack_from('<Q', data, 24)[0]
ln  = struct.unpack_from('<Q', data, 32)[0]
req2 = urllib.request.Request(url, headers={'Range': f'bytes={off}-{off+ln-1}'})
meta = json.loads(urllib.request.urlopen(req2).read())
for layer in meta.get('vector_layers', []):
    print('layer name:', layer['id'])
    print('fields:', list(layer.get('fields', {}).keys()))
"
```

The `vector_layers[].id` value is the internal layer name (must be present in `vector:layers` in the STAC asset). The `vector_layers[].fields` keys are the only field names valid for `tooltip_fields` and `default_filter`.

---

## Troubleshooting: layer not appearing in the overlay list

Two common causes:

1. **`collection_id` mismatch** — the value in `layers-input.json` does not match the STAC collection's actual `"id"` field. Run the one-liner above and compare. The framework silently drops the collection if the IDs don't match.

2. **Wrong source-layer name** — the `vector:layers` field in the STAC asset is missing or incorrect, so the app uses the asset key as the source-layer name and MapLibre finds no matching layer in the tiles. Check `vector:layers` with the one-liner above, and verify it matches the `vector_layers[].id` value from the PMTiles metadata script.

---

## MapLibre filter syntax

Use the modern `match` form for list membership:

```json
["match", ["get", "ColumnName"], ["value1", "value2"], true, false]
```

Do **not** use the legacy `["in", "ColumnName", "value1", "value2"]` form — it is silently ignored by current MapLibre.

---

## LLM config (user-provided key mode)

```json
"llm": {
    "user_provided": true,
    "default_endpoint": "https://openrouter.ai/api/v1",
    "models": [
        { "value": "anthropic/claude-sonnet-4", "label": "Claude Sonnet" },
        { "value": "google/gemini-2.5-flash",   "label": "Gemini Flash" }
    ]
}
```

Omit the `llm` block entirely for Kubernetes deployments where `config.json` is injected server-side.
