"""Tests for mod_draft_summary — draft_policy_decision 7-subtype breakdown."""
import pandas as pd
import pytest

DRAFT_SUBTYPES = [
    "allowed",
    "potentially_blocked",
    "blocked_by_boundary",
    "blocked_by_override_deny",
    "potentially_blocked_by_boundary",
    "potentially_blocked_by_override_deny",
    "allowed_across_boundary",
]


def _base_row(**kwargs):
    row = {"src": "a", "dst": "b", "port": 80, "policy_decision": "allowed"}
    row.update(kwargs)
    return row


def test_all_7_subtypes_in_counts():
    from src.report.analysis.mod_draft_summary import analyze
    rows = [_base_row(draft_policy_decision=s) for s in DRAFT_SUBTYPES]
    out = analyze(pd.DataFrame(rows))
    assert set(out["counts"].keys()) == set(DRAFT_SUBTYPES)


def test_counts_are_correct():
    from src.report.analysis.mod_draft_summary import analyze
    rows = [
        _base_row(draft_policy_decision="allowed"),
        _base_row(draft_policy_decision="allowed"),
        _base_row(draft_policy_decision="blocked_by_boundary"),
    ]
    out = analyze(pd.DataFrame(rows))
    assert out["counts"]["allowed"] == 2
    assert out["counts"]["blocked_by_boundary"] == 1
    assert out["counts"]["potentially_blocked"] == 0  # zero-filled


def test_absent_subtypes_zero_filled():
    from src.report.analysis.mod_draft_summary import analyze
    rows = [_base_row(draft_policy_decision="allowed")]
    out = analyze(pd.DataFrame(rows))
    for s in DRAFT_SUBTYPES:
        assert s in out["counts"]
        assert isinstance(out["counts"][s], int)


def test_top_pairs_by_subtype():
    from src.report.analysis.mod_draft_summary import analyze
    rows = [_base_row(src="x", dst="y", draft_policy_decision="blocked_by_boundary")]
    out = analyze(pd.DataFrame(rows))
    assert "blocked_by_boundary" in out["top_pairs_by_subtype"]
    pairs = out["top_pairs_by_subtype"]["blocked_by_boundary"]
    assert len(pairs) == 1
    assert pairs[0]["src"] == "x"
    assert pairs[0]["dst"] == "y"


def test_absent_when_column_missing():
    from src.report.analysis.mod_draft_summary import analyze
    rows = [{"src": "a", "dst": "b", "port": 80, "policy_decision": "allowed"}]
    out = analyze(pd.DataFrame(rows))
    assert out.get("skipped") is True
    assert "no draft_policy_decision column" in out.get("reason", "")


def test_chart_spec_present():
    from src.report.analysis.mod_draft_summary import analyze
    rows = [_base_row(draft_policy_decision="allowed")]
    out = analyze(pd.DataFrame(rows))
    assert "chart_spec" in out
    cs = out["chart_spec"]
    assert cs["kind"] == "bar"
    assert "title_key" in cs
    assert len(cs["categories"]) == 7
    assert len(cs["values"]) == 7
