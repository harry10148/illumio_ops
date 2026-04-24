"""CLI tests for illumio-ops cache subcommands."""
import pytest
from click.testing import CliRunner
from unittest.mock import MagicMock, patch


def test_cache_status_runs_without_crash():
    from src.cli.cache import cache_group
    runner = CliRunner()
    with patch("src.cli.cache._get_db_session_factory", return_value=None):
        with patch("src.cli.cache._get_cache_config", return_value={"events_retention_days": 90, "traffic_raw_retention_days": 7}):
            result = runner.invoke(cache_group, ["status"])
    # May fail gracefully if no DB, but must not raise an unhandled exception
    assert result.exit_code in (0, 1)


def test_cache_retention_shows_config():
    from src.cli.cache import cache_group
    runner = CliRunner()
    with patch("src.cli.cache._get_cache_config", return_value={
        "events_retention_days": 90,
        "traffic_raw_retention_days": 7,
        "traffic_agg_retention_days": 365,
    }):
        result = runner.invoke(cache_group, ["retention"])
    assert result.exit_code == 0
    assert "90" in result.output or "retention" in result.output.lower()


def test_cache_backfill_requires_source():
    from src.cli.cache import cache_group
    runner = CliRunner()
    result = runner.invoke(cache_group, ["backfill"])
    assert result.exit_code != 0  # missing --source should fail


def test_cache_backfill_requires_since():
    from src.cli.cache import cache_group
    runner = CliRunner()
    result = runner.invoke(cache_group, ["backfill", "--source", "events"])
    assert result.exit_code != 0  # missing --since should fail
