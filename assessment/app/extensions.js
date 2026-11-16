/**
 * What the Assessment Explorer adds to glen-charts: the {{LAND}} template
 * token, the representation table (report Tables 3-13), the 2025 Conserved
 * Areas map layer, polygon drawing, and the "How to read this" note, each
 * aware of the `manager` param (one kind of manager's conserved land).
 *
 * Passed to createExplorer({ extensions }) by index.html, and read by the
 * glen-charts precompute CLI (app.json "extensions") for its tokens and the
 * overlay's tile URL, so nothing here may touch the DOM at load time.
 */

import { fmt, escapeHtml } from 'https://cdn.jsdelivr.net/gh/SchmidtDSE/glen-charts@v0.16.1/core/format.js';
import { polygonSource } from 'https://cdn.jsdelivr.net/gh/SchmidtDSE/glen-charts@v0.16.1/sources/polygon-source.js';
import { renderRepresentation, NEED, REP_CSS } from './represent.js';
import { tokens, agencyPick } from './tokens.js';

const shortName = s => String(s).replace(/^(Congressional|State Senate|Assembly) District /, (m, k) => ({ Congressional: 'CD ', 'State Senate': 'SD ', Assembly: 'AD ' }[k]));

/**
 * The selected manager ({ value, label, levels }), or null for all managers.
 * With managers picked in the level's menu: { value, label, levels, agencies },
 * labelled by the one manager, or by how many were picked.
 */
export function managerOf(app, params = {}) {
    const p = (app.params || []).find(x => x.id === 'manager');
    const o = p?.options.find(x => x.value === (params.manager ?? p.default));
    if (!o?.levels) return null;
    const a = agencyPick(app, params);
    if (!a) return o;
    const label = a.picked.length === 1 ? a.picked[0].label : `${a.picked.length} ${o.label.toLowerCase()} managers`;
    return { value: a.picked.map(x => x.value).join(','), label, levels: o.levels, agencies: a.picked.flatMap(x => x.agencies) };
}

/** A manager's share of its own conserved land in 30x30, from a protection row. */
const ownShare = r => {
    const a = Number(r?.gap12_acres), b = Number(r?.gap34_acres);
    return a + b > 0 ? a / (a + b) : null;
};

/** What a sub-state area is called in "on par with the ... level". */
const KIND_WORD = { ecoregion: 'ecoregion', county: 'county', cd: 'district', sldu: 'district', sldl: 'district' };

/**
 * The representation table needs, beside the feature rows: California's share
 * in 30x30 (a tick), the area's own share (a second tick, and the need-class
 * benchmark for a sub-state area), the same rows statewide for a sub-state
 * area's California column, and on the statewide view the report's published values. With a manager
 * selected, both levels are that manager's, and the same rows for every
 * manager give the manager's share of each feature's 30x30 acres.
 */
const representation = {
    load({ engine, theme, chart, aoi, isRegion, params, opts }) {
        const app = engine.config.app;
        const overview = engine.config.overview;
        const mgr = managerOf(app, params);
        return Promise.all([
            engine.run(theme, chart.query, aoi),
            engine.runStatewide(overview, 'protection', params),
            isRegion ? null : engine.run(overview, 'protection', aoi),
            isRegion || mgr ? null : engine.runStatewide(theme, chart.query, params).catch(() => null),
        ]).then(([rows, st, ar, state]) => [rows, {
            stateLevel: st?.[0]?.frac_gap12 ?? null,
            areaLevel: ar?.[0]?.frac_gap12 ?? null,
            areaLabel: shortName(aoi.label),
            areaKind: KIND_WORD[aoi.kind] || 'area',
            report: isRegion ? opts.reference?.values?.features ?? null : null,
            manager: mgr,
            managerLevel: mgr ? ownShare((isRegion ? st : ar)?.[0]) : null,
            state,
        }]);
    },
    render(el, chart, [rows, ctx]) {
        renderRepresentation(el, chart, rows, ctx);
    },
    css: REP_CSS,
};

/** Conserved-area units, colored by majority status as in the report's maps. */
const g12 = ['+', ['to-number', ['get', 'Final_g1_p'], 0], ['to-number', ['get', 'Final_g2_p'], 0]];
const conserved = {
    id: 'conserved',
    url: 'https://s3-west.nrp-nautilus.io/public-ca30x30/conserved-areas-terrestrial-2025.pmtiles',
    source_layer: 'conserved-areas-terrestrial-2025',
    paint: { 'fill-color': ['case', ['>=', g12, 50], '#1b6e3a', '#7dbb63'], 'fill-opacity': 0.55 },
    popup: p => {
        const g = (Number(p.Final_g1_p) || 0) + (Number(p.Final_g2_p) || 0);
        return `<b>${escapeHtml(p.UNIT_NAME || 'Conserved area')}</b><br>${escapeHtml(p.MNG_AGENCY || '')}<br>${Math.round(g)}% GAP 1–2 · ${Math.round(100 - g)}% GAP 3–4`;
    },
    legend: `<div class="title">2025 30x30 Conserved Areas</div>
        <div class="lg-row"><i class="s12"></i>Mostly GAP 1–2<span class="lg-long"> (30x30)</span></div>
        <div class="lg-row"><i class="s34"></i>Mostly GAP 3–4<span class="lg-long"> (other conserved or public)</span></div>
        <div class="lg-row"><i class="snone"></i>Non-conserved<span class="lg-long"> (unshaded)</span></div>`,
    toggle: 'Show conserved areas',
};

/**
 * Show only the selected manager's units on the conserved-areas layer.
 * glen-charts has no per-param overlay filter, so index.html hands over the
 * explorer (attach) and each report draw (reportHead) sets the filter.
 */
let mapView = null;
let shown = null;     // the manager whose units are drawn, or null for all
function filterConserved(tries = 0) {
    const m = mapView?.map;
    if (!m) return;
    const layer = `ov-${conserved.id}-fill`;
    if (!m.getLayer(layer)) {
        if (tries < 50) setTimeout(() => filterConserved(tries + 1), 200);
        return;
    }
    const uniq = a => [...new Set(a)];
    const f = !shown ? null
        : shown.agencies ? ['match', ['get', 'MNG_AGENCY'], uniq(shown.agencies), true, false]
            : ['match', ['get', 'MNG_AG_LEV'], uniq(shown.levels), true, false];
    m.setFilter(layer, f);
    const title = document.querySelector(`#overlay-legend .ov[data-ov="${conserved.id}"] .title`);
    if (title) title.textContent = shown ? `2025 30x30 Conserved Areas: ${shown.label} only` : '2025 30x30 Conserved Areas';
}
function showManager(mgr) {
    shown = mgr;
    filterConserved();
}
/** Called by index.html with the explorer once it has started. */
function attach(ex) {
    mapView = ex?.mapView || null;
    filterConserved();
}

/**
 * California's share in 30x30, all managers, into every .ca-level span once
 * it loads (precomputed, so at once); the note is written before it is known.
 */
function fillLevel(engine) {
    engine.runStatewide(engine.config.overview, 'protection', { manager: 'all' }).then(rows => {
        const v = rows?.[0]?.frac_gap12;
        if (v != null) document.querySelectorAll('.ca-level').forEach(el => { el.textContent = fmt(v, 'pct'); });
    }).catch(() => {});
}

/**
 * Move the note from under the report title to just below the land summary
 * (the overview card), above the first section. glen-charts writes the head
 * and then appends the overview in the same task, so a microtask sees both.
 */
function placeNote() {
    queueMicrotask(() => {
        const note = document.querySelector('#report > details.framework');
        const overview = document.querySelector('#report > .card:not(.theme-card):not(.framework)');
        if (note && overview) overview.after(note);
    });
}

/** The area's own share in 30x30 into every .area-level span, as fillLevel. */
function fillAreaLevel(engine, aoi) {
    engine.run(engine.config.overview, 'protection', aoi).then(rows => {
        const v = rows?.[0]?.frac_gap12;
        if (v != null) document.querySelectorAll('.area-level').forEach(el => { el.textContent = fmt(v, 'pct'); });
    }).catch(() => {});
}

/** How to read the tables: the report's framework, in one collapsible note. */
function reportHead(aoi, { engine, reference, isRegion }) {
    fillLevel(engine);
    placeNote();
    if (!isRegion) fillAreaLevel(engine, aoi);
    const place = escapeHtml(shortName(aoi.label || 'this area'));
    const lvl = isRegion ? '<span class="ca-level">California’s level</span>' : `<span class="area-level">${place}’s level</span>`;
    const whose = isRegion ? 'California' : place;
    // a drawn area never has a precomputed file (app.live_note covers named areas)
    const live = aoi.kind === 'polygon' ? '<p class="tile-note live-note">Results for this area are computed live from the source data; larger areas can take a minute or two.</p>' : '';
    const mgr = managerOf(engine.config.app, aoi.params);
    showManager(mgr);
    if (mgr) return `${live}${managerNote(mgr, isRegion)}`;
    return `${live}<details class="card framework">
        <summary><b>How to read this</b> — the report's representation framework</summary>
        <div class="framework-body">
        <p>Each table shows how much of a habitat or feature lies in <b>30x30 Conservation Areas</b> (GAP 1–2), on
           <b>other conserved or public land</b> (GAP 3–4), and on <b>non-conserved land</b>, following the
           <a href="${escapeHtml(reference?.values?.url || reference?.url || '#')}" target="_blank" rel="noopener">2025 Biodiversity Assessment</a>.</p>
        <ul class="need-legend">
            <li><span class="pct need-under">&lt; 20%</span> ${NEED.under.label}${isRegion ? '' : ` (or below ${lvl}, where that is under 20%)`}</li>
            <li><span class="pct need-slight">20% – ${lvl}</span> ${NEED.slightly_under.label}</li>
            <li><span class="pct need-par">≥ ${lvl}</span> ${NEED.on_par.label}: ${whose}’s current share of land in 30x30</li>
            <li><span class="pct need-na key">Key feature</span> rare or critical; the report recommends conserving all remaining extent</li>
        </ul>
        <p>The <b>pathway</b> pie splits what lies outside 30x30: <span class="sw s34"></span> other conserved or public land
           (improve management or durability) vs <span class="sw snone"></span> non-conserved land (acquisition or easement).
           ${isRegion ? 'Need classes compare with California’s level.'
        : `Need classes compare with ${place}’s own share of land in 30x30 (the dashed tick on each bar), not California’s (the solid tick);
           the <b>California</b> column gives each feature’s statewide share in 30x30, coloured against California’s level, so the statewide goal stays in view.`}
           ${isRegion ? 'The <b>Report</b> column gives the published value and this app’s difference from it, in percentage points.' : ''}</p>
        <p class="tile-note">No AI model is involved: every number is fixed, reviewable SQL over public data — see “Method &amp; SQL” under each section, or Export.</p>
        </div></details>`;
}

/** Which units count, in words, with the inventory's own names where they differ from the label. */
function who(mgr) {
    const m = escapeHtml(mgr.label);
    if (mgr.agencies) return mgr.agencies.length === 1 && mgr.agencies[0] === mgr.label
        ? `the managing agency <b>${m}</b> in the 2025 Conserved Areas inventory`
        : `the managing ${mgr.agencies.length > 1 ? 'agencies' : 'agency'} ${escapeHtml(mgr.agencies.join('; '))} in the 2025 Conserved Areas inventory (<b>${m}</b>)`;
    const names = mgr.levels;
    return `a <b>${m}</b> manager${names.length > 1 || names[0] !== mgr.label
        ? ` (manager level ${escapeHtml(names.join(', '))} in the 2025 Conserved Areas inventory)` : ''}`;
}

/** How to read the tables with one manager selected. */
function managerNote(mgr, isRegion) {
    const m = escapeHtml(mgr.label);
    return `<details class="card framework" open>
        <summary><b>How to read this</b>: ${m} land only</summary>
        <div class="framework-body">
        <p>Only conserved land with ${who(mgr)} counts here.</p>
        <p>In each table, a bar is ${m} land only: of what ${m} holds of a habitat or feature in this ${isRegion ? 'state' : 'area'},
           the share in <span class="sw s12"></span> 30x30 (GAP 1–2) and in <span class="sw s34"></span> GAP 3–4.
           The dashed tick is the share of all ${m} land here in 30x30, so a feature left of it is less protected than ${m}’s land as a whole.
           <b>GAP 3–4</b> gives the acres that could be managed to count toward 30x30, and the last column what ${m} holds of each feature
           and its share of the feature’s whole extent here.</p>
        <p>Need classes and the report’s published values describe all managers together, so they are not shown here.
           Choose <b>All</b> under “Managed by” to see them.</p>
        <p class="tile-note">The manager is each unit’s managing agency level (CPAD / CCED); for an easement it is the easement holder,
           so non-profit land includes easements on private land.</p>
        </div></details>`;
}

export default {
    tokens,
    charts: { representation },
    overlays: [conserved],
    sources: [polygonSource()],
    reportHead,
    shortName,
    attach,
};
