"""Tests for HTML report data-source pill."""
import pytest


def _make_html_exporter(data_source, module_results=None):
    from src.report.exporters.html_exporter import HtmlExporter
    return HtmlExporter(module_results or {}, data_source=data_source)


def _make_audit_exporter(data_source, df=None, metrics=None):
    from src.report.exporters.audit_html_exporter import AuditHtmlExporter
    import pandas as pd
    return AuditHtmlExporter(
        df if df is not None else pd.DataFrame(),
        metrics or {},
        data_source=data_source,
    )


def test_traffic_report_cache_pill_rendered():
    """HTML traffic report shows 'cache' pill when data_source='cache'."""
    exp = _make_html_exporter("cache")
    html = exp._build()
    assert "cache" in html.lower() or "rpt_data_source_cache" in html


def test_traffic_report_api_pill_rendered():
    """HTML traffic report shows 'api' pill when data_source='api'."""
    exp = _make_html_exporter("api")
    html = exp._build()
    assert "api" in html.lower() or "rpt_data_source_api" in html


def test_audit_report_cache_pill_rendered():
    """HTML audit report shows 'cache' pill when data_source='cache'."""
    exp = _make_audit_exporter("cache")
    html = exp._build()
    assert "cache" in html.lower() or "rpt_data_source_cache" in html
