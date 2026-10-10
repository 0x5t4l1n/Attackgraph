from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class ReportData:
    project_name: str
    target_url: str
    scope: dict
    crawl_summary: dict
    endpoints: list[dict]
    graph_statistics: dict
    findings: list[dict]
    attack_paths: list[dict]
    test_plans: list[dict]
    generated_at: str = ""

    def __post_init__(self):
        if not self.generated_at:
            self.generated_at = datetime.now(timezone.utc).isoformat()


class ReportGenerator:
    def generate_json(self, data: ReportData) -> str:
        return json.dumps(self._to_dict(data), indent=2, default=str)

    def generate_markdown(self, data: ReportData) -> str:
        lines = [
            "# AttackGraph Security Assessment Report",
            "",
            f"**Target:** {data.target_url}",
            f"**Project:** {data.project_name}",
            f"**Generated:** {data.generated_at}",
            "",
            "---",
            "",
            "## 1. Scope",
            "",
            f"- **Allowed Hosts:** {', '.join(data.scope.get('allowed_hosts', []))}",
            f"- **Allowed Schemes:** {', '.join(data.scope.get('allowed_schemes', []))}",
            f"- **Excluded Paths:** {', '.join(data.scope.get('exclude_paths', [])) or 'None'}",
            "",
            "## 2. Discovery Summary",
            "",
        ]
        cs = data.crawl_summary
        lines.extend([
            f"- **Pages Crawled:** {cs.get('pages_crawled', 0)}",
            f"- **Pages Discovered:** {cs.get('pages_discovered', 0)}",
            f"- **Total Endpoints:** {len(data.endpoints)}",
            f"- **Errors:** {cs.get('errors', 0)}",
            "",
            "## 3. Endpoint Inventory",
            "",
            "| Method | Path | Status | Source |",
            "|--------|------|--------|--------|",
        ])
        for ep in data.endpoints[:100]:
            lines.append(
                f"| {ep.get('method', 'GET')} | {ep.get('url', '')} "
                f"| {ep.get('status_code', '')} | {ep.get('discovery_source', '')} |"
            )
        if len(data.endpoints) > 100:
            lines.append(f"\n*...and {len(data.endpoints) - 100} more endpoints*")

        lines.extend([
            "",
            "## 4. Application Graph",
            "",
            f"- **Total Nodes:** {data.graph_statistics.get('total_nodes', 0)}",
            f"- **Total Edges:** {data.graph_statistics.get('total_edges', 0)}",
            f"- **Observed Nodes:** {data.graph_statistics.get('observed_nodes', 0)}",
            f"- **Inferred Nodes:** {data.graph_statistics.get('inferred_nodes', 0)}",
            f"- **Components:** {data.graph_statistics.get('components', 0)}",
            "",
            "## 5. Security Findings",
            "",
        ])

        if not data.findings:
            lines.append("No security findings were generated.")
        else:
            for i, f in enumerate(data.findings, 1):
                status_badge = f.get("validation_status", "hypothesis").upper()
                confidence_val = f.get("confidence", 0)
                lines.extend([
                    f"### {i}. {f.get('title', 'Untitled')}",
                    "",
                    f"- **Severity:** {f.get('severity', 'info')} | "
                    f"**Confidence:** {confidence_val:.0%} | **Status:** {status_badge}",
                    f"- **Detection Rule:** {f.get('detection_rule', '')}",
                    f"- **Affected Endpoints:** {', '.join(f.get('affected_endpoints', [])[:5])}",
                    "",
                    f"**Description:** {f.get('description', '')}",
                    "",
                    f"**Reasoning:** {f.get('reasoning', '')}",
                    "",
                    f"**Assumptions:** {', '.join(f.get('assumptions', []))}",
                    "",
                    f"**Remediation:** {f.get('remediation', '')}",
                    "",
                ])

        lines.extend([
            "## 6. Candidate Attack Paths",
            "",
        ])
        if not data.attack_paths:
            lines.append("No candidate attack paths were generated.")
        else:
            for i, p in enumerate(data.attack_paths, 1):
                conf = p.get("confidence", 0)
                score = p.get("priority_score", 0)
                lines.extend([
                    f"### Path {i}: {p.get('entry_point', '')} -> {p.get('target_operation', '')}",
                    "",
                    f"- **Confidence:** {conf:.0%} | **Priority:** {score:.2f}",
                    f"- **Impact:** {p.get('potential_impact', '')}",
                    f"- **Assumptions:** {', '.join(p.get('unverified_assumptions', []))}",
                    "",
                ])

        lines.extend([
            "## 7. Test Plans",
            "",
        ])
        if not data.test_plans:
            lines.append("No test plans were generated.")
        else:
            for i, tp in enumerate(data.test_plans, 1):
                lines.extend([
                    f"### Test {i}: {tp.get('hypothesis', '')}",
                    "",
                    "**Procedure:**",
                    "```",
                    tp.get("test_procedure", ""),
                    "```",
                    "",
                    f"**Expected:** {tp.get('expected_secure_behavior', '')}",
                    "",
                ])

        lines.extend([
            "",
            "---",
            "",
            "*Report generated by AttackGraph v0.1.0. Findings are hypotheses "
            "unless explicitly validated. This report does not constitute a "
            "complete security assessment.*",
        ])
        return "\n".join(lines)

    def generate_html(self, data: ReportData) -> str:
        md_content = self.generate_markdown(data)
        html_safe = (
            md_content.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )
        return (
            "<!DOCTYPE html>\n"
            "<html lang=\"en\">\n"
            "<head>\n"
            "<meta charset=\"UTF-8\">\n"
            '<meta name="viewport" content="width=device-width, initial-scale=1.0">\n'
            f"<title>AttackGraph Report - {data.project_name}</title>\n"
            "<style>\n"
            "body { font-family: 'Inter', -apple-system, sans-serif; background: #0f1117; "
            "color: #e1e4e8; max-width: 960px; margin: 0 auto; padding: 2rem; line-height: 1.6; }\n"
            "h1 { color: #58a6ff; border-bottom: 1px solid #30363d; padding-bottom: 0.5rem; }\n"
            "h2 { color: #79c0ff; margin-top: 2rem; }\n"
            "h3 { color: #d2a8ff; }\n"
            "table { border-collapse: collapse; width: 100%; margin: 1rem 0; }\n"
            "th, td { border: 1px solid #30363d; padding: 0.5rem; text-align: left; }\n"
            "th { background: #161b22; }\n"
            "code, pre { background: #161b22; padding: 0.2rem 0.4rem; border-radius: 4px; "
            "font-size: 0.9rem; }\n"
            "pre { padding: 1rem; overflow-x: auto; }\n"
            "a { color: #58a6ff; }\n"
            "hr { border: none; border-top: 1px solid #30363d; margin: 2rem 0; }\n"
            "</style>\n"
            "</head>\n"
            "<body>\n"
            f'<pre style="white-space: pre-wrap;">{html_safe}</pre>\n'
            "</body>\n"
            "</html>"
        )

    def _to_dict(self, data: ReportData) -> dict:
        return {
            "project_name": data.project_name,
            "target_url": data.target_url,
            "scope": data.scope,
            "crawl_summary": data.crawl_summary,
            "endpoints": data.endpoints,
            "graph_statistics": data.graph_statistics,
            "findings": data.findings,
            "attack_paths": data.attack_paths,
            "test_plans": data.test_plans,
            "generated_at": data.generated_at,
            "disclaimer": "Findings are hypotheses unless explicitly validated.",
        }
