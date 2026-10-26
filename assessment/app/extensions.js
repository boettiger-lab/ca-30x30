/**
 * What the Assessment Explorer adds to glen-charts: the {{LAND}} template
 * token, the representation table (report Tables 3-13), the 2025 Conserved
 * Areas map layer, polygon drawing, and the "How to read this" note.
 *
 * Passed to createExplorer({ extensions }) by index.html, and read by the
 * glen-charts precompute CLI (app.json "extensions") for its tokens and the
 * overlay's tile URL, so nothing here may touch the DOM at load time.
 */

import { fmt, escapeHtml } from 'https://cdn.jsdelivr.net/gh/SchmidtDSE/glen-charts@v0.2.10/core/format.js';
import { polygonSource } from 'https://cdn.jsdelivr.net/gh/SchmidtDSE/glen-charts@v0.2.10/sources/polygon-source.js';
import { renderRepresentation, NEED, REP_CSS } from './represent.js';
import { tokens } from './tokens.js';

const shortName = s => String(s).replace(/^(Congressional|State Senate|Assembly) District /, (m, k) => ({ Congressional: 'CD ', 'State Senate': 'SD ', Assembly: 'AD ' }[k]));

/**
 * The representation table needs, beside the feature rows: California's share
 * in 30x30 (the need-class benchmark), the area's own share (a second tick),
 * and on the statewide view the report's published values.
 */
const representation = {
    load({ engine, theme, chart, aoi, isRegion, opts }) {
        const overview = engine.config.overview;
        return Promise.all([
            engine.run(theme, chart.query, aoi),
            engine.runStatewide(overview, 'protection'),
            isRegion ? null : engine.run(overview, 'protection', aoi),
        ]).then(([rows, st, ar]) => [rows, {
            stateLevel: st?.[0]?.frac_gap12 ?? null,
            areaLevel: ar?.[0]?.frac_gap12 ?? null,
            areaLabel: shortName(aoi.label),
            report: isRegion ? opts.reference?.values?.features ?? null : null,
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

/** How to read the tables: the report's framework, in one collapsible note. */
function reportHead(aoi, { engine, reference, isRegion }) {
    const st = engine.statewide?.results?.overview?.protection?.[0]?.frac_gap12;
    const lvl = st ? fmt(st, 'pct') : 'California’s level';
    // a drawn area never has a precomputed file (app.live_note covers named areas)
    const live = aoi.kind === 'polygon' ? '<p class="tile-note live-note">Results for this area are computed live from the source data; larger areas can take a minute or two.</p>' : '';
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

export default {
    tokens,
    charts: { representation },
    overlays: [conserved],
    sources: [polygonSource()],
    reportHead,
    shortName,
};
