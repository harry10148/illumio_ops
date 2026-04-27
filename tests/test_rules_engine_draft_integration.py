"""Integration test: ruleset_needs_draft_pd helper + ACTIVE_RULES wiring."""


def test_ruleset_needs_draft_pd_returns_true_for_draft_rules():
    from src.report.rules_engine import ruleset_needs_draft_pd, DRAFT_PD_RULES
    assert ruleset_needs_draft_pd(DRAFT_PD_RULES) is True


def test_ruleset_needs_draft_pd_returns_false_for_empty():
    from src.report.rules_engine import ruleset_needs_draft_pd
    assert ruleset_needs_draft_pd([]) is False


def test_ruleset_needs_draft_pd_returns_false_for_non_draft_rules():
    from src.report.rules_engine import ruleset_needs_draft_pd

    class FakeRule:
        pass  # no needs_draft_pd method

    assert ruleset_needs_draft_pd([FakeRule()]) is False


def test_active_ruleset_includes_draft_pd_rules():
    """DRAFT_PD_RULES are present and non-empty, meaning queries will auto-enable compute_draft."""
    from src.report.rules_engine import DRAFT_PD_RULES
    assert len(DRAFT_PD_RULES) >= 5
