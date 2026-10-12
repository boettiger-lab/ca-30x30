/**
 * Query engine: loads the declarative config (jurisdictions + themes + SQL
 * templates), expands templates for an area of interest, runs them through
 * MCP, and caches results.
 *
 * Template tokens
 *   {{AOI}}    → a SELECT returning DISTINCT (h0, h8) res-8 cells of the area.
 *               Fast; overhangs the boundary by up to ~0.5 km (fine for
 *               counties and districts, rough for small cities).
 *   {{AOI10}}  → a SELECT returning DISTINCT (h0, h8, h10) res-10 cells.
 *               Use for population-weighted or boundary-sensitive measures.
 *   {{BANDS10}} → (isochrone AOIs only) (band, h0, h8, h10): every cell of the
 *               largest isochrone, labelled with the smallest travel-time band
 *               (minutes) that reaches it.
 *   {{ORIGIN_LAT}}, {{ORIGIN_LON}} → (isochrone AOIs only) the starting point.
 *   {{LAND}}   → the area's California land cells at res 10:
 *               (h0, h8, h9, h10, area_km2, w12, w34), where w12 / w34 are the
 *               cell's GAP 1+2 / GAP 3+4 shares (0 outside any conserved unit).
 *               Built from app.land around app.land_cells (or the AOI's own
 *               `cells`, e.g. statewide), so every metric is masked to
 *               California's land grid, the 30x30 denominator.
 *   {{ID}}   → (jurisdiction AOI templates only) the sanitized feature id.
 *
 * Theme ids in app.json may be paths (e.g. "../config/themes/equity") so a
 * site variant can reuse another variant's themes; the id is the last segment.
 *
 * Shared by the browser app and scripts/precompute.mjs.
 */

import { McpQueryClient } from './mcp.js';

export async function loadConfig(base = '.', fetchText = defaultFetchText, { themes: only = null } = {}) {
    const app = JSON.parse(await fetchText(`${base}/config/app.json`));
    const themes = [];
    for (let id of [app.overview, ...app.themes]) {
        const dir = id.includes('/') ? `${base}/${id}` : `${base}/config/themes/${id}`;
        const path = id;
        id = id.split('/').pop();
        if (only && !only.includes(id)) continue;
        let theme;
        try {
            theme = JSON.parse(await fetchText(`${dir}/theme.json`));
        } catch (err) {
            if (path === app.overview) throw err;
            console.warn(`Skipping theme "${id}": ${err.message}`);
            continue;
        }
        theme.id = id;
        theme.sql = {};
        await Promise.all(Object.entries(theme.queries).map(async ([name, q]) => {
            theme.sql[name] = await fetchText(`${dir}/${q.file}`);
        }));
        themes.push(theme);
    }
    return {
        app,
        overview: themes[0],
        themes: themes.slice(1),
        themeById: Object.fromEntries(themes.map(t => [t.id, t])),
    };
}

async function defaultFetchText(url) {
    const res = await fetch(url, { cache: 'no-cache' });
    if (!res.ok) throw new Error(`Failed to load ${url}: ${res.status}`);
    return res.text();
}

/** Ids are spliced into SQL string literals, so allow only safe characters (no quotes). */
export function sanitizeId(id) {
    const s = String(id);
    if (!/^[A-Za-z0-9 _.()-]{1,64}$/.test(s)) throw new Error(`Invalid id: ${s}`);
    return s;
}

export function expand(template, tokens) {
    return template.replace(/\{\{(\w+)\}\}/g, (m, k) => {
        if (!(k in tokens)) throw new Error(`Unbound template token ${m}`);
        return tokens[k];
    });
}

/**
 * An AOI is { key, label, sql } where sql yields DISTINCT (h0, h8).
 * Jurisdictions build theirs from config; drawn/uploaded polygons will build
 * theirs from H3 polyfill (future) — the themes don't care which.
 */
export function jurisdictionAoi(jur, feature) {
    const id = sanitizeId(feature.id);
    return {
        key: `${jur.id}:${id}`,
        kind: jur.id,
        id,
        label: feature.name,
        sql: expand(jur.aoi, { ID: id }).trim(),
        sql10: expand(jur.aoi10, { ID: id }).trim(),
    };
}

export function statewideAoi(app) {
    return {
        key: 'statewide', kind: 'state', id: 'CA', label: 'California',
        sql: app.statewide.aoi.trim(), sql10: app.statewide.aoi10.trim(),
        cells: app.statewide.cells?.trim(),
    };
}

export class Engine {
    constructor(config, { mcpUrl, statewide = null, base = null } = {}) {
        this.base = base;                // site folder, for precomputed area files (browser only)
        this.config = config;
        this.client = new McpQueryClient(mcpUrl || config.app.mcp_url);
        this.cache = new Map();          // key → Promise<rows>
        this.statewide = statewide;      // { results: { themeId: { query: rows } } }
    }

    sqlFor(theme, queryName, aoi) {
        const tokens = { AOI: aoi.sql, AOI10: aoi.sql10 };
        const app = this.config.app;
        if (app.land) {
            const cells = aoi.cells || expand(app.land_cells, { AOI10: aoi.sql10 });
            tokens.LAND = expand(app.land, { CELLS: cells });
        }
        if (aoi.bands10) tokens.BANDS10 = aoi.bands10;
        if (aoi.origin) { tokens.ORIGIN_LAT = String(+aoi.origin.lat); tokens.ORIGIN_LON = String(+aoi.origin.lon); }
        return expand(theme.sql[queryName], tokens);
    }

    run(theme, queryName, aoi) {
        const key = `${aoi.key}|${theme.id}|${queryName}`;
        if (!this.cache.has(key)) {
            const sql = this.sqlFor(theme, queryName, aoi);
            const p = this.precomputed(aoi).then(pre => pre?.results?.[theme.id]?.[queryName] ?? this.client.query(sql)).catch(err => {
                this.cache.delete(key);          // let a retry re-run it
                err.sql = sql;
                throw err;
            });
            this.cache.set(key, p);
        }
        return this.cache.get(key);
    }

    /**
     * Precomputed results for a named area (data/areas/<kind>/<id>.json,
     * written by `precompute.mjs areas`), or null. The same SQL, run ahead.
     */
    precomputed(aoi) {
        if (!aoi.id || aoi.kind === 'state' || aoi.kind === 'polygon' || typeof fetch === 'undefined' || !this.base) return Promise.resolve(null);
        const key = `pre|${aoi.key}`;
        if (!this.cache.has(key)) {
            this.cache.set(key, fetch(`${this.base}/data/areas/${aoi.kind}/${encodeURIComponent(aoi.id)}.json`, { cache: 'no-cache' })
                .then(r => (r.ok ? r.json() : null))
                .catch(() => null));
        }
        return this.cache.get(key);
    }

    /** Statewide comparison rows: precomputed file first, live query as fallback. */
    runStatewide(theme, queryName) {
        const pre = this.statewide?.results?.[theme.id]?.[queryName];
        if (pre) return Promise.resolve(pre);
        if (theme.queries[queryName].statewide === false) return Promise.resolve(null);
        return this.run(theme, queryName, statewideAoi(this.config.app));
    }

    /**
     * Precomputed peer table for a theme and jurisdiction type
     * (data/peers/<theme>/<jur>.json, written by `precompute.mjs peers`);
     * null when absent.
     */
    peers(themeId, jurId, base = '.') {
        const key = `peers|${themeId}|${jurId}`;
        if (!this.cache.has(key)) {
            this.cache.set(key, fetch(`${base}/data/peers/${themeId}/${jurId}.json`, { cache: 'no-cache' })
                .then(r => (r.ok ? r.json() : null))
                .catch(() => null));
        }
        return this.cache.get(key);
    }

    /** Pick list for a jurisdiction type: precomputed file first, then live. */
    async listFeatures(jur, base = '.') {
        const key = `list|${jur.id}`;
        if (!this.cache.has(key)) {
            this.cache.set(key, (async () => {
                try {
                    const res = await fetch(`${base}/data/lists/${jur.id}.json`, { cache: 'no-cache' });
                    if (res.ok) return res.json();
                } catch { /* fall through to live query */ }
                return this.client.query(jur.list);
            })());
        }
        return this.cache.get(key);
    }
}
