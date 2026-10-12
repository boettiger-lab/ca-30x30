/**
 * Data paths ↔ STAC records, shared by the export (browser) and
 * scripts/precompute.mjs (which writes data/sources.json). Mirrors the
 * matching rule of geo-agent's export: a path belongs to the collection whose
 * own asset is its longest prefix.
 */

/** Every s3:// parquet path and https:// .pmtiles URL in a text. */
export function dataPaths(text) {
    return (String(text || '').match(/\b(?:s3|https?):\/\/[^\s'"`)]+/g) || [])
        .filter(p => p.startsWith('s3://') || /\.pmtiles$/.test(p));
}

/**
 * A path as a comparable prefix: https://host/bucket/key and s3://bucket/key
 * are the same object, and the directory a glob sits in ends the part that
 * names the dataset.
 */
export function pathPrefix(path) {
    let p = String(path).replace(/^https?:\/\/[^/]+\//, 's3://');
    const glob = p.search(/[*?[{]/);
    if (glob >= 0) p = p.slice(0, p.lastIndexOf('/', glob));
    return p.replace(/\/+$/, '');
}

/**
 * The datasets behind a set of query texts and map tile URLs, in order of
 * first use: [{ stac, queried, mapped }].
 */
export function matchSources(sources, sqlTexts, tileUrls = []) {
    const entries = (sources?.datasets || []).flatMap(d => d.prefixes.map(p => ({ p, d }))).sort((a, b) => b.p.length - a.p.length);
    const used = new Map();
    const use = (d, how) => {
        if (!used.has(d.id)) used.set(d.id, { stac: d.stac, queried: false, mapped: false });
        used.get(d.id)[how] = true;
    };
    for (const path of sqlTexts.flatMap(dataPaths)) {
        const t = pathPrefix(path);
        const hit = entries.find(({ p }) => t === p || t.startsWith(p + '/'));
        if (hit) use(hit.d, 'queried');
    }
    for (const url of tileUrls) {
        const hit = entries.find(({ p }) => p === url);
        if (hit) use(hit.d, 'mapped');
    }
    return [...used.values()];
}
