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
            {"url": "https://example.com/api/admin", "method": "GET", "status_code": 200, "discovery_source": "crawl"},
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
            },
        ],
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

    def test_html_report(self):
        gen = ReportGenerator()
        result = gen.generate_html(_sample_data())
        assert "<!DOCTYPE html>" in result
        assert "Test Project" in result

    def test_empty_findings_report(self):
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
