#!/usr/bin/env node
/**
 * Run one theme query for one area and print the rows — for checking a
 * template while writing it. Uses the same engine and MCP client as the app.
 *
 *   node scripts/run.mjs <theme> <query>                 # statewide
 *   node scripts/run.mjs <theme> <query> <jur> <id>      # e.g. ecoregion Mono
 *   node scripts/run.mjs <theme> <query> --sql           # print the expanded SQL only
 */

import { readFile } from 'node:fs/promises';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { loadConfig, Engine, statewideAoi, jurisdictionAoi } from '../app/engine.js';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const args = process.argv.slice(2);
const sqlOnly = args.includes('--sql');
const [themeId, query, jurId, ...idParts] = args.filter(a => a !== '--sql');
const config = await loadConfig(root, p => readFile(p, 'utf8'), { themes: ['overview', themeId] });
const engine = new Engine(config, { mcpUrl: process.env.MCP_URL || config.app.mcp_url });
const theme = config.themeById[themeId];
if (!theme) throw new Error(`No theme ${themeId}`);
const aoi = jurId
    ? jurisdictionAoi(config.app.jurisdictions.find(j => j.id === jurId), { id: idParts.join(' '), name: idParts.join(' ') })
    : statewideAoi(config.app);
const sql = engine.sqlFor(theme, query, aoi);
if (sqlOnly) { console.log(sql); process.exit(0); }
const t0 = Date.now();
const rows = await engine.client.query(sql);
console.table(rows.map(r => Object.fromEntries(Object.entries(r).map(([k, v]) => [k, typeof v === 'number' && !Number.isInteger(v) ? +v.toPrecision(5) : v]))));
console.log(`${rows.length} rows, ${((Date.now() - t0) / 1000).toFixed(1)}s`);
