# Contributing to AttackGraph

## Getting Started

1. Fork and clone the repository
2. Set up the development environment (see README.md)
3. Create a feature branch from `main`
4. Make your changes
5. Run the test suite: `python -m pytest backend/tests/ -v`
6. Submit a pull request

## Development Guidelines

- Write tests for new features and bug fixes
- Follow existing code conventions
- Keep security findings as hypotheses — never claim confirmed vulnerabilities from passive analysis
- All crawling must respect scope configuration
- Redact credentials and secrets in stored data
- AI features must remain optional

## Reporting Security Issues

See [SECURITY.md](SECURITY.md) for responsible disclosure guidelines.
