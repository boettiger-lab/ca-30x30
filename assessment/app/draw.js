/**
 * Draw a polygon on the map (click to add points, double-click or click the
 * first point to finish, Escape to cancel), or read polygons from an uploaded
 * GeoJSON file. Either becomes an AOI through iso.js polygonAoi (H3 polyfill
 * on the DuckDB server), so every section's SQL runs unchanged.
 */

const MAX_VERTICES = 5000;

export class DrawTool {
    constructor(mapView, { onDone }) {
        this.mv = mapView;
        this.onDone = onDone;
        this.pts = [];
        this.active = false;
        this._click = e => this._add(e);
        this._move = e => this._preview(e.lngLat);
        this._dbl = e => { e.preventDefault(); this._finish(); };
        this._key = e => { if (e.key === 'Escape') this.cancel(); };
    }

    async start() {
        await this.mv.ready;
        this.cancel();
        const m = this.mv.map;
        this.active = true;
        this.mv._drawing = true;
        this.pts = [];
        if (!m.getSource('draw')) {
            m.addSource('draw', { type: 'geojson', data: empty() });
            m.addLayer({ id: 'draw-fill', type: 'fill', source: 'draw', filter: ['==', ['geometry-type'], 'Polygon'], paint: { 'fill-color': '#111', 'fill-opacity': 0.08 } });
            m.addLayer({ id: 'draw-line', type: 'line', source: 'draw', paint: { 'line-color': '#111', 'line-width': 2, 'line-dasharray': [2, 1.5] } });
            m.addLayer({ id: 'draw-pts', type: 'circle', source: 'draw', filter: ['==', ['geometry-type'], 'Point'], paint: { 'circle-radius': 4, 'circle-color': '#fff', 'circle-stroke-color': '#111', 'circle-stroke-width': 1.5 } });
        }
        m.doubleClickZoom.disable();
        m.getCanvas().style.cursor = 'crosshair';
        m.on('click', this._click);
        m.on('mousemove', this._move);
        m.on('dblclick', this._dbl);
        window.addEventListener('keydown', this._key);
    }

    cancel() {
        if (!this.active) return;
        const m = this.mv.map;
        this.active = false;
        this.mv._drawing = false;
        m.off('click', this._click);
        m.off('mousemove', this._move);
        m.off('dblclick', this._dbl);
        window.removeEventListener('keydown', this._key);
        setTimeout(() => m.doubleClickZoom.enable(), 0);
        m.getCanvas().style.cursor = '';
        m.getSource('draw')?.setData(empty());
    }

    _add(e) {
        const p = [e.lngLat.lng, e.lngLat.lat];
        if (this.pts.length >= 3) {
            const first = this.mv.map.project(this.pts[0]);
            if (Math.hypot(first.x - e.point.x, first.y - e.point.y) < 10) return this._finish();
        }
        this.pts.push(p);
        this._preview(null);
    }

    _preview(cursor) {
        const pts = cursor ? [...this.pts, [cursor.lng, cursor.lat]] : this.pts;
        const feats = this.pts.map(p => ({ type: 'Feature', properties: {}, geometry: { type: 'Point', coordinates: p } }));
        if (pts.length >= 3) feats.push({ type: 'Feature', properties: {}, geometry: { type: 'Polygon', coordinates: [[...pts, pts[0]]] } });
        else if (pts.length === 2) feats.push({ type: 'Feature', properties: {}, geometry: { type: 'LineString', coordinates: pts } });
        this.mv.map.getSource('draw')?.setData({ type: 'FeatureCollection', features: feats });
    }

    _finish() {
        // a double-click also fires two clicks: drop a duplicate final vertex
        const pts = this.pts.filter((p, i, a) => i === 0 || p[0] !== a[i - 1][0] || p[1] !== a[i - 1][1]);
        if (pts.length < 3) return;
        const geom = { type: 'Polygon', coordinates: [[...pts, pts[0]]] };
        this.cancel();
        this.onDone(geom);
    }
}

/** Polygon/MultiPolygon geometries from a GeoJSON file (FeatureCollection, Feature or geometry). */
export async function readGeoJsonFile(file) {
    if (file.size > 20e6) throw new Error('File is larger than 20 MB; simplify it first.');
    let gj;
    try { gj = JSON.parse(await file.text()); } catch { throw new Error('Not a GeoJSON file.'); }
    const geoms = [];
    const visit = o => {
        if (!o) return;
        if (o.type === 'FeatureCollection') o.features.forEach(visit);
        else if (o.type === 'Feature') visit(o.geometry);
        else if (o.type === 'GeometryCollection') o.geometries.forEach(visit);
        else if (o.type === 'Polygon' || o.type === 'MultiPolygon') geoms.push(o);
    };
    visit(gj);
    if (!geoms.length) throw new Error('No polygons found in this file.');
    let n = 0;
    const count = c => (typeof c[0] === 'number' ? n++ : c.forEach(count));
    geoms.forEach(g => count(g.coordinates));
    if (n > MAX_VERTICES) throw new Error(`The polygons have ${n.toLocaleString()} vertices; please simplify to under ${MAX_VERTICES.toLocaleString()}.`);
    const lonlat = c => (typeof c[0] === 'number' ? Math.abs(c[0]) <= 180 && Math.abs(c[1]) <= 90 : c.every(lonlat));
    if (!geoms.every(g => lonlat(g.coordinates))) throw new Error('Coordinates must be longitude/latitude (EPSG:4326).');
    return geoms;
}

const empty = () => ({ type: 'FeatureCollection', features: [] });
