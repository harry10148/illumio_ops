"""Tests for offline-bundle PDF graceful-degrade behaviour."""
from __future__ import annotations


def test_pdf_available_flag_is_bool():
    from src.report.exporters.pdf_exporter import PDF_AVAILABLE
    assert isinstance(PDF_AVAILABLE, bool)


def test_requirements_offline_excludes_weasyprint(tmp_path):
    import os
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    offline_req = os.path.join(root, "requirements-offline.txt")
    assert os.path.exists(offline_req), "requirements-offline.txt not found"
    content = open(offline_req).read().lower()
    assert "weasyprint" not in content
    # Must still list the other core packages
    for pkg in ("flask", "pandas", "requests", "apscheduler", "loguru"):
        assert pkg in content, f"{pkg} missing from requirements-offline.txt"


from click.testing import CliRunner
from unittest.mock import patch


def test_report_traffic_pdf_raises_when_unavailable():
    from src.cli.report import report_traffic
    with patch("src.report.exporters.pdf_exporter.PDF_AVAILABLE", False):
        result = CliRunner().invoke(report_traffic, ["--format", "pdf"])
    assert result.exit_code != 0
    assert "PDF export is not available" in result.output


def test_report_audit_pdf_raises_when_unavailable():
    from src.cli.report import report_audit
    with patch("src.report.exporters.pdf_exporter.PDF_AVAILABLE", False):
        result = CliRunner().invoke(report_audit, ["--format", "pdf"])
    assert result.exit_code != 0
    assert "PDF export is not available" in result.output


def test_report_ven_pdf_raises_when_unavailable():
    from src.cli.report import report_ven_status
    with patch("src.report.exporters.pdf_exporter.PDF_AVAILABLE", False):
        result = CliRunner().invoke(report_ven_status, ["--format", "pdf"])
    assert result.exit_code != 0
    assert "PDF export is not available" in result.output


def test_report_policy_usage_pdf_raises_when_unavailable():
    from src.cli.report import report_policy_usage
    with patch("src.report.exporters.pdf_exporter.PDF_AVAILABLE", False):
        result = CliRunner().invoke(report_policy_usage, ["--format", "pdf"])
    assert result.exit_code != 0
    assert "PDF export is not available" in result.output


def test_verify_deps_production_list_uses_reportlab_not_weasyprint():
    """The production package list must contain reportlab and not weasyprint.

    ReportLab is pure-Python so both online and offline builds use the same list.
    """
    from scripts.verify_deps import PRODUCTION
    dist_names = [p.dist.lower() for p in PRODUCTION]
    assert "reportlab" in dist_names
    assert "weasyprint" not in dist_names
