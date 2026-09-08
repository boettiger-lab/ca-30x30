# ca-30x30 — shared static pages

Published at <https://boettiger-lab.github.io/ca-30x30/>.

This branch is an **orphan branch** holding static pages for public sharing. It shares no
history with `main` and is not part of the app. The live app runs on Kubernetes
(namespace `biodiversity`, deployment `ca-30x30`) and is served from `main` — nothing here
affects it.

## Contents

| Path | What it is |
|---|---|
| `index.html` | **30x30 Commentary Review** — 162 replies from the California 30x30 data agent, each scored by two LLM graders for unsupported commentary (see `suite/rubrics/commentary.md` in `geo-agent-benchmark`). |
| `fonts.css` | Google Fonts CSS (IBM Plex Mono / Newsreader), vendored so the page has one less third-party request. |
| `marked.min.js` | marked v12.0.2, MIT (renders each reply's Markdown client-side). |

## Provenance of `index.html`

Derived from a browser-saved copy of a Claude artifact (`share/` on `main`, untracked). The
claude.ai frame-runtime wrapper and the ~740 KB of pre-rendered DOM were stripped, leaving the
artifact's own inline CSS, its 536 KB `<script id="data" type="application/json">` block of
162 scored replies, and its 5 KB render script. The page is fully client-side — no network
calls, no MCP, no API key.

Stripping the pre-rendered DOM is required, not cosmetic: the render script *appends* to
`#board` and populates `#f-arm`/`#f-q`, so a saved copy double-renders. The `value=""`
placeholder options in those two selects must be kept or the page loads pre-filtered.

## Updating

Rebuild the page from its source, then commit here:

    git switch gh-pages
    cp <new>/index.html .
    git commit -am "Update commentary review" && git push
