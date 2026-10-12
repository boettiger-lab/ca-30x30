#!/usr/bin/env node
/**
 * Precompute the slow, shared results so the app opens fast:
 *   data/lists/<jurisdiction>.json   pick lists (id, name, bbox)
 *   data/statewide.json              every theme query run over all of California
 *   data/areas/<jur>/<id>.json       every theme query run over each feature of
 *                                    a jurisdiction type (ecoregions, counties)
 *   data/sources.json                the STAC records of every dataset the
 *                                    config reads (for the export's citations)
 *
 * Uses the same engine + MCP client as the browser, so a precomputed number
 * is exactly what the live query returns.
 *
 *   node scripts/precompute.mjs                       # lists, statewide, sources
 *   node scripts/precompute.mjs lists [jur ...]       # pick lists only
 *   node scripts/precompute.mjs statewide [theme ...]
 *   node scripts/precompute.mjs areas <jur> [id ...]  # e.g. areas ecoregion; skips files already written unless --force
 *   node scripts/precompute.mjs areas <jur> --theme climate   # re-run only these themes in files already written
 *   node scripts/precompute.mjs sources
 */

import { readFile, writeFile, mkdir } from 'node:fs/promises';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { loadConfig, Engine, statewideAoi, jurisdictionAoi } from '../app/engine.js';
import { dataPaths, pathPrefix } from '../app/sources.js';

const argv = process.argv.slice(2);
const force = argv.includes('--force') ? (argv.splice(argv.indexOf('--force'), 1), true) : false;
const siteAt = argv.indexOf('--site');
const site = siteAt >= 0 ? argv.splice(siteAt, 2)[1] : '.';
const themeAt = argv.indexOf('--theme');
const onlyThemes = themeAt >= 0 ? argv.splice(themeAt, 2)[1].split(',') : null;
const root = resolve(dirname(fileURLToPath(import.meta.url)), '..', site);
const fetchText = p => readFile(p, 'utf8');
const [what = 'all', ...only] = argv;
const config = await loadConfig(root, fetchText, what === 'lists' ? { themes: ['overview'] } : what === 'statewide' && only.length ? { themes: ['overview', ...only] } : {});
const engine = new Engine(config, { mcpUrl: process.env.MCP_URL || config.app.mcp_url });

if (what === 'all' || what === 'lists') {
    await mkdir(`${root}/data/lists`, { recursive: true });
    for (const jur of config.app.jurisdictions || []) {
        if (what === 'lists' && only.length && !only.includes(jur.id)) continue;
        const t0 = Date.now();
        const rows = await engine.client.query(jur.list);
        await writeFile(`${root}/data/lists/${jur.id}.json`, JSON.stringify(rows));
        console.log(`list ${jur.id}: ${rows.length} rows (${((Date.now() - t0) / 1000).toFixed(1)}s)`);
    }
}

if (what === 'all' || what === 'statewide') {
    const file = `${root}/data/statewide.json`;
    let out = { generated: null, results: {} };
    try { out = JSON.parse(await readFile(file, 'utf8')); } catch { /* fresh */ }
    const aoi = statewideAoi(config.app);
    for (const theme of [config.overview, ...config.themes]) {
        if (only.length && !only.includes(theme.id)) continue;
        out.results[theme.id] ??= {};
        for (const [name, q] of Object.entries(theme.queries)) {
            if (q.statewide === false) continue;
            const t0 = Date.now();
            try {
                out.results[theme.id][name] = await engine.client.query(engine.sqlFor(theme, name, aoi));
                console.log(`statewide ${theme.id}.${name}: ok (${((Date.now() - t0) / 1000).toFixed(1)}s)`);
            } catch (err) {
                console.error(`statewide ${theme.id}.${name}: FAILED — ${err.message.split('\n')[0]}`);
            }
        }
    }
    out.generated = new Date().toISOString();
    await writeFile(file, JSON.stringify(out, null, 1));
}

if (what === 'areas') {
    const [jurId, ...ids] = only;
    const jur = (config.app.jurisdictions || []).find(j => j.id === jurId);
    if (!jur) throw new Error(`Unknown jurisdiction ${jurId}`);
    const list = JSON.parse(await readFile(`${root}/data/lists/${jur.id}.json`, 'utf8'));
    await mkdir(`${root}/data/areas/${jur.id}`, { recursive: true });
    for (const f of list) {
        if (ids.length && !ids.includes(String(f.id))) continue;
        const file = `${root}/data/areas/${jur.id}/${f.id}.json`;
        let prior = null;
        try { prior = JSON.parse(await readFile(file, 'utf8')); } catch { /* not yet */ }
        if (prior && !force && !onlyThemes) continue;
        const aoi = jurisdictionAoi(jur, f);
        const out = onlyThemes && prior ? prior : { generated: null, id: f.id, name: f.name, results: {} };
        let failed = 0;
        const t0 = Date.now();
        for (const theme of [config.overview, ...config.themes]) {
            if (onlyThemes && prior && !onlyThemes.includes(theme.id)) continue;
            out.results[theme.id] = {};
            for (const name of Object.keys(theme.queries)) {
                try {
                    out.results[theme.id][name] = await engine.client.query(engine.sqlFor(theme, name, aoi));
                } catch (err) {
                    failed++;
                    console.error(`  ${f.name} ${theme.id}.${name}: FAILED — ${err.message.split('\n')[0]}`);
                }
            }
        }
        out.generated = new Date().toISOString();
        if (!failed) await writeFile(file, JSON.stringify(out));
        console.log(`areas ${jur.id} ${f.name}: ${failed ? `${failed} failed, not written` : 'ok'} (${((Date.now() - t0) / 1000).toFixed(0)}s)`);
    }
}

if (what === 'all' || what === 'sources') {
    // Every data path the config can read or draw, matched to the STAC
    // collection whose own asset is its longest prefix (as geo-agent's export
    // does), so the export can cite a dataset without crawling the catalog.
    const catalogUrl = config.app.stac_catalog || 'https://s3-west.nrp-nautilus.io/public-data/stac/catalog.json';
    const text = [JSON.stringify(config.app), ...[config.overview, ...config.themes].flatMap(t => Object.values(t.sql))].join('\n');
    const paths = [...new Set(dataPaths(text))];
    const t0 = Date.now();
    const collections = await crawl(catalogUrl);
    const assets = [];
    for (const c of collections) {
        for (const a of Object.values(c.assets || {})) {
            if (!a?.href) continue;
            const pmtiles = /\.pmtiles$/.test(a.href);
            const parquet = String(a.type || '').includes('parquet') || /\.parquet$|\/hex\/*$/.test(a.href);
            if (!pmtiles && !parquet) continue;
            const p = pmtiles ? a.href : pathPrefix(a.href);
            if (/^s3:\/\/[^/]+\/.+/.test(p) || pmtiles) assets.push({ p, pmtiles, c });
        }
    }
    assets.sort((a, b) => b.p.length - a.p.length);
    const used = new Map();
    const unmatched = [];
    for (const path of paths) {
        const target = /\.pmtiles$/.test(path) ? path : pathPrefix(path);
        const hit = assets.find(({ p, pmtiles }) => pmtiles ? p === path : (target === p || target.startsWith(p + '/')));
        if (!hit) { unmatched.push(path); continue; }
        if (!used.has(hit.c.id)) {
            const c = hit.c;
            used.set(c.id, {
                id: c.id,
                prefixes: [],
                stac: {
                    id: c.id, title: c.title, license: c.license, providers: c.providers,
                    'sci:citation': c['sci:citation'], 'sci:doi': c['sci:doi'],
                    links: (c.links || []).filter(l => ['self', 'about', 'license', 'cite-as'].includes(l.rel)),
                },
            });
        }
        const e = used.get(hit.c.id);
        if (!e.prefixes.includes(hit.p)) e.prefixes.push(hit.p);
    }
    await writeFile(`${root}/data/sources.json`, JSON.stringify({ generated: new Date().toISOString(), catalog: catalogUrl, datasets: [...used.values()] }, null, 1));
    console.log(`sources: ${used.size} datasets from ${collections.length} collections (${((Date.now() - t0) / 1000).toFixed(1)}s)`);
    if (unmatched.length) console.warn('no STAC record for:\n  ' + unmatched.join('\n  '));
}

/** Every collection under a STAC catalog (children followed recursively). */
async function crawl(url) {
    const seen = new Set();
    const out = [];
    async function visit(u) {
        if (seen.has(u)) return;
        seen.add(u);
        let doc;
        try {
            const r = await fetch(u);
            if (!r.ok) return;
            doc = await r.json();
        } catch { return; }
        if (doc.type === 'Collection') out.push({ ...doc, links: (doc.links || []).map(l => ({ ...l, href: new URL(l.href, u).href })) });
        const kids = (doc.links || []).filter(l => l.rel === 'child').map(l => new URL(l.href, u).href);
        await Promise.all(kids.map(visit));
    }
    await visit(url);
    return out;
}
