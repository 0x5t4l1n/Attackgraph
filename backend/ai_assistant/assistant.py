from __future__ import annotations

import json
import re

from backend.config import settings

SENSITIVE_PATTERNS = re.compile(
    r"("
    r"eyJ[A-Za-z0-9_-]+\.eyJ[A-Za-z0-9_-]+"
    r"|Bearer\s+\S+"
    r"|password[\"']?\s*[:=]\s*[\"']?\S+"
    r"|api[_-]?key[\"']?\s*[:=]\s*[\"']?\S+"
    r"|secret[\"']?\s*[:=]\s*[\"']?\S+"
    r"|token[\"']?\s*[:=]\s*[\"']?\S+"
    r")",
    re.I,
)


class AIAssistant:
    def __init__(self):
        self.enabled = settings.ai.enabled
        self.client = None
        if self.enabled:
            try:
                from openai import AsyncOpenAI

                self.client = AsyncOpenAI(
                    base_url=settings.ai.api_base,
                    api_key=settings.ai.api_key or "not-needed",
                )
            except ImportError:
                self.enabled = False

    def redact_sensitive(self, text: str) -> str:
        return SENSITIVE_PATTERNS.sub("[REDACTED]", text)

    def _build_graph_context(self, graph_data: dict) -> str:
        nodes = graph_data.get("nodes", [])
        edges = graph_data.get("edges", [])
        findings = graph_data.get("findings", [])

        if not nodes:
            return "NO_DATA"

        lines = [f"Nodes: {len(nodes)}, Edges: {len(edges)}"]

        # Deduplicated endpoint list
        seen: set[str] = set()
        endpoints = []
        for n in nodes[:30]:
            label = n.get("label", "")
            method = n.get("method", "")
            observed = n.get("observed", True)
            key = f"{method} {label}".strip()
            if key not in seen:
                seen.add(key)
                obs = "obs" if observed else "inf"
                entry = f"`{key}` ({obs})" if method else f"`{label}` ({obs})"
                endpoints.append(entry)

        lines.append("Endpoints: " + ", ".join(endpoints[:20]))

        if findings:
            f_list = [f"[{f.get('severity','?').upper()}] {f.get('title','')}" for f in findings[:8]]
            lines.append("Findings: " + "; ".join(f_list))

        return "\n".join(lines)

    async def summarize_graph(self, graph_data: dict) -> str:
        if not self.enabled or not self.client:
            return "AI is disabled. Enable it in settings to get AI-powered summaries."

        context = self._build_graph_context(graph_data)

        if context == "NO_DATA":
            return (
                "## No Graph Data Available\n\n"
                "The application graph is empty. Run a crawl or import traffic first, "
                "then rebuild the graph before requesting an AI summary."
            )

        prompt = f"""You are a security researcher. Summarize this web application's attack surface based ONLY on the data below. Use Markdown. Use inline code for paths. Note what is observed vs inferred. State when authentication was not verified.

Data:
{context}

Write sections: ## Entry Points, ## Security Observations, ## Potential Risks, ## Limitations. Be concise."""

        try:
            response = await self.client.chat.completions.create(
                model=settings.ai.model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a security researcher analyzing a web application's "
                            "structure. Be factual and precise. Distinguish observations "
                            "from hypotheses."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                max_tokens=settings.ai.max_tokens,
                temperature=settings.ai.temperature,
            )
            return response.choices[0].message.content or "No summary generated."
        except Exception as e:
            return f"AI summary failed: {e!s}"

    async def explain_finding(self, finding: dict) -> str:
        if not self.enabled or not self.client:
            return "AI is disabled."

        safe_finding = self.redact_sensitive(json.dumps(finding, default=str))
        prompt = (
            "Explain this security finding in clear language for a penetration tester:\n\n"
            f"{safe_finding}\n\n"
            "Include: what was detected, why it matters, how to verify it, "
            "and recommended remediation."
        )

        try:
            response = await self.client.chat.completions.create(
                model=settings.ai.model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are an application security expert. Be precise about "
                            "what is confirmed vs hypothetical."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                max_tokens=settings.ai.max_tokens,
                temperature=settings.ai.temperature,
            )
            return response.choices[0].message.content or "No explanation generated."
        except Exception as e:
            return f"AI explanation failed: {e!s}"

    async def suggest_tests(self, attack_path: dict) -> str:
        if not self.enabled or not self.client:
            return "AI is disabled."

        safe_path = self.redact_sensitive(json.dumps(attack_path, default=str))
        prompt = (
            "Given this candidate attack path, suggest specific security tests:\n\n"
            f"{safe_path}\n\n"
            "For each test, specify: hypothesis, exact steps, expected secure "
            "vs insecure outcomes."
        )

        try:
            response = await self.client.chat.completions.create(
                model=settings.ai.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a penetration testing expert. Provide actionable test procedures.",
                    },
                    {"role": "user", "content": prompt},
                ],
                max_tokens=settings.ai.max_tokens,
                temperature=settings.ai.temperature,
            )
            return response.choices[0].message.content or "No suggestions generated."
        except Exception as e:
            return f"AI suggestion failed: {e!s}"
