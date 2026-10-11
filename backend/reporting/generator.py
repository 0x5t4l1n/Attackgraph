from __future__ import annotations

import html
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


def _h(value: object) -> str:
    """HTML-escape a value safely."""
    return html.escape(str(value) if value is not None else "")


_SEVERITY_COLORS = {
    "critical": "#dc2626",
    "high": "#f85149",
    "medium": "#d29922",
    "low": "#3fb950",
    "info": "#58a6ff",
}

_SEVERITY_LABELS = {
    "critical": "CRITICAL",
    "high": "HIGH",
    "medium": "MEDIUM",
    "low": "LOW",
    "info": "INFO",
}

_STATUS_LABELS = {
    "hypothesis": "Hypothesis",
    "unvalidated": "Unvalidated",
    "confirmed": "Confirmed",
    "false_positive": "False Positive",
    "inconclusive": "Inconclusive",
}


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

    def generate_html(self, data: ReportData) -> str:  # noqa: C901
        gen_date = data.generated_at
        try:
            dt = datetime.fromisoformat(gen_date)
            gen_date = dt.strftime("%B %d, %Y %H:%M UTC")
        except Exception:
            pass

        # ── severity counts for executive summary ────────────────────────────
        sev_counts: dict[str, int] = {}
        for f in data.findings:
            sev = f.get("severity", "info").lower()
            sev_counts[sev] = sev_counts.get(sev, 0) + 1

        total_findings = len(data.findings)
        total_paths = len(data.attack_paths)
        total_plans = len(data.test_plans)
        total_eps = len(data.endpoints)

        def severity_badge(severity: str) -> str:
            sev = severity.lower()
            color = _SEVERITY_COLORS.get(sev, "#8893a4")
            label = _SEVERITY_LABELS.get(sev, severity.upper())
            return (
                f'<span class="badge sev-{_h(sev)}" '
                f'style="background:{color};color:#fff;padding:2px 8px;border-radius:3px;'
                f'font-size:11px;font-weight:700;letter-spacing:.05em">{_h(label)}</span>'
            )

        def status_badge(status: str) -> str:
            label = _STATUS_LABELS.get(status, status.replace("_", " ").title())
            colors = {
                "hypothesis": "#505868",
                "unvalidated": "#d29922",
                "confirmed": "#f85149",
                "false_positive": "#3fb950",
                "inconclusive": "#8893a4",
            }
            color = colors.get(status, "#505868")
            return (
                f'<span style="background:{color};color:#fff;padding:2px 6px;'
                f'border-radius:3px;font-size:11px;font-weight:600">{_h(label)}</span>'
            )

        # ── TOC and section IDs ───────────────────────────────────────────────
        sections = [
            ("executive-summary", "Executive Summary"),
            ("scope", "Assessment Scope"),
            ("discovery", "Discovery Summary"),
            ("endpoints", "Endpoint Inventory"),
            ("graph", "Application Graph"),
            ("findings", "Security Findings"),
            ("attack-paths", "Candidate Attack Paths"),
            ("test-plans", "Security Test Plans"),
            ("limitations", "Limitations and Notes"),
        ]

        toc_items = "".join(
            f'<li><a href="#{sid}">{_h(title)}</a></li>'
            for sid, title in sections
        )

        # ── Findings HTML ─────────────────────────────────────────────────────
        if not data.findings:
            findings_html = '<p class="no-data">No security findings were generated for this project.</p>'
        else:
            finding_blocks = []
            for i, f in enumerate(data.findings, 1):
                conf = f.get("confidence", 0)
                sev = f.get("severity", "info").lower()
                border_color = _SEVERITY_COLORS.get(sev, "#8893a4")
                eps = f.get("affected_endpoints", [])[:5]
                eps_html = ", ".join(f'<code>{_h(e)}</code>' for e in eps) or "—"
                assumptions = f.get("assumptions", [])
                assumption_items = "".join(
                    f"<li>{_h(a)}</li>" for a in assumptions
                ) if assumptions else "<li>None stated</li>"

                repro = f.get("reproduction_steps", "")
                repro_html = f'<pre><code>{_h(repro)}</code></pre>' if repro else "<p>Not provided.</p>"

                finding_blocks.append(f"""
<div class="finding" id="finding-{i}" style="border-left:4px solid {border_color};margin-bottom:2rem;padding:1.25rem 1.5rem;background:#f8fafc;page-break-inside:avoid">
  <div style="display:flex;align-items:center;gap:.75rem;margin-bottom:.75rem;flex-wrap:wrap">
    <h3 style="margin:0;font-size:1.05rem;color:#111827">{i}. {_h(f.get("title","Untitled"))}</h3>
    {severity_badge(sev)}
    {status_badge(f.get("validation_status","hypothesis"))}
    <span style="color:#6b7280;font-size:.85rem;margin-left:auto">Confidence: {conf:.0%}</span>
  </div>
  <table class="meta-table">
    <tr><th>Detection Rule</th><td><code>{_h(f.get("detection_rule",""))}</code></td></tr>
    <tr><th>Affected Endpoints</th><td>{eps_html}</td></tr>
  </table>
  <h4>Description</h4>
  <p>{_h(f.get("description",""))}</p>
  <h4>Reasoning</h4>
  <p>{_h(f.get("reasoning",""))}</p>
  <h4>Assumptions</h4>
  <ul>{assumption_items}</ul>
  <h4>Reproduction Steps</h4>
  {repro_html}
  <h4>Remediation</h4>
  <p>{_h(f.get("remediation",""))}</p>
</div>""")
            findings_html = "\n".join(finding_blocks)

        # ── Attack Paths HTML ─────────────────────────────────────────────────
        if not data.attack_paths:
            paths_html = '<p class="no-data">No candidate attack paths were identified.</p>'
        else:
            path_rows = []
            for i, p in enumerate(data.attack_paths, 1):
                assumptions = "; ".join(p.get("unverified_assumptions", [])) or "None"
                path_rows.append(f"""
<tr>
  <td>{i}</td>
  <td><code>{_h(p.get("entry_point",""))}</code></td>
  <td><code>{_h(p.get("target_operation",""))}</code></td>
  <td>{_h(p.get("potential_impact",""))}</td>
  <td>{p.get("confidence",0):.0%}</td>
  <td style="color:#d29922;font-size:.85rem">{_h(assumptions)}</td>
</tr>""")
            paths_html = f"""
<table>
<thead><tr><th>#</th><th>Entry Point</th><th>Target</th><th>Potential Impact</th><th>Conf.</th><th>Unverified Assumptions</th></tr></thead>
<tbody>{"".join(path_rows)}</tbody>
</table>"""

        # ── Test Plans HTML ───────────────────────────────────────────────────
        if not data.test_plans:
            plans_html = '<p class="no-data">No security test plans were generated.</p>'
        else:
            plan_blocks = []
            for i, tp in enumerate(data.test_plans, 1):
                status_color = {"pending": "#6b7280", "approved": "#2563eb", "completed": "#16a34a"}.get(
                    tp.get("status", "pending"), "#6b7280"
                )
                plan_blocks.append(f"""
<div style="border:1px solid #e5e7eb;border-radius:6px;padding:1rem 1.25rem;margin-bottom:1.5rem;page-break-inside:avoid">
  <div style="display:flex;align-items:center;gap:.5rem;margin-bottom:.75rem">
    <strong style="color:#111827">{i}. {_h(tp.get("hypothesis",""))}</strong>
    <span style="margin-left:auto;color:{status_color};font-size:.85rem;font-weight:600">{_h(tp.get("status","pending").upper())}</span>
  </div>
  <h4>Test Procedure</h4>
  <pre><code>{_h(tp.get("test_procedure",""))}</code></pre>
  <h4>Expected Secure Behavior</h4>
  <p>{_h(tp.get("expected_secure_behavior",""))}</p>
</div>""")
            plans_html = "".join(plan_blocks)

        # ── Endpoint table HTML ───────────────────────────────────────────────
        if not data.endpoints:
            ep_table = '<p class="no-data">No endpoints were discovered.</p>'
        else:
            ep_rows = "".join(
                f'<tr><td><span class="method method-{_h(ep.get("method","get").lower())}">{_h(ep.get("method","GET"))}</span></td>'
                f'<td style="word-break:break-all"><code>{_h(ep.get("url",""))}</code></td>'
                f'<td>{_h(ep.get("status_code",""))}</td>'
                f'<td>{_h(ep.get("content_type","") or "")}</td>'
                f'<td>{_h(ep.get("discovery_source",""))}</td></tr>'
                for ep in data.endpoints[:200]
            )
            extra = f'<p style="color:#6b7280;font-style:italic">Showing 200 of {total_eps} endpoints.</p>' if total_eps > 200 else ""
            ep_table = f"""
<table>
<thead><tr><th>Method</th><th>URL / Path</th><th>Status</th><th>Content-Type</th><th>Source</th></tr></thead>
<tbody>{ep_rows}</tbody>
</table>{extra}"""

        # ── Scope section ─────────────────────────────────────────────────────
        cs = data.crawl_summary
        scope = data.scope
        scope_rows = "".join([
            f"<tr><th>Allowed Hosts</th><td>{_h(', '.join(scope.get('allowed_hosts',[])) or 'Not specified')}</td></tr>",
            f"<tr><th>Allowed Schemes</th><td>{_h(', '.join(scope.get('allowed_schemes',[])) or 'Not specified')}</td></tr>",
            f"<tr><th>Excluded Paths</th><td>{_h(', '.join(scope.get('exclude_paths',[])) or 'None')}</td></tr>",
        ])

        # ── Severity summary row ───────────────────────────────────────────────
        sev_order = ["critical", "high", "medium", "low", "info"]
        sev_summary = "".join(
            f'<div style="text-align:center;padding:.5rem 1rem;background:#f9fafb;border:1px solid #e5e7eb;border-radius:6px">'
            f'{severity_badge(sev)}<br><span style="font-size:1.5rem;font-weight:700;color:{_SEVERITY_COLORS[sev]}">'
            f'{sev_counts.get(sev,0)}</span></div>'
            for sev in sev_order
        )

        # ── Full HTML document ────────────────────────────────────────────────
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Security Assessment Report — {_h(data.project_name)}</title>
<style>
  /* ── Base ── */
  *, *::before, *::after {{ box-sizing: border-box; }}
  body {{ font-family: -apple-system, 'Inter', 'Segoe UI', Arial, sans-serif; font-size: 15px;
    line-height: 1.65; color: #111827; background: #f3f4f6; margin: 0; }}
  a {{ color: #2563eb; text-decoration: none; }}
  a:hover {{ text-decoration: underline; }}
  code {{ font-family: 'JetBrains Mono', 'Fira Code', Consolas, monospace; font-size: .88em;
    background: #f1f5f9; padding: 1px 5px; border-radius: 3px; color: #1e3a5f;
    word-break: break-all; }}
  pre {{ background: #1e293b; color: #e2e8f0; padding: 1rem 1.25rem; border-radius: 6px;
    overflow-x: auto; margin: .75rem 0; font-size: .875rem; line-height: 1.6; }}
  pre code {{ background: none; color: inherit; padding: 0; font-size: inherit; word-break: normal; }}
  table {{ border-collapse: collapse; width: 100%; margin: .75rem 0; font-size: .9rem; }}
  th {{ background: #1e3a5f; color: #fff; padding: .5rem .75rem; text-align: left;
    font-weight: 600; white-space: nowrap; }}
  td {{ padding: .5rem .75rem; border-bottom: 1px solid #e5e7eb; vertical-align: top; }}
  tr:nth-child(even) td {{ background: #f8fafc; }}
  h1 {{ font-size: 1.75rem; font-weight: 700; color: #111827; margin: 0 0 .5rem; }}
  h2 {{ font-size: 1.25rem; font-weight: 700; color: #1e3a5f; margin: 2rem 0 .75rem;
    padding-bottom: .4rem; border-bottom: 2px solid #dbeafe; }}
  h3 {{ font-size: 1.05rem; font-weight: 600; color: #111827; margin: 1rem 0 .4rem; }}
  h4 {{ font-size: .9rem; font-weight: 600; color: #374151; margin: .75rem 0 .25rem;
    text-transform: uppercase; letter-spacing: .04em; }}
  p {{ margin: .5rem 0; }}
  ul, ol {{ margin: .4rem 0; padding-left: 1.5rem; }}
  li {{ margin: .15rem 0; }}
  hr {{ border: none; border-top: 1px solid #e5e7eb; margin: 1.5rem 0; }}

  /* ── Layout ── */
  .wrapper {{ max-width: 1100px; margin: 0 auto; background: #fff;
    box-shadow: 0 1px 3px rgba(0,0,0,.1); }}
  .cover {{ background: linear-gradient(135deg, #1e3a5f 0%, #1d4ed8 100%);
    color: #fff; padding: 3rem 3rem 2.5rem; }}
  .cover-logo {{ font-size: 1rem; font-weight: 700; letter-spacing: .1em;
    text-transform: uppercase; opacity: .8; margin-bottom: 1rem; }}
  .cover-title {{ font-size: 2rem; font-weight: 800; margin: 0 0 .5rem; }}
  .cover-subtitle {{ font-size: 1rem; opacity: .85; margin: 0 0 2rem; }}
  .cover-meta {{ display: flex; gap: 2rem; flex-wrap: wrap; border-top: 1px solid rgba(255,255,255,.2);
    padding-top: 1.25rem; font-size: .9rem; opacity: .9; }}
  .cover-meta-item {{ display: flex; flex-direction: column; gap: .2rem; }}
  .cover-meta-label {{ font-size: .75rem; text-transform: uppercase; letter-spacing: .05em; opacity: .7; }}

  .body {{ padding: 2rem 3rem; }}
  .toc {{ background: #f8fafc; border: 1px solid #e5e7eb; border-radius: 6px;
    padding: 1.25rem 1.5rem; margin-bottom: 2rem; }}
  .toc h2 {{ margin-top: 0; border: none; font-size: 1rem; }}
  .toc ol {{ margin: 0; padding-left: 1.25rem; }}
  .toc li {{ margin: .3rem 0; }}
  .toc a {{ color: #2563eb; }}

  .summary-grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 1rem; margin-bottom: 1.5rem; }}
  .summary-card {{ background: #f8fafc; border: 1px solid #e5e7eb; border-radius: 8px;
    padding: 1rem; text-align: center; }}
  .summary-number {{ font-size: 2rem; font-weight: 800; color: #1e3a5f; line-height: 1; }}
  .summary-label {{ font-size: .8rem; color: #6b7280; text-transform: uppercase;
    letter-spacing: .04em; margin-top: .25rem; }}

  .sev-grid {{ display: grid; grid-template-columns: repeat(5, 1fr); gap: .75rem; margin-bottom: 1.5rem; }}
  .meta-table {{ width: auto; margin-bottom: .75rem; }}
  .meta-table th {{ background: #f1f5f9; color: #374151; width: 150px; font-size: .85rem; }}
  .meta-table td {{ background: transparent; border-bottom: none; }}

  .method {{ display: inline-block; padding: 1px 6px; border-radius: 3px; font-size: .8rem;
    font-weight: 700; font-family: monospace; }}
  .method-get {{ background: #dbeafe; color: #1d4ed8; }}
  .method-post {{ background: #d1fae5; color: #065f46; }}
  .method-put {{ background: #fef3c7; color: #92400e; }}
  .method-delete {{ background: #fee2e2; color: #991b1b; }}
  .method-patch {{ background: #ede9fe; color: #5b21b6; }}

  .no-data {{ color: #6b7280; font-style: italic; }}
  .disclaimer {{ background: #fffbeb; border: 1px solid #fcd34d; border-radius: 6px;
    padding: 1rem 1.25rem; font-size: .9rem; color: #78350f; margin-top: 2rem; }}
  .footer {{ background: #f8fafc; border-top: 1px solid #e5e7eb; padding: 1rem 3rem;
    text-align: center; font-size: .8rem; color: #9ca3af; }}

  /* ── Print ── */
  @media print {{
    body {{ background: #fff; }}
    .wrapper {{ box-shadow: none; max-width: 100%; }}
    .cover {{ -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
    h2 {{ page-break-after: avoid; }}
    .finding, .toc, tr {{ page-break-inside: avoid; }}
    .footer {{ display: none; }}
    a {{ color: #1e3a5f; text-decoration: none; }}
    a::after {{ content: " (" attr(href) ")"; font-size: .85em; color: #6b7280; }}
    .toc a::after {{ content: ""; }}
  }}
  @media (max-width: 768px) {{
    .body {{ padding: 1.5rem 1.25rem; }}
    .summary-grid {{ grid-template-columns: repeat(2, 1fr); }}
    .sev-grid {{ grid-template-columns: repeat(3, 1fr); }}
  }}
</style>
</head>
<body>
<div class="wrapper">

<!-- COVER -->
<div class="cover">
  <div class="cover-logo">⬡ AttackGraph</div>
  <h1 class="cover-title">Security Assessment Report</h1>
  <p class="cover-subtitle">Web Application Attack Surface Analysis</p>
  <div class="cover-meta">
    <div class="cover-meta-item">
      <span class="cover-meta-label">Project</span>
      <strong>{_h(data.project_name)}</strong>
    </div>
    <div class="cover-meta-item">
      <span class="cover-meta-label">Target</span>
      <strong>{_h(data.target_url)}</strong>
    </div>
    <div class="cover-meta-item">
      <span class="cover-meta-label">Generated</span>
      <strong>{_h(gen_date)}</strong>
    </div>
    <div class="cover-meta-item">
      <span class="cover-meta-label">AttackGraph Version</span>
      <strong>v0.1.0</strong>
    </div>
  </div>
</div>

<div class="body">

<!-- TABLE OF CONTENTS -->
<div class="toc">
  <h2>Table of Contents</h2>
  <ol>{toc_items}</ol>
</div>

<!-- EXECUTIVE SUMMARY -->
<section id="executive-summary">
  <h2>1. Executive Summary</h2>
  <p>This report presents the results of an automated web application security assessment
  performed against <strong>{_h(data.target_url)}</strong> using AttackGraph. The assessment
  discovered <strong>{total_eps} endpoint{'' if total_eps == 1 else 's'}</strong>, identified
  <strong>{total_findings} security finding{'' if total_findings == 1 else 's'}</strong>, and
  generated <strong>{total_paths} candidate attack path{'' if total_paths == 1 else 's'}</strong>.</p>

  <div class="summary-grid">
    <div class="summary-card">
      <div class="summary-number">{total_eps}</div>
      <div class="summary-label">Endpoints</div>
    </div>
    <div class="summary-card">
      <div class="summary-number">{total_findings}</div>
      <div class="summary-label">Findings</div>
    </div>
    <div class="summary-card">
      <div class="summary-number">{total_paths}</div>
      <div class="summary-label">Attack Paths</div>
    </div>
    <div class="summary-card">
      <div class="summary-number">{total_plans}</div>
      <div class="summary-label">Test Plans</div>
    </div>
  </div>

  <h3>Finding Severity Distribution</h3>
  <div class="sev-grid">
    {sev_summary}
  </div>

  <p><strong>Important:</strong> All findings are automatically generated hypotheses unless
  they have been explicitly validated by a security professional. This report does not
  constitute a complete manual security assessment.</p>
</section>

<!-- SCOPE -->
<section id="scope">
  <h2>2. Assessment Scope</h2>
  <table class="meta-table">
    {scope_rows}
  </table>
  <p>The assessment was limited to the scope defined above. Endpoints, behaviors, and
  vulnerabilities outside this scope were not examined.</p>
</section>

<!-- DISCOVERY -->
<section id="discovery">
  <h2>3. Discovery Summary</h2>
  <table>
    <thead><tr><th>Metric</th><th>Value</th></tr></thead>
    <tbody>
      <tr><td>Pages Crawled</td><td>{_h(cs.get('pages_crawled', 0))}</td></tr>
      <tr><td>Pages Discovered</td><td>{_h(cs.get('pages_discovered', 0))}</td></tr>
      <tr><td>Total Endpoints Inventoried</td><td>{total_eps}</td></tr>
      <tr><td>Crawl Errors</td><td>{_h(cs.get('errors', 0))}</td></tr>
    </tbody>
  </table>
</section>

<!-- ENDPOINTS -->
<section id="endpoints">
  <h2>4. Endpoint Inventory</h2>
  {ep_table}
</section>

<!-- GRAPH -->
<section id="graph">
  <h2>5. Application Graph</h2>
  <table>
    <thead><tr><th>Metric</th><th>Value</th></tr></thead>
    <tbody>
      <tr><td>Total Nodes</td><td>{_h(data.graph_statistics.get('total_nodes', 0))}</td></tr>
      <tr><td>Total Edges</td><td>{_h(data.graph_statistics.get('total_edges', 0))}</td></tr>
      <tr><td>Observed Nodes</td><td>{_h(data.graph_statistics.get('observed_nodes', 0))}</td></tr>
      <tr><td>Inferred Nodes</td><td>{_h(data.graph_statistics.get('inferred_nodes', 0))}</td></tr>
      <tr><td>Connected Components</td><td>{_h(data.graph_statistics.get('components', 0))}</td></tr>
    </tbody>
  </table>
</section>

<!-- FINDINGS -->
<section id="findings">
  <h2>6. Security Findings</h2>
  {findings_html}
</section>

<!-- ATTACK PATHS -->
<section id="attack-paths">
  <h2>7. Candidate Attack Paths</h2>
  <p>The following candidate attack paths represent potential routes an attacker could
  take based on the observed application structure. All paths should be treated as
  hypotheses requiring manual validation.</p>
  {paths_html}
</section>

<!-- TEST PLANS -->
<section id="test-plans">
  <h2>8. Security Test Plans</h2>
  {plans_html}
</section>

<!-- LIMITATIONS -->
<section id="limitations">
  <h2>9. Limitations and Assessment Notes</h2>
  <ul>
    <li>This assessment was performed using automated crawling and static analysis only.</li>
    <li>Dynamic testing, authenticated workflows, and business-logic testing were not performed unless explicitly configured.</li>
    <li>Findings represent hypotheses based on observed application structure, not confirmed exploitable vulnerabilities.</li>
    <li>No destructive tests, actual exploitation attempts, or denial-of-service tests were performed.</li>
    <li>Authentication bypass, privilege escalation, and injection vulnerabilities require manual validation.</li>
    <li>The scope was limited to endpoints reachable by the configured crawler within the defined scope.</li>
  </ul>

  <div class="disclaimer">
    <strong>⚠ Disclaimer:</strong> This report was generated automatically by AttackGraph v0.1.0.
    All findings are unvalidated hypotheses unless explicitly marked as confirmed.
    This report should be reviewed by a qualified security professional before being
    used as the basis for security decisions. AttackGraph does not guarantee completeness
    or accuracy of automated findings.
  </div>
</section>

</div><!-- /body -->

<div class="footer">
  Generated by AttackGraph v0.1.0 &nbsp;·&nbsp; {_h(gen_date)}
  &nbsp;·&nbsp; This report is confidential and intended for authorized personnel only.
</div>

</div><!-- /wrapper -->
</body>
</html>"""

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
