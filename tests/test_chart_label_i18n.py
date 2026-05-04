"""Regression: pie/bar slice labels must be translated to zh_TW for the PDF.

Task 4 plumbed `title_key` / `*_label_key` for chart titles and axes, but the
slice/bar labels (chart_spec.data["labels"]) are populated by each analyzer.
mod01/mod02/mod04 hardcoded English; this test ensures they now produce
Chinese when the language is set to zh_TW.
"""
from __future__ import annotations

import pandas as pd
import pytest

from src.i18n import set_language, get_language


def _make_traffic_df() -> pd.DataFrame:
    """Minimal traffic DataFrame that exercises every chart_spec branch
    in mod01 / mod02 / mod04 — all four policy decisions and at least one
    flow on critical/high/medium ransomware-risk ports."""
    return pd.DataFrame({
        "src_ip":            ["10.0.0.1", "10.0.0.2", "10.0.0.3", "10.0.0.4"],
        "dst_ip":            ["10.0.1.1", "10.0.1.2", "10.0.1.3", "10.0.1.4"],
        "port":              [445, 3389, 22, 80],
        "proto":             ["TCP", "TCP", "TCP", "TCP"],
        "bytes_total":       [10_000, 5_000, 20_000, 3_000],
        "num_connections":   [5, 3, 10, 2],
        "policy_decision":   ["allowed", "blocked", "potentially_blocked", "unknown"],
        "src_managed":       [True, True, False, True],
        "dst_managed":       [True, False, True, True],
        "first_detected":    pd.to_datetime(["2024-01-01"] * 4),
        "last_detected":     pd.to_datetime(["2024-01-02"] * 4),
        "src_app":           ["web", "db", "admin", "web"],
        "dst_app":           ["db", "cache", "web", "api"],
    })


_RANSOMWARE_CONFIG = {
    "ransomware_risk_ports": {
        "critical": [{"ports": [445], "service": "SMB"}],
        "high":     [{"ports": [3389], "service": "RDP"}],
        "medium":   [{"ports": [22], "service": "SSH"}],
        "low":      [{"ports": [80], "service": "HTTP"}],
    }
}


@pytest.fixture
def zh_tw_lang():
    prev = get_language()
    set_language("zh_TW")
    try:
        yield
    finally:
        set_language(prev)


def test_mod01_traffic_overview_labels_translate_to_zh_tw(zh_tw_lang):
    from src.report.analysis.mod01_traffic_overview import traffic_overview

    out = traffic_overview(_make_traffic_df())
    labels = out["chart_spec"]["data"]["labels"]

    # Chinese present
    assert "已允許" in labels
    assert "已封鎖" in labels
    assert "可能被封鎖" in labels
    assert "未知" in labels
    # English absent (regression: prevents accidental revert to literals)
    assert "Allowed" not in labels
    assert "Blocked" not in labels
    assert "Potentially Blocked" not in labels
    assert "Unknown" not in labels


def test_mod02_policy_decisions_labels_translate_to_zh_tw(zh_tw_lang):
    from src.report.analysis.mod02_policy_decisions import policy_decision_analysis

    out = policy_decision_analysis(_make_traffic_df())
    labels = out["chart_spec"]["data"]["labels"]

    assert "已允許" in labels
    assert "已封鎖" in labels
    assert "可能被封鎖" in labels
    assert "Allowed" not in labels
    assert "Blocked" not in labels
    assert "Potentially Blocked" not in labels


def test_mod04_ransomware_exposure_labels_translate_to_zh_tw(zh_tw_lang):
    from src.report.analysis.mod04_ransomware_exposure import ransomware_exposure

    out = ransomware_exposure(_make_traffic_df(), _RANSOMWARE_CONFIG)
    labels = out["chart_spec"]["data"]["labels"]

    # All four risk levels are present in the test config + DataFrame, so
    # all four Chinese labels must surface.
    assert "嚴重" in labels
    assert "高" in labels
    assert "中" in labels
    assert "低" in labels
    # English absent
    assert "Critical" not in labels
    assert "High" not in labels
    assert "Medium" not in labels
    assert "Low" not in labels
