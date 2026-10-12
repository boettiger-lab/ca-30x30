"""Compare every value the app shows with the 2025 Biodiversity Assessment.

Two references:
  data/report.json   values transcribed from the published PDF (Tables 3-13,
                     need classes, Key Features, pathway pies, prose figures)
  Result_CSVs_2025data/featureGAPSummary_*_wTotals.csv
                     the authors' result tables (acres by status per feature);
                     path given as the first argument

Checks, for the statewide view and each ecoregion's overview:
  extent        feature acres (streams: length, units differ, ratio only)
  gap12/34/none share of the feature in each status
  need class    the app's class vs the report's printed class
  key feature   the app's Key Feature list vs the report's outline
  pathway       GAP 3-4 share of the feature outside 30x30, vs the pie
  network       share of the 30x30 network (ecoregions, habitats, climate)

Usage: python3 scripts/validate.py <dir with the CSVs> [--md out.md]
"""
import csv, json, sys, glob, os

ROOT = os.path.join(os.path.dirname(__file__), '..')
CSV_DIR = sys.argv[1]
MD = sys.argv[sys.argv.index('--md') + 1] if '--md' in sys.argv else None

WHR13 = {'CONIFER_FO': 'Conifer Forest', 'HARDWOOD_F': 'Hardwood Forest', 'HERBACEOUS': 'Grassland', 'SHRUB': 'Shrub',
         'WETLAND': 'Wetland', 'BARREN_OTH': 'Barren/Other', 'URBAN': 'Urban', 'WATER': 'Water', 'AGRICULTUR': 'Agriculture',
         'HARDWOOD_W': 'Hardwood Woodland', 'CONIFER_WO': 'Conifer Woodland', 'DESERT_SHR': 'Desert Shrub', 'DESERT_WOO': 'Desert Woodland'}
WHRTYPE = {'KMC': 'Klamath Mixed Conifer', 'RFR': 'Red Fir', 'DFR': 'Douglas Fir', 'MRI': 'Montane Riparian', 'WFR': 'White Fir',
           'PGS': 'Perennial Grassland', 'MCP': 'Montane Chaparral', 'SCN': 'Subalpine Conifer', 'WTM': 'Wet Meadow',
           'AGS': 'Annual Grassland', 'MHC': 'Montane Hardwood-Conifer', 'MHW': 'Montane Hardwood', 'RDW': 'Redwood',
           'CSC': 'Coastal Scrub', 'CPC': 'Closed-Cone Pine-Cypress', 'JPN': 'Jeffrey Pine', 'MCH': 'Mixed Chaparral',
           'RIV': 'Riverine', 'LPN': 'Lodgepole Pine', 'COW': 'Coastal Oak Woodland', 'EST': 'Estuarine', 'LAC': 'Lacustrine',
           'SEW': 'Saline Emergent Wetland', 'VRI': 'Valley Foothill Riparian', 'PPN': 'Ponderosa Pine',
           'CRC': 'Chamise-Redshank Chaparral', 'SMC': 'Sierran Mixed Conifer', 'ASP': 'Aspen', 'ADS': 'Alpine-Dwarf Shrub',
           'LSG': 'Low Sage', 'JUN': 'Juniper', 'SGB': 'Sagebrush', 'EPN': 'Eastside Pine', 'BBR': 'Bitterbrush',
           'VOW': 'Valley Oak Woodland', 'BOW': 'Blue Oak Woodland', 'FEW': 'Fresh Emergent Wetland', 'ASC_': 'Alkali Desert Scrub',
           'EUC': 'Eucalyptus', 'BOP': 'Blue Oak-Foothill Pine', 'DSC': 'Desert Scrub', 'PJN': 'Pinyon-Juniper',
           'DRI': 'Desert Riparian', 'DSW': 'Desert Wash', 'JST': 'Joshua Tree', 'DSS': 'Desert Succulent Shrub', 'POS': 'Palm Oasis'}
ALL = {'slr5ft': 'clim:slr', 'fire_perimeter': 'clim:fire', 'scmlinkage': 'link:scml', 'gde': 'fw:gde',
       'wetlands': 'fw:wetlands', 'fwa_rich': 'fw:fwrich', 'stream_1_2': 'fw:headwaters', 'stream_3_5': 'fw:streams',
       'stream_6_9': 'fw:rivers'}
SIMPLE = {'cnrm': 'clim:cnrm', 'miroc': 'clim:miroc', 'endp': 'kling:endp', 'plant': 'kling:plant', 'flood': 'fw:floodplain',
          'chn': 'conn:chn', 'int': 'conn:int', 'diff': 'conn:diff', 'clink': 'conn:clink'}


def read(name):
    with open(os.path.join(CSV_DIR, f'featureGAPSummary_{name}_wTotals.csv')) as f:
        rows = list(csv.reader(f))
    head = rows[0]
    return {r[0]: dict(zip(head[1:], map(float, r[1:]))) for r in rows[1:]}


def ref(r):
    t = r['Feature Total']
    return {'extent': t, 'gap12': r['Disc'] / t, 'gap34': r['g34'] / t, 'none': r['nonconserved'] / t}


statewide = json.load(open(f'{ROOT}/data/statewide.json'))['results']
report = json.load(open(f'{ROOT}/data/report.json'))
rep = report['features']
app = {}            # feature id -> row
for theme in statewide.values():
    for rows in theme.values():
        for r in rows:
            if r.get('feature'):
                app.setdefault(r['feature'], r)
by_label = {}
for r in statewide['habitat']['cwhr13']:
    by_label[('cwhr13', r['label'])] = r['feature']
for r in statewide['habitat']['cwhr']:
    by_label[('cwhr', r['label'])] = r['feature']

# --- reference rows keyed by app feature id
gt = {}
net = {}            # feature id -> share of the 30x30 network
for name, r in read('all').items():
    fid = ALL.get(name) or (f'ace:{name}' if f'ace:{name}' in app else None)
    if fid:
        gt[fid] = ref(r)
for name in ('cnrm', 'miroc', 'endp', 'plant', 'flood', 'connectivity'):
    t = read(name)
    for k, r in t.items():
        if k in SIMPLE:
            gt[SIMPLE[k]] = ref(r)
            net[SIMPLE[k]] = r['Disc'] / t['Network Total']['Disc']
for k, r in read('all').items():
    if k in ALL:
        net[ALL[k]] = r['Disc'] / read('all')['Network Total']['Disc']
for table, names, kind in (('WHR13NAME', WHR13, 'cwhr13'), ('WHRTYPE', WHRTYPE, 'cwhr')):
    t = read(table)
    for code, label in names.items():
        fid = by_label.get((kind, label))
        if fid is None:
            print(f'! no app feature for {table} {code} {label}', file=sys.stderr)
            continue
        gt[fid] = ref(t[code])
        net[fid] = t[code]['Disc'] / t['Network Total']['Disc']
eco = read('ecoregion')
eco_net = {k: r['Disc'] / eco['Network Total']['Disc'] for k, r in eco.items() if k != 'Network Total'}

STATE = statewide['overview']['protection'][0]['frac_gap12']


def need(f, applies=True):
    if not applies:
        return 'not_applicable'
    return 'under' if f < 0.20 else 'slightly_under' if f < STATE else 'on_par'


# need-class configuration as the app applies it
themes = {os.path.basename(os.path.dirname(p)): json.load(open(p)) for p in glob.glob(f'{ROOT}/config/themes/*/theme.json')}
keys, no_need = set(), set()
for th in themes.values():
    for c in th.get('charts', []):
        if c.get('type') != 'representation':
            continue
        keys |= set(c.get('key_features', []))
        no_need |= set(c.get('na_features', []))
        if c.get('need') is False:
            rows = statewide[[k for k, v in themes.items() if v is th][0]][c['query']]
            w = c.get('where') or {}
            no_need |= {r['feature'] for r in rows if all(r.get(a) == b for a, b in w.items())}

out = []


def pp(a, b):
    return None if a is None or b is None else 100 * (a - b)


rows = []
for fid, r in app.items():
    if fid in eco:
        continue
    g = gt.get(fid)
    p = rep.get(fid)
    rest = r['frac_gap34'] + r['frac_none']
    green = r['frac_gap34'] / rest if rest else None
    a_ext = r.get('acres') or r.get('miles')
    rows.append({
        'feature': fid, 'label': r['label'],
        'ext_ratio': a_ext / g['extent'] if g else None,
        'd12_csv': pp(r['frac_gap12'], g and g['gap12']), 'd34_csv': pp(r['frac_gap34'], g and g['gap34']),
        'dnone_csv': pp(r['frac_none'], g and g['none']),
        'd12_pdf': pp(r['frac_gap12'], p and p['pct'] / 100),
        'csv_vs_pdf': pp(g and g['gap12'], p and p['pct'] / 100) if g and p else None,
        'need_app': need(r['frac_gap12'], fid not in keys and fid not in no_need),
        'need_pdf': p and (p['need'] if not p.get('key') else 'key'),
        'need_rule_on_pdf': p and need(p['pct'] / 100),
        'key_app': fid in keys, 'key_pdf': bool(p and p.get('key')),
        'green_app': green, 'green_pdf': p and p.get('pathway_green'),
        'net_app': r.get('share_of_network'), 'net_csv': net.get(fid),
        'printed': p and p['pct'], 'app': 100 * r['frac_gap12'],
    })
json.dump(rows, open(os.path.join(CSV_DIR, '..', 'validate_rows.json'), 'w'), indent=1)

# --- summary
def stat(name, vals, tol):
    vals = [abs(v) for v in vals if v is not None]
    within = sum(v <= tol for v in vals)
    return f'{name}: {len(vals)} compared, {within} within {tol}, max {max(vals):.2f}' if vals else f'{name}: none'


print(stat('30x30 share vs CSV (pp)', [r['d12_csv'] for r in rows], 1))
print(stat('GAP 3-4 share vs CSV (pp)', [r['d34_csv'] for r in rows], 1))
print(stat('non-conserved share vs CSV (pp)', [r['dnone_csv'] for r in rows], 1))
print(stat('30x30 share vs PDF (pp, unrounded)', [r['d12_pdf'] for r in rows], 1))
print(stat('CSV vs PDF 30x30 share (pp)', [r['csv_vs_pdf'] for r in rows], 0.5))
print(stat('network share vs CSV (pp)', [pp(r['net_app'], r['net_csv']) for r in rows if r['net_app'] is not None], 0.5))
print(stat('pathway green vs PDF pie', [r['green_app'] - r['green_pdf'] for r in rows if r['green_pdf'] is not None], 0.1))
print(stat('extent ratio - 1', [r['ext_ratio'] - 1 for r in rows if r['ext_ratio'] and not r['feature'].startswith('fw:') or r['feature'] in ('fw:wetlands', 'fw:gde', 'fw:fwrich', 'fw:floodplain')], 0.02))

print('\n# extent off by more than 2%')
for r in sorted(rows, key=lambda r: -abs((r['ext_ratio'] or 1) - 1)):
    if r['ext_ratio'] and abs(r['ext_ratio'] - 1) > 0.02:
        print(f"  {r['feature']:16s} {r['label'][:45]:45s} app/report = {r['ext_ratio']:.3f}")
print('\n# status share off CSV by more than 1 pp')
for r in rows:
    d = [(k, r[k]) for k in ('d12_csv', 'd34_csv', 'dnone_csv') if r[k] is not None and abs(r[k]) > 1]
    if d:
        print(f"  {r['feature']:16s} {r['label'][:40]:40s} " + ' '.join(f'{k[1:-4]}={v:+.1f}' for k, v in d))
print('\n# CSV and PDF disagree by more than 0.5 pp (30x30 share)')
for r in rows:
    if r['csv_vs_pdf'] is not None and abs(r['csv_vs_pdf']) > 0.5 + (0.5 if float(r['printed']).is_integer() else 0.05):
        print(f"  {r['feature']:16s} {r['label'][:40]:40s} csv-pdf={r['csv_vs_pdf']:+.2f} printed={r['printed']}")
print('\n# need class: app vs report (keys shown as key)')
for r in rows:
    if r['need_pdf'] is None:
        continue
    app_n = 'key' if r['key_app'] else r['need_app']
    if app_n != r['need_pdf']:
        rule = r['need_rule_on_pdf']
        print(f"  {r['feature']:16s} {r['label'][:38]:38s} app={app_n:15s} report={r['need_pdf']:15s} "
              f"rule-on-printed={rule} app%={r['app']:.1f} printed={r['printed']}")
print('\n# pathway pie off by more than 0.1')
for r in rows:
    if r['green_pdf'] is not None and abs(r['green_app'] - r['green_pdf']) > 0.1:
        print(f"  {r['feature']:16s} {r['label'][:40]:40s} app={r['green_app']:.2f} pie~{r['green_pdf']:.2f}")
print('\n# network share off CSV by more than 0.5 pp')
for r in rows:
    if r['net_app'] is not None and r['net_csv'] is not None and abs(pp(r['net_app'], r['net_csv'])) > 0.5:
        print(f"  {r['feature']:16s} {r['label'][:40]:40s} app={100*r['net_app']:.1f} csv={100*r['net_csv']:.1f}")

# --- overview: statewide land, report prose network figures, ecoregion table and each ecoregion page
print('\n# land characterization (statewide)')
lp = statewide['overview']['protection'][0]
tot = read('all')['Total']
for k, c in (('frac_gap12', 'Disc'), ('frac_gap34', 'g34'), ('frac_none', 'nonconserved')):
    print(f"  {k}: app {100*lp[k]:.2f}  csv {100*tot[c]/tot['Feature Total']:.2f}  pdf {100*report['land'][k]:.1f}")
print(f"  land acres: app {lp['land_acres']:,.0f}  csv {tot['Feature Total']:,.0f}")
print('\n# report prose network figures')
for k, v in report['network'].items():
    if isinstance(v, dict):
        for f, x in v.items():
            a = next((r.get('share_of_network') for r in statewide['overview']['ecoregions'] if r['feature'] == f), None) \
                if k == 'ecoregion' else app.get(f, {}).get('share_of_network')
            print(f"  {k:10s} {f:42s} app {100*a:.1f}  pdf {100*x:.1f}" if a is not None else f'  {k} {f} app none')
    else:
        print(f'  {k:20s} pdf {100*v:.1f}')
print('\n# ecoregion table (statewide view) and each ecoregion page')
worst = []
for r in statewide['overview']['ecoregions']:
    g = ref(eco[r['feature']])
    page = json.load(open(f"{ROOT}/data/areas/ecoregion/{r['feature']}.json"))['results']['overview']['protection'][0]
    d = [100 * (r['frac_gap12'] - g['gap12']), 100 * (r['frac_gap34'] - g['gap34']), 100 * (r['frac_none'] - g['none']),
         100 * (r['share_of_network'] - eco_net[r['feature']]), r['acres'] / g['extent'] - 1,
         100 * (page['frac_gap12'] - r['frac_gap12']), 100 * (page['frac_gap34'] - r['frac_gap34'])]
    worst.append((r['feature'], d))
    print(f"  {r['feature'][:34]:34s} d12 {d[0]:+.2f} d34 {d[1]:+.2f} dnone {d[2]:+.2f} dnet {d[3]:+.2f} ext {100*d[4]:+.2f}% "
          f"page-table {d[5]:+.2f}/{d[6]:+.2f}")
