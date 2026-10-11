import json
import pytest
from backend.reporting.generator import ReportGenerator, ReportData


def _sample_data() -> ReportData:
    return ReportData(
        project_name="Test Project",
        target_url="https://example.com",
        scope={"allowed_hosts": ["example.com"], "allowed_schemes": ["https"], "exclude_paths": []},
        crawl_summary={"pages_crawled": 15, "pages_discovered": 30, "errors": 2},
        endpoints=[
            {"url": "https://example.com/api/users", "method": "GET", "status_code": 200, "discovery_source": "crawl"},
            {"url": "https://example.com/api/admin", "method": "POST", "status_code": 200, "discovery_source": "crawl"},
        ],
        graph_statistics={"total_nodes": 20, "total_edges": 15, "observed_nodes": 18, "inferred_nodes": 2, "components": 1},
        findings=[
            {
                "title": "Unauthenticated admin endpoint",
                "description": "The /admin endpoint has no observed auth",
                "affected_endpoints": ["https://example.com/api/admin"],
                "severity": "high",
                "confidence": 0.5,
                "validation_status": "hypothesis",
                "detection_rule": "unauth-sensitive",
                "reasoning": "No auth dependency observed",
                "assumptions": ["Auth may exist at another layer"],
                "remediation": "Add authentication",
                "reproduction_steps": "GET /api/admin\nExpect: 401",
            },
        ],
        attack_paths=[
            {
                "entry_point": "GET /",
                "target_operation": "GET /api/admin",
                "confidence": 0.4,
                "priority_score": 0.7,
                "potential_impact": "Admin access",
                "unverified_assumptions": ["No auth on admin"],
            },
        ],
        test_plans=[
            {
                "hypothesis": "Admin endpoint accessible without auth",
                "test_procedure": "1. Access /api/admin without credentials\n2. Check response",
                "expected_secure_behavior": "401 Unauthorized",
                "status": "pending",
            },
        ],
    )


def _xss_data() -> ReportData:
    return ReportData(
        project_name='<script>alert(1)</script>',
        target_url="https://xss-test.example.com",
        scope={"allowed_hosts": ["xss-test.example.com"], "allowed_schemes": ["https"], "exclude_paths": []},
        crawl_summary={"pages_crawled": 1, "pages_discovered": 1, "errors": 0},
        endpoints=[
            {"url": 'https://example.com/<img onerror=alert(1)>', "method": "GET", "status_code": 200, "discovery_source": "crawl"},
        ],
        graph_statistics={"total_nodes": 1, "total_edges": 0, "observed_nodes": 1, "inferred_nodes": 0, "components": 1},
        findings=[
            {
                "title": '<b>Bold</b><script>alert(2)</script>',
                "description": "Test <iframe src=x>",
                "affected_endpoints": ['<script>x</script>'],
                "severity": "high",
                "confidence": 0.9,
                "validation_status": "confirmed",
                "detection_rule": "xss-test",
                "reasoning": "javascript:alert(1)",
                "assumptions": ['"><svg onload=alert(1)>'],
                "remediation": '<a href="javascript:void(0)">fix</a>',
                "reproduction_steps": "",
            },
        ],
        attack_paths=[],
        test_plans=[],
    )


class TestReportGenerator:
    def test_json_report(self):
        gen = ReportGenerator()
        result = gen.generate_json(_sample_data())
        parsed = json.loads(result)
        assert parsed["project_name"] == "Test Project"
        assert parsed["target_url"] == "https://example.com"
        assert len(parsed["findings"]) == 1
        assert "disclaimer" in parsed

    def test_markdown_report(self):
        gen = ReportGenerator()
        result = gen.generate_markdown(_sample_data())
        assert "# AttackGraph Security Assessment Report" in result
        assert "Test Project" in result
        assert "Unauthenticated admin endpoint" in result
        assert "hypothesis" in result.lower() or "HYPOTHESIS" in result

    def test_html_report_structure(self):
        gen = ReportGenerator()
        result = gen.generate_html(_sample_data())
        assert "<!DOCTYPE html>" in result
        assert "<html" in result
        assert "</html>" in result
        assert "Test Project" in result

    def test_html_report_no_raw_markdown(self):
        """HTML report must not contain raw Markdown syntax."""
        gen = ReportGenerator()
        result = gen.generate_html(_sample_data())
        # Should not contain raw Markdown heading markers
        assert "## " not in result
        assert "### " not in result
        # Should not contain raw Markdown bold markers
        assert "**Severity:**" not in result
        assert "**Description:**" not in result
        # Should not contain raw Markdown table pipes at line start
        assert "| Method |" not in result

    def test_html_report_has_real_sections(self):
        """HTML report must have proper HTML sections, not a pre block."""
        gen = ReportGenerator()
        result = gen.generate_html(_sample_data())
        # Cover section
        assert "Security Assessment Report" in result
        assert "https://example.com" in result
        # Proper HTML tags
        assert "<section" in result
        assert "<h2>" in result
        assert "<table>" in result
        # Findings visible as HTML
        assert "Unauthenticated admin endpoint" in result
        # Not wrapped in a raw <pre> block
        assert '<pre style="white-space: pre-wrap;">' not in result

    def test_html_report_severity_badge(self):
        gen = ReportGenerator()
        result = gen.generate_html(_sample_data())
        # Severity badge must be proper HTML
        assert 'class="badge sev-high"' in result or 'sev-high' in result
        assert "HIGH" in result

    def test_html_report_endpoint_table(self):
        gen = ReportGenerator()
        result = gen.generate_html(_sample_data())
        assert "https://example.com/api/users" in result
        assert "https://example.com/api/admin" in result
        # Method badge
        assert 'class="method method-get"' in result or 'method-get' in result

    def test_html_report_attack_paths(self):
        gen = ReportGenerator()
        result = gen.generate_html(_sample_data())
        assert "GET /" in result
        assert "GET /api/admin" in result

    def test_html_report_toc(self):
        gen = ReportGenerator()
        result = gen.generate_html(_sample_data())
        assert 'href="#executive-summary"' in result
        assert 'href="#findings"' in result

    def test_html_report_print_styles(self):
        gen = ReportGenerator()
        result = gen.generate_html(_sample_data())
        assert "@media print" in result

    def test_html_report_xss_safe(self):
        """User-supplied data must be HTML-escaped in the HTML report."""
        gen = ReportGenerator()
        result = gen.generate_html(_xss_data())
        # Raw script tags must be escaped
        assert "<script>" not in result
        assert "<iframe" not in result
        assert "<img onerror=" not in result
        assert "<svg onload=" not in result
        # But the escaped versions should be present
        assert "&lt;script&gt;" in result or "&#x27;" in result or "&lt;b&gt;" in result

    def test_html_report_standalone(self):
        """HTML report must be self-contained (no external CSS links)."""
        gen = ReportGenerator()
        result = gen.generate_html(_sample_data())
        # All styles must be inline/embedded
        assert 'rel="stylesheet"' not in result
        assert '<link href="' not in result
        assert 'src="https://' not in result
        assert "<style>" in result

    def test_html_empty_findings(self):
        data = _sample_data()
        data.findings = []
        data.attack_paths = []
        data.test_plans = []
        gen = ReportGenerator()
        result = gen.generate_html(data)
        assert "No security findings" in result
        assert "No candidate attack paths" in result
        assert "No security test plans" in result

    def test_html_report_cover(self):
        gen = ReportGenerator()
        result = gen.generate_html(_sample_data())
        assert "AttackGraph" in result
        assert "class=\"cover\"" in result or "cover" in result

    def test_empty_findings_markdown(self):
        data = _sample_data()
        data.findings = []
        data.attack_paths = []
        gen = ReportGenerator()
        result = gen.generate_markdown(data)
        assert "No security findings" in result

    def test_report_contains_scope(self):
        gen = ReportGenerator()
        result = gen.generate_markdown(_sample_data())
        assert "example.com" in result
        assert "Scope" in result

    def test_report_redaction_disclaimer(self):
        gen = ReportGenerator()
        result = gen.generate_markdown(_sample_data())
        assert "hypothes" in result.lower()

    def test_html_and_markdown_same_data(self):
        """Both HTML and Markdown must include the same key project data."""
        gen = ReportGenerator()
        data = _sample_data()
        md = gen.generate_markdown(data)
        html = gen.generate_html(data)
        # Both must mention findings
        assert "Unauthenticated admin endpoint" in md
        assert "Unauthenticated admin endpoint" in html
        # Both must mention target
        assert "https://example.com" in md
        assert "https://example.com" in html
