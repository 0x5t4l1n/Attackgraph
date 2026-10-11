# Contributing to AttackGraph

## Getting Started

1. Fork and clone the repository
2. Set up the development environment (see [README.md](README.md))
3. Create a feature branch from `main`
4. Make your changes
5. Run the test suite: `python -m pytest backend/tests/ -v`
6. Submit a pull request

---

## AI Contribution Policy

AttackGraph welcomes both human and AI-assisted contributions. We believe in transparency — every pull request must clearly disclose whether AI was used and, if so, which provider and model.

### Why we require this

- Helps reviewers understand the context and nature of changes
- Builds trust in the contribution history
- Lets us learn which tools and models are most effective for security tooling
- Distinguishes AI-generated hypotheses from human-verified findings (critical for a security tool)

### What to disclose in your PR

Every PR must fill in the **Contribution Type** section in the PR template:

| Author type | Fill in |
|------------|---------|
| 👤 **Human only** | Check "Human" — no further fields needed |
| 🤖 **AI only** | Provider, Model, Tool, AI role |
| 🤝 **Human + AI** | Provider, Model, Tool, AI role |

**Provider** — The company that made the model:
> `Anthropic`, `OpenAI`, `Google`, `Meta`, `Mistral`, `Ollama (local)`, etc.

**Model** — The specific model version:
> `Claude Opus 4.6`, `Claude Sonnet 4`, `GPT-4o`, `GPT-4o-mini`, `Gemini 2.0 Flash`, `Llama 3.3 70B`, `Qwen 2.5`, etc.

**Tool** — How you accessed the model:
> `Claude Code`, `GitHub Copilot`, `Cursor`, `ChatGPT`, `Aider`, `OpenRouter`, `Direct API`, etc.

**AI role** — What the AI actually did:
> `Wrote full implementation`, `Suggested fix`, `Code review`, `Pair programming`, `Autocomplete`, `Generated tests`, etc.

### Example PR descriptions

```
## Contribution Type
- [x] 🤝 Human + AI collaboration

| Field    | Value                              |
|----------|------------------------------------|
| Provider | Anthropic                          |
| Model    | Claude Opus 4.6                    |
| Tool     | Claude Code                        |
| AI role  | Wrote implementation, human reviewed and tested |
```

```
## Contribution Type
- [x] 👤 Human

| Field    | Value |
|----------|-------|
| Provider | None  |
| Model    | None  |
| Tool     | None  |
| AI role  | Human only |
```

### What AI-assisted PRs still need

AI-assisted contributions are welcome but must still meet all quality standards:

- All tests must pass
- Code must be reviewed and understood by the human submitting the PR
- Security-sensitive logic must be human-verified (crawler scope, data redaction, injection prevention)
- AI-generated security findings must be marked as `hypothesis` — never `confirmed`
- The human submitting the PR takes responsibility for the code

---

## Development Guidelines

- Write tests for new features and bug fixes
- Follow existing code conventions (React 19, TypeScript strict, FastAPI async)
- Keep security findings as hypotheses — never claim confirmed vulnerabilities from passive analysis
- All crawling must respect scope configuration
- Redact credentials, cookies, and secrets in all stored and displayed data
- AI features must remain optional — the app must work fully with AI disabled
- Never render AI output via `dangerouslySetInnerHTML`

## Code Style

**Backend (Python)**
- Type annotations on all functions
- `async`/`await` throughout (no sync SQLAlchemy calls)
- Pydantic models for all request/response schemas

**Frontend (TypeScript)**
- Strict TypeScript — no `any` unless unavoidable
- CSS classes from `index.css` design system — no inline styles for layout
- Every page must handle loading, empty, and error states

## Testing

```bash
# Backend
python -m pytest backend/tests/ -v

# Frontend
npm run build          # TypeScript + Vite build
npx tsc --noEmit       # Type check only
```

## Reporting Security Issues

See [SECURITY.md](SECURITY.md) for responsible disclosure guidelines.
