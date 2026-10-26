#!/usr/bin/env node
/**
 * Run one theme query for one area and print the rows — for checking a
 * template while writing it. Uses the app's glen-charts engine and MCP client
 * (fetched from jsDelivr at the pinned tag) and its {{LAND}} token.
 *
 *   node scripts/run.mjs <theme> <query>                 # statewide
 *   node scripts/run.mjs <theme> <query> <jur> <id>      # e.g. ecoregion Mono
 *   node scripts/run.mjs <theme> <query> --sql           # print the expanded SQL only
 */

import { readFile, writeFile, mkdir } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { dirname, resolve, join } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { tokens } from '../app/tokens.js';

const GLEN = 'v0.2.8';      // keep in step with index.html

async function glenEngine() {
    const dir = join(tmpdir(), `glen-charts-${GLEN}`, 'core');
    await mkdir(dir, { recursive: true });
    for (const f of ['engine.js', 'mcp.js']) {
        const res = await fetch(`https://cdn.jsdelivr.net/gh/SchmidtDSE/glen-charts@${GLEN}/core/${f}`);
        if (!res.ok) throw new Error(`glen-charts ${GLEN} ${f}: ${res.status}`);
        await writeFile(join(dir, f), await res.text());
    }
    return import(pathToFileURL(join(dir, 'engine.js')).href);
}

const { loadConfig, Engine, statewideAoi, jurisdictionAoi } = await glenEngine();
const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const args = process.argv.slice(2);
const sqlOnly = args.includes('--sql');
const [themeId, query, jurId, ...idParts] = args.filter(a => a !== '--sql');
const config = await loadConfig(root, p => readFile(p, 'utf8'), { themes: ['overview', themeId] });
const engine = new Engine(config, { mcpUrl: process.env.MCP_URL || config.app.mcp_url, dataBase: null, tokens });
const theme = config.themeById[themeId];
if (!theme) throw new Error(`No theme ${themeId}`);
const aoi = jurId
    ? jurisdictionAoi(config.app.jurisdictions.find(j => j.id === jurId), { id: idParts.join(' '), name: idParts.join(' ') }, config.app)
    : statewideAoi(config.app);
const sql = engine.sqlFor(theme, query, aoi);
if (sqlOnly) { console.log(sql); process.exit(0); }
const t0 = Date.now();
const rows = await engine.client.query(sql);
console.table(rows.map(r => Object.fromEntries(Object.entries(r).map(([k, v]) => [k, typeof v === 'number' && !Number.isInteger(v) ? +v.toPrecision(5) : v]))));
console.log(`${rows.length} rows, ${((Date.now() - t0) / 1000).toFixed(1)}s`);
