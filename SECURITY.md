# Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability in AttackGraph itself, please report it responsibly:

1. Do not open a public GitHub issue
2. Email the maintainers with a description of the issue, steps to reproduce, and potential impact
3. Allow reasonable time for a fix before public disclosure

## Responsible Use

AttackGraph is designed for authorized security testing only:

- Only test applications you have explicit permission to assess
- Configure scope limits before crawling
- Do not use AttackGraph to attack systems without authorization
- Respect robots.txt and rate limits
- Do not store or transmit credentials unnecessarily

## Security Model

- Findings are hypotheses requiring manual validation
- The tool does not automatically exploit vulnerabilities
- Scope enforcement prevents crawling outside configured boundaries
- Sensitive data is redacted in reports and storage
- AI features do not transmit data without explicit configuration

## Threat Model

### In Scope
- Imported HTTP traffic may contain malicious content (XSS payloads, injected headers)
- OpenAPI specs may reference malicious URLs
- AI model responses may contain prompt injection attempts

### Mitigations
- All imported data is treated as untrusted
- URLs are validated against scope before any outbound request
- AI output is validated against schemas and never executed as code
- Credentials are redacted before external transmission
