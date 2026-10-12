/**
 * Horizontal bar charts in plain SVG (no chart library).
 *
 * spec (from theme.json):
 *   category      row label field
 *   series        [{ field, label, color? }]
 *   stacked       stack series end to end (else grouped)
 *   format        value format (see format.js)
 *   compare       { field, label } — draw a statewide tick per row, matched on `category`
 *   sort          'desc' to sort rows by total
 *   limit         keep the first N rows
 */

import { fmt, fmtTick, escapeHtml } from './format.js';

const PALETTE = ['#2a78d6', '#eb6834', '#1baf7a', '#eda100'];   // validated categorical order
const SVG_NS = 'http://www.w3.org/2000/svg';

export function renderBarChart(container, spec, rows, stateRows) {
    container.innerHTML = '';
    if (!rows || !rows.length) {
        container.innerHTML = '<div class="sub">No data in this area.</div>';
        return;
    }
    const series = spec.series.map((s, i) => ({ ...s, color: s.color || PALETTE[i % PALETTE.length] }));
    if (spec.exclude) {
        rows = (rows || []).filter(r => !Object.entries(spec.exclude).every(([k, v]) => r[k] === v));
    }
    let data = rows.map(r => ({
        cat: r[spec.category],
        vals: series.map(s => Number(r[s.field]) || 0),
        raw: r,
    }));
    if (spec.sort === 'desc') {
        data.sort((a, b) => sum(b.vals) - sum(a.vals));
    }
    if (spec.limit) data = data.slice(0, spec.limit);

    const stateByCat = new Map();
    if (spec.compare && stateRows) {
        for (const r of stateRows) stateByCat.set(String(r[spec.category]), Number(r[spec.compare.field]));
    }

    // legend (always when ≥2 series or a statewide tick)
    if (series.length > 1 || spec.compare) {
        const lg = document.createElement('div');
        lg.className = 'legend-row';
        lg.innerHTML = series.map(s => `<span><i style="background:${s.color}"></i>${escapeHtml(s.label)}</span>`).join('')
            + (spec.compare && stateByCat.size ? `<span><i class="tick" style="background:var(--series-state)"></i>${escapeHtml(spec.compare.label || 'California')}</span>` : '');
        container.appendChild(lg);
    }

    // draw at the container's real pixel width so text stays at its CSS size
    const W = Math.max(300, Math.round(container.clientWidth || 480)), labelW = Math.min(spec.label_width || 150, Math.round(W * (spec.label_width ? 0.45 : 0.34))), valueW = 64, rowH = spec.stacked || series.length === 1 ? 24 : 12 * series.length + 12;
    const barArea = W - labelW - valueW;
    const maxChars = Math.max(8, Math.floor((labelW - 10) / 6.4));   // ~6.4px per char at 11.5px
    const top = 4, axisH = 18;
    const H = top + data.length * rowH + axisH;

    let max = 0;
    for (const d of data) {
        max = Math.max(max, spec.stacked ? sum(d.vals) : Math.max(...d.vals));
        const sv = stateByCat.get(String(d.cat));
        if (Number.isFinite(sv)) max = Math.max(max, sv);
    }
    if (spec.domain_max) max = Math.max(max, spec.domain_max);
    if (max <= 0) max = 1;
    const ticks = niceTicks(max, 4);
    max = ticks[ticks.length - 1];
    const x = v => labelW + (v / max) * barArea;

    const svg = el('svg', { viewBox: `0 0 ${W} ${H}`, role: 'img', 'aria-label': spec.title || '' });

    // gridlines + axis labels
    for (const t of ticks) {
        svg.appendChild(el('line', { x1: x(t), x2: x(t), y1: top, y2: H - axisH, stroke: 'var(--grid)' }));
        const tx = el('text', { x: x(t), y: H - 4, 'text-anchor': 'middle' });
        tx.textContent = fmtTick(t, spec.format);
        svg.appendChild(tx);
    }

    data.forEach((d, i) => {
        const y0 = top + i * rowH;
        const lab = el('text', { x: labelW - 8, y: y0 + rowH / 2 + 4, 'text-anchor': 'end' });
        lab.textContent = truncate(String(d.cat), maxChars);
        if (String(d.cat).length > maxChars) lab.appendChild(titleEl(String(d.cat)));
        svg.appendChild(lab);

        if (spec.stacked) {
            let acc = 0;
            const segs = d.vals.map((v, k) => ({ v, k })).filter(s => s.v > 0);
            segs.forEach((s, j) => {
                const x0 = x(acc), x1 = x(acc + s.v);
                const isLast = j === segs.length - 1;
                const w = Math.max(0, x1 - x0 - (isLast ? 0 : 2));
                svg.appendChild(bar(x0, y0 + 5, w, rowH - 10, series[s.k].color, isLast,
                    `<b>${escapeHtml(d.cat)}</b><br>${escapeHtml(series[s.k].label)}: ${fmt(s.v, spec.format)}`));
                acc += s.v;
            });
            if (spec.show_total !== false) {
                const vt = el('text', { x: x(acc) + 5, y: y0 + rowH / 2 + 4, class: 'val' });
                vt.textContent = fmt(acc, spec.format);
                svg.appendChild(vt);
            } else if (segs.length) {
                // label the first (leading) segment instead of a meaningless 100% total
                const s0 = segs[0];
                const vt = el('text', { x: x(s0.v) + 5, y: y0 + rowH / 2 + 4, class: 'val', 'paint-order': 'stroke', stroke: 'white', 'stroke-width': 3 });
                vt.textContent = fmt(s0.v, spec.format);
                svg.appendChild(vt);
            }
        } else {
            const bh = series.length === 1 ? rowH - 10 : 10;
            d.vals.forEach((v, k) => {
                const yy = series.length === 1 ? y0 + 5 : y0 + 6 + k * 12;
                svg.appendChild(bar(x(0), yy, Math.max(0, x(v) - x(0)), bh, series[k].color, true,
                    `<b>${escapeHtml(d.cat)}</b><br>${escapeHtml(series[k].label)}: ${fmt(v, spec.format)}`));
                const vt = el('text', { x: x(v) + 5, y: yy + bh - 1, class: 'val' });
                vt.textContent = fmt(v, spec.format);
                svg.appendChild(vt);
            });
        }

        const sv = stateByCat.get(String(d.cat));
        if (Number.isFinite(sv)) {
            const t = el('line', {
                x1: x(sv), x2: x(sv), y1: y0 + 2, y2: y0 + rowH - 2,
                stroke: 'var(--series-state)', 'stroke-width': 2,
            });
            hover(t, `<b>${escapeHtml(d.cat)}</b><br>${escapeHtml(spec.compare.label || 'California')}: ${fmt(sv, spec.format)}`);
            svg.appendChild(t);
        }
    });

    // baseline
    svg.appendChild(el('line', { x1: x(0), x2: x(0), y1: top, y2: H - axisH, stroke: 'var(--line-strong)' }));
    container.appendChild(svg);
}

function bar(x, y, w, h, color, roundEnd, tip) {
    // 4px rounded data-end, square at the baseline/neighbour side
    const r = roundEnd ? Math.min(4, w / 2, h / 2) : 0;
    const d = `M${x},${y} h${Math.max(0, w - r)} ${r ? `a${r},${r} 0 0 1 ${r},${r}` : ''} v${h - 2 * r} ${r ? `a${r},${r} 0 0 1 ${-r},${r}` : ''} h${-Math.max(0, w - r)} z`;
    const p = el('path', { d, fill: color });
    hover(p, tip);
    return p;
}

const tooltip = () => document.getElementById('tooltip');
export function hover(node, html) {
    node.addEventListener('mousemove', e => {
        const t = tooltip();
        if (!t) return;
        t.innerHTML = html;
        t.hidden = false;
        t.style.left = Math.min(e.clientX + 12, window.innerWidth - 270) + 'px';
        t.style.top = e.clientY + 12 + 'px';
    });
    node.addEventListener('mouseleave', () => { const t = tooltip(); if (t) t.hidden = true; });
}

function niceTicks(max, n) {
    const raw = max / n;
    const mag = Math.pow(10, Math.floor(Math.log10(raw)));
    const step = [1, 2, 2.5, 5, 10].map(m => m * mag).find(s => s >= raw);
    const out = [];
    for (let v = 0; v <= max + step * 0.999; v += step) out.push(+v.toPrecision(12));
    return out;
}

function el(tag, attrs = {}) {
    const n = document.createElementNS(SVG_NS, tag);
    for (const [k, v] of Object.entries(attrs)) n.setAttribute(k, v);
    return n;
}
function titleEl(text) { const t = el('title'); t.textContent = text; return t; }
const sum = a => a.reduce((s, v) => s + v, 0);
const truncate = (s, n) => (s.length > n ? s.slice(0, n - 1) + '…' : s);
