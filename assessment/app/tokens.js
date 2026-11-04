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
 *
 * Kept free of imports so scripts/run.mjs can load it without glen-charts.
 */

const sqlList = xs => xs.map(x => `'${String(x).replace(/'/g, "''")}'`).join(', ');

export function landSql(aoi, app, params = {}) {
    const cells = aoi.cells || app.land_cells.replaceAll('{{AOI10}}', aoi.sql10);
    const p = (app.params || []).find(x => x.id === 'manager');
    const opt = p?.options.find(o => o.value === (params.manager ?? p.default));
    if (!opt?.levels) return app.land.replaceAll('{{CELLS}}', cells);
    return app.land_manager.replaceAll('{{LEVELS}}', sqlList(opt.levels)).replaceAll('{{CELLS}}', cells);
}

export const tokens = { LAND: landSql };

export default { tokens };
