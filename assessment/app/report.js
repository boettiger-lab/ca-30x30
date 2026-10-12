/**
 * Theme card renderer shared by every site variant: headline tiles, bar
 * charts and the "Method & SQL" disclosure for one theme over one AOI.
 */

import { renderBarChart } from './charts.js';
import { renderRepresentation } from './represent.js';
import { fmt, escapeHtml } from './format.js';

export function renderThemeCard(engine, theme, aoi, { overview = false, isCurrent = () => true, onMapToggle = null, compareLabel = 'California', repContext = null, reportValues = null } = {}) {
    const statewide = aoi.kind === 'state';
    const card = document.createElement('section');
    card.className = 'card' + (overview ? '' : ' theme-card');
    card.dataset.theme = theme.id;
    card.style.setProperty('--c', theme.color || 'var(--primary)');
    card.innerHTML = `
        <div class="card-head">
            <h3>${overview ? '' : '<span class="dot"></span>'}${escapeHtml(theme.label)}</h3>
            ${!overview && theme.map ? `<button class="map-btn" type="button" data-theme="${theme.id}">Show on map</button>` : ''}
        </div>
        ${theme.blurb && !overview ? `<p class="card-blurb">${escapeHtml(theme.blurb)}</p>` : ''}
        <div class="tiles"></div>
        <div class="charts"></div>
        <details class="method"><summary>Method &amp; SQL</summary><div class="method-body"></div></details>`;

    const mapBtn = card.querySelector('.map-btn');
    if (mapBtn) {
        if (onMapToggle) mapBtn.onclick = () => onMapToggle(theme.id);
        else mapBtn.remove();
    }

    const tiles = card.querySelector('.tiles');
    tiles.dataset.n = (theme.headlines || []).length;
    for (const h of theme.headlines || []) {
        const t = document.createElement('div');
        t.className = 'tile skeleton';
        t.innerHTML = `<div class="tile-label">${escapeHtml(h.label)}</div><div class="tile-value">0000</div><div class="tile-compare">&nbsp;</div>`;
        tiles.appendChild(t);
        Promise.all([engine.run(theme, h.query, aoi), h.compare === false || statewide ? null : engine.runStatewide(theme, h.query).catch(() => null)])
            .then(([rows, st]) => {
                if (!isCurrent()) return;
                t.classList.remove('skeleton');
                const row = pickRow(rows, h.row);
                const v = row?.[h.field];
                const sv = pickRow(st, h.row)?.[h.compare_field || h.field];
                const rv = statewide && h.report ? h.report.split('.').reduce((o, k) => o?.[k], reportValues) : null;
                t.innerHTML = `
                    <div class="tile-label">${escapeHtml(h.label)}</div>
                    <div class="tile-value">${fmt(v, h.format)}</div>
                    ${h.compare !== false && sv !== undefined && sv !== null ? `<div class="tile-compare">${escapeHtml(compareLabel)}: ${fmt(sv, h.compare_format || h.format)}</div>` : ''}
                    ${rv != null ? `<div class="tile-compare" title="Published in the 2025 Biodiversity Assessment">Report: ${fmt(rv, h.format)}</div>` : ''}
                    ${h.detail_field && row?.[h.detail_field] != null ? `<div class="tile-note">${escapeHtml(h.detail_template.replace('{}', fmt(row[h.detail_field], h.detail_format)))}</div>` : ''}
                    ${h.note ? `<div class="tile-note">${escapeHtml(h.note)}</div>` : ''}`;
                if (h.rank) addRank(engine, theme, h, aoi, t, isCurrent);
            })
            .catch(err => failTile(t, h, err, isCurrent));
    }

    const charts = card.querySelector('.charts');
    for (const c of theme.charts || []) {
        const box = document.createElement('div');
        box.className = 'chart' + (c.wide ? ' wide' : '');
        box.innerHTML = `<h4>${escapeHtml(c.title)}</h4>${c.subtitle ? `<div class="sub">${escapeHtml(c.subtitle)}</div>` : ''}<div class="plot skeleton" style="height:120px"></div>`;
        charts.appendChild(box);
        const plot = box.querySelector('.plot');
        const wantState = !statewide && (c.compare || c.statewide_row);
        const load = c.type === 'representation'
            ? Promise.all([engine.run(theme, c.query, aoi), repContext ? repContext(aoi) : {}])
            : c.pivot
            ? pivotRows(engine, theme, c, aoi).then(rows => [rows, null])
            : Promise.all([engine.run(theme, c.query, aoi), wantState ? engine.runStatewide(theme, c.query).catch(() => null) : null]);
        load
            .then(([rows, st]) => {
                if (!isCurrent()) return;
                plot.classList.remove('skeleton');
                plot.style.height = '';
                if (c.type === 'representation') {
                    renderRepresentation(plot, c, rows, st);
                    return;
                }
                if (c.statewide_row) {
                    // one-row result → compare this place and California side by side
                    // (statewide: California beside the report's published split)
                    rows = [{ ...rows?.[0], __label: shortLabel(aoi.label) }];
                    if (st?.[0]) rows.push({ ...st[0], __label: compareLabel });
                    if (statewide && c.report_row && reportValues) {
                        const rr = c.report_row.split('.').reduce((o, k) => o?.[k], reportValues);
                        if (rr) rows.push({ ...rr, __label: 'Report (2025)' });
                    }
                    st = null;
                }
                renderBarChart(plot, c, rows, st);
            })
            .catch(err => {
                if (!isCurrent()) return;
                plot.classList.remove('skeleton');
                plot.style.height = '';
                plot.innerHTML = `<div class="err">Query failed: ${escapeHtml(shortErr(err))}</div>`;
                console.error(err, err.sql);
            });
    }

    // method + exact SQL as run for this area
    const mb = card.querySelector('.method-body');
    card.querySelector('details').addEventListener('toggle', function once() {
        mb.innerHTML = (theme.method ? `<p>${escapeHtml(theme.method)}</p>` : '') +
            Object.keys(theme.queries)
                .map(q => `<div><b>${escapeHtml(q)}</b></div><pre>${escapeHtml(engine.sqlFor(theme, q, aoi))}</pre>`).join('');
    }, { once: true });
    return card;
}

/** "#9 of 58 California counties" from the precomputed peer table. */
async function addRank(engine, theme, h, aoi, tile, isCurrent) {
    const jur = engine.config.app.jurisdictions?.find(j => j.id === aoi.kind);
    if (!jur || !aoi.id) return;
    const peers = await engine.peers(theme.id, jur.id);
    const field = h.rank.field || h.field;
    const vals = (peers || []).filter(r => r[field] != null);
    const me = vals.find(r => r.id === aoi.id);
    if (!me || !isCurrent()) return;
    const rank = 1 + vals.filter(r => r[field] > me[field]).length;
    const el = document.createElement('div');
    el.className = 'tile-rank';
    el.innerHTML = `<b>#${rank}</b> of ${vals.length} ${escapeHtml(jur.peer_label || jur.label.toLowerCase())}`;
    tile.querySelector('.tile-value').after(el);
}

function failTile(t, h, err, isCurrent) {
    if (!isCurrent()) return;
    t.classList.remove('skeleton');
    t.innerHTML = `<div class="tile-label">${escapeHtml(h.label)}</div><div class="tile-value">—</div><div class="err" title="${escapeHtml(err.message)}">Query failed</div>`;
    console.error(err, err.sql);
}

/**
 * Build chart rows from one-row results of several queries:
 *   pivot: [{ label, query, fields: { seriesField: resultColumn } }]
 */
async function pivotRows(engine, theme, c, aoi) {
    const queries = [...new Set(c.pivot.map(p => p.query))];
    const results = Object.fromEntries(await Promise.all(queries.map(async q => [q, (await engine.run(theme, q, aoi))?.[0] || {}])));
    return c.pivot.map(p => {
        const row = { __label: p.label };
        for (const [k, col] of Object.entries(p.fields)) row[k] = results[p.query][col];
        return row;
    });
}

/** First row, or the row whose fields match `where` (e.g. {"grp": "DAC tracts"}). */
export function pickRow(rows, where) {
    if (!rows) return null;
    if (!where) return rows[0];
    return rows.find(r => Object.entries(where).every(([k, v]) => r[k] === v)) || null;
}

const shortLabel = s => String(s).replace(/^(Congressional|State Senate|Assembly) District /, (m, k) => ({ Congressional: 'CD ', 'State Senate': 'SD ', Assembly: 'AD ' }[k]));

export const shortErr = err => (err.message || String(err)).split('\n')[0].slice(0, 160);

