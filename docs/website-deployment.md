# AttackGraph Website — Deployment Guide

The public website lives on the `website` branch in the `website/` directory.
`main` contains the application code and is **never modified** by website changes.

---

## Branch structure

| Branch | Contents | Deploy target |
|--------|----------|---------------|
| `main` | Application source code | — |
| `website` | All of `main` + `website/` site + `netlify.toml` | Netlify production |

---

## Run locally

No build step required. Use any static file server:

```bash
# Python (built-in)
cd website
python3 -m http.server 8080
# → open http://localhost:8080

# Node.js (npx)
npx serve website

# VS Code Live Server extension
# Right-click website/index.html → Open with Live Server
```

---

## Build

There is no build step. The site is plain HTML, CSS, and JavaScript.
Netlify serves the `website/` directory directly.

---

## Connect to Netlify

### Option A — Netlify UI (recommended for first deploy)

1. Push the `website` branch to GitHub (see below).
2. Go to [netlify.com](https://www.netlify.com) → **Add new site → Import an existing project**.
3. Connect your GitHub account and select `0x5t4l1n/Attackgraph`.
4. In **Build settings**:
   - **Branch to deploy:** `website`
   - **Build command:** *(leave empty)*
   - **Publish directory:** `website`
5. Click **Deploy site**.

Netlify reads `netlify.toml` automatically — no manual settings needed after step 4.

### Option B — Netlify CLI

```bash
npm install -g netlify-cli
netlify login
netlify init
# Select: Link to existing site or create new
# Set: publish directory = website, branch = website
netlify deploy --prod --dir website
```

---

## Push the website branch

```bash
# Switch to website branch
git checkout website

# Make changes to website/ files
# e.g. edit website/index.html

# Commit and push
git add website/ netlify.toml docs/website-deployment.md
git commit -m "website: update landing page content"
git push origin website
```

Netlify auto-deploys when `website` branch receives a push.

---

## Update safely without touching main

```bash
# Always work from the website branch
git checkout website

# Pull latest main changes into website (to keep app code current)
git merge main --no-edit

# Make website/ changes
# ... edit website/index.html, website/style.css, etc.

git add website/
git commit -m "website: ..."
git push origin website
```

---

## Update the website for a new app release

When a new app version is released on `main`:

1. Merge `main` into `website`:
   ```bash
   git checkout website && git merge main
   ```
2. Update version numbers in `website/index.html` (hero stats, download links, install tabs).
3. Commit and push `website`.

---

## File structure

```
website/
├── index.html          ← Landing page
├── 404.html            ← Custom 404 error page
├── style.css           ← All styles
├── script.js           ← Mobile menu, tabs, scroll animations
├── favicon.ico         ← Browser tab icon
└── images/
    ├── logo.png        ← 128×128 AttackGraph logo
    └── attackgraph-banner.png  ← Hero banner (from docs/assets/)

netlify.toml            ← Netlify build + redirect + header config
docs/
└── website-deployment.md  ← This file
```

---

## Netlify settings reference

| Setting | Value |
|---------|-------|
| Branch | `website` |
| Build command | *(none)* |
| Publish directory | `website` |
| Node version | 20 (set in `netlify.toml`) |
| Custom 404 | `website/404.html` |

Security headers, cache rules, and the 404 redirect are all set in `netlify.toml`.

---

## What not to do

- **Do not merge `website` into `main`** — the website has no business being in the application branch.
- **Do not add application code to `website/`** — keep website files separate from app source.
- **Do not put API keys or secrets in website files** — the site is public and static.
- **Do not hardcode private targets, user data, or internal IP addresses** in site content.
