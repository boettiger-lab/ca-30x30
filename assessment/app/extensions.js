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

import { fmt, escapeHtml } from 'https://cdn.jsdelivr.net/gh/SchmidtDSE/glen-charts@v0.11.0/core/format.js';
import { paramKey, statewideAoi, matchesWhen } from 'https://cdn.jsdelivr.net/gh/SchmidtDSE/glen-charts@v0.11.0/core/engine.js';
import { polygonSource } from 'https://cdn.jsdelivr.net/gh/SchmidtDSE/glen-charts@v0.11.0/sources/polygon-source.js';
import { renderRepresentation, NEED, REP_CSS } from './represent.js';
import { tokens } from './tokens.js';

const shortName = s => String(s).replace(/^(Congressional|State Senate|Assembly) District /, (m, k) => ({ Congressional: 'CD ', 'State Senate': 'SD ', Assembly: 'AD ' }[k]));

/**
 * The selected manager ({ value, label, levels }), or null for all managers.
 * Under Federal with one agency chosen, the agency: { label, levels, agencies }
 * or, for "Other federal", { label, levels, rest: the agencies it leaves out }.
 */
export function managerOf(app, params = {}) {
    const p = (app.params || []).find(x => x.id === 'manager');
    const o = p?.options.find(x => x.value === (params.manager ?? p.default));
    if (!o?.levels) return null;
    const ap = (app.params || []).find(x => x.id === 'agency');
    const a = ap && matchesWhen(ap.when, app, params) && ap.options.find(x => x.value === (params.agency ?? ap.default));
    if (!a?.agencies && !a?.rest) return o;
    return { value: a.value, label: a.label, levels: o.levels, agencies: a.agencies || null,
        rest: a.rest ? ap.options.filter(x => x.agencies).map(x => x.label) : null };
}

/** The same area with every manager counted. */
function allManagers(app, aoi) {
    const params = { ...(aoi.params || {}), manager: 'all' };
    if (aoi.kind === 'state') return statewideAoi(app, params);
    return { ...aoi, key: `${aoi.key.split('@')[0]}@${paramKey(app, params)}`, params };
}

/**
 * The representation table needs, beside the feature rows: California's share
 * in 30x30 (the need-class benchmark), the area's own share (a second tick),
 * and on the statewide view the report's published values. With a manager
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
            mgr ? engine.run(theme, chart.query, allManagers(app, aoi)) : null,
        ]).then(([rows, st, ar, all]) => [rows, {
            stateLevel: st?.[0]?.frac_gap12 ?? null,
            areaLevel: ar?.[0]?.frac_gap12 ?? null,
            areaLabel: shortName(aoi.label),
            report: isRegion ? opts.reference?.values?.features ?? null : null,
            manager: mgr,
            all,
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
 * California's share in 30x30, all managers, into every .ca-level span once
 * it loads (precomputed, so at once); the note is written before it is known.
 */
function fillLevel(engine) {
    engine.runStatewide(engine.config.overview, 'protection', { manager: 'all' }).then(rows => {
        const v = rows?.[0]?.frac_gap12;
        if (v != null) document.querySelectorAll('.ca-level').forEach(el => { el.textContent = fmt(v, 'pct'); });
    }).catch(() => {});
}

/** How to read the tables: the report's framework, in one collapsible note. */
function reportHead(aoi, { engine, reference, isRegion }) {
    fillLevel(engine);
    const lvl = '<span class="ca-level">California’s level</span>';
    // a drawn area never has a precomputed file (app.live_note covers named areas)
    const live = aoi.kind === 'polygon' ? '<p class="tile-note live-note">Results for this area are computed live from the source data; larger areas can take a minute or two.</p>' : '';
    const mgr = managerOf(engine.config.app, aoi.params);
    if (mgr) return `${live}${managerNote(mgr, isRegion)}`;
    return `${live}<details class="card framework">
        <summary><b>How to read this</b> — the report's representation framework</summary>
        <div class="framework-body">
        <p>Each table shows how much of a habitat or feature lies in <b>30x30 Conservation Areas</b> (GAP 1–2), on
           <b>other conserved or public land</b> (GAP 3–4), and on <b>non-conserved land</b>, following the
           <a href="${escapeHtml(reference?.values?.url || reference?.url || '#')}" target="_blank" rel="noopener">2025 Biodiversity Assessment</a>.</p>
        <ul class="need-legend">
            <li><span class="pct need-under">&lt; 20%</span> ${NEED.under.label}</li>
            <li><span class="pct need-slight">20% – ${lvl}</span> ${NEED.slightly_under.label}</li>
            <li><span class="pct need-par">≥ ${lvl}</span> ${NEED.on_par.label}: California's current share of land in 30x30</li>
            <li><span class="pct need-na key">Key feature</span> rare or critical; the report recommends conserving all remaining extent</li>
        </ul>
        <p>The <b>pathway</b> pie splits what lies outside 30x30: <span class="sw s34"></span> other conserved or public land
           (improve management or durability) vs <span class="sw snone"></span> non-conserved land (acquisition or easement).
           Need classes always compare with California's level${isRegion ? '' : ', even for a smaller area; the area’s own share in 30x30 is the second tick on each bar'}.
           ${isRegion ? 'The <b>Report</b> column gives the published value and this app’s difference from it, in percentage points.' : ''}</p>
        <p class="tile-note">No AI model is involved: every number is fixed, reviewable SQL over public data — see “Method &amp; SQL” under each section, or Export.</p>
        </div></details>`;
}

/** Which units count, in words, with the inventory's own names where they differ from the label. */
function who(mgr) {
    const m = escapeHtml(mgr.label);
    if (mgr.rest) return `a federal manager other than the ${escapeHtml(mgr.rest.join(', '))} (<b>${m}</b>)`;
    const names = mgr.agencies || mgr.levels;
    const field = mgr.agencies ? 'managing agency' : 'manager level';
    return `a <b>${m}</b> manager${names.length > 1 || names[0] !== mgr.label
        ? ` (${field} ${escapeHtml(names.join(', '))} in the 2025 Conserved Areas inventory)` : ''}`;
}

/** How to read the tables with one manager selected. */
function managerNote(mgr, isRegion) {
    const m = escapeHtml(mgr.label);
    return `<details class="card framework" open>
        <summary><b>How to read this</b>: ${m} land only</summary>
        <div class="framework-body">
        <p>Only conserved land with ${who(mgr)} counts as <span class="sw s12"></span> 30x30 (GAP 1–2) or <span class="sw s34"></span> GAP 3–4.
           Other managers’ conserved land is shown separately (<span class="sw sother"></span>), and
           <span class="sw snone"></span> non-conserved land is unchanged.</p>
        <p>Every share is still a share of the whole ${isRegion ? 'state' : 'area'}: a habitat at 5% in ${m} 30x30 has 5% of its
           ${isRegion ? 'California' : 'local'} extent on ${m} GAP 1–2 land, not 5% of ${m} land. <b>Share of 30x30</b> is ${m}’s part
           of each feature’s 30x30 acres, all managers together. The tick marks ${m}’s share of all land in 30x30, so a feature
           right of the tick is better represented in ${m} 30x30 than land as a whole.</p>
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
};
