"""illumio-ops click-based CLI subcommand entrypoints.

Phase 1 introduced the click framework (monitor/gui/report/status/version).
Phase 3 added `illumio-ops config validate/show` — registered on `cli` in root.py.
"""
from src.cli.root import cli

__all__ = ["cli"]
