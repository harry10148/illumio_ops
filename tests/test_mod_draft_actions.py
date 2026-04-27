"""mod_draft_actions: Override Deny remediation suggestions."""
import pandas as pd

from src.report.analysis import mod_draft_actions


def _flows_with_override_deny():
    return pd.DataFrame([
        {"src": "web-1", "dst": "db-1", "port": 3306, "policy_decision": "allowed",
         "draft_policy_decision": "blocked_by_override_deny"},
        {"src": "web-1", "dst": "db-2", "port": 3306, "policy_decision": "allowed",
         "draft_policy_decision": "blocked_by_override_deny"},
        {"src": "app-1", "dst": "log-1", "port": 514, "policy_decision": "allowed",
         "draft_policy_decision": "potentially_blocked_by_override_deny"},
    ])


def test_skipped_when_no_draft_column():
    out = mod_draft_actions.analyze(pd.DataFrame([{"src": "a", "dst": "b", "port": 80,
                                                    "policy_decision": "allowed"}]))
    assert out.get("skipped") is True


def test_override_deny_remediation_top_pairs():
    out = mod_draft_actions.analyze(_flows_with_override_deny())
    od = out["override_deny"]
    assert od["count"] == 2
    assert any(p["src"] == "web-1" and p["port"] == 3306 for p in od["top_pairs"])


def test_potentially_blocked_by_override_deny_separate():
    out = mod_draft_actions.analyze(_flows_with_override_deny())
    pod = out["potentially_blocked_by_override_deny"]
    assert pod["count"] == 1


def test_remediation_suggestion_present():
    out = mod_draft_actions.analyze(_flows_with_override_deny())
    od = out["override_deny"]
    assert "remediation" in od
    for r in od["remediation"]:
        assert "action_code" in r and "description_key" in r
