/**
 * Minimal MCP client for the duckdb-geo server — one stateless POST per call.
 *
 * Works in the browser and in Node ≥ 18 (global fetch), so the precompute
 * script and the app share exactly the same query path.
 *
 * Every query is wrapped so DuckDB returns a single JSON array (one cell),
 * which sidesteps parsing the server's markdown table output.
 */

let _id = 0;

export class McpQueryClient {
    constructor(url, { timeoutMs = 300000 } = {}) {
        this.url = url;
        this.timeoutMs = timeoutMs;
    }

    async callTool(name, args) {
        const ctrl = new AbortController();
        const timer = setTimeout(() => ctrl.abort(), this.timeoutMs);
        try {
            const res = await fetch(this.url, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json, text/event-stream',
                },
                body: JSON.stringify({
                    jsonrpc: '2.0', id: ++_id, method: 'tools/call',
                    params: { name, arguments: args },
                }),
                signal: ctrl.signal,
            });
            if (!res.ok) throw new Error(`MCP HTTP ${res.status}`);
            const text = await res.text();
            const msg = parseRpc(text);
            if (msg.error) throw new Error(msg.error.message || 'MCP error');
            const out = msg.result?.content?.map(c => c.text).join('\n') ?? '';
            if (msg.result?.isError || /^\s*SQL Error/i.test(out)) throw new Error(out.slice(0, 600));
            return out;
        } finally {
            clearTimeout(timer);
        }
    }

    /** Run SQL and return an array of row objects. */
    async query(sql) {
        const wrapped = `SELECT CAST(to_json(list(__q)) AS VARCHAR) AS __json FROM (\n${sql.trim().replace(/;\s*$/, '')}\n) __q`;
        const text = await this.callTool('query', { sql: wrapped });
        return extractJson(text);
    }
}

function parseRpc(text) {
    // Streamable HTTP may answer with plain JSON or an SSE stream.
    const t = text.trim();
    if (t.startsWith('{')) return JSON.parse(t);
    let last = null;
    for (const line of t.split('\n')) {
        if (line.startsWith('data:')) {
            const m = JSON.parse(line.slice(5));
            if (m.result || m.error) last = m;
        }
    }
    if (!last) throw new Error('Empty MCP response');
    return last;
}

function extractJson(text) {
    const a = text.indexOf('[');
    const b = text.lastIndexOf(']');
    if (a < 0 || b < a) return [];   // zero rows → to_json(list()) is NULL
    return JSON.parse(text.slice(a, b + 1));
}
