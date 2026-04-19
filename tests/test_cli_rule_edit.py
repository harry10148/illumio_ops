"""Tests for `illumio-ops rule edit <id>` interactive command."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from src.cli.rule import edit_rule


def _make_cm(rules=None):
    cm = MagicMock()
    cm.config = {
        "rules": rules or [
            {"id": 1, "name": "Old Name", "type": "traffic", "enabled": True, "threshold": 100},
        ]
    }
    cm.save = MagicMock()
    return cm


class TestRuleEditCommand:
    def test_edit_saves_changed_fields(self):
        cm = _make_cm()
        runner = CliRunner()
        with patch("src.config.ConfigManager", return_value=cm):
            with patch("questionary.text") as mock_text, \
                 patch("questionary.confirm") as mock_confirm:
                mock_text.return_value.unsafe_ask.side_effect = ["New Name", "50"]
                mock_confirm.return_value.unsafe_ask.side_effect = [False, True]
                result = runner.invoke(edit_rule, ["1", "--no-preview"])
        assert result.exit_code == 0, result.output
        assert cm.config["rules"][0]["name"] == "New Name"
        assert cm.config["rules"][0]["threshold"] == 50
        cm.save.assert_called_once()

    def test_edit_invalid_id_shows_error(self):
        cm = _make_cm()
        runner = CliRunner()
        with patch("src.config.ConfigManager", return_value=cm):
            result = runner.invoke(edit_rule, ["99"])
        assert result.exit_code != 0
        assert "out of range" in result.output

    def test_edit_abort_does_not_save(self):
        cm = _make_cm()
        runner = CliRunner()
        with patch("src.config.ConfigManager", return_value=cm):
            with patch("questionary.text") as mock_text, \
                 patch("questionary.confirm") as mock_confirm:
                mock_text.return_value.unsafe_ask.side_effect = ["New Name", "50"]
                # enabled=True, then Save?=False
                mock_confirm.return_value.unsafe_ask.side_effect = [True, False]
                result = runner.invoke(edit_rule, ["1"])
        assert result.exit_code == 0
        assert "Aborted" in result.output
        cm.save.assert_not_called()

    def test_edit_no_preview_skips_diff(self):
        cm = _make_cm()
        runner = CliRunner()
        with patch("src.config.ConfigManager", return_value=cm):
            with patch("questionary.text") as mock_text, \
                 patch("questionary.confirm") as mock_confirm:
                mock_text.return_value.unsafe_ask.side_effect = ["Updated", ""]
                mock_confirm.return_value.unsafe_ask.side_effect = [True]
                result = runner.invoke(edit_rule, ["1", "--no-preview"])
        assert result.exit_code == 0
        assert "saved" in result.output.lower()
        cm.save.assert_called_once()

    def test_edit_empty_threshold_keeps_existing(self):
        cm = _make_cm([{"id": 1, "name": "R", "type": "traffic", "enabled": True, "threshold": 200}])
        runner = CliRunner()
        with patch("src.config.ConfigManager", return_value=cm):
            with patch("questionary.text") as mock_text, \
                 patch("questionary.confirm") as mock_confirm:
                mock_text.return_value.unsafe_ask.side_effect = ["R", "   "]  # blank threshold
                mock_confirm.return_value.unsafe_ask.side_effect = [True]
                runner.invoke(edit_rule, ["1", "--no-preview"])
        assert cm.config["rules"][0]["threshold"] == 200  # unchanged
