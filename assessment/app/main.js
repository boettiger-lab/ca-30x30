/**
 * App controller: area (California, a jurisdiction, or a drawn/uploaded
 * polygon) → sections → report + map. California is the default view; its
 * results are precomputed, so the app opens on the report's own numbers.
 * State is mirrored to the URL hash (#ecoregion/Mono?themes=a,b) so a view is a
 * shareable link.
 */

import { loadConfig, Engine, jurisdictionAoi, statewideAoi } from './engine.js';
import { MapView } from './map.js';
import { renderThemeCard } from './report.js';
import { wireExportButton } from './export.js';
import { polygonAoi } from './polygon.js';
import { DrawTool, readGeoJsonFile } from './draw.js';
import { fmt, escapeHtml } from './format.js';
import { NEED } from './represent.js';

const $ = sel => document.querySelector(sel);

const state = {
    mode: 'state',      // 'state' | jurisdiction id | 'draw'
    jur: null,
    themes: new Set(),
    feature: null,
    aoi: null,
    features: [],
    token: 0,
};

let config, engine, mapView, draw, reportValues = null;

async function boot() {
    config = await loadConfig('.');
    const [statewide, report] = await Promise.all([fetchJson('data/statewide.json'), fetchJson('data/report.json')]);
    reportValues = report;

    let mcpUrl = config.app.mcp_url;
    const rt = await fetchJson('config.json');
    if (rt?.mcp_server_url) mcpUrl = rt.mcp_server_url;

    engine = new Engine(config, { mcpUrl, statewide, base: '.' });
    mapView = new MapView('map', config.app);
    mapView.onPick = id => pickById(id);
    mapView.showConserved(config.app.conserved);
    $('#conserved-toggle').onchange = e => mapView.setConservedVisible(e.target.checked);
    draw = new DrawTool(mapView, { onDone: geom => useGeometry([geom], 'Drawn area') });

    for (const t of config.themes) state.themes.add(t.id);
    renderModeButtons();
    renderThemeButtons();
    wireSearch();
    wireDraw();
    wireResize();
    if (!(await restoreFromHash())) setState();
}

async function fetchJson(url) {
    try {
        const r = await fetch(url, { cache: 'no-cache' });
        return r.ok ? await r.json() : null;
    } catch { return null; }
}

/* ------------------------------------------------------------------ steps */

function modes() {
    return [{ id: 'state', label: 'California', description: 'The whole state, as in the report' },
        ...config.app.jurisdictions,
        { id: 'draw', label: 'Draw / upload', description: 'Draw a polygon on the map or upload a GeoJSON file' }];
}

function renderModeButtons() {
    const wrap = $('#jur-buttons');
    wrap.innerHTML = '';
    for (const m of modes()) {
        const b = document.createElement('button');
        b.type = 'button';
        b.setAttribute('role', 'radio');
        b.setAttribute('aria-checked', 'false');
        b.dataset.id = m.id;
        b.textContent = m.label;
        b.title = m.description || m.label;
        b.onclick = () => setMode(m.id);
        wrap.appendChild(b);
    }
}

function renderThemeButtons() {
    const wrap = $('#theme-buttons');
    wrap.innerHTML = '';
    for (const t of config.themes) {
        const b = document.createElement('button');
        b.type = 'button';
        b.dataset.id = t.id;
        b.style.setProperty('--c', t.color);
        b.setAttribute('aria-pressed', String(state.themes.has(t.id)));
        b.innerHTML = `<span class="dot"></span>${escapeHtml(t.label)}`;
        b.title = t.blurb || t.label;
        b.onclick = () => toggleTheme(t.id);
        wrap.appendChild(b);
    }
}

function markMode(id) {
    document.querySelectorAll('#jur-buttons button').forEach(b => b.setAttribute('aria-checked', String(b.dataset.id === id)));
    $('#step-place').hidden = id === 'state' || id === 'draw';
    $('#step-draw').hidden = id !== 'draw';
}

async function setMode(id, { keepFeature = false } = {}) {
    if (id === 'state') return setState();
    if (id === 'draw') {
        state.mode = 'draw';
        state.jur = null;
        markMode('draw');
        mapView.clearJurisdiction();
        if (!keepFeature) { draw.start(); showHint('Click to add points; double-click (or click the first point) to finish'); }
        writeHash();
        return;
    }
    const jur = config.app.jurisdictions.find(j => j.id === id);
    if (!jur) return;
    draw.cancel();
    state.mode = id;
    state.jur = jur;
    markMode(id);
    $('#place-label').textContent = jur.singular || jur.label;
    const input = $('#place-input');
    input.disabled = false;
    input.value = '';
    input.placeholder = `Loading ${jur.label.toLowerCase()}…`;
    if (!keepFeature) {
        state.feature = null;
        setAoi(null);
    }
    await mapView.showJurisdiction(jur);
    showHint(`Click ${/^[aeiou]/i.test(jur.singular) ? 'an' : 'a'} ${(jur.singular || jur.label).toLowerCase()} on the map, or search by name`);
    try {
        state.features = await engine.listFeatures(jur);
        state.features.sort((a, b) => naturalCompare(a.name, b.name));
        input.placeholder = `Search ${state.features.length} ${jur.label.toLowerCase()}…`;
    } catch (err) {
        input.placeholder = 'Could not load list — click the map instead';
        console.error(err);
    }
    writeHash();
}

function setState() {
    draw.cancel();
    state.mode = 'state';
    state.jur = null;
    state.feature = null;
    markMode('state');
    hideHint();
    mapView.clearJurisdiction();
    mapView.clearShape();
    mapView.fit(config.app.view);
    setAoi(statewideAoi(config.app));
}

function toggleTheme(id) {
    if (state.themes.has(id)) state.themes.delete(id); else state.themes.add(id);
    document.querySelectorAll('#theme-buttons button').forEach(b => b.setAttribute('aria-pressed', String(state.themes.has(b.dataset.id))));
    writeHash();
    if (state.aoi) renderReport();
}

function orderedThemes() {
    return config.themes.filter(t => state.themes.has(t.id));
}

/* ----------------------------------------------------------------- search */

function wireSearch() {
    const input = $('#place-input');
    const list = $('#place-results');
    let matches = [];
    let active = -1;

    const close = () => { list.hidden = true; active = -1; };
    const render = () => {
        const q = input.value.trim().toLowerCase();
        matches = (q ? state.features.filter(f => f.name.toLowerCase().includes(q)) : state.features).slice(0, 60);
        list.innerHTML = matches.map((f, i) =>
            `<li role="option" data-i="${i}" aria-selected="${i === active}">${escapeHtml(f.name)}${f.detail ? `<small>${escapeHtml(f.detail)}</small>` : ''}</li>`).join('');
        list.hidden = !matches.length;
    };
    input.addEventListener('input', () => { active = -1; render(); });
    input.addEventListener('focus', render);
    input.addEventListener('keydown', e => {
        if (e.key === 'ArrowDown') { active = Math.min(matches.length - 1, active + 1); render(); e.preventDefault(); }
        else if (e.key === 'ArrowUp') { active = Math.max(0, active - 1); render(); e.preventDefault(); }
        else if (e.key === 'Enter') {
            const f = matches[active >= 0 ? active : 0];
            if (f) { pick(f); close(); input.blur(); }
        } else if (e.key === 'Escape') close();
    });
    list.addEventListener('mousedown', e => {
        const li = e.target.closest('li');
        if (!li) return;
        pick(matches[Number(li.dataset.i)]);
        close();
    });
    input.addEventListener('blur', () => setTimeout(close, 150));
}

function pickById(id) {
    if (!state.jur) return;
    const f = state.features.find(x => String(x.id) === String(id));
    pick(f || { id, name: `${state.jur.singular || state.jur.label} ${id}` });
}

function pick(feature) {
    if (!feature || !state.jur) return;
    state.feature = feature;
    $('#place-input').value = feature.name;
    hideHint();
    const bbox = ['xmin', 'ymin', 'xmax', 'ymax'].map(k => Number(feature[k]));
    mapView.select(feature.id, bbox);
    setAoi(jurisdictionAoi(state.jur, feature));
}

/* ------------------------------------------------------------ draw/upload */

function wireDraw() {
    $('#draw-btn').onclick = () => { draw.start(); showHint('Click to add points; double-click (or click the first point) to finish'); };
    $('#draw-clear').onclick = () => { draw.cancel(); mapView.clearShape(); hideHint(); };
    $('#upload-input').onchange = async e => {
        const file = e.target.files?.[0];
        e.target.value = '';
        if (!file) return;
        try {
            const geoms = await readGeoJsonFile(file);
            useGeometry(geoms, file.name.replace(/\.(geo)?json$/i, ''));
        } catch (err) {
            $('#draw-help').textContent = err.message;
        }
    };
}

function useGeometry(geoms, label) {
    hideHint();
    $('#draw-help').textContent = '';
    if (state.mode !== 'draw') { state.mode = 'draw'; state.jur = null; markMode('draw'); mapView.clearJurisdiction(); }
    mapView.showShape(geoms);
    const aoi = polygonAoi(geoms, label);
    aoi.kindLabel = 'Custom area';
    setAoi(aoi);
}

/* ----------------------------------------------------------------- report */

function setAoi(aoi) {
    state.aoi = aoi;
    state.token++;
    writeHash();
    if (aoi) renderReport();
    else renderIntro();
}

function kindLabel() {
    if (state.mode === 'state') return 'Statewide';
    if (state.mode === 'draw') return 'Custom area';
    return state.jur.singular || state.jur.label;
}

function renderIntro() {
    $('#report').innerHTML = `<div class="intro"><p>Choose a ${escapeHtml((state.jur?.singular || 'place').toLowerCase())} by name or on the map.</p></div>`;
}

function repContext(aoi) {
    const overview = config.overview;
    const isState = aoi.kind === 'state';
    return Promise.all([
        engine.runStatewide(overview, 'protection'),
        isState ? null : engine.run(overview, 'protection', aoi),
    ]).then(([st, ar]) => ({
        stateLevel: st?.[0]?.frac_gap12 ?? null,
        areaLevel: ar?.[0]?.frac_gap12 ?? null,
        areaLabel: shortName(aoi.label),
        report: isState ? reportValues?.features : null,
    }));
}

function renderReport() {
    const token = state.token;
    const aoi = state.aoi;
    const r = $('#report');
    const isState = aoi.kind === 'state';
    r.innerHTML = `
        <div class="report-head">
            <div>
                <div class="kind">${escapeHtml(kindLabel())}</div>
                <h2>${escapeHtml(aoi.label)}</h2>
            </div>
            <div class="head-actions">
                <button class="ghost-btn" id="export-btn" type="button" title="Download this view as a report: numbers, charts, code (SQL / R / Python) and data citations">Export</button>
                <button class="ghost-btn" id="copy-link" type="button" title="Copy a link to this view">Copy link</button>
            </div>
        </div>
        ${frameworkNote(isState)}`;
    $('#copy-link').onclick = async () => {
        try { await navigator.clipboard.writeText(location.href); $('#copy-link').textContent = 'Copied'; } catch { /* ignore */ }
    };
    wireExportButton($('#export-btn'), () => ({
        engine, aoi, mapView, kind: kindLabel(),
        themes: [config.overview, ...orderedThemes()],
        reportEl: r, legendEl: $('#map-legend'), siteTitle: config.app.title,
        projectUrl: config.app.project_url,
    }));

    const opts = { isCurrent: () => token === state.token, repContext, reportValues, compareLabel: 'California' };
    r.appendChild(renderThemeCard(engine, config.overview, aoi, { ...opts, overview: true }));
    for (const t of orderedThemes()) r.appendChild(renderThemeCard(engine, t, aoi, opts));
    if (!isState) {
        engine.precomputed(aoi).then(pre => {
            if (pre || token !== state.token) return;
            const n = document.createElement('p');
            n.className = 'tile-note live-note';
            n.textContent = 'Results for this area are computed live from the source data; larger areas can take a minute or two.';
            r.querySelector('.report-head')?.after(n);
        });
    }
}

/** How to read the tables: the report's framework, in one collapsible note. */
function frameworkNote(isState) {
    const st = engine.statewide?.results?.overview?.protection?.[0]?.frac_gap12;
    const lvl = st ? fmt(st, 'pct') : 'California’s level';
    return `<details class="card framework">
        <summary><b>How to read this</b> — the report's representation framework</summary>
        <div class="framework-body">
        <p>Each table shows how much of a habitat or feature lies in <b>30x30 Conservation Areas</b> (GAP 1–2), on
           <b>other conserved or public land</b> (GAP 3–4), and on <b>non-conserved land</b>, following the
           <a href="${escapeHtml(reportValues?.url || '#')}" target="_blank" rel="noopener">2025 Biodiversity Assessment</a>.</p>
        <ul class="need-legend">
            <li><span class="pct need-under">&lt; 20%</span> ${NEED.under.label}</li>
            <li><span class="pct need-slight">20% – ${lvl}</span> ${NEED.slightly_under.label}</li>
            <li><span class="pct need-par">≥ ${lvl}</span> ${NEED.on_par.label}: California's current share of land in 30x30</li>
            <li><span class="pct need-na key">Key feature</span> rare or critical; the report recommends conserving all remaining extent</li>
        </ul>
        <p>The <b>pathway</b> pie splits what lies outside 30x30: <span class="sw s34"></span> other conserved or public land
           (improve management or durability) vs <span class="sw snone"></span> non-conserved land (acquisition or easement).
           Need classes always compare with California's level${isState ? '' : ', even for a smaller area; the area’s own share in 30x30 is the second tick on each bar'}.
           ${isState ? 'The <b>Report</b> column gives the published value and this app’s difference from it, in percentage points.' : ''}</p>
        <p class="tile-note">No AI model is involved: every number is fixed, reviewable SQL over public data — see “Method &amp; SQL” under each section, or Export.</p>
        </div></details>`;
}

/* ------------------------------------------------------------------- hash */

function writeHash() {
    const parts = [];
    if (state.mode !== 'state') parts.push(state.mode);
    if (state.jur && state.feature) parts.push(encodeURIComponent(state.feature.id));
    const q = new URLSearchParams();
    if (state.themes.size !== config.themes.length) q.set('themes', orderedThemes().map(t => t.id).join(','));
    const hash = '#' + parts.join('/') + (q.toString() ? '?' + q.toString().replace(/%2C/g, ',') : '');
    history.replaceState(null, '', hash === '#' ? location.pathname + location.search : hash);
}

async function restoreFromHash() {
    const h = location.hash.slice(1);
    if (!h) return false;
    const [path, query] = h.split('?');
    const q = new URLSearchParams(query || '');
    if (q.has('themes')) {
        state.themes.clear();
        for (const id of q.get('themes').split(',').filter(Boolean)) {
            if (config.themes.some(t => t.id === id)) state.themes.add(id);
        }
        document.querySelectorAll('#theme-buttons button').forEach(b => b.setAttribute('aria-pressed', String(state.themes.has(b.dataset.id))));
    }
    const [modeId, featId] = path.split('/');
    if (!modeId || modeId === 'draw') { setState(); return true; }   // a drawn shape isn't in the link
    await setMode(modeId, { keepFeature: !!featId });
    if (featId) pickById(decodeURIComponent(featId));
    return true;
}

/* ----------------------------------------------------------------- resize */

function wireResize() {
    const handle = document.querySelector('.sidebar-resize');
    const sidebar = $('#sidebar');
    try {
        const f = Number(localStorage.getItem('ca30x30-sidebar-frac'));
        if (f > 0.2 && f < 0.85) document.documentElement.style.setProperty('--sidebar-width', (f * 100).toFixed(1) + 'vw');
    } catch { /* storage unavailable */ }
    handle.addEventListener('pointerdown', e => {
        handle.setPointerCapture(e.pointerId);
        const move = ev => {
            const w = Math.max(360, Math.min(window.innerWidth - 320, window.innerWidth - ev.clientX));
            document.documentElement.style.setProperty('--sidebar-width', w + 'px');
            mapView.map.resize();
        };
        const up = () => {
            handle.removeEventListener('pointermove', move);
            try { localStorage.setItem('ca30x30-sidebar-frac', parseInt(getComputedStyle(sidebar).width) / window.innerWidth); } catch { /* ignore */ }
        };
        handle.addEventListener('pointermove', move);
        handle.addEventListener('pointerup', up, { once: true });
    });
}

function showHint(text) { const h = $('#map-hint'); h.textContent = text; h.hidden = false; }
function hideHint() { $('#map-hint').hidden = true; }
const naturalCompare = (a, b) => String(a).localeCompare(String(b), 'en', { numeric: true });
const shortName = s => String(s).replace(/^(Congressional|State Senate|Assembly) District /, (m, k) => ({ Congressional: 'CD ', 'State Senate': 'SD ', Assembly: 'AD ' }[k]));

boot().catch(err => {
    console.error(err);
    $('#report').innerHTML = `<div class="err">Failed to start: ${escapeHtml(err.message)}</div>`;
});

