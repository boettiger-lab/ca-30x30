#!/usr/bin/env python3
"""Build the browser-only copy of the app, for GitHub Pages.

The copy runs with no server. The visitor brings their own LLM key (the `llm`
block in layers-input.json), geo-query's tools run in the browser on
DuckDB-wasm (SchmidtDSE/geo-query-wasm), and every dataset is read from its
source.coop mirror rather than NRP.

It is generated from the app's own files, so it never drifts from them:

    index.html         the NRP redirect removed; an import map that swaps GLEN's
                       MCP client for wasm/glen-wasm-mcp.js, and the worker config
    layers-input.json  collection URLs moved to source.coop, mcp_url unused
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
GEO_QUERY_WASM = "v0.6.0"
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
    glen = f"https://cdn.jsdelivr.net/gh/SchmidtDSE/glen@{pins.pop()}/app/"
    importmap = {"imports": {
        "glen/": glen,
        "geo-query-wasm/": GQW_BASE,
        glen + "mcp-client.js": "./glen-wasm-mcp.js",
    }}
    head = (
        "\n    <!-- Browser-only copy (scripts/build-wasm-copy.py): GLEN's MCP client is\n"
        "         replaced by one that runs geo-query in a Web Worker. -->\n"
        f'    <script type="importmap">{json.dumps(importmap)}</script>\n'
        f'    <script type="application/json" id="geo-query-wasm-config">{json.dumps(WORKER_CONFIG)}</script>\n'
    )
    # The import map must come before any module script; the charset stays first.
    charset = '<meta charset="UTF-8">\n'
    if charset not in html:
        sys.exit("index.html: no charset meta to place the import map after")
    html = html.replace(charset, charset + head, 1)
    (out / "index.html").write_text(html)

    cfg = json.loads((root / "layers-input.json").read_text())
    cfg["catalog"] = "stac/catalog.json"
    # Never fetched. Same-origin, so GLEN (v3.42.0+) offers no "Data server
    # token" field, which would do nothing here.
    cfg["mcp_url"] = "geo-query-wasm/mcp"
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

    shutil.copy(root / "wasm/glen-wasm-mcp.js", out)
    shutil.copy(root / "system-prompt.md", out)
    shutil.copy(root / "docs.html", out)
    shutil.copytree(root / "assets", out / "assets", dirs_exist_ok=True)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    build(Path(__file__).resolve().parent.parent, Path(sys.argv[1]))
