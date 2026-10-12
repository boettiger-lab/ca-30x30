/** Number formatting by named format (as used in theme.json). */

const nf0 = new Intl.NumberFormat('en-US', { maximumFractionDigits: 0 });
const nf1 = new Intl.NumberFormat('en-US', { maximumFractionDigits: 1 });
const compact = new Intl.NumberFormat('en-US', { notation: 'compact', maximumFractionDigits: 1 });

export function fmt(value, format = 'num') {
    if (value === null || value === undefined || value === '') return '—';
    if (format === 'text') return String(value);
    if (Number.isNaN(Number(value))) return '—';
    const v = Number(value);
    switch (format) {
        case 'int': return nf0.format(v);
        case 'compact': return Math.abs(v) >= 1e4 ? compact.format(v) : nf0.format(v);
        case 'usd': return '$' + (Math.abs(v) >= 1e4 ? compact.format(v) : nf0.format(v));
        case 'pct': return pct(v * 100);            // 0–1 fraction
        case 'pct100': return pct(v);               // already 0–100
        case 'acres': return (Math.abs(v) >= 1e5 ? compact.format(v) : nf0.format(v)) + ' ac';
        case 'num1': return nf1.format(v);
        case 'per1k': return nf1.format(v);
        case 'degC': return (v > 0 ? '+' : '') + nf1.format(v) + ' °C';   // a change
        case 'meters': return v >= 1000 ? nf1.format(v / 1000) + ' km' : nf0.format(Math.round(v / 10) * 10) + ' m';
        case 'text': return String(value);
        case 'tempC': return nf1.format(v) + ' °C';                         // a level
        default: return Math.abs(v) >= 1e5 ? compact.format(v) : nf1.format(v);
    }
}

function pct(p) {
    if (p !== 0 && Math.abs(p) < 0.1) return '<0.1%';
    return nf1.format(p) + '%';   // one decimal throughout: comparisons with the report are often within a point
}

/** Short axis-tick formatting. */
export function fmtTick(value, format) {
    if (format === 'usd') return '$' + compact.format(value);
    if (format === 'pct') return nf0.format(value * 100) + '%';
    if (format === 'pct100') return nf0.format(value) + '%';
    if (format === 'degC' || format === 'tempC') return nf1.format(value) + '°';
    return compact.format(value);
}

export function escapeHtml(s) {
    return String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}
