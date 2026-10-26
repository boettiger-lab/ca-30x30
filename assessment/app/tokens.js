/**
 * {{LAND}}: the area's California land cells at H3 res 10, as
 * (h0, h8, h9, h10, area_km2, w12, w34), where w12 / w34 are the cell's
 * GAP 1+2 / GAP 3+4 shares (0 outside any conserved unit). Built from
 * app.land around app.land_cells (or the area's own `cells`, e.g. statewide),
 * so every metric is masked to California's land grid, the 30x30 denominator.
 *
 * Kept free of imports so the glen-charts precompute CLI can load it
 * (app.json "extensions") without the browser modules.
 */

export const tokens = {
    LAND: (aoi, app) => app.land.replaceAll('{{CELLS}}', aoi.cells || app.land_cells.replaceAll('{{AOI10}}', aoi.sql10)),
};

export default { tokens };
