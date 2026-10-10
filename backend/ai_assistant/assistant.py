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

    async def summarize_graph(self, graph_data: dict) -> str:
        if not self.enabled or not self.client:
            return "AI is disabled. Enable it in settings to get AI-powered summaries."

        safe_data = self.redact_sensitive(json.dumps(graph_data.get("statistics", {})))
        nodes_summary: list[str] = []
        for n in graph_data.get("nodes", [])[:50]:
            nodes_summary.append(f"- {n.get('type')}: {n.get('label')}")

        prompt = (
            "Summarize this web application's structure based on the following graph data.\n"
            "Focus on: main entry points, sensitive operations, authentication mechanisms, "
            "and potential security-relevant areas.\n\n"
            f"Statistics: {safe_data}\n\n"
            f"Sample nodes ({len(graph_data.get('nodes', []))} total):\n"
            + "\n".join(nodes_summary[:30])
            + "\n\nProvide a concise 2-3 paragraph summary."
        )

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
