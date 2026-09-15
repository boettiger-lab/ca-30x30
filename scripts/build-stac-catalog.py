#!/usr/bin/env python3
"""Regenerate stac/catalog.json from layers-input.json.

The curated catalog is the agent's data universe: `ca30x30-mcp` reads it as
`STAC_CATALOG_URL`, so `get_stac_details` can only resolve IDs this app
actually configures (ca-30x30#126). Run after editing `collections` and commit
the result — CI re-runs this and fails on a dirty tree.
"""
import json
import pathlib

APP = "https://ca-30x30.nrp-nautilus.io"

root = pathlib.Path(__file__).resolve().parent.parent
cols = json.loads((root / "layers-input.json").read_text())["collections"]
self_href = f"{APP}/stac/catalog.json"

missing = [c for c in cols if not isinstance(c, dict) or "collection_url" not in c]
if missing:
    raise SystemExit(
        "every entry in layers-input.json:collections must be an object with a "
        f"collection_url; {len(missing)} do not: {missing}"
    )

catalog = {
    "type": "Catalog",
    "stac_version": "1.0.0",
    "id": "ca-30x30",
    "title": "California 30x30 — app data scope",
    "description": (
        "Curated STAC catalog: exactly the collections this app configures in "
        "layers-input.json. Served to ca30x30-mcp as STAC_CATALOG_URL so the agent's "
        "data universe is the app's own."
    ),
    "links": [
        {"rel": "self", "href": self_href, "type": "application/json"},
        {"rel": "root", "href": self_href, "type": "application/json"},
        *[
            {
                "rel": "child",
                "href": c["collection_url"],
                "type": "application/json",
                "title": c["collection_id"],
            }
            for c in cols
        ],
    ],
}

out = root / "stac" / "catalog.json"
out.parent.mkdir(exist_ok=True)
out.write_text(json.dumps(catalog, indent=2, ensure_ascii=False) + "\n")
print(f"wrote {out} with {len(cols)} children")
