"""Tests for mod13 draft enforcement gap dimension."""
import pandas as pd


def _row(pd_val, dpd_val=None):
    row = {"src": "a", "dst": "b", "port": 80, "policy_decision": pd_val,
           "proto": "TCP", "count": 1}
    if dpd_val is not None:
        row["draft_policy_decision"] = dpd_val
    return row


def test_draft_gap_present_when_column_exists():
    from src.report.analysis.mod13_readiness import analyze
    rows = [
        _row("allowed", "allowed"),
        _row("allowed", "blocked_by_boundary"),
    ]
    try:
        out = analyze(pd.DataFrame(rows))
    except TypeError:
        out = analyze(pd.DataFrame(rows), {})
    assert "draft_enforcement_gap" in out


def test_draft_gap_counts_blocked_family():
    from src.report.analysis.mod13_readiness import analyze
    rows = [
        _row("allowed", "allowed"),          # not a gap
        _row("allowed", "blocked_by_boundary"),  # gap
        _row("allowed", "blocked_by_override_deny"),  # gap
    ]
    try:
        out = analyze(pd.DataFrame(rows))
    except TypeError:
        out = analyze(pd.DataFrame(rows), {})
    assert out["draft_enforcement_gap"] == 2


def test_draft_gap_absent_when_column_missing():
    from src.report.analysis.mod13_readiness import analyze
    rows = [_row("allowed"), _row("potentially_blocked")]
    try:
        out = analyze(pd.DataFrame(rows))
    except TypeError:
        out = analyze(pd.DataFrame(rows), {})
    assert "draft_enforcement_gap" not in out
