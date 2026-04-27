"""mod_change_impact: compare current KPIs to a previous snapshot."""
import pandas as pd
import pytest

from src.report.analysis import mod_change_impact


def _kpis(**overrides):
    base = {"pb_uncovered_exposure": 1000, "blocked_flows": 50,
            "high_risk_lateral_paths": 10, "active_allow_coverage": 0.6,
            "microsegmentation_maturity": 0.5}
    base.update(overrides)
    return base


def test_returns_skipped_when_no_previous():
    out = mod_change_impact.compare(current_kpis=_kpis(), previous=None)
    assert out["skipped"] is True
    assert "no_previous_snapshot" in out["reason"]


def test_detects_improvement():
    previous = {"kpis": _kpis(pb_uncovered_exposure=2000, high_risk_lateral_paths=20)}
    out = mod_change_impact.compare(current_kpis=_kpis(pb_uncovered_exposure=1000,
                                                       high_risk_lateral_paths=10),
                                    previous=previous)
    assert out["overall_verdict"] == "improved"
    deltas = out["deltas"]
    assert deltas["pb_uncovered_exposure"]["delta"] == -1000
    assert deltas["pb_uncovered_exposure"]["direction"] == "improved"


def test_detects_regression():
    previous = {"kpis": _kpis(pb_uncovered_exposure=500, blocked_flows=10)}
    out = mod_change_impact.compare(current_kpis=_kpis(pb_uncovered_exposure=2000, blocked_flows=100),
                                    previous=previous)
    assert out["overall_verdict"] == "regressed"


def test_mixed_returns_mixed():
    previous = {"kpis": _kpis(pb_uncovered_exposure=2000, blocked_flows=10)}
    out = mod_change_impact.compare(current_kpis=_kpis(pb_uncovered_exposure=1000, blocked_flows=100),
                                    previous=previous)
    assert out["overall_verdict"] == "mixed"
