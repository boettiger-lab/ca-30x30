# ca-30x30 — shared static pages

Orphan branch holding static pages for public sharing, served by GitHub Pages from
<https://boettiger-lab.github.io/ca-30x30/>. It shares no history with `main` and is not part
of the app. The live app runs on Kubernetes (namespace `biodiversity`, deployment
`ca-30x30`) and is served from `main` — nothing here affects it.

**There is deliberately no root landing page.** Pages live at unguessable `logs/<uuid>/`
paths so a link can be shared with whoever needs it without the content being discoverable
from the repo's Pages root, which returns 404. `robots.txt` disallows all crawlers and each
page also carries `<meta name="robots" content="noindex, nofollow">`. This is obscurity, not
access control — anyone with the link can read it, and it is a public repo, so the URL is
visible in this branch's history.

## Published pages

| Path | What it is |
|---|---|
| `logs/265007cc-f50f-4f1d-abad-27d7f31e0180/` | **30x30 Commentary Review** — 162 replies from the California 30x30 data agent, each scored by two LLM graders (Opus 5, Sonnet 4.6) for unsupported commentary, per the rubric `suite/rubrics/commentary.md` in `geo-agent-benchmark`. |

Each page directory is self-contained: `index.html` plus its own copies of `fonts.css`
(Google Fonts CSS for IBM Plex Mono / Newsreader, vendored) and `marked.min.js`
(marked v12.0.2, MIT — renders each reply's Markdown client-side).

## Provenance of the commentary review

Derived from a browser-saved copy of a Claude artifact (`share/` on `main`, untracked). The
claude.ai frame-runtime wrapper and the ~740 KB of pre-rendered DOM were stripped, leaving the
artifact's own inline CSS, its 536 KB `<script id="data" type="application/json">` block of
162 scored replies, and its 5 KB render script. Fully client-side — no network calls, no MCP,
no API key.

Stripping the pre-rendered DOM is required, not cosmetic: the render script *appends* to
`#board` and populates `#f-arm`/`#f-q`, so a saved copy double-renders. The `value=""`
placeholder options in those two selects must be kept, or the page loads pre-filtered to a
single arm instead of all 162 replies.

## Adding or updating a page

    git switch gh-pages
    mkdir -p "logs/$(uuidgen)" && cp <built>/* "logs/<uuid>/"
    git add -A && git commit -m "Publish <name>" && git push

GitHub rebuilds on push. Confirm with
`gh api repos/boettiger-lab/ca-30x30/pages/builds/latest --jq .status`.
