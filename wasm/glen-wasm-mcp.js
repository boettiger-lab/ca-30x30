/**
 * GLEN's MCP client, connected to geo-query-wasm in a Web Worker rather than
 * to geo-query over HTTP.
 *
 * The browser copy of this app (wasm/, built by scripts/build-wasm-copy.py)
 * has no server: its import map loads this module in place of GLEN's
 * app/mcp-client.js. The class keeps GLEN's MCPClient for everything but the
 * connection, which starts the worker and speaks MCP to it over postMessage.
 * The worker runs geo-query's tools on DuckDB-wasm and reads the data from
 * source.coop.
 *
 * Hex tile layers need two more things that GLEN does not do yet
 * (SchmidtDSE/glen#445): MapLibre must fetch `geoquerywasm:` tile URLs through
 * the worker, and the `fetch` that reads a tileset's metadata.json must too.
 * Both are set up here, once, when GLEN loads this module.
 */

import { MCPClient as HttpMCPClient } from 'glen/mcp-client.js';
import { Client } from 'glen/vendor/mcp-sdk.js';
import { PostMessageTransport } from 'geo-query-wasm/transport.js';
import { addHexTileProtocol, hexFetch } from 'geo-query-wasm/hex-protocol.js';

// The worker's configuration, written into index.html by the build script.
const config = JSON.parse(document.getElementById('geo-query-wasm-config').textContent);
config.catalog = new URL(config.catalog, document.baseURI).href;
const workerUrl = new URL('worker.js', import.meta.url);
workerUrl.searchParams.set('config', JSON.stringify(config));

// The SDK client connected to the running worker, for the hex tile hooks.
let current = null;
let worker = null;
const live = { get client() { return current; } };

if (globalThis.maplibregl) addHexTileProtocol(globalThis.maplibregl, live);
globalThis.fetch = hexFetch(live, globalThis.fetch.bind(globalThis));

export class MCPClient extends HttpMCPClient {
    async _doConnect() {
        try {
            // A reconnect starts a fresh worker: the MCP server in the old
            // one is bound to the old transport.
            worker?.terminate();
            worker = new Worker(workerUrl, { type: 'module' });
            const transport = new PostMessageTransport(worker);
            this.client = new Client(
                { name: 'geo-chat-client', version: '2.0.0' },
                { capabilities: {} }
            );
            await this.client.connect(transport);
            const response = await this.client.listTools();
            this.tools = response.tools || [];
            current = this.client;
            this.connected = true;
            this.reconnectAttempts = 0;
            console.log('[MCP] Connected to geo-query-wasm. Tools:', this.tools.map(t => t.name));
        } catch (error) {
            this.connected = false;
            this.client = null;
            console.error('[MCP] geo-query-wasm failed to start:', error.message);
            throw error;
        }
    }
}
