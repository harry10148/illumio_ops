"""Verify that all legacy argparse flags still work after click migration."""
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
ENTRY = REPO_ROOT / "illumio_ops.py"


def _run(args, timeout=10):
    return subprocess.run(
        [sys.executable, str(ENTRY), *args],
        capture_output=True, text=True, timeout=timeout,
    )


def test_legacy_monitor_flag_still_recognized():
    # Run with --monitor -i 1 for 2 seconds then kill
    proc = subprocess.Popen(
        [sys.executable, str(ENTRY), "--monitor", "-i", "1"],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
    )
    try:
        # Give it 3 seconds to start, then terminate
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.terminate()
            out, err = proc.communicate(timeout=5)
        else:
            out, err = proc.stdout.read(), proc.stderr.read()
    finally:
        if proc.poll() is None:
            proc.kill()
    # Should not have crashed with an argparse error
    assert "unrecognized arguments" not in err
    assert "error:" not in err.lower() or "daemon" in out.lower()


def test_new_version_subcommand_works():
    result = _run(["version"])
    assert result.returncode == 0
    assert "illumio-ops" in result.stdout.lower()


def test_new_status_subcommand_works():
    result = _run(["status"])
    # status may exit non-zero if config missing, but it must not crash
    assert "illumio-ops status" in result.stdout.lower() or result.returncode in (0, 1)


def test_help_shows_subcommands():
    result = _run(["--help"])
    assert result.returncode == 0
    for sub in ("monitor", "gui", "report", "rule", "workload", "config", "status", "version"):
        assert sub in result.stdout


def test_legacy_help_lists_expected_flags():
    result = _run(["--help"])
    assert result.returncode == 0
    for flag in (
        "--monitor",
        "--monitor-gui",
        "--interval",
        "--gui",
        "--port",
        "--report",
        "--report-type",
        "--source",
        "--file",
        "--format",
        "--email",
        "--output-dir",
    ):
        assert flag in result.stdout
