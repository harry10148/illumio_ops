"""Verify the new `illumio-ops` subcommand framework."""
from click.testing import CliRunner


def test_root_help_lists_subcommands():
    from src.cli.root import cli
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    # Check all planned subcommands appear in help
    for sub in ("monitor", "gui", "report", "rule", "workload", "config", "status"):
        assert sub in result.output, f"subcommand {sub} missing from --help"


def test_version_subcommand():
    from src.cli.root import cli
    runner = CliRunner()
    result = runner.invoke(cli, ["version"])
    assert result.exit_code == 0
    assert "illumio" in result.output.lower()


def test_report_help_lists_report_subcommands():
    from src.cli.report import report_group
    runner = CliRunner()
    result = runner.invoke(report_group, ["--help"])
    assert result.exit_code == 0
    for sub in ("traffic", "audit", "ven-status", "policy-usage"):
        assert sub in result.output
