/**
 * Representation table: the interactive form of the 2025 Biodiversity
 * Assessment's Tables 3-13. One row per habitat/feature:
 *
 *   share in 30x30 (GAP 1-2), with the report's need class
 *   status bar: 30x30 | other conserved or public (GAP 3-4) | non-conserved,
 *     with a tick at California's level and (for a sub-state area) the area's
 *   pathway pie: of the feature outside 30x30, the share on GAP 3-4 land
 *     (improve management / durability) vs non-conserved land (acquisition /
 *     easement)
 *   the report's published value (statewide view only), and extent
 *
 * spec (theme.json chart with "type": "representation"):
 *   query, title, subtitle
 *   need          false for threshold/value features (ACE, richness): the
 *                 report gives these no need class ("not applicable")
 *   key_features  feature ids the report marks as Key Features (no need class)
 *   na_features   other feature ids the report gives no need class
 *   where         { field: value } row filter (e.g. {"natural": true})
 *   group_field   field to split rows under sub-headings (e.g. "grp")
 *   sort          "asc" (by share in 30x30, as the report's tables) or "none"
 *   measure       "acres" (default) or "miles"
 *
 * ctx: { stateLevel, areaLevel, report: {feature: {...}} | null, areaLabel }
 * The need class is always measured against California's level (the report's
 * framework); the area's own level is shown as a second reference tick.
 */

import { fmt, escapeHtml } from 'https://cdn.jsdelivr.net/gh/SchmidtDSE/glen-charts@v0.2.8/core/format.js';
import { hover } from 'https://cdn.jsdelivr.net/gh/SchmidtDSE/glen-charts@v0.2.8/core/charts.js';

export const STATUS = [
    { key: 'frac_gap12', label: '30x30 Conservation Areas (GAP 1–2)', short: '30x30', cls: 's12' },
    { key: 'frac_gap34', label: 'Other conserved or public land (GAP 3–4)', short: 'GAP 3–4', cls: 's34' },
    { key: 'frac_none', label: 'Non-conserved land', short: 'Non-conserved', cls: 'snone' },
];

export const NEED = {
    under: { label: 'Under-represented', cls: 'need-under', note: '< 20% in 30x30' },
    slightly_under: { label: 'Slightly under', cls: 'need-slight', note: '20% to California level' },
    on_par: { label: 'On par or above', cls: 'need-par', note: '≥ California level' },
    not_applicable: { label: 'Not applicable', cls: 'need-na', note: 'threshold features are not classed' },
};

/** The report's definition of a Key Feature (Methods, "Representation framework"). */
export const KEY_FEATURE = 'Key Features are rare (3% of the state or less), historically converted (such as wetlands), or critical ' +
    'to ecosystem function (such as connectivity linkages and groundwater-dependent ecosystems).';

export function needClass(frac, stateLevel, applies = true) {
    if (!applies || frac == null || !Number.isFinite(frac)) return 'not_applicable';
    if (frac < 0.20) return 'under';
    if (frac < stateLevel) return 'slightly_under';
    return 'on_par';
}

export function renderRepresentation(container, spec, rows, ctx) {
    container.innerHTML = '';
    rows = (rows || []).filter(r => !spec.where || Object.entries(spec.where).every(([k, v]) => r[k] === v));
    rows = rows.filter(r => Number(r.acres ?? r.miles) > 0 || r.frac_gap12 != null);
    if (!rows.length) {
        container.innerHTML = '<div class="sub">None of these features occur in this area.</div>';
        return;
    }
    if (spec.sort !== 'none') rows = [...rows].sort((a, b) => (a.frac_gap12 ?? -1) - (b.frac_gap12 ?? -1));
    const keys = new Set(spec.key_features || []);
    const na = new Set(spec.na_features || []);
    const measure = spec.measure || 'acres';
    const showReport = !!ctx.report;
    const state = ctx.stateLevel, area = ctx.areaLevel;

    // legend: status colors, reference ticks, need classes
    const lg = document.createElement('div');
    lg.className = 'legend-row rep-legend';
    lg.innerHTML = STATUS.map(s => `<span><i class="${s.cls}"></i>${escapeHtml(s.label)}</span>`).join('') +
        (state != null ? `<span><i class="tick state"></i>California in 30x30 (${fmt(state, 'pct')})</span>` : '') +
        (area != null ? `<span><i class="tick area"></i>${escapeHtml(ctx.areaLabel || 'This area')} in 30x30 (${fmt(area, 'pct')})</span>` : '');
    container.appendChild(lg);
    if (rows.some(r => keys.has(r.feature))) {
        const kn = document.createElement('div');
        kn.className = 'key-note';
        kn.innerHTML = `<span class="key-badge">Key feature</span> ${escapeHtml(KEY_FEATURE)} The report recommends conserving all remaining ` +
            'extent wherever feasible, so these are not given a need class against the California level.';
        container.appendChild(kn);
    }

    const groups = new Map();
    for (const r of rows) {
        const g = spec.group_field ? r[spec.group_field] : '';
        if (!groups.has(g)) groups.set(g, []);
        groups.get(g).push(r);
    }

    const table = document.createElement('table');
    table.className = 'rep-table';
    table.innerHTML = `<thead><tr>
        <th class="c-feat">Feature</th>
        <th class="c-pct">In 30x30</th>
        <th class="c-bar">Conservation status</th>
        <th class="c-pie" title="Of the feature outside 30x30: on other conserved or public land (GAP 3–4) vs non-conserved land">Pathway</th>
        ${showReport ? '<th class="c-rep" title="Value published in the 2025 Biodiversity Assessment (proportional estimate, with its lower–upper range)">Report</th>' : ''}
        <th class="c-ext">Extent</th></tr></thead>`;

    for (const [g, list] of groups) {
        const tb = document.createElement('tbody');
        if (g) tb.innerHTML = `<tr class="rep-group"><th colspan="${showReport ? 6 : 5}">${escapeHtml(g)}</th></tr>`;
        for (const r of list) tb.appendChild(row(r));
        table.appendChild(tb);
    }
    container.appendChild(table);

    function row(r) {
        const tr = document.createElement('tr');
        const f12 = num(r.frac_gap12), f34 = num(r.frac_gap34), fn = num(r.frac_none);
        const isKey = keys.has(r.feature);
        const need = needClass(f12, state, spec.need !== false && !isKey && !na.has(r.feature));
        const N = NEED[need];
        const rest = (f34 ?? 0) + (fn ?? 0);
        const green = rest > 0 ? (f34 ?? 0) / rest : null;
        const rep = ctx.report?.[r.feature];
        const ext = measure === 'miles' ? fmtMiles(r.miles) : fmt(r.acres, 'acres');

        tr.innerHTML = `
            <td class="c-feat">${escapeHtml(r.label)}${isKey ? ` <span class="key-badge" title="${escapeHtml(KEY_FEATURE)} The report recommends conserving all remaining extent.">Key feature</span>` : ''}</td>
            <td class="c-pct"><span class="pct ${N.cls}${isKey ? ' key' : ''}">${f12 == null ? '—' : fmt(f12, 'pct')}</span><span class="need-label">${need === 'not_applicable' ? '' : escapeHtml(N.label)}</span></td>
            <td class="c-bar"><div class="sbar">${STATUS.map(s => `<span class="${s.cls}" style="width:${(100 * Math.max(0, num(r[s.key]) ?? 0)).toFixed(2)}%"></span>`).join('')}
                ${state != null ? `<i class="tick state" style="left:${(100 * state).toFixed(2)}%"></i>` : ''}
                ${area != null ? `<i class="tick area" style="left:${(100 * area).toFixed(2)}%"></i>` : ''}</div></td>
            <td class="c-pie">${green == null ? '' : pie(green)}</td>
            ${showReport ? `<td class="c-rep">${rep ? reportCell(rep, f12) : '<span class="muted">—</span>'}</td>` : ''}
            <td class="c-ext">${ext}</td>`;

        hover(tr.querySelector('.sbar'), `<b>${escapeHtml(r.label)}</b><br>` +
            STATUS.map(s => `${escapeHtml(s.label)}: ${fmt(r[s.key], 'pct')}`).join('<br>') +
            `<br>Extent: ${ext}`);
        const pieEl = tr.querySelector('.c-pie svg');
        if (pieEl) hover(pieEl, `<b>Of the ${escapeHtml(r.label.toLowerCase())} outside 30x30</b><br>` +
            `${fmt(green, 'pct')} on other conserved or public land (improve management / durability)<br>` +
            `${fmt(1 - green, 'pct')} on non-conserved land (acquisition / easement)`);
        if (rep) hover(tr.querySelector('.c-rep'), `<b>Report (Table ${rep.table})</b>: ${rep.pct}%` +
            (rep.lower != null ? ` (range ${rep.lower}–${rep.upper}%)` : '') +
            `<br>Need class: ${escapeHtml(NEED[rep.need]?.label || rep.need)}${rep.key ? ' · Key feature' : ''}` +
            `<br>Pathway pie, GAP 3–4 share: ~${Math.round(rep.pathway_green * 100)}%` +
            `<br>This app: ${fmt(f12, 'pct')}`);
        return tr;
    }
}

/**
 * The report's value beside this app's. The report prints some tables to whole
 * percents and others to one decimal, so compare at the precision it printed:
 * a check mark when this app's value rounds to the printed one, otherwise the
 * difference in percentage points.
 */
function reportCell(rep, f12) {
    const dec = (String(rep.pct).split('.')[1] || '').length;
    let diff = '';
    if (f12 != null) {
        const ours = Number((f12 * 100).toFixed(dec));
        const d = ours - rep.pct;
        diff = Math.abs(d) < 1e-9
            ? '<span class="rep-diff rep-ok" title="This app matches the report at the precision the report printed">✓</span>'
            : `<span class="rep-diff" title="This app minus the report, in percentage points, at the report's printed precision">${d > 0 ? '+' : '−'}${Math.abs(d).toFixed(Math.max(dec, 1))}</span>`;
    }
    return `<span class="rep-val">${rep.pct}%</span>${diff}`;
}

/** Two-slice pie: GAP 3-4 share (green) vs non-conserved (sand). */
function pie(g) {
    const r = 9, c = 11;
    if (g >= 0.999 || g <= 0.001) {
        return `<svg viewBox="0 0 22 22" width="22" height="22" role="img" aria-label="${Math.round(g * 100)}% on GAP 3–4 land"><circle cx="${c}" cy="${c}" r="${r}" class="${g > 0.5 ? 's34' : 'snone'}"/></svg>`;
    }
    const a = 2 * Math.PI * g;
    const x = c + r * Math.sin(a), y = c - r * Math.cos(a);
    const large = g > 0.5 ? 1 : 0;
    return `<svg viewBox="0 0 22 22" width="22" height="22" role="img" aria-label="${Math.round(g * 100)}% on GAP 3–4 land">
        <circle cx="${c}" cy="${c}" r="${r}" class="snone"/>
        <path d="M${c},${c} L${c},${c - r} A${r},${r} 0 ${large} 1 ${x.toFixed(2)},${y.toFixed(2)} Z" class="s34"/>
        <circle cx="${c}" cy="${c}" r="${r}" class="pie-ring"/></svg>`;
}

const num = v => (v == null || !Number.isFinite(Number(v)) ? null : Number(v));
const fmtMiles = v => (v == null ? '—' : (v >= 1e4 ? new Intl.NumberFormat('en-US', { notation: 'compact', maximumFractionDigits: 1 }).format(v) : Math.round(v).toLocaleString('en-US')) + ' mi');

/**
 * Styles for the table and status swatches. Registered as the chart type's
 * css, which glen-charts injects into the page and into exported reports.
 */
export const REP_CSS = `
.s12 { background: #1b6e3a; fill: #1b6e3a; }
.s34 { background: #7dbb63; fill: #7dbb63; }
.snone { background: #ece3b5; fill: #ece3b5; }
.legend-row i.s12, .legend-row i.s34, .legend-row i.snone, .sw { width: 11px; height: 11px; border-radius: 2px; display: inline-block; vertical-align: -1px; }
.legend-row i.snone, .sw.snone { box-shadow: inset 0 0 0 1px rgba(0,0,0,.18); }
.legend-row i.tick { width: 0; height: 12px; border-radius: 0; background: none; border-left: 2px solid #22201f; }
.legend-row i.tick.area { border-left: 2px dashed #b45309; }
.rep-legend { margin: 4px 0 6px; }
.rep-table { width: 100%; border-collapse: collapse; font-size: 12.5px; font-variant-numeric: tabular-nums; }
.rep-table th, .rep-table td { padding: 5px 6px; border-bottom: 1px solid rgba(30,40,30,.10); vertical-align: middle; text-align: left; }
.rep-table thead th { font-size: 11px; font-weight: 600; color: #77706b; text-transform: uppercase; letter-spacing: .4px; border-bottom: 1px solid rgba(30,40,30,.22); }
.rep-table .rep-group th { font-size: 12px; font-weight: 650; color: #22201f; text-transform: none; letter-spacing: 0; padding-top: 12px; background: none; }
.rep-table .c-feat { min-width: 120px; }
.rep-table .c-pct { white-space: nowrap; width: 1%; }
.rep-table .c-bar { width: 38%; min-width: 120px; }
.rep-table .c-pie, .rep-table .c-rep, .rep-table .c-ext { white-space: nowrap; width: 1%; }
.rep-table .c-ext { color: #77706b; text-align: right; }
.rep-table .c-pie svg { display: block; width: 22px; height: 22px; }
.pie-ring { fill: none; stroke: rgba(0,0,0,.25); stroke-width: .8; }
.pct { display: inline-block; min-width: 46px; padding: 2px 6px; border-radius: 4px; font-weight: 650; text-align: center; color: #22201f; }
.need-under { background: #f2a07b; }
.need-slight { background: #fbdcc8; }
.need-par { background: #d3e4f1; }
.need-na { background: #fff; box-shadow: inset 0 0 0 1px rgba(30,40,30,.18); }
.pct.key { box-shadow: inset 0 0 0 2px #8b1a1a; }
.need-label { display: block; font-size: 10.5px; color: #77706b; margin-top: 2px; }
.key-note { font-size: 11.5px; color: #5d5852; margin: 0 0 8px; line-height: 1.45; }
.key-note .key-badge { margin-left: 0; }
.key-badge { display: inline-block; font-size: 10px; font-weight: 600; color: #8b1a1a; border: 1px solid #8b1a1a; border-radius: 3px; padding: 0 4px; margin-left: 4px; vertical-align: 1px; white-space: nowrap; }
.sbar { position: relative; display: flex; gap: 2px; height: 14px; }
.sbar span { display: block; height: 100%; min-width: 0; }
.sbar span:first-child { border-radius: 3px 0 0 3px; }
.sbar span:last-child { border-radius: 0 3px 3px 0; }
.sbar span.snone { box-shadow: inset 0 0 0 1px rgba(0,0,0,.10); }
.sbar .tick { position: absolute; top: -3px; bottom: -3px; width: 0; border-left: 2px solid #22201f; transform: translateX(-1px); }
.sbar .tick.area { border-left: 2px dashed #b45309; }
.rep-val { font-weight: 600; }
.rep-diff { margin-left: 6px; font-size: 11px; color: #77706b; }
.rep-ok { color: #1b6e3a; font-weight: 700; }
.muted { color: #77706b; }
@media (max-width: 560px) { .rep-table .c-ext, .rep-table .c-pie { display: none; } }
`;
