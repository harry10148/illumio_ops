"""Regression tests for rule scheduler CLI input handling."""
from unittest.mock import MagicMock


def test_schedule_management_blank_enter_does_not_exit(monkeypatch):
    from src.rule_scheduler_cli import _RuleSchedulerCLI

    cli = _RuleSchedulerCLI(MagicMock(), MagicMock(), MagicMock(), MagicMock())
    list_calls = []
    answers = iter(["", "q"])

    monkeypatch.setattr(cli, "_list_grouped", lambda: list_calls.append("listed"))
    monkeypatch.setattr("builtins.input", lambda _prompt="": next(answers))

    cli.schedule_management_ui()

    assert len(list_calls) == 2
