/**
 * Export a profile as a self-contained HTML report, in the manner of
 * geo-agent's session export: the map (live, re-hydrated from its style),
 * headline numbers and charts as shown, every query as a folded code chunk
 * (SQL / R / Python) with its output, downloads as .R / .py / .qmd / .ipynb,
 * print-to-PDF (with or without code), and citations for every dataset read.
 *
 * The language wrappers, the anonymous-S3 setup block, the map embed and the
 * STAC citation fields come from geo-agent's export module, so both apps hand
 * readers the same runnable code. It is loaded only when someone exports.
 */

import { matchSources } from './sources.js';
import { escapeHtml } from './format.js';
import { REP_CSS } from './represent.js';

const GEO_AGENT_EXPORT = 'https://cdn.jsdelivr.net/gh/boettiger-lab/geo-agent@v3.35.0/app/export-report.js';
const PROJECT_URL = 'https://github.com/boettiger-lab/ca-30x30/tree/main/assessment';
const REPORT_REF = 'Schloss, C., Howard, J., Olliff Yang, R., et al. (2026). California’s 30x30 Initiative in 2025: A Biodiversity Assessment of the State’s 30x30 Conservation Areas. California Biodiversity Network.';
const REPORT_URL = 'https://cabiodiversitynetwork.org/wp-content/uploads/2026/08/CBN-Biodiversity-Assessment-2025-Final-Report.pdf';
const OUTPUT_ROWS = 20;
const SPEED_NOTE = 'The app runs these queries on servers next to the data (the duckdb-geo MCP server). ' +
    'Re-run on a personal computer, large areas may take much longer.';

/**
 * Build the report and download it.
 *
 * @param {object} o
 * @param {Engine} o.engine
 * @param {object} o.aoi           the area the report shows
 * @param {string} o.kind          e.g. "County", "15-minute walk"
 * @param {object[]} o.themes      overview first, then the selected themes
 * @param {MapView} o.mapView
 * @param {HTMLElement} o.reportEl the rendered report (#report)
 * @param {HTMLElement} [o.legendEl]
 * @param {string} o.siteTitle
 * @param {string} [o.base]        site folder (for data/sources.json)
 */
export async function exportReport(o) {
    const ga = await import(GEO_AGENT_EXPORT);
    await settled(o.reportEl);

    const exportedAt = new Date();
    const slug = `${o.aoi.label}`.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '').slice(0, 60) || 'profile';
    const basename = `${slug}-${exportedAt.toISOString().slice(0, 10)}`;
    const filename = `${basename}.html`;

    // what ran: every query of every theme shown, in the order of the report
    const sections = [];
    let n = 0;
    for (const theme of o.themes) {
        const card = o.reportEl.querySelector(`.card[data-theme="${CSS.escape(theme.id)}"]`);
        const queries = [];
        for (const name of usedQueries(theme)) {
            let rows = null, error = null;
            try { rows = await o.engine.run(theme, name, o.aoi); } catch (err) { error = err.message || String(err); }
            queries.push({ name, n: ++n, sql: o.engine.sqlFor(theme, name, o.aoi), rows, error });
        }
        sections.push({ theme, card, queries });
    }

    const map = o.mapView.map;
    const c = map.getCenter();
    const style = map.getStyle();
    const mapEmbed = ga.buildMapEmbedHtml({
        style, center: [c.lng, c.lat], zoom: map.getZoom(), bearing: map.getBearing(), pitch: map.getPitch(),
    }, { filename });
    const snapshot = await mapSnapshot(map);
    const tileUrls = Object.values(style.sources || {}).map(s => String(s.url || '').replace(/^pmtiles:\/\//, '')).filter(Boolean);

    let sources = null;
    try {
        const r = await fetch(`${o.base || '.'}/data/sources.json`, { cache: 'no-cache' });
        if (r.ok) sources = await r.json();
    } catch { /* no citations */ }
    const datasets = matchSources(sources, sections.flatMap(s => s.queries.map(q => q.sql)), tileUrls)
        .map(d => ({ ...ga.datasetCitation(d.stac), queried: d.queried, mapped: d.mapped }));

    const doc = { ...o, sections, datasets, exportedAt, basename, snapshot, appUrl: location.href };
    const files = buildFiles(doc, ga);
    const html = buildHtml(doc, ga, mapEmbed, files);
    download(filename, html, 'text/html');
}

/**
 * PNG of the map as drawn, for print: a WebGL canvas often prints blank, so
 * the live map is swapped for this picture on paper. Read inside a render
 * pass, so the app's map needs no preserveDrawingBuffer.
 */
function mapSnapshot(map) {
    return new Promise(resolve => {
        const timer = setTimeout(() => resolve(null), 5000);
        map.once('render', () => {
            clearTimeout(timer);
            try { resolve(map.getCanvas().toDataURL('image/png')); } catch { resolve(null); }
        });
        map.triggerRepaint();
    });
}

/** Wait until no panel is still loading (or give up after 5 minutes). */
async function settled(el, timeoutMs = 300000) {
    const t0 = Date.now();
    while (el.querySelector('.skeleton') && Date.now() - t0 < timeoutMs) {
        await new Promise(r => setTimeout(r, 250));
    }
    await new Promise(r => setTimeout(r, 300));   // ranks and other late tile details
}

/** Queries a theme's panel shows: headlines, charts (incl. pivots) and its map. */
function usedQueries(theme) {
    const names = new Set();
    for (const h of theme.headlines || []) names.add(h.query);
    for (const c of theme.charts || []) {
        if (c.pivot) c.pivot.forEach(p => names.add(p.query));
        else names.add(c.query);
    }
    if (theme.map?.query) names.add(theme.map.query);
    return [...names].filter(q => q && theme.queries[q]);
}

function download(name, text, mime) {
    const url = URL.createObjectURL(new Blob([text], { type: mime }));
    const a = document.createElement('a');
    a.href = url;
    a.download = name;
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 0);
}

/* --------------------------------------------------------------- outputs */

/** A raw query value as plain text for an output table. */
function cell(v) {
    if (v == null) return 'NA';
    if (typeof v === 'number') {
        if (Number.isInteger(v)) return v.toLocaleString('en-US');
        const a = Math.abs(v);
        return a >= 1000 ? Math.round(v).toLocaleString('en-US') : String(+v.toPrecision(4));
    }
    if (typeof v === 'object') return JSON.stringify(v);
    return String(v);
}

function outputHtml(q) {
    if (q.error) return `<pre class="chunk-output err">Query failed: ${escapeHtml(q.error)}</pre>`;
    const rows = q.rows || [];
    if (!rows.length) return '<p class="chunk-more">No rows.</p>';
    const cols = Object.keys(rows[0]);
    const shown = rows.slice(0, OUTPUT_ROWS);
    return `<div class="chunk-output"><table><thead><tr>${cols.map(k => `<th>${escapeHtml(k)}</th>`).join('')}</tr></thead><tbody>` +
        shown.map(r => `<tr>${cols.map(k => `<td>${escapeHtml(cell(r[k]))}</td>`).join('')}</tr>`).join('') +
        `</tbody></table>${rows.length > OUTPUT_ROWS ? `<p class="chunk-more">Showing the first ${OUTPUT_ROWS} of ${rows.length} rows.</p>` : ''}</div>`;
}

function codeVariants(ga, sql, name) {
    return '<div class="code-variants">' + ga.CODE_LANGUAGES.map(l =>
        `<pre class="code-variant" data-lang="${l.id}"><code>${escapeHtml(ga.wrapQuery(sql, l.id, name))}</code></pre>`).join('') + '</div>';
}

/** The panel as the reader saw it: tiles and charts, cloned from the page. */
function panelHtml(card) {
    if (!card) return '';
    const tiles = card.querySelector('.tiles');
    const charts = [...card.querySelectorAll('.chart')].map(ch => {
        const k = ch.cloneNode(true);
        k.querySelectorAll('svg').forEach(svg => {
            // keep the drawn pixel size, so text stays at its designed size
            const vb = (svg.getAttribute('viewBox') || '').split(/\s+/).map(Number);
            if (vb.length === 4) { svg.setAttribute('width', vb[2]); svg.setAttribute('height', vb[3]); }
        });
        return k.outerHTML;
    }).join('');
    return `${tiles ? `<div class="tiles" data-n="${tiles.dataset.n}">${tiles.innerHTML}</div>` : ''}
${charts ? `<div class="charts">${charts}</div>` : ''}`;
}

/* ----------------------------------------------------------- the report */

function buildHtml(d, ga, mapEmbed, files) {
    const date = d.exportedAt.toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' });
    const lang = 'sql';
    const langButtons = ga.CODE_LANGUAGES.map(l =>
        `<button type="button" data-set-lang="${l.id}" aria-pressed="${l.id === lang}">${escapeHtml(l.label)}</button>`).join('');
    const dlButtons = files.map(f =>
        `<button type="button" data-download="${escapeHtml(f.filename)}" title="${escapeHtml(f.label)}">.${escapeHtml(f.ext)}</button>`).join('');
    const filesJson = JSON.stringify(Object.fromEntries(files.map(f => [f.filename, { mime: f.mime, text: f.text }]))).replace(/</g, '\\u003c');
    const setup = ga.CODE_LANGUAGES.map(l =>
        `<pre class="code-variant" data-lang="${l.id}"><code>${escapeHtml(ga.buildSetupSnippet(l.id))}</code></pre>`).join('');
    let legend = '';
    if (d.legendEl && !d.legendEl.hidden) {
        const lg = d.legendEl.cloneNode(true);
        lg.querySelectorAll('input, label').forEach(n => n.remove());   // live-only controls
        legend = `<div class="map-legend">${lg.innerHTML}</div>`;
    }

    const toc = `<nav class="report-toc" aria-label="Contents"><p class="report-rail-title">Contents</p><ol>` +
        d.sections.map((s, i) => `<li><a href="#s-${i + 1}">${escapeHtml(s.theme.label || 'At a glance')}</a></li>`).join('') +
        (d.datasets.length ? `<li class="report-toc-log"><a href="#data-sources">Data sources</a></li>` : '') + `</ol></nav>`;

    const sections = d.sections.map((s, i) => `<section class="report-section" id="s-${i + 1}" style="--c:${escapeHtml(s.theme.color || '#006837')}">
<h2>${escapeHtml(s.theme.label || 'At a glance')}</h2>
${s.theme.blurb && i ? `<p class="report-blurb">${escapeHtml(s.theme.blurb)}</p>` : ''}
${panelHtml(s.card)}
${s.theme.method ? `<p class="report-method"><b>Method.</b> ${escapeHtml(s.theme.method)}</p>` : ''}
<h3 class="report-queries">Queries</h3>
${s.queries.map(q => `<div class="chunk">
<details class="chunk-code"><summary>Code <span class="chunk-tool">${escapeHtml(q.name)}</span> <span class="chunk-var">→ df${q.n}</span></summary>${codeVariants(ga, q.sql, `df${q.n}`)}</details>
${outputHtml(q)}
</div>`).join('\n')}
</section>`).join('\n');

    return `<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>${escapeHtml(d.aoi.label)} — ${escapeHtml(d.siteTitle)}</title>
<style>${REPORT_CSS}</style>
${mapEmbed.headTags}
</head>
<body data-code-lang="${lang}" data-print="full">
<header class="report-header">
  <p class="report-kicker">${escapeHtml(d.siteTitle)} · ${escapeHtml(d.kind)}</p>
  <h1 class="report-title">${escapeHtml(d.aoi.label)}</h1>
  <p class="report-subtitle">Profile exported ${escapeHtml(date)}${d.subtitle ? ` · ${escapeHtml(d.subtitle)}` : ''}</p>
  <aside class="report-disclosure">
    No AI model produced these numbers. Every figure comes from the fixed SQL shown under each section, run against public
    cloud-hosted datasets through the <a href="https://duckdb-mcp.nrp-nautilus.io/mcp">duckdb-geo</a> server, exactly as written
    here. California comparisons are the same SQL run over the whole state.
    Features, thresholds and the representation framework follow <a href="${REPORT_URL}">${escapeHtml(REPORT_REF)}</a>
    <span class="report-disclosure-speed">${escapeHtml(SPEED_NOTE)}</span>
  </aside>
</header>
<aside class="report-rail">
  <p class="report-rail-title" id="report-options-title">Options</p>
  <div class="report-controls" role="group" aria-labelledby="report-options-title">
    <span class="ctl-label">Code</span>
    <div class="ctl-seg code-fold-toggle" role="group" aria-label="Code"><button type="button" data-code-all="show">Show</button><button type="button" data-code-all="hide">Hide</button></div>
    <span class="ctl-label">Code as</span>
    <div class="ctl-seg code-lang-toggle" role="group" aria-label="Show code as">${langButtons}</div>
    <span class="ctl-label">Download</span>
    <div class="ctl-seg export-download-controls" role="group" aria-label="Download code">${dlButtons}</div>
    <span class="ctl-label">Print</span>
    <div class="export-print-controls"><button type="button" class="export-print-btn">Print / PDF</button>
      <label class="export-print-report"><input type="checkbox" id="export-report-style"> without code</label></div>
  </div>
  ${toc}
</aside>
<section class="report-setup" id="setup">
  <details class="chunk-code"><summary>Code <span class="chunk-tool">setup</span></summary><div class="code-variants">${setup}</div></details>
  <p class="report-setup-note">To re-run these queries yourself, run the setup chunk once: it points <code>s3://</code> paths at the public
     endpoint with anonymous access. Each query's result lands in <code>df1</code>, <code>df2</code>, …; or download them all as a script or
     notebook (<em>Download</em>, under Options).</p>
</section>
${mapEmbed.body.replace('Map at time of export', 'Map').replace('<div id="export-map" class="export-map"></div>',
        `<div id="export-map" class="export-map"></div>${d.snapshot ? `<img class="export-map-print" alt="Map of ${escapeHtml(d.aoi.label)}" src="${d.snapshot}">` : ''}`)}
${legend}
<main class="report-body">
${sections}
</main>
${sourcesHtml(d.datasets)}
<footer class="report-colophon">
  <p>Exported from <a href="${escapeHtml(d.appUrl)}">${escapeHtml(d.siteTitle)}</a> (<a href="${escapeHtml(d.projectUrl || PROJECT_URL)}">source</a>) on ${escapeHtml(d.exportedAt.toLocaleString())}.
     Open the link to see this profile live.</p>
</footer>
<script type="application/json" id="export-session-files">${filesJson}</script>
<script>${REPORT_SCRIPT}</script>
</body>
</html>`;
}

function sourcesHtml(datasets) {
    if (!datasets.length) return '';
    const a = (href, text) => href ? `<a href="${escapeHtml(href)}">${text}</a>` : text;
    const items = datasets.map(d => {
        const by = d.producers.length ? ` — ${escapeHtml(d.producers.join(', '))}` : '';
        const cite = d.citation ? `<p class="ds-citation">${escapeHtml(d.citation)}${d.doiUrl && !d.citation.includes(d.doiUrl.replace(/^https?:\/\/(dx\.)?doi\.org\//, '')) ? ` ${a(d.doiUrl, escapeHtml(d.doiUrl))}` : ''}</p>`
            : d.doiUrl ? `<p class="ds-citation">Cite as ${a(d.doiUrl, escapeHtml(d.doiUrl))}</p>`
            : '<p class="ds-citation ds-none">The catalog gives no formal citation; cite the producer.</p>';
        const use = d.queried && d.mapped ? 'queried and mapped' : d.queried ? 'queried' : 'mapped';
        const meta = [
            d.license ? `License: ${a(d.licenseUrl, escapeHtml(d.license))}` : '',
            d.stacUrl ? a(d.stacUrl, 'STAC record') : '',
            d.aboutUrl ? a(d.aboutUrl, 'About') : '',
            `${use} in this report`,
        ].filter(Boolean).join(' · ');
        return `<li><p class="ds-title"><strong>${escapeHtml(d.title)}</strong>${by}</p>${cite}<p class="ds-meta">${meta}</p></li>`;
    }).join('\n');
    return `<section class="report-sources" id="data-sources">
<h2>Data sources</h2>
<p class="report-appendix-note">The datasets this report's queries read or its map shows, with the citation their catalog record gives.</p>
<ol class="ds-list">
${items}
</ol>
</section>`;
}

/* ------------------------------------------------- scripts and notebooks */

function datasetLines(d) {
    const lines = [d.title + (d.producers.length ? ` - ${d.producers.join(', ')}` : '') + '.'];
    if (d.citation) lines.push(d.citation);
    else if (d.doiUrl) lines.push(`Cite as: ${d.doiUrl}`);
    if (d.license) lines.push(`License: ${d.license}`);
    if (d.stacUrl) lines.push(`STAC: ${d.stacUrl}`);
    return lines.map(l => l.replace(/\s+/g, ' ').trim());
}

function buildFiles(d, ga) {
    const title = `${d.siteTitle}: ${d.aoi.label} (${d.kind}), exported ${d.exportedAt.toISOString().slice(0, 10)}`;
    const about = [
        `From ${d.appUrl}`,
        'These are the exact queries behind the exported profile; no AI model was involved.',
        SPEED_NOTE,
    ];
    const show = (name, lang) => lang === 'r' ? `print(head(${name}, ${OUTPUT_ROWS}))` : `print(${name})`;

    const script = lang => {
        const out = [`# ${title}`, '#', ...about.map(l => `# ${l}`)];
        if (lang === 'r') out.push('# Needs R >= 4.0 for the raw strings around each query.');
        out.push('', ga.buildSetupSnippet(lang));
        for (const s of d.sections) {
            out.push('', lang === 'r' ? `# ---- ${s.theme.label || 'At a glance'} ----` : `# %% ${s.theme.label || 'At a glance'}`);
            for (const q of s.queries) out.push('', `# ${q.name}`, ga.wrapQuery(q.sql, lang, `df${q.n}`), show(`df${q.n}`, lang));
        }
        if (d.datasets.length) {
            out.push('', lang === 'r' ? '# ---- Data sources ----' : '# %% Data sources');
            for (const ds of d.datasets) { out.push('#'); datasetLines(ds).forEach((l, i) => out.push(`# ${i ? '  ' : '- '}${l}`)); }
        }
        return out.join('\n') + '\n';
    };

    const sourcesMd = () => '## Data sources\n\n' + d.datasets.map(ds => {
        const [first, ...rest] = datasetLines(ds);
        return `- ${first}` + rest.map(l => `\n  ${l}`).join('');
    }).join('\n');

    const qmd = () => {
        const chunk = (code, label) => '```{r}\n' + (label ? `#| label: ${label}\n` : '') + code + '\n```';
        const out = ['---', `title: ${JSON.stringify(title)}`, 'format: html', '---', '',
            '::: {.callout-note}', about.join(' '), ':::', '', chunk(ga.buildSetupSnippet('r'), 'setup')];
        for (const s of d.sections) {
            out.push('', `## ${s.theme.label || 'At a glance'}`);
            if (s.theme.method) out.push('', s.theme.method);
            for (const q of s.queries) out.push('', `### ${q.name}`, '', chunk(`${ga.wrapQuery(q.sql, 'r', `df${q.n}`)}\nhead(df${q.n}, ${OUTPUT_ROWS})`));
        }
        if (d.datasets.length) out.push('', sourcesMd());
        return out.join('\n') + '\n';
    };

    const ipynb = () => {
        const cells = [];
        const md = source => cells.push({ cell_type: 'markdown', id: `cell-${cells.length + 1}`, metadata: {}, source });
        const code = source => cells.push({ cell_type: 'code', id: `cell-${cells.length + 1}`, metadata: {}, execution_count: null, outputs: [], source });
        md(`# ${title}\n\n> ${about.join(' ')}`);
        code(ga.buildSetupSnippet('python'));
        for (const s of d.sections) {
            md(`## ${s.theme.label || 'At a glance'}` + (s.theme.method ? `\n\n${s.theme.method}` : ''));
            for (const q of s.queries) { md(`### ${q.name}`); code(`${ga.wrapQuery(q.sql, 'python', `df${q.n}`)}\ndf${q.n}`); }
        }
        if (d.datasets.length) md(sourcesMd());
        return JSON.stringify({
            cells,
            metadata: { kernelspec: { display_name: 'Python 3', language: 'python', name: 'python3' }, language_info: { name: 'python' } },
            nbformat: 4, nbformat_minor: 5,
        }, null, 1) + '\n';
    };

    return [
        { ext: 'R', label: 'R script', mime: 'text/plain', text: script('r') },
        { ext: 'py', label: 'Python script', mime: 'text/x-python', text: script('python') },
        { ext: 'qmd', label: 'Quarto notebook (R)', mime: 'text/markdown', text: qmd() },
        { ext: 'ipynb', label: 'Jupyter notebook (Python)', mime: 'application/x-ipynb+json', text: ipynb() },
    ].map(f => ({ ...f, filename: `${d.basename}.${f.ext}` }));
}

/* ------------------------------------------------- in-document behaviour */

// Language toggle (remembered), show/hide all code, print (opens folded code
// unless "without code"), and the download buttons.
const REPORT_SCRIPT = `
(function () {
  var KEY = 'ca30x30-assessment-export-code-lang';
  var strip = document.querySelector('.code-lang-toggle');
  function apply(lang) {
    document.body.setAttribute('data-code-lang', lang);
    strip.querySelectorAll('button').forEach(function (b) { b.setAttribute('aria-pressed', String(b.getAttribute('data-set-lang') === lang)); });
    try { localStorage.setItem(KEY, lang); } catch (e) {}
  }
  var saved = null;
  try { saved = localStorage.getItem(KEY); } catch (e) {}
  if (saved && strip.querySelector('button[data-set-lang="' + saved + '"]')) apply(saved);
  strip.addEventListener('click', function (e) { var b = e.target.closest('button[data-set-lang]'); if (b) apply(b.getAttribute('data-set-lang')); });

  document.querySelector('.code-fold-toggle').addEventListener('click', function (e) {
    var b = e.target.closest('button[data-code-all]'); if (!b) return;
    var open = b.getAttribute('data-code-all') === 'show';
    document.querySelectorAll('details.chunk-code').forEach(function (d) { d.open = open; });
  });

  var check = document.getElementById('export-report-style');
  check.addEventListener('change', function () { document.body.setAttribute('data-print', check.checked ? 'report' : 'full'); });
  var reopened = [];
  window.addEventListener('beforeprint', function () {
    reopened = [];
    document.querySelectorAll('details:not([open])').forEach(function (d) { reopened.push(d); d.open = true; });
  });
  window.addEventListener('afterprint', function () { reopened.forEach(function (d) { d.open = false; }); reopened = []; });
  document.querySelector('.export-print-btn').addEventListener('click', function () { window.print(); });

  var files = JSON.parse(document.getElementById('export-session-files').textContent);
  document.querySelector('.export-download-controls').addEventListener('click', function (e) {
    var b = e.target.closest('button[data-download]'); var f = b && files[b.getAttribute('data-download')];
    if (!f) return;
    var url = URL.createObjectURL(new Blob([f.text], { type: f.mime }));
    var a = document.createElement('a'); a.href = url; a.download = b.getAttribute('data-download');
    document.body.appendChild(a); a.click(); a.remove();
    setTimeout(function () { URL.revokeObjectURL(url); }, 0);
  });
})();
`;

/** Report stylesheet: geo-agent's Quarto-like document, plus this app's tiles and charts. */
const REPORT_CSS = REP_CSS + `
:root { --fg: #22201f; --muted: #6c6a67; --rule: #dee2e6; --code-bg: #f6f8fa; --accent: #1b6e3a;
        --text: #22201f; --text-2: #4f4a47; --text-3: #77706b; --surface: #f5faf1;
        --grid: rgba(0,0,0,0.08); --line-strong: rgba(30,40,30,0.22); --series-state: #2b2b2b;
        --series-protected: #1b6e3a; --series-other: #9aa59a; --primary: #1b6e3a;
        --font: "Inter", system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
        --mono: SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace; }
* { box-sizing: border-box; }
html { background: #fff; }
body { font-family: var(--font); color: var(--fg); background: #fff; line-height: 1.55; font-size: 15px;
       max-width: 900px; margin: 0 auto; padding: 2rem 16px 4rem; }
a { color: var(--accent); }
code { font-family: var(--mono); font-size: 0.875em; }
p code { background: rgba(0,0,0,0.04); padding: 0.1em 0.3em; border-radius: 3px; }

.report-header { margin-bottom: 1.25rem; }
.report-kicker { color: var(--muted); font-size: 0.85rem; text-transform: uppercase; letter-spacing: 0.04em; margin: 0; }
.report-title { font-size: 2.1rem; line-height: 1.2; margin: 0.1rem 0 0.25rem; font-weight: 650; }
.report-subtitle { color: var(--muted); margin: 0 0 1rem; }
.report-disclosure { border-left: 4px solid var(--accent); background: #f1f8f3; padding: 0.6rem 0.9rem;
                     border-radius: 0 4px 4px 0; font-size: 0.9rem; margin: 0 0 1rem; }
.report-disclosure-speed { display: block; margin-top: 0.35rem; color: var(--muted); }
.report-rail { border: 1px solid var(--rule); border-radius: 6px; padding: 0.75rem 1rem; margin: 0 0 1.5rem; }
.report-rail-title { font-weight: 600; font-size: 0.9rem; margin: 0 0 0.25rem; }
.report-controls { display: grid; grid-template-columns: max-content 1fr; gap: 8px 12px; align-items: center; font-size: 13px; margin-top: 0.4rem; }
.ctl-label { color: var(--muted); font-size: 12px; }
.report-controls button { font: inherit; font-size: 12px; padding: 3px 10px; cursor: pointer;
                          border: 1px solid #ced4da; border-radius: 4px; background: #fff; color: #495057; }
.report-controls button:hover { background: #f1f3f5; }
.ctl-seg { display: flex; flex-wrap: wrap; }
.ctl-seg button { border-radius: 0; }
.ctl-seg button:first-child { border-radius: 4px 0 0 4px; }
.ctl-seg button:last-child { border-radius: 0 4px 4px 0; }
.ctl-seg button + button { border-left: 0; }
.code-lang-toggle button[aria-pressed="true"] { background: var(--accent); border-color: var(--accent); color: #fff; }
.export-print-controls { display: flex; flex-wrap: wrap; align-items: center; gap: 4px 10px; color: var(--muted); font-size: 12px; }
.export-print-report { display: flex; align-items: center; gap: 4px; cursor: pointer; }
.report-toc { font-size: 0.9rem; margin: 0.9rem 0 0; padding-top: 0.75rem; border-top: 1px solid var(--rule); }
.report-toc ol { margin: 0; padding-left: 1.4rem; }
.report-toc a { text-decoration: none; }
.report-toc-log { list-style: none; margin-left: -1.4rem; margin-top: 0.4rem; }
@media (min-width: 1500px) {
  .report-rail { position: fixed; top: 2rem; left: calc(50% - 450px - 290px); width: 260px; margin: 0;
                 border: 0; border-left: 1px solid var(--rule); border-radius: 0; padding: 0 0 0 1rem;
                 max-height: calc(100vh - 4rem); overflow-y: auto; }
  .report-rail .report-controls button { padding: 3px 7px; }
}

.chunk { margin: 0.9rem 0; }
details.chunk-code > summary { cursor: pointer; list-style: none; color: var(--muted); font-size: 0.85rem;
                               display: inline-flex; align-items: center; gap: 6px; padding: 2px 0; user-select: none; }
details.chunk-code > summary::-webkit-details-marker { display: none; }
details.chunk-code > summary::before { content: '▸'; font-size: 0.8em; }
details.chunk-code[open] > summary::before { content: '▾'; }
.chunk-tool, .chunk-var { font-family: var(--mono); font-size: 0.8rem; color: #868e96; }
.code-variant { display: none; margin: 0.35rem 0 0; background: var(--code-bg); border-left: 3px solid var(--rule);
                padding: 0.75rem 1rem; overflow-x: auto; font-size: 0.8rem; line-height: 1.45; }
body[data-code-lang="sql"] .code-variant[data-lang="sql"],
body[data-code-lang="r"] .code-variant[data-lang="r"],
body[data-code-lang="python"] .code-variant[data-lang="python"] { display: block; }
.chunk-output { margin: 0.4rem 0 0; overflow-x: auto; }
.chunk-output table { border-collapse: collapse; font-size: 0.8rem; }
.chunk-output th, .chunk-output td { border-bottom: 1px solid var(--rule); padding: 0.25rem 0.7rem; text-align: left; white-space: nowrap; }
.chunk-output th { border-bottom: 2px solid #adb5bd; font-weight: 600; }
.chunk-output td { font-family: var(--mono); font-size: 0.76rem; }
pre.chunk-output.err { color: #b02a37; white-space: pre-wrap; }
.chunk-more { color: var(--muted); font-size: 0.82rem; margin: 0.3rem 0 0; }
.report-setup { margin: 0 0 1.5rem; }
.report-setup-note { color: var(--muted); font-size: 0.85rem; margin: 0.35rem 0 0; }

.report-section { margin: 2.5rem 0 0; }
.report-section h2 { font-size: 1.45rem; font-weight: 650; line-height: 1.3; margin: 0 0 0.4rem;
                     padding-bottom: 0.3rem; border-bottom: 3px solid var(--c, var(--rule)); }
.report-blurb { color: var(--muted); margin: 0 0 0.75rem; }
.report-method { font-size: 0.88rem; color: #3d3a38; margin: 1rem 0 0; }
.report-queries { font-size: 1rem; margin: 1.25rem 0 0; color: var(--muted); font-weight: 600; }

.tiles { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 8px; margin: 0.5rem 0; }
.tiles[data-n="3"] { grid-template-columns: repeat(3, minmax(0, 1fr)); }
.tiles[data-n="2"] { grid-template-columns: repeat(2, minmax(0, 1fr)); }
@media (max-width: 640px) { .tiles, .tiles[data-n="3"] { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
.tile { padding: 8px 10px; border-radius: 8px; background: var(--surface); min-width: 0; break-inside: avoid; }
.tile-label { font-size: 12px; color: var(--text-2); }
.tile-value { font-size: 24px; font-weight: 650; font-variant-numeric: tabular-nums; line-height: 1.15; margin-top: 2px; }
.tile-compare { font-size: 11.5px; color: var(--text-3); margin-top: 2px; font-variant-numeric: tabular-nums; }
.tile-note { font-size: 11px; color: var(--text-3); margin-top: 2px; }
.tile-rank { font-size: 12px; color: var(--text-2); margin-top: 3px; }
.tile-rank b { color: var(--c, var(--primary)); }
.tile .err { color: #b02a37; font-size: 11px; }
.charts { display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 0 24px; }
.chart { margin-top: 12px; min-width: 0; break-inside: avoid; }
.chart.wide { grid-column: 1 / -1; }
.chart h4 { font-size: 13px; margin: 0; font-weight: 600; }
.chart .sub { font-size: 12px; color: var(--text-3); margin: 1px 0 6px; }
.chart svg { display: block; max-width: 100%; height: auto; overflow: visible; }
.chart svg text { font-size: 11.5px; fill: var(--text-2); font-variant-numeric: tabular-nums; }
.chart svg .val { fill: var(--text); }
.legend-row { display: flex; flex-wrap: wrap; gap: 12px; font-size: 12px; color: var(--text-2); margin: 2px 0 4px; }
.legend-row span { display: inline-flex; align-items: center; gap: 5px; }
.legend-row i { width: 11px; height: 11px; border-radius: 2px; display: inline-block; }
.legend-row i.tick { width: 2px; height: 12px; border-radius: 0; }

.export-map-section { margin: 0 0 0.5rem; }
.export-map-title { font-size: 1rem; font-weight: 600; margin: 0 0 0.5rem; }
.export-map { width: 100%; height: 480px; border: 1px solid var(--rule); border-radius: 4px; }
.export-map-note { font-size: 0.8rem; color: var(--muted); margin: 6px 0 0; }
.export-map-error { padding: 1rem; color: #991b1b; font-size: 13px; }
.export-embed { margin: 8px 0 0; }
.export-embed-toggle, .export-embed-copy { font: inherit; font-size: 12px; padding: 4px 10px; cursor: pointer;
                       border: 1px solid #ced4da; border-radius: 4px; background: #fff; color: var(--accent); }
.export-embed-help { border: 1px solid var(--rule); border-radius: 6px; padding: 10px 12px; margin: 8px 0 0; font-size: 13px; background: #f8f9fa; }
.export-embed-snippet { background: var(--code-bg); padding: 8px; border-radius: 4px; overflow-x: auto; font-size: 11px; white-space: pre-wrap; word-break: break-word; }
.export-embed-note { font-size: 12px; color: var(--muted); }
.export-map-print { display: none; width: 100%; height: auto; border: 1px solid var(--rule); border-radius: 4px; }
.map-legend { font-size: 12px; max-width: 320px; margin: 0.5rem 0 1.5rem; padding: 8px 10px; border: 1px solid var(--rule); border-radius: 6px; }
.map-legend .title { font-weight: 600; }
.map-legend .lg-row { display: flex; align-items: center; gap: 6px; margin-top: 3px; }
.map-legend .lg-row i { width: 12px; height: 12px; border-radius: 2px; display: inline-block; flex: none; }
.map-legend .lg-row i.snone { box-shadow: inset 0 0 0 1px rgba(0,0,0,.18); }
.map-legend .ramp { display: flex; height: 10px; border-radius: 2px; overflow: hidden; margin: 5px 0 3px; }
.map-legend .ramp span { flex: 1; }
.map-legend .ends { display: flex; justify-content: space-between; color: var(--text-3); }
.map-legend .tile-note { font-size: 11px; color: var(--text-3); }

.report-sources { margin: 3rem 0 0; padding-top: 1rem; border-top: 2px solid var(--rule); }
.report-sources h2 { font-size: 1.2rem; margin: 0 0 0.25rem; }
.report-appendix-note { color: var(--muted); font-size: 0.85rem; }
.ds-list { padding-left: 1.4rem; margin: 0.75rem 0 0; }
.ds-list li { margin: 0 0 0.9rem; }
.ds-list p { margin: 0.1rem 0; }
.ds-citation { font-size: 0.9rem; }
.ds-none { color: var(--muted); font-style: italic; }
.ds-meta { color: var(--muted); font-size: 0.82rem; }
.report-colophon { margin-top: 3rem; padding-top: 0.75rem; border-top: 1px solid var(--rule); color: var(--muted); font-size: 0.8rem; }

body[data-view="map"] { margin: 0; padding: 0; max-width: none; }
body[data-view="map"] > *:not(.export-map-section) { display: none !important; }
body[data-view="map"] .export-map-title, body[data-view="map"] .export-map-note, body[data-view="map"] .export-embed { display: none; }
body[data-view="map"] .export-map { height: 100vh; border: 0; border-radius: 0; }

@media print {
  body { max-width: none; margin: 0; padding: 0; font-size: 12px; }
  .report-rail, .export-embed, .export-map-note { display: none !important; }
  a { color: inherit; text-decoration: none; }
  .chunk, .code-variants, pre, .export-map-section, .chart, .tiles { break-inside: avoid; }
  .report-section h2, .report-queries { break-after: avoid; }
  .export-map:has(+ .export-map-print) { display: none; }
  .export-map-print { display: block; }
  .export-map { height: 400px; }
  .chunk-output { overflow: visible; }
  .chunk-output table { font-size: 8px; }
  .chunk-output th, .chunk-output td { white-space: normal; padding: 0.15rem 0.4rem; }
  .code-variant { white-space: pre-wrap; word-break: break-all; font-size: 8px; }
  details.chunk-code > summary::before { content: ''; }
  body[data-print="report"] details.chunk-code, body[data-print="report"] .report-setup,
  body[data-print="report"] .report-queries, body[data-print="report"] .chunk { display: none !important; }
}
`;

/** Hook an "Export" button: shows progress, reports failure in place. */
export function wireExportButton(btn, getOptions) {
    btn.onclick = async () => {
        if (btn.disabled) return;
        const label = btn.textContent;
        btn.disabled = true;
        btn.textContent = 'Preparing…';
        try {
            await exportReport(getOptions());
            btn.textContent = 'Downloaded';
        } catch (err) {
            console.error(err);
            btn.textContent = 'Export failed';
            btn.title = err.message || String(err);
        }
        setTimeout(() => { btn.textContent = label; btn.disabled = false; }, 2500);
    };
}
