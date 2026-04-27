"""Tests for mod02 draft_policy_decision cross-tab."""
import pandas as pd


def _row(pd_val, dpd_val=None):
    row = {
        "src_app": "app_a",
        "dst_app": "app_b",
        "port": 80,
        "proto": "TCP",
        "num_connections": 1,
        "src_managed": True,
        "dst_managed": False,
        "policy_decision": pd_val,
    }
    if dpd_val is not None:
        row["draft_policy_decision"] = dpd_val
    return row


def test_draft_breakdown_present_when_column_exists():
    from src.report.analysis.mod02_policy_decisions import policy_decision_analysis
    rows = [
        _row("allowed", "allowed"),
        _row("allowed", "blocked_by_boundary"),
        _row("potentially_blocked", "potentially_blocked_by_boundary"),
    ]
    out = policy_decision_analysis(pd.DataFrame(rows))
    assert "draft_breakdown" in out


def test_draft_breakdown_absent_when_column_missing():
    from src.report.analysis.mod02_policy_decisions import policy_decision_analysis
    rows = [_row("allowed"), _row("potentially_blocked")]
    out = policy_decision_analysis(pd.DataFrame(rows))
    assert "draft_breakdown" not in out


def test_draft_breakdown_structure():
    from src.report.analysis.mod02_policy_decisions import policy_decision_analysis
    rows = [
        _row("allowed", "allowed"),
        _row("allowed", "blocked_by_boundary"),
    ]
    out = policy_decision_analysis(pd.DataFrame(rows))
    db = out["draft_breakdown"]
    # Should be a dict of {draft_pd: {policy_decision: count}}
    assert isinstance(db, dict)
    # "allowed" policy_decision row should exist as a key in the inner dicts
    inner_keys = set()
    for v in db.values():
        inner_keys.update(v.keys())
    assert "allowed" in inner_keys
