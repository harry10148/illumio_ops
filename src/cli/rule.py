"""`illumio-ops rule ...` subcommand group."""
from __future__ import annotations

import click
from rich.console import Console
from rich.table import Table


@click.group("rule")
def rule_group() -> None:
    """Inspect monitoring rules."""


@rule_group.command("list")
@click.option(
    "--type", "rule_type",
    type=click.Choice(["event", "traffic", "bandwidth", "volume", "system", "all"]),
    default="all",
    help="Filter by rule type",
)
@click.option("--enabled-only", is_flag=True, default=False, help="Show only enabled rules")
def list_rules(rule_type: str, enabled_only: bool) -> None:
    """List configured monitoring rules."""
    from src.config import ConfigManager

    cm = ConfigManager()
    rules = cm.config.get("rules", [])
    if rule_type != "all":
        rules = [r for r in rules if r.get("type") == rule_type]
    if enabled_only:
        rules = [r for r in rules if r.get("enabled", True)]

    console = Console()
    table = Table(title=f"Monitoring Rules ({len(rules)})", show_header=True, header_style="cyan")
    table.add_column("#", justify="right", no_wrap=True, width=4)
    table.add_column("Type", width=12)
    table.add_column("Name")
    table.add_column("Enabled", justify="center", width=8)
    table.add_column("Threshold", justify="right", width=10)

    for i, r in enumerate(rules, 1):
        table.add_row(
            str(i),
            r.get("type", ""),
            r.get("name", ""),
            "✓" if r.get("enabled", True) else "✗",
            str(r.get("threshold", "")) if "threshold" in r else "-",
        )
    console.print(table)


@rule_group.command("edit")
@click.argument("rule_id", type=int)
@click.option("--no-preview", is_flag=True, help="Skip the diff preview before save")
def edit_rule(rule_id: int, no_preview: bool) -> None:
    """Interactively edit a rule by its 1-based index."""
    import json
    import questionary
    from src.config import ConfigManager
    from rich.syntax import Syntax

    cm = ConfigManager()
    rules = cm.config.get("rules", [])
    if rule_id < 1 or rule_id > len(rules):
        raise click.ClickException(f"rule_id {rule_id} out of range (1..{len(rules)})")

    rule = rules[rule_id - 1]
    before = json.dumps(rule, indent=2, ensure_ascii=False)

    name = questionary.text("Rule name:", default=rule.get("name", "")).unsafe_ask()
    enabled = questionary.confirm("Enabled?", default=bool(rule.get("enabled", True))).unsafe_ask()
    threshold_str = questionary.text(
        "Threshold (blank to keep):",
        default=str(rule.get("threshold", "")),
    ).unsafe_ask()

    rule["name"] = name
    rule["enabled"] = enabled
    if threshold_str.strip():
        try:
            rule["threshold"] = int(threshold_str)
        except ValueError:
            rule["threshold"] = threshold_str

    after = json.dumps(rule, indent=2, ensure_ascii=False)

    if not no_preview:
        console = Console()
        console.print("[bold]Before:[/bold]")
        console.print(Syntax(before, "json", theme="monokai", line_numbers=False))
        console.print("[bold]After:[/bold]")
        console.print(Syntax(after, "json", theme="monokai", line_numbers=False))
        if not questionary.confirm("Save changes?", default=True).unsafe_ask():
            click.echo("Aborted.")
            return

    cm.save()
    click.echo(f"Rule {rule_id} saved.")
