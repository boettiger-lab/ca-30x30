#!/usr/bin/env python3
"""Build the browser-only copy of the app, for GitHub Pages.

The copy runs with no server. The visitor brings their own LLM key (the `llm`
block in layers-input.json), geo-query's tools run in the browser on
DuckDB-wasm (SchmidtDSE/geo-query-wasm), and every dataset is read from its
source.coop mirror rather than NRP.

It is generated from the app's own files, so it never drifts from them:

    index.html         the NRP redirect removed
    layers-input.json  collection URLs moved to source.coop; the mcp plugin runs
                       geo-query-wasm in a worker (worker.js) instead of reaching
                       a server, and the hex plugin loads its tile protocol
    stac/catalog.json  child links moved to source.coop
    worker.js          a same-origin wrapper around geo-query-wasm's worker
    system-prompt.md, docs.html, assets/   copied as they are

Usage: scripts/build-wasm-copy.py OUT_DIR
"""
import json
import re
import shutil
import sys
from pathlib import Path

# geo-query-wasm at a pinned release. Bump deliberately, and check the copy.
GEO_QUERY_WASM = "v0.7.0"
GQW_BASE = f"https://cdn.jsdelivr.net/gh/SchmidtDSE/geo-query-wasm@{GEO_QUERY_WASM}/src/"

# An NRP bucket `public-<repo>` is mirrored to source.coop as `cboettig/<repo>`.
NRP_HTTPS = re.compile(r"https://s3-west\.nrp-nautilus\.io/public-([^/]+)/")
SC_HTTPS = r"https://data.source.coop/cboettig/\1/"

WORKER_CONFIG = {
    "catalog": "stac/catalog.json",
    "discovery": False,
    "workers": 2,
    # SQL the model writes from NRP paths reads the mirror instead.
    "rewrite": [
        {"from": "s3://public-", "to": "s3://us-west-2.opendata.source.coop/cboettig/"},
        {"from": "https://s3-west.nrp-nautilus.io/public-", "to": "https://data.source.coop/cboettig/"},
    ],
}

REDIRECT = re.compile(
    r"\s*<script>\s*// The site moved off GitHub Pages to NRP.*?</script>", re.S)


def to_source_coop(url):
    return NRP_HTTPS.sub(SC_HTTPS, url)


def build(root, out):
    out.mkdir(parents=True, exist_ok=True)

    html = (root / "index.html").read_text()
    html, n = REDIRECT.subn("", html, count=1)
    if n != 1:
        sys.exit("index.html: could not find the NRP redirect script")
    pins = set(re.findall(r"cdn\.jsdelivr\.net/gh/SchmidtDSE/glen@([^/]+)/", html))
    if len(pins) != 1:
        sys.exit(f"index.html: expected one GLEN pin, found {sorted(pins)}")
    if "/core/main.js" not in html:
        sys.exit("index.html: expected glen core (core/main.js)")
    (out / "index.html").write_text(html)

    cfg = json.loads((root / "layers-input.json").read_text())
    cfg["catalog"] = "stac/catalog.json"
    # GLEN core runs a worker server itself (core/README.md, "plugins"): the
    # mcp plugin takes `worker` in place of `url`, and the hex plugin then
    # reads geo-query-wasm's tiles through it.
    cfg.pop("mcp_url", None)
    plugins, mcp = [], 0
    for p in cfg.get("plugins", []):
        url = p if isinstance(p, str) else p["url"]
        opts = {} if isinstance(p, str) else dict(p.get("options", {}))
        if url.endswith("/core/plugins/mcp.js"):
            mcp += 1
            opts = {"worker": "worker.js", "worker_config": WORKER_CONFIG,
                    **({"prompt": opts["prompt"]} if "prompt" in opts else {})}
        elif url.endswith("/core/plugins/hex.js"):
            opts["geo_query_wasm"] = GEO_QUERY_WASM
        plugins.append({"url": url, "options": opts} if opts else url)
    if mcp != 1:
        sys.exit(f"layers-input.json: expected one mcp plugin, found {mcp}")
    cfg["plugins"] = plugins
    for c in cfg.get("collections", []):
        if isinstance(c, dict) and "collection_url" in c:
            c["collection_url"] = to_source_coop(c["collection_url"])
            if NRP_HTTPS.search(c["collection_url"]) or "nrp-nautilus" in c["collection_url"]:
                sys.exit(f"no source.coop mirror for {c['collection_url']}")
    (out / "layers-input.json").write_text(json.dumps(cfg, indent=4) + "\n")

    cat = json.loads((root / "stac/catalog.json").read_text())
    cat["links"] = [l for l in cat["links"] if l["rel"] not in ("self", "root")]
    for l in cat["links"]:
        l["href"] = to_source_coop(l["href"])
    (out / "stac").mkdir(exist_ok=True)
    (out / "stac/catalog.json").write_text(json.dumps(cat, indent=2) + "\n")

    (out / "worker.js").write_text(
        "// geo-query-wasm's worker, started from this origin so it can read its\n"
        "// configuration from this file's URL (built by scripts/build-wasm-copy.py).\n"
        f"import '{GQW_BASE}worker.js';\n")

    shutil.copy(root / "system-prompt.md", out)
    shutil.copy(root / "docs.html", out)
    shutil.copytree(root / "assets", out / "assets", dirs_exist_ok=True)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    build(Path(__file__).resolve().parent.parent, Path(sys.argv[1]))
