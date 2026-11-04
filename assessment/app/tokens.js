/**
 * {{LAND}}: the area's California land cells at H3 res 10, as
 * (h0, h8, h9, h10, area_km2, w12, w34, wc), where w12 / w34 are the cell's
 * GAP 1+2 / GAP 3+4 shares and wc its whole conserved share (all 0 outside
 * any conserved unit). Built from app.land around app.land_cells (or the
 * area's own `cells`, e.g. statewide), so every metric is masked to
 * California's land grid, the 30x30 denominator.
 *
 * With the `manager` param set, w12 and w34 count only the units whose
 * MNG_AG_LEV is in that option's `levels` (app.land_manager), and wc stays
 * every manager's, so wc - w12 - w34 is other managers' conserved land.
 * Under Federal, the `agency` param narrows that to the units whose
 * MNG_AGENCY is in its option's `agencies`; "rest" takes the federal units
 * no other agency option names, so the agencies partition Federal.
 *
 * Kept free of imports so scripts/run.mjs can load it without glen-charts.
 */

const sqlList = xs => xs.map(x => `'${String(x).replace(/'/g, "''")}'`).join(', ');
const option = (app, id, params) => {
    const p = (app.params || []).find(x => x.id === id);
    return p && { p, o: p.options.find(o => o.value === (params[id] ?? p.default)) };
};

/** The SQL predicate on a conserved-areas unit row `u` for the chosen manager, or null for all managers. */
export function unitFilter(app, params = {}) {
    const m = option(app, 'manager', params)?.o;
    if (!m?.levels) return null;
    const where = [`u.MNG_AG_LEV IN (${sqlList(m.levels)})`];
    const a = option(app, 'agency', params);
    const applies = a && Object.entries(a.p.when || {}).every(([k, v]) => [].concat(v).includes(params[k] ?? option(app, k, {})?.o?.value));
    if (applies && a.o?.agencies) where.push(`u.MNG_AGENCY IN (${sqlList(a.o.agencies)})`);
    if (applies && a.o?.rest) where.push(`COALESCE(u.MNG_AGENCY, '') NOT IN (${sqlList(a.p.options.flatMap(o => o.agencies || []))})`);
    return `(${where.join(' AND ')})`;
}

export function landSql(aoi, app, params = {}) {
    const cells = aoi.cells || app.land_cells.replaceAll('{{AOI10}}', aoi.sql10);
    const units = unitFilter(app, params);
    if (!units) return app.land.replaceAll('{{CELLS}}', cells);
    return app.land_manager.replaceAll('{{UNITS}}', units).replaceAll('{{CELLS}}', cells);
}

export const tokens = { LAND: landSql };

export default { tokens };
