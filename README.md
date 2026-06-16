# geo-agent-template

A GitHub template for deploying an AI-powered interactive map app.
Users describe in plain language what datasets to show; the app uses an LLM agent with map tools and SQL access to visualize and analyze cloud-native geospatial data.

**No JavaScript to write.** The core modules (map, chat, agent, tools) are loaded from CDN. You configure which data to show via three small files.

**Full documentation:** [boettiger-lab.github.io/geo-agent/docs](https://boettiger-lab.github.io/geo-agent/docs/)

## Repository structure

```
index.html          ← HTML shell — loads core JS/CSS from CDN
layers-input.json   ← which STAC collections to show + LLM settings
system-prompt.md    ← LLM system prompt (customize per app)
k8s/                ← Kubernetes deployment manifests (optional)
```

## Quick start

### 1. Create your repo from this template

Click **"Use this template"** on GitHub → **"Create a new repository"**.

### 2. Choose your datasets

Browse the available STAC catalog:

```
https://radiantearth.github.io/stac-browser/#/external/s3-west.nrp-nautilus.io/public-data/stac/catalog.json
```

Edit `layers-input.json` — set your collections and adjust the default map view.
See the [configuration reference](https://boettiger-lab.github.io/geo-agent/docs/guide/configuration) for all fields.

### 3. Edit `system-prompt.md`

Describe the domain, what users are likely to ask, and include SQL examples relevant to your datasets.

### 4. Deploy

#### Option A: GitHub Pages (no server needed)

The `llm` block in `layers-input.json` is already enabled. Each visitor enters their own API key (e.g. from [OpenRouter](https://openrouter.ai)) in the in-app settings panel — keys are stored in the browser only, never on the server.

1. Enable GitHub Pages in your repo: Settings → Pages → Source → **GitHub Actions**
2. Add `.github/workflows/gh-pages.yml`:

```yaml
name: Deploy to GitHub Pages
on:
  push:
    branches: [main]
permissions:
  contents: read
  pages: write
  id-token: write
jobs:
  deploy:
    runs-on: ubuntu-latest
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    steps:
      - uses: actions/checkout@v4
      - uses: actions/configure-pages@v5
      - uses: actions/upload-pages-artifact@v3
        with:
          path: .
      - id: deployment
        uses: actions/deploy-pages@v4
```

3. Push — the workflow deploys automatically on changes to `main`.

#### Option B: Kubernetes

API keys are injected server-side via a ConfigMap + Kubernetes secrets — no user-facing key entry.

1. Delete the `llm` block from `layers-input.json` (the server-injected `config.json` takes precedence anyway)
2. Replace the git clone URL in `k8s/deployment.yaml` with your repo URL
3. Replace the slug `calenviroscreen` throughout `k8s/` with your app name
4. Set your hostname in `k8s/ingress.yaml`
5. Create the required secret:

```bash
kubectl create secret generic llm-proxy-secrets \
  --from-literal=proxy-key=YOUR_PROXY_KEY
```

6. Deploy:

```bash
kubectl apply -f k8s/
kubectl rollout status deployment/my-app
```

After pushing changes, redeploy: `kubectl rollout restart deployment/my-app`

See the [deployment guide](https://boettiger-lab.github.io/geo-agent/docs/guide/deployment) for full details on all options including Hugging Face Spaces.

## Local development

```bash
python -m http.server 8000
# Open http://localhost:8000 — enter your API key in the settings panel
```

## More resources

- [Configuration reference](https://boettiger-lab.github.io/geo-agent/docs/guide/configuration) — all `layers-input.json` fields with examples
- [Deployment guide](https://boettiger-lab.github.io/geo-agent/docs/guide/deployment) — GitHub Pages, Hugging Face Spaces, Kubernetes
- [Core library](https://github.com/boettiger-lab/geo-agent) — source code for the map, chat, and agent modules
