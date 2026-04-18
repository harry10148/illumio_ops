"""Verify the new `illumio-ops` subcommand framework."""
from click.testing import CliRunner


def test_root_help_lists_subcommands():
    from src.cli.root import cli
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    # Check all planned subcommands appear in help
    for sub in ("monitor", "gui", "report", "status"):
        assert sub in result.output, f"subcommand {sub} missing from --help"


def test_version_subcommand():
    from src.cli.root import cli
    runner = CliRunner()
    result = runner.invoke(cli, ["version"])
    assert result.exit_code == 0
    assert "illumio" in result.output.lower()
