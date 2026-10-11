# AttackGraph — Project Documentation

## Overview

AttackGraph is an open-source, local-first web application security testing platform. It maps API endpoints, builds attack graphs, generates AI-powered test plans, and produces security reports — all running on your machine.

- **License:** AGPL-3.0
- **Version:** 1.0.0
- **Website:** [attackgraph.w4nn4d13.tech](https://attackgraph.w4nn4d13.tech)
- **Repository:** [github.com/0x5t4l1n/Attackgraph](https://github.com/0x5t4l1n/Attackgraph)
- **AUR Package:** `attackgraph-bin`

---

## Branch Structure

| Branch | Purpose | Deploy target |
|--------|---------|---------------|
| `main` | Application source code (backend + frontend + Tauri desktop) | GitHub Releases |
| `website` | Public website (static HTML/CSS/JS) | [Netlify](https://attackgraph.w4nn4d13.tech) |

> **Rule:** Never merge `website` into `main`. Never put application code in `website/`. These branches serve completely different purposes.

---

## Project Structure

```
attackgraph/
├── backend/                # FastAPI + SQLAlchemy backend
│   ├── api/                # REST API routes
│   ├── ai_assistant/       # AI integration (Ollama, OpenAI, Gemini, OpenRouter)
│   ├── crawler/            # Web crawler and endpoint discovery
│   ├── graph/              # Attack graph builder
│   ├── reporting/          # HTML/JSON report generation
│   ├── scanner/            # Vulnerability scanner
│   └── tests/              # Backend test suite
├── frontend/               # React 19 + TypeScript + Vite
│   ├── src/
│   │   ├── assets/         # Logo, images
│   │   ├── components/     # Shared UI components
│   │   ├── contexts/       # Theme, Toast, Confirm providers
│   │   ├── pages/          # 13 application pages
│   │   └── services/       # API client
│   └── src-tauri/          # Tauri 2 desktop shell (Rust)
│       ├── src/lib.rs       # Backend lifecycle, window management
│       └── tauri.conf.json  # App config, bundling targets
├── packaging/              # AUR PKGBUILD
├── docs/                   # Documentation
│   ├── DOCUMENTATION.md    # This file
│   └── website-deployment.md # Netlify deployment guide
├── website/                # Public website (website branch only)
│   ├── index.html
│   ├── style.css
│   ├── script.js
│   ├── 404.html
│   └── images/
├── netlify.toml            # Netlify config (website branch only)
├── LICENSE                 # AGPL-3.0
├── CONTRIBUTING.md         # Contribution guidelines + AI disclosure policy
└── README.md               # Project README
```

---

## Tech Stack

### Backend
- **Python 3.14** — FastAPI, SQLAlchemy, aiosqlite
- **Database:** SQLite (XDG-compliant: `~/.local/share/attackgraph/`)
- **AI Providers:** Ollama (local), OpenAI, Gemini, OpenRouter
- **Bundling:** PyInstaller (standalone binary for desktop app)

### Frontend
- **React 19** + TypeScript + Vite
- **Graph Visualization:** @xyflow/react
- **Markdown Rendering:** react-markdown
- **Styling:** CSS custom properties design system (no Tailwind, no CSS modules)
- **Themes:** Dark / Light / System with localStorage persistence

### Desktop App
- **Tauri 2** (Rust) — lightweight native shell
- **Targets:** AppImage, .deb (Linux)
- **Backend:** Bundled PyInstaller binary, auto-started on launch

### Website
- **Plain HTML/CSS/JS** — no build step
- **Hosting:** Netlify (auto-deploys from `website` branch)
- **Custom domain:** `attackgraph.w4nn4d13.tech`
- **Netlify subdomain:** Redirects 301 → custom domain

---

## Running Locally

### Backend
```bash
cd backend
pip install -r requirements.txt
uvicorn api.main:app --reload --port 8000
```

### Frontend (dev server)
```bash
cd frontend
npm install
npm run dev
# → http://localhost:5174
```

### Desktop App (Tauri)
```bash
cd frontend
npm run tauri dev
```

### Website
```bash
cd website
python3 -m http.server 8080
# → http://localhost:8080
```

---

## Installation

### AUR (Arch Linux)
```bash
yay -S attackgraph-bin
```

### GitHub Release
Download the latest AppImage or .deb from [GitHub Releases](https://github.com/0x5t4l1n/Attackgraph/releases).

### From Source
```bash
git clone https://github.com/0x5t4l1n/Attackgraph.git
cd Attackgraph
# See "Running Locally" above
```

---

## Website Deployment

The public website is hosted on Netlify and auto-deploys from the `website` branch.

- **Custom domain:** `attackgraph.w4nn4d13.tech`
- **Netlify URL:** Redirects to custom domain (301)
- **DNS:** CNAME record `attackgraph` → `fluffy-donut-5ea1b7.netlify.app`

For full deployment instructions, see [website-deployment.md](./website-deployment.md).

---

## Key Design Decisions

1. **Local-first** — All data stays on the user's machine. No cloud accounts required.
2. **AI is optional** — The app works fully without any AI provider configured.
3. **No Tailwind** — CSS custom properties design system for full control and smaller bundle.
4. **AGPL-3.0** — Ensures derivative works remain open source.
5. **Tauri over Electron** — Smaller binary, lower memory usage, native performance.
6. **XDG compliance** — Data stored in `~/.local/share/attackgraph/` on Linux.

---

## Contributing

See [CONTRIBUTING.md](../CONTRIBUTING.md) for guidelines, including the AI contribution disclosure policy.

All pull requests must use the PR template which includes an AI contribution disclosure section.
