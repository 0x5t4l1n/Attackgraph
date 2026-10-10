# AttackGraph

**Map the application. Discover the attack paths. Validate the risks.**

AttackGraph is an open-source security research platform that maps web applications using active crawling, Burp Suite HTTP traffic, and API specifications, then generates evidence-backed security hypotheses and prioritized testing plans.

## Features

- **Active Web Crawler** — Configurable async crawler with scope enforcement, robots.txt compliance, form discovery, and JavaScript URL extraction
- **Burp Suite Import** — Parse Burp XML exports with full request/response analysis, cookie extraction, and sensitive data redaction
- **OpenAPI Import** — Support for OpenAPI 2.0/3.0/3.1 specs with endpoint comparison against observed traffic
- **Application Graph** — NetworkX-powered directed graph with typed nodes (endpoints, hosts, parameters, auth mechanisms) and evidence-tracked edges
- **Security Analysis** — 10 deterministic detection rules generating hypotheses (not false confirmations) for IDOR, auth bypass, mass assignment, debug exposure, and more
- **Attack-Path Engine** — Automated discovery and prioritization of candidate attack paths through the application graph
- **Test Planner** — Structured test plans with specific procedures, expected outcomes, and evidence requirements
- **Report Generation** — JSON, Markdown, and HTML reports with redaction and clear distinction between confirmed and hypothetical findings
- **Optional AI Assistant** — OpenAI-compatible API integration for graph summarization and test suggestions (all core features work without AI)
- **Professional Dashboard** — React-based dark-themed UI with interactive graph visualization, filtering, and evidence navigation

## Quick Start

### Prerequisites

- Python 3.12+
- Node.js 20+
- pip and npm

### Backend Setup

```bash
cd attackgraph
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt

# Start the API server
uvicorn backend.api.main:app --host 0.0.0.0 --port 8000
```

### Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173 in your browser.

### Run Tests

```bash
source .venv/bin/activate
python -m pytest backend/tests/ -v
```

### Run the Vulnerable Test Application

```bash
source .venv/bin/activate
uvicorn backend.tests.test_app.app:app --host 127.0.0.1 --port 9000
```

This starts a deliberately vulnerable application on localhost:9000 for testing AttackGraph's detection capabilities. **Do not expose this to untrusted networks.**

## Usage

1. **Create a Project** — Define your target URL and allowed scope
2. **Discover Endpoints** — Crawl the target, import Burp traffic, or upload an OpenAPI spec
3. **Build the Graph** — Merge all observations into a unified application graph
4. **Run Analysis** — Generate security findings and candidate attack paths
5. **Review Test Plans** — Get structured testing procedures for each hypothesis
6. **Export Reports** — Generate JSON, Markdown, or HTML reports

## Architecture

```
backend/
  api/           — FastAPI REST endpoints
  crawler/       — Async HTTP crawler with scope enforcement
  burp_import/   — Burp Suite XML parser and redaction
  openapi_import/— OpenAPI 2/3 parser and spec comparator
  graph_engine/  — NetworkX graph with typed nodes/edges
  security_rules/— 10 deterministic detection rules
  attack_paths/  — Attack path analysis and prioritization
  validation/    — Test plan generation
  ai_assistant/  — Optional AI integration
  reporting/     — JSON/Markdown/HTML report generation
  storage/       — SQLAlchemy models, async SQLite
  tests/         — pytest suite with fixtures and vulnerable test app

frontend/
  src/pages/     — Dashboard pages
  src/components/— React components
  src/services/  — API client
```

## Security Model

- **Hypotheses, not confirmations** — All findings are clearly labeled as hypotheses, unvalidated, or confirmed. Passive analysis cannot prove exploitability.
- **Scope enforcement** — Every outbound request is validated against the configured scope. Redirects cannot escape allowed hosts.
- **No automatic exploitation** — The tool discovers and suggests; it never automatically submits forms, bypasses auth, or executes destructive operations.
- **Credential redaction** — Sensitive headers and body fields are redacted before storage and reporting.
- **AI isolation** — AI features are optional. No data is sent to external models without explicit configuration. Prompts are sanitized against injection.
- **Private network protection** — Crawling to localhost, internal IPs, and link-local addresses is blocked by default.

## Known Limitations

- JavaScript-heavy SPAs may require Playwright-based crawling (optional feature)
- Browser automation is not included in the default crawl mode
- AI features require an OpenAI-compatible API endpoint
- SQLite is suitable for single-user research; PostgreSQL migration is not yet implemented
- Burp import supports XML format only (not Burp project files)
- OpenAPI $ref resolution is single-level (no recursive references)

## License

MIT License. See [LICENSE](LICENSE).

## Disclaimer

AttackGraph is a security research tool. Only use it against applications you are authorized to test. The developers are not responsible for misuse. Findings are hypotheses that require manual validation — do not treat automated output as confirmed vulnerabilities.
