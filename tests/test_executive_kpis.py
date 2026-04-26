"""mod12 executive summary must expose the 6+6 KPIs per profile, with names
matching spec §6.4."""
import pandas as pd

from src.report.analysis import mod12_executive_summary


SECURITY_RISK_KPI_NAMES = {
    "microsegmentation_maturity",
    "active_allow_coverage",
    "pb_uncovered_exposure",
    "blocked_flows",
    "high_risk_lateral_paths",
    "top_remediation_action",
}

NETWORK_INVENTORY_KPI_NAMES = {
    "observed_apps_envs",
    "known_dependency_coverage",
    "label_completeness",
    "rule_candidate_count",
    "unmanaged_unknown_dependencies",
    "top_rule_building_gap",
}


def _sample_flows():
    return pd.DataFrame([
        {"src": "a", "dst": "b", "port": 443, "policy_decision": "allowed"},
        {"src": "a", "dst": "c", "port": 80,  "policy_decision": "potentially_blocked"},
        {"src": "x", "dst": "y", "port": 22,  "policy_decision": "blocked"},
    ])


def test_security_risk_profile_returns_6_kpis():
    out = mod12_executive_summary.analyze(_sample_flows(), profile="security_risk")
    kpis = out.get("kpis", {})
    assert SECURITY_RISK_KPI_NAMES.issubset(set(kpis.keys())), (
        f"missing: {SECURITY_RISK_KPI_NAMES - set(kpis.keys())}")


def test_network_inventory_profile_returns_6_kpis():
    out = mod12_executive_summary.analyze(_sample_flows(), profile="network_inventory")
    kpis = out.get("kpis", {})
    assert NETWORK_INVENTORY_KPI_NAMES.issubset(set(kpis.keys())), (
        f"missing: {NETWORK_INVENTORY_KPI_NAMES - set(kpis.keys())}")


def test_top_3_actions_block_present_in_security_risk():
    out = mod12_executive_summary.analyze(_sample_flows(), profile="security_risk")
    actions = out.get("top_actions", [])
    assert isinstance(actions, list)
    assert len(actions) <= 3
    # Each action should have count + code + text + optional top app/env
    for a in actions:
        assert "code" in a and "count" in a


def test_default_profile_is_security_risk():
    out_default = mod12_executive_summary.analyze(_sample_flows())
    out_explicit = mod12_executive_summary.analyze(_sample_flows(), profile="security_risk")
    assert set(out_default.get("kpis", {}).keys()) == set(out_explicit.get("kpis", {}).keys())
