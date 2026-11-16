"""Write the agency menus under "Managed by" into config/app.json.

Each manager level (the `manager` param's options with `levels`) gets one
"multiple" menu param listing every managing agency (MNG_AGENCY) in the 2025
Conserved Areas inventory at that level, largest first, so any manager, down
to a single land trust or homeowners association, can be found by typing.
Local and Other menus are grouped by the inventory's own level (City, County,
Private, Tribal...). Federal keeps the param id `agency` and the merged
Forest Service, BLM, National Park Service and Fish and Wildlife Service
options, whose statewide results are precomputed.

Only the "params" block of app.json is rewritten; run from assessment/:

    python3 scripts/build-manager-options.py
"""

import json
import re
import duckdb

SRC = "s3://public-ca30x30/conserved-areas-terrestrial-2025.parquet"
APP = "config/app.json"

# Federal: the merged options the precomputed statewide files are keyed on.
FEDERAL = [
    {"value": "usfs", "label": "Forest Service", "agencies": ["United States Forest Service", "USFS"]},
    {"value": "blm", "label": "BLM", "agencies": ["United States Bureau of Land Management", "BLM"]},
    {"value": "nps", "label": "National Park Service",
     "agencies": ["United States National Park Service", "National Park Service", "NPS", "Golden Gate National Recreation Area"]},
    {"value": "fws", "label": "Fish and Wildlife Service", "agencies": ["United States Fish and Wildlife Service"]},
]

# The param id for each manager level; groups are shown where a level spans several inventory levels.
IDS = {"federal": "agency", "state": "agency_state", "local": "agency_local",
       "nonprofit": "agency_nonprofit", "other": "agency_other"}


def slug(s, taken):
    base = re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:60] or "x"
    v, i = base, 2
    while v in taken:
        v, i = f"{base}-{i}", i + 1
    taken.add(v)
    return v


def main():
    app = json.load(open(APP))
    manager = next(p for p in app["params"] if p["id"] == "manager")
    con = duckdb.connect()
    con.sql("INSTALL httpfs; LOAD httpfs; SET s3_endpoint='s3-west.nrp-nautilus.io'; SET s3_url_style='path';")
    rows = con.sql(f"""SELECT MNG_AG_LEV AS lev, MNG_AGENCY AS ag, SUM(Total_Acre) AS ac FROM read_parquet('{SRC}')
                       WHERE MNG_AGENCY IS NOT NULL GROUP BY ALL HAVING SUM(Total_Acre) > 0 ORDER BY ac DESC, ag""").fetchall()

    params = [manager]
    for m in manager["options"]:
        if not m.get("levels"):
            continue
        levels = m["levels"]
        grouped = len(levels) > 1
        taken = {"all"}
        opts = [{"value": "all", "label": f"All {m['label'].lower()}"}]
        merged = set()
        if m["value"] == "federal":
            for o in FEDERAL:
                taken.add(o["value"])
                merged.update(o["agencies"])
                opts.append(dict(o))
        for lev, ag, _ in rows:
            if lev not in levels or ag in merged:
                continue
            o = {"value": slug(ag, taken), "label": ag, "agencies": [ag]}
            if grouped:
                o["group"] = lev
            opts.append(o)
        if grouped:  # a group's members together, groups in the order of `levels`
            opts = opts[:1] + sorted(opts[1:], key=lambda o: levels.index(o["group"]))
        params.append({
            "id": IDS[m["value"]], "label": f"{m['label']} manager", "token": IDS[m["value"]].upper(),
            "default": "all", "any": "all", "multiple": True, "control": "menu",
            "when": {"manager": m["value"]},
            "help": "Pick one or more managers. Type to filter.",
            "options": opts,
        })

    # one option per line, so a diff shows which managers came or went
    def param_text(p):
        head = {k: v for k, v in p.items() if k != "options"}
        inner = ",\n".join("            " + json.dumps(o, ensure_ascii=False) for o in p["options"])
        return "{\n" + "".join(f"        {json.dumps(k)}: {json.dumps(v, ensure_ascii=False)},\n" for k, v in head.items()) + \
            f'        "options": [\n{inner}\n        ]\n    }}'

    block = '"params": [' + ", ".join(param_text(p) for p in params) + "],"
    text = open(APP).read()
    start = text.index('"params": [')
    end = text.index('\n\n    "land_cells"')
    text = text[:start] + block + text[end:]
    json.loads(text)
    open(APP, "w").write(text)
    for p in params[1:]:
        print(p["id"], len(p["options"]) - 1)


if __name__ == "__main__":
    main()
