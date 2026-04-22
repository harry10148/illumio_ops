# Phase 16: Offline Bundle Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship two offline bundles — one Linux tarball and one Windows zip — each containing a portable CPython 3.12, pre-built wheels, and a bootstrap installer. Both install and run with zero internet access and zero pre-installed Python on the target host.

| Artifact | Target | Format |
|---|---|---|
| `illumio_ops-<ver>-offline-linux-x86_64.tar.gz` | RHEL 8 + RHEL 9 | `.tar.gz` |
| `illumio_ops-<ver>-offline-windows-x86_64.zip` | Windows 10/11, Windows Server 2019+ | `.zip` |

**Architecture:** Both bundles are built by a single `scripts/build_offline_bundle.sh` run on any Linux/WSL machine (cross-platform wheel download works natively via `pip download --platform`). Linux uses `manylinux_2_17_x86_64` wheels + `install.sh` + systemd unit. Windows uses `win_amd64` wheels + `install.ps1` + NSSM service. PDF export is disabled in both offline builds; HTML/XLSX/CSV work on both.

**Tech Stack:** bash + PowerShell, python-build-standalone (Astral), `manylinux_2_17_x86_64` + `win_amd64` PyPI wheels, systemd (Linux), NSSM (Windows).

---

## File Map

| Path | Action | Purpose |
|---|---|---|
| `requirements-offline.txt` | Create | requirements.txt minus weasyprint (shared by both platforms) |
| `src/report/exporters/pdf_exporter.py` | Modify | Add module-level `PDF_AVAILABLE` bool |
| `src/cli/report.py` | Modify | Guard `--format pdf` when `PDF_AVAILABLE=False` |
| `scripts/verify_deps.py` | Modify | Add `--offline-bundle` mode |
| `scripts/build_offline_bundle.sh` | Create | Builds **both** Linux + Windows bundles from Linux/WSL |
| `scripts/preflight.sh` | Create | Linux pre-install environment check (run before install.sh or setup.sh) |
| `scripts/preflight.ps1` | Create | Windows pre-install environment check (run before install.ps1 or install_service.ps1) |
| `scripts/setup.sh` | Create | Linux git-clone install + uninstall (`--action install\|uninstall`) |
| `scripts/install.sh` | Create | Linux offline-bundle install + uninstall (`--action install\|uninstall`) |
| `scripts/install.ps1` | Create | Windows offline-bundle install + uninstall (`-Action install\|uninstall`) |
| `deploy/illumio-ops.service` | Create | Linux systemd unit using PBS python |
| `deploy/install_service.ps1` | Modify | Add PBS python priority + `$InstallRoot` param (git-clone Windows, already has install/uninstall/status) |
| `tests/test_offline_pdf_degrade.py` | Create | PDF degrade + CLI guard tests |
| `tests/test_pdf_exporter.py` | Modify | Add `PDF_AVAILABLE` import test |
| `docs/User_Manual.md` | Modify | §1.2 Offline Bundle — Linux + Windows sections |

---

## Task 1: `PDF_AVAILABLE` flag + `requirements-offline.txt`

**Files:**
- Modify: `src/report/exporters/pdf_exporter.py`
- Create: `requirements-offline.txt`
- Create: `tests/test_offline_pdf_degrade.py`
- Modify: `tests/test_pdf_exporter.py`

- [ ] **Step 1: Write failing test for `PDF_AVAILABLE` flag**

Create `tests/test_offline_pdf_degrade.py`:

```python
"""Tests for offline-bundle PDF graceful-degrade behaviour."""
from __future__ import annotations


def test_pdf_available_flag_is_bool():
    from src.report.exporters.pdf_exporter import PDF_AVAILABLE
    assert isinstance(PDF_AVAILABLE, bool)


def test_requirements_offline_excludes_weasyprint(tmp_path):
    import os
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    offline_req = os.path.join(root, "requirements-offline.txt")
    assert os.path.exists(offline_req), "requirements-offline.txt not found"
    content = open(offline_req).read().lower()
    assert "weasyprint" not in content
    # Must still list the other core packages
    for pkg in ("flask", "pandas", "requests", "apscheduler", "loguru"):
        assert pkg in content, f"{pkg} missing from requirements-offline.txt"
```

- [ ] **Step 2: Run to confirm failure**

```bash
cd /mnt/d/RD/illumio_ops
python -m pytest tests/test_offline_pdf_degrade.py -v 2>&1 | head -30
```

Expected: `FAILED` – `ImportError: cannot import name 'PDF_AVAILABLE'` and file-not-found for requirements-offline.txt.

- [ ] **Step 3: Add `PDF_AVAILABLE` to `pdf_exporter.py`**

Replace the top of `src/report/exporters/pdf_exporter.py` so it reads:

```python
"""HTML -> PDF export via weasyprint.

On the RHEL RPM target (pango + cairo present) this works natively. On
Windows dev machines lacking GTK3, this module imports cleanly but export
will raise OSError — tests skip accordingly.
On the offline bundle (weasyprint excluded), PDF_AVAILABLE=False.
"""
from __future__ import annotations

from loguru import logger
from typing import Optional

try:
    import weasyprint as _wp  # noqa: F401 — probe only
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False


def export_pdf(html: str, output_path: str, base_url: Optional[str] = None) -> None:
    """Render HTML to a PDF file. base_url is used to resolve relative assets."""
    # Deferred import so modules importing pdf_exporter don't fail on Windows dev
    from weasyprint import HTML, CSS

    # Basic CJK + print CSS overlay
    cjk_css = CSS(string="""
        @page { size: A4; margin: 20mm; }
        body {
            font-family: "Noto Sans CJK TC", "Microsoft JhengHei",
                         "PingFang TC", "Heiti TC", sans-serif;
            font-size: 11pt;
            line-height: 1.5;
        }
        /* plotly <div> renders only in HTML — hide and fall back to <img>
           which the HTML exporter is expected to emit for PDF. */
        .plotly-fallback-img { display: inline-block; max-width: 100%; }
        div.plotly-graph-div, script[type="application/json"] { display: none; }
    """)
    HTML(string=html, base_url=base_url).write_pdf(output_path, stylesheets=[cjk_css])
    logger.info("pdf report written to {}", output_path)
```

- [ ] **Step 4: Create `requirements-offline.txt`**

```
# illumio_ops offline bundle — all packages from requirements.txt except weasyprint.
# weasyprint requires system cairo/pango which are not bundled.
# pip download target: --only-binary=:all: --platform manylinux_2_17_x86_64 --python-version 3.12

# ── Existing core ──────────────────────────────────────────────────────────────
flask>=3.0,<4.0
pandas>=2.0,<3.0
pyyaml>=6.0,<7.0

# ── Phase 1: CLI UX ────────────────────────────────────────────────────────────
rich>=13.7,<14.0
questionary>=2.0,<3.0
click>=8.1,<9.0
humanize>=4.9,<5.0

# ── Phase 2: HTTP client ───────────────────────────────────────────────────────
requests>=2.31,<3.0
orjson>=3.9,<4.0
cachetools>=5.3,<6.0

# ── Phase 3: Settings validation ──────────────────────────────────────────────
pydantic>=2.6,<3.0
pydantic-settings>=2.2,<3.0

# ── Phase 4: Web GUI security ─────────────────────────────────────────────────
flask-wtf>=1.2,<2.0
flask-limiter>=3.5,<4.0
flask-talisman>=1.1,<2.0
flask-login>=0.6,<0.7
argon2-cffi>=23.1,<25.0

# ── Phase 5: Reports (Excel + interactive charts; PDF excluded) ───────────────
openpyxl>=3.1,<4.0
matplotlib>=3.8,<4.0
plotly>=5.20,<6.0
pygments>=2.17,<3.0

# ── Phase 6: Scheduler ────────────────────────────────────────────────────────
APScheduler>=3.10,<4.0
SQLAlchemy>=2.0

# ── Phase 7: Logging ──────────────────────────────────────────────────────────
loguru>=0.7,<0.8
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
python -m pytest tests/test_offline_pdf_degrade.py::test_pdf_available_flag_is_bool \
                 tests/test_offline_pdf_degrade.py::test_requirements_offline_excludes_weasyprint -v
```

Expected: both PASSED.

- [ ] **Step 6: Also update `tests/test_pdf_exporter.py` to add PDF_AVAILABLE import test**

Append to `tests/test_pdf_exporter.py` (after the last existing test):

```python

def test_pdf_available_is_bool():
    from src.report.exporters.pdf_exporter import PDF_AVAILABLE
    assert isinstance(PDF_AVAILABLE, bool)
```

- [ ] **Step 7: Run full existing pdf_exporter suite to confirm no regressions**

```bash
python -m pytest tests/test_pdf_exporter.py -v
```

Expected: existing tests PASSED (or SKIPPED on systems without weasyprint); new test PASSED.

- [ ] **Step 8: Commit**

```bash
git add requirements-offline.txt \
        src/report/exporters/pdf_exporter.py \
        tests/test_offline_pdf_degrade.py \
        tests/test_pdf_exporter.py
git commit -m "feat(phase-16): PDF_AVAILABLE flag + requirements-offline.txt"
```

---

## Task 2: CLI guard for `--format pdf` when offline

**Files:**
- Modify: `src/cli/report.py`
- Modify: `tests/test_offline_pdf_degrade.py`

When `PDF_AVAILABLE=False`, `--format pdf` must raise a clean `ClickException`. `--format all` is NOT guarded — it already silently skips PDF via the existing try/except in the generators.

- [ ] **Step 1: Write failing tests for the CLI guard**

Append to `tests/test_offline_pdf_degrade.py`:

```python
from click.testing import CliRunner
from unittest.mock import patch


def _runner_invoke(cmd, args):
    runner = CliRunner()
    return runner.invoke(cmd, args, catch_exceptions=False)


def test_report_traffic_pdf_raises_when_unavailable():
    from src.cli.report import report_traffic
    with patch("src.report.exporters.pdf_exporter.PDF_AVAILABLE", False):
        result = CliRunner().invoke(report_traffic, ["--format", "pdf"])
    assert result.exit_code != 0
    assert "PDF export is not available" in result.output


def test_report_audit_pdf_raises_when_unavailable():
    from src.cli.report import report_audit
    with patch("src.report.exporters.pdf_exporter.PDF_AVAILABLE", False):
        result = CliRunner().invoke(report_audit, ["--format", "pdf"])
    assert result.exit_code != 0
    assert "PDF export is not available" in result.output


def test_report_ven_pdf_raises_when_unavailable():
    from src.cli.report import report_ven_status
    with patch("src.report.exporters.pdf_exporter.PDF_AVAILABLE", False):
        result = CliRunner().invoke(report_ven_status, ["--format", "pdf"])
    assert result.exit_code != 0
    assert "PDF export is not available" in result.output


def test_report_policy_usage_pdf_raises_when_unavailable():
    from src.cli.report import report_policy_usage
    with patch("src.report.exporters.pdf_exporter.PDF_AVAILABLE", False):
        result = CliRunner().invoke(report_policy_usage, ["--format", "pdf"])
    assert result.exit_code != 0
    assert "PDF export is not available" in result.output
```

- [ ] **Step 2: Run to confirm failure**

```bash
python -m pytest tests/test_offline_pdf_degrade.py -k "pdf_raises" -v 2>&1 | head -30
```

Expected: 4 tests FAILED (no guard yet).

- [ ] **Step 3: Add `_check_pdf_available()` to `src/cli/report.py`**

Insert after the imports, before `_REPORT_FORMATS`:

```python
def _check_pdf_available(fmt: str) -> None:
    """Raise ClickException if PDF was requested but weasyprint is not installed."""
    if fmt == "pdf":
        from src.report.exporters.pdf_exporter import PDF_AVAILABLE
        if not PDF_AVAILABLE:
            raise click.ClickException(
                "PDF export is not available in this build. "
                "Use --format html or --format xlsx."
            )
```

- [ ] **Step 4: Add guard calls to all 4 report commands**

In `report_traffic`:
```python
def report_traffic(source: str, file_path, fmt: str, output_dir, email: bool) -> None:
    """Generate Traffic Flow Report."""
    _check_pdf_available(fmt)
    for path in generate_traffic_report(
        source=source,
        file_path=file_path,
        fmt=fmt,
        output_dir=output_dir,
        email=email,
    ):
        click.echo(path)
```

In `report_audit`:
```python
def report_audit(start_date: str | None, end_date: str | None, fmt: str, output_dir) -> None:
    """Generate Audit Report."""
    _check_pdf_available(fmt)
    for path in generate_audit_report(
        start_date=start_date,
        end_date=end_date,
        fmt=fmt,
        output_dir=output_dir,
    ):
        click.echo(path)
```

In `report_ven_status`:
```python
def report_ven_status(fmt: str, output_dir) -> None:
    """Generate VEN Status Report."""
    _check_pdf_available(fmt)
    for path in generate_ven_status_report(fmt=fmt, output_dir=output_dir):
        click.echo(path)
```

In `report_policy_usage`:
```python
def report_policy_usage(
    source: str, file_path, start_date: str | None, end_date: str | None,
    fmt: str, output_dir,
) -> None:
    """Generate Policy Usage Report."""
    _check_pdf_available(fmt)
    for path in generate_policy_usage_report(
        source=source,
        file_path=file_path,
        start_date=start_date,
        end_date=end_date,
        fmt=fmt,
        output_dir=output_dir,
    ):
        click.echo(path)
```

- [ ] **Step 5: Run the new tests**

```bash
python -m pytest tests/test_offline_pdf_degrade.py -k "pdf_raises" -v
```

Expected: 4 tests PASSED.

- [ ] **Step 6: Confirm existing CLI compat-matrix tests still pass**

```bash
python -m pytest tests/test_cli_compat_matrix.py -v
```

Expected: all PASSED (the compat matrix uses `PDF_AVAILABLE=True` because weasyprint is in the dev environment).

- [ ] **Step 7: Run full suite baseline**

```bash
python -m pytest --tb=short -q 2>&1 | tail -5
```

Expected: ≥523 passed, 0 failed.

- [ ] **Step 8: Commit**

```bash
git add src/cli/report.py tests/test_offline_pdf_degrade.py
git commit -m "feat(phase-16): CLI guard for --format pdf when PDF_AVAILABLE=False"
```

---

## Task 3: `verify_deps.py` offline-bundle mode

**Files:**
- Modify: `scripts/verify_deps.py`
- Modify: `tests/test_offline_pdf_degrade.py`

- [ ] **Step 1: Write failing test**

Append to `tests/test_offline_pdf_degrade.py`:

```python
def test_verify_deps_offline_production_list_excludes_weasyprint():
    """The offline production package list must not contain weasyprint."""
    from scripts.verify_deps import PRODUCTION
    dist_names = [p.dist.lower() for p in PRODUCTION]
    # Baseline: weasyprint IS in the normal PRODUCTION list
    assert "weasyprint" in dist_names

    # Simulate offline bundle: filter as build_offline_bundle.sh does
    offline = [p for p in PRODUCTION if p.dist != "weasyprint"]
    offline_names = [p.dist.lower() for p in offline]
    assert "weasyprint" not in offline_names
    # All other packages must survive the filter
    assert len(offline) == len(PRODUCTION) - 1
```

- [ ] **Step 2: Run to confirm it passes already (it's a logic test)**

```bash
python -m pytest tests/test_offline_pdf_degrade.py::test_verify_deps_offline_production_list_excludes_weasyprint -v
```

Expected: PASSED (this test doesn't require a code change; it documents the invariant).

- [ ] **Step 3: Add `--offline-bundle` flag to `scripts/verify_deps.py`**

Replace the `main()` function with:

```python
def main() -> int:
    import argparse
    parser = argparse.ArgumentParser(
        description="Verify illumio_ops dependencies can be imported."
    )
    parser.add_argument(
        "--offline-bundle",
        action="store_true",
        help="Verify offline bundle: weasyprint must be absent; all others must import.",
    )
    args = parser.parse_args()

    print("illumio_ops dependency baseline verification")
    print(f"Python: {sys.version}")

    if args.offline_bundle:
        offline_production = [p for p in PRODUCTION if p.dist != "weasyprint"]
        failed = verify(offline_production, "Production (offline bundle — weasyprint excluded)", fatal=True)
        # Assert weasyprint is genuinely absent from this Python env
        try:
            importlib.import_module("weasyprint")
            print("  FAIL  weasyprint must NOT be installed in offline bundle env")
            return 1
        except (ImportError, OSError):
            print("  OK    weasyprint absent (expected for offline bundle)")
        if failed:
            print(f"\nFAILED: {len(failed)} package(s): {', '.join(failed)}")
            return 1
        print("\nOffline bundle dependency check passed.")
        return 0

    failed = verify(PRODUCTION, "Production", fatal=True)
    verify(DEV, "Development (non-fatal)", fatal=False)
    if failed:
        print(f"\nFAILED: {len(failed)} production package(s) missing: {', '.join(failed)}")
        print("Run: pip install -r requirements.txt")
        return 1
    print("\nAll production packages imported successfully.")
    return 0
```

- [ ] **Step 4: Run existing dependency baseline test to confirm no regressions**

```bash
python -m pytest tests/test_dependency_baseline.py -v
```

Expected: 3 tests PASSED.

- [ ] **Step 5: Run offline_pdf_degrade suite in full**

```bash
python -m pytest tests/test_offline_pdf_degrade.py -v
```

Expected: all PASSED.

- [ ] **Step 6: Commit**

```bash
git add scripts/verify_deps.py tests/test_offline_pdf_degrade.py
git commit -m "feat(phase-16): verify_deps --offline-bundle mode"
```

---

## Task 4: Build script, install/uninstall scripts (both platforms, both methods)

**Files:**
- Create: `scripts/build_offline_bundle.sh` — builds both Linux tarball + Windows zip
- Create: `scripts/setup.sh` — Linux git-clone install **and** uninstall (`--action install|uninstall`)
- Create: `scripts/install.sh` — Linux offline-bundle install **and** uninstall (`--action install|uninstall`)
- Create: `scripts/install.ps1` — Windows offline-bundle install **and** uninstall (`-Action install|uninstall`)
- Create: `deploy/illumio-ops.service` — Linux systemd unit using PBS python
- Modify: `deploy/install_service.ps1` — add PBS python priority + `$InstallRoot` param

These are infrastructure files — no pytest tests. Verification is the smoke test in Task 7.

### Script decision matrix

| Script | Deployment | Platform | install | uninstall |
|---|---|---|---|---|
| `scripts/setup.sh` | git clone | Linux | venv + pip + systemd unit | stop + disable + rm service file |
| `scripts/install.sh` | offline bundle | Linux | PBS python + wheels + systemd | stop + disable + rm service + rm dir + userdel |
| `deploy/install_service.ps1` | git clone | Windows | NSSM + venv/system python | NSSM remove (already exists) |
| `scripts/install.ps1` | offline bundle | Windows | PBS python + wheels + NSSM | NSSM remove + rm dir |

- [ ] **Step 1: Create `scripts/build_offline_bundle.sh`**

The script builds both Linux and Windows bundles in one run from any Linux/WSL machine.
Windows wheels are downloaded with `--platform win_amd64` — this works even on Linux.

```bash
#!/usr/bin/env bash
# Build illumio_ops offline bundles for Linux and Windows.
# Requires: curl, tar, zip, git, any Linux x86_64 with Python 3.10+.
# Output:
#   dist/illumio_ops-<version>-offline-linux-x86_64.tar.gz
#   dist/illumio_ops-<version>-offline-windows-x86_64.zip
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
DIST_DIR="$REPO_ROOT/dist"

VERSION="${VERSION:-$(cd "$REPO_ROOT" && git describe --tags --always 2>/dev/null || echo "dev")}"

# python-build-standalone release — update these two lines when upgrading Python
PBS_TAG="20241016"
PBS_PYTHON="3.12.7"

PBS_LINUX_URL="https://github.com/astral-sh/python-build-standalone/releases/download/${PBS_TAG}/cpython-${PBS_PYTHON}+${PBS_TAG}-x86_64-unknown-linux-gnu-install_only.tar.gz"
PBS_WIN_URL="https://github.com/astral-sh/python-build-standalone/releases/download/${PBS_TAG}/cpython-${PBS_PYTHON}+${PBS_TAG}-x86_64-pc-windows-msvc-install_only.tar.gz"

mkdir -p "$DIST_DIR"

# ── Shared helper: stage app files (no credentials) ───────────────────────────
stage_app() {
    local dest="$1"
    mkdir -p "$dest/app"
    rsync -a --exclude='__pycache__' --exclude='*.pyc' --exclude='.git' \
        "$REPO_ROOT/illumio_ops.py" \
        "$REPO_ROOT/src/" \
        "$dest/app/"
    # config templates only — NEVER bundle config.json (API credentials) or runtime data
    rsync -a \
        --exclude='config.json' \
        --exclude='rule_schedules.json' \
        "$REPO_ROOT/config/" "$dest/app/config/"
    rsync -a "$REPO_ROOT/scripts/" "$dest/app/scripts/"
    cp "$REPO_ROOT/requirements-offline.txt" "$dest/app/"
    echo "$VERSION" > "$dest/VERSION"
}

# ── Linux bundle ──────────────────────────────────────────────────────────────
build_linux() {
    local BUILD="$REPO_ROOT/build/offline-linux"
    local ARCHIVE="illumio_ops-${VERSION}-offline-linux-x86_64.tar.gz"
    echo "==> [Linux] Cleaning build dir"
    rm -rf "$BUILD" && mkdir -p "$BUILD"

    echo "==> [Linux] Downloading PBS ${PBS_PYTHON}"
    curl -fL "$PBS_LINUX_URL" | tar xz -C "$BUILD"

    echo "==> [Linux] Downloading manylinux_2_17_x86_64 wheels"
    mkdir -p "$BUILD/wheels"
    "$BUILD/python/bin/python3" -m pip download \
        --only-binary=:all: \
        --platform manylinux_2_17_x86_64 \
        --python-version 3.12 \
        --implementation cp \
        -d "$BUILD/wheels" \
        -r "$REPO_ROOT/requirements-offline.txt"

    stage_app "$BUILD"

    mkdir -p "$BUILD/deploy"
    cp "$REPO_ROOT/deploy/illumio-ops.service" "$BUILD/deploy/"
    cp "$REPO_ROOT/scripts/preflight.sh" "$BUILD/"
    chmod +x "$BUILD/preflight.sh"
    cp "$REPO_ROOT/scripts/install.sh" "$BUILD/"
    chmod +x "$BUILD/install.sh"

    echo "==> [Linux] Creating $ARCHIVE"
    tar czf "$DIST_DIR/$ARCHIVE" -C "$(dirname "$BUILD")" "$(basename "$BUILD")"
    echo "    Size: $(du -sh "$DIST_DIR/$ARCHIVE" | cut -f1)"
}

# ── Windows bundle ─────────────────────────────────────────────────────────────
build_windows() {
    local BUILD="$REPO_ROOT/build/offline-windows"
    local ARCHIVE="illumio_ops-${VERSION}-offline-windows-x86_64.zip"
    echo "==> [Windows] Cleaning build dir"
    rm -rf "$BUILD" && mkdir -p "$BUILD"

    echo "==> [Windows] Downloading PBS ${PBS_PYTHON} for Windows"
    curl -fL "$PBS_WIN_URL" | tar xz -C "$BUILD"

    echo "==> [Windows] Downloading win_amd64 wheels"
    mkdir -p "$BUILD/wheels"
    # Use the local Linux PBS pip to download Windows wheels (cross-platform download)
    "$REPO_ROOT/build/offline-linux/python/bin/python3" -m pip download \
        --only-binary=:all: \
        --platform win_amd64 \
        --python-version 3.12 \
        --implementation cp \
        -d "$BUILD/wheels" \
        -r "$REPO_ROOT/requirements-offline.txt"

    stage_app "$BUILD"

    mkdir -p "$BUILD/deploy"
    cp "$REPO_ROOT/deploy/install_service.ps1" "$BUILD/deploy/"
    cp "$REPO_ROOT/scripts/preflight.ps1" "$BUILD/"
    cp "$REPO_ROOT/scripts/install.ps1" "$BUILD/"

    echo "==> [Windows] Creating $ARCHIVE"
    (cd "$(dirname "$BUILD")" && zip -r "$DIST_DIR/$ARCHIVE" "$(basename "$BUILD")" -x "*.pyc" -x "__pycache__/*")
    echo "    Size: $(du -sh "$DIST_DIR/$ARCHIVE" | cut -f1)"
}

build_linux
build_windows

echo ""
echo "==> All bundles ready in dist/:"
ls -lh "$DIST_DIR"/illumio_ops-"${VERSION}"-offline-*.{tar.gz,zip} 2>/dev/null || true
```

- [ ] **Step 2: Mark it executable**

```bash
chmod +x /mnt/d/RD/illumio_ops/scripts/build_offline_bundle.sh
```

- [ ] **Step 3: Create `scripts/setup.sh`** (git clone deployment — Linux)

```bash
#!/usr/bin/env bash
# Setup illumio_ops from a git clone (venv + pip + systemd service).
# Run as root from the repository root.
# Usage:
#   sudo bash scripts/setup.sh                          # install
#   sudo bash scripts/setup.sh --action uninstall       # remove service (keeps repo)
set -euo pipefail

ACTION="install"
INTERVAL=10
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SERVICE_NAME="illumio-ops"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --action)   ACTION="$2";   shift 2 ;;
        --interval) INTERVAL="$2"; shift 2 ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

if [ "$ACTION" = "uninstall" ]; then
    echo "==> Stopping and disabling service"
    systemctl stop  "$SERVICE_NAME" 2>/dev/null || true
    systemctl disable "$SERVICE_NAME" 2>/dev/null || true
    rm -f "$SERVICE_FILE"
    systemctl daemon-reload
    echo "==> Service removed. The git clone directory was NOT deleted."
    echo "    To fully remove, delete the repository directory manually."
    exit 0
fi

# ── Install ───────────────────────────────────────────────────────────────────
echo "==> Creating virtualenv"
python3 -m venv "$REPO_ROOT/venv"

echo "==> Installing Python packages"
"$REPO_ROOT/venv/bin/pip" install -r "$REPO_ROOT/requirements.txt" --quiet

# First run: initialise config
if [ ! -f "$REPO_ROOT/config/config.json" ]; then
    cp "$REPO_ROOT/config/config.json.example" "$REPO_ROOT/config/config.json"
    echo "==> config/config.json created. Fill in your PCE credentials before starting."
fi

VENV_PYTHON="$REPO_ROOT/venv/bin/python3"

cat > "$SERVICE_FILE" << EOF
[Unit]
Description=Illumio PCE Ops
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=$(whoami)
WorkingDirectory=$REPO_ROOT
ExecStart=$VENV_PYTHON $REPO_ROOT/illumio_ops.py --monitor --interval $INTERVAL
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=illumio-ops

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable "$SERVICE_NAME"
echo "==> Setup complete."
echo "    Edit config : nano $REPO_ROOT/config/config.json"
echo "    Start service: sudo systemctl start $SERVICE_NAME"
```

- [ ] **Step 4: Create `scripts/install.sh`** (offline bundle deployment — Linux)

```bash
#!/usr/bin/env bash
# Install or uninstall the illumio_ops offline bundle.
# Run as root from the extracted bundle directory.
# Usage:
#   sudo ./install.sh                              # install / upgrade
#   sudo ./install.sh --action uninstall           # remove everything
#   sudo ./install.sh --install-root /opt/custom   # custom path
set -euo pipefail

ACTION="install"
INSTALL_ROOT="/opt/illumio_ops"
while [[ $# -gt 0 ]]; do
    case "$1" in
        --action)       ACTION="$2";       shift 2 ;;
        --install-root) INSTALL_ROOT="$2"; shift 2 ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

SERVICE_NAME="illumio-ops"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"

# ── Uninstall ─────────────────────────────────────────────────────────────────
if [ "$ACTION" = "uninstall" ]; then
    echo "==> Stopping and disabling service"
    systemctl stop    "$SERVICE_NAME" 2>/dev/null || true
    systemctl disable "$SERVICE_NAME" 2>/dev/null || true
    rm -f "$SERVICE_FILE"
    systemctl daemon-reload
    echo "==> Removing $INSTALL_ROOT"
    rm -rf "$INSTALL_ROOT"
    if id illumio_ops &>/dev/null; then
        userdel illumio_ops
        echo "==> User illumio_ops removed"
    fi
    echo "==> Uninstall complete."
    exit 0
fi

# ── Install / Upgrade ─────────────────────────────────────────────────────────
SRC="$(cd "$(dirname "$0")" && pwd)"
IS_UPGRADE=false
[ -f "$INSTALL_ROOT/config/config.json" ] && IS_UPGRADE=true

echo "==> Installing to $INSTALL_ROOT (upgrade=$IS_UPGRADE)"
mkdir -p "$INSTALL_ROOT"

rsync -a "$SRC/python/" "$INSTALL_ROOT/python/"

# Preserve operator-owned files on upgrade
rsync -a \
    --exclude='config/config.json' \
    --exclude='config/rule_schedules.json' \
    "$SRC/app/" "$INSTALL_ROOT/"

if [ "$IS_UPGRADE" = false ]; then
    cp "$INSTALL_ROOT/config/config.json.example" "$INSTALL_ROOT/config/config.json"
fi

"$INSTALL_ROOT/python/bin/python3" -m pip install \
    --no-index --find-links "$SRC/wheels" \
    -r "$INSTALL_ROOT/requirements-offline.txt" --quiet

if ! id illumio_ops &>/dev/null; then
    useradd --system --no-create-home --shell /sbin/nologin illumio_ops
fi
chown -R illumio_ops:illumio_ops "$INSTALL_ROOT"

install -m 0644 "$SRC/deploy/illumio-ops.service" "$SERVICE_FILE"
systemctl daemon-reload

if [ "$IS_UPGRADE" = true ]; then
    echo "==> Upgrade complete. Run: sudo systemctl restart $SERVICE_NAME"
else
    echo "==> Installation complete."
    echo "    Edit config : nano $INSTALL_ROOT/config/config.json"
    echo "    Start service: sudo systemctl enable --now $SERVICE_NAME"
fi
```

- [ ] **Step 5: Mark both scripts executable**

```bash
chmod +x /mnt/d/RD/illumio_ops/scripts/setup.sh
chmod +x /mnt/d/RD/illumio_ops/scripts/install.sh
```

- [ ] **Step 5: Create `deploy/illumio-ops.service`**

```ini
[Unit]
Description=Illumio PCE Ops (offline bundle)
Documentation=https://github.com/your-org/illumio_ops
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=illumio_ops
Group=illumio_ops
WorkingDirectory=/opt/illumio_ops
ExecStart=/opt/illumio_ops/python/bin/python3 /opt/illumio_ops/illumio_ops.py --monitor --interval 10
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=illumio-ops

# Security hardening
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/opt/illumio_ops

[Install]
WantedBy=multi-user.target
```

- [ ] **Step 6: Create `scripts/install.ps1`** (offline bundle — Windows, install + uninstall)

```powershell
<#
.SYNOPSIS
    Install or uninstall the illumio_ops offline bundle on Windows.
.DESCRIPTION
    install  : Copies bundled Python + app, installs wheels, registers NSSM service.
               Safe to re-run for upgrades — config.json and rule_schedules.json preserved.
    uninstall: Stops and removes the NSSM service, then deletes the install directory.
.PARAMETER Action
    install (default) | uninstall
.PARAMETER InstallRoot
    Installation directory. Default: C:\illumio_ops
.EXAMPLE
    .\install.ps1
    .\install.ps1 -Action uninstall
    .\install.ps1 -InstallRoot D:\illumio_ops
    .\install.ps1 -Action uninstall -InstallRoot D:\illumio_ops
#>
param(
    [ValidateSet("install", "uninstall")]
    [string]$Action = "install",
    [string]$InstallRoot = "C:\illumio_ops"
)

# Require elevation
if (-not ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole(
        [Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Host "ERROR: Run this script as Administrator." -ForegroundColor Red
    exit 1
}

$SRC = Split-Path -Parent $MyInvocation.MyCommand.Path

# ── Uninstall ─────────────────────────────────────────────────────────────────
if ($Action -eq "uninstall") {
    Write-Host "==> Removing NSSM service" -ForegroundColor Yellow
    & "$SRC\deploy\install_service.ps1" -Action uninstall -InstallRoot $InstallRoot
    Write-Host "==> Removing $InstallRoot" -ForegroundColor Yellow
    Remove-Item -Recurse -Force $InstallRoot -ErrorAction SilentlyContinue
    Write-Host "==> Uninstall complete." -ForegroundColor Green
    exit 0
}

# ── Install / Upgrade ─────────────────────────────────────────────────────────
$IsUpgrade = Test-Path (Join-Path $InstallRoot "config\config.json")

Write-Host "==> Installing to $InstallRoot  (upgrade=$IsUpgrade)" -ForegroundColor Cyan
New-Item -ItemType Directory -Path $InstallRoot -Force | Out-Null

Write-Host "==> Copying Python runtime"
Robocopy "$SRC\python" "$InstallRoot\python" /E /NP /NFL /NDL | Out-Null

Write-Host "==> Copying application files"
if ($IsUpgrade) {
    # Preserve operator-owned files on upgrade
    Robocopy "$SRC\app" "$InstallRoot" /E /NP /NFL /NDL `
        /XF "config.json" "rule_schedules.json" | Out-Null
} else {
    Robocopy "$SRC\app" "$InstallRoot" /E /NP /NFL /NDL | Out-Null
    Copy-Item "$InstallRoot\config\config.json.example" `
              "$InstallRoot\config\config.json" -Force
}

Write-Host "==> Installing Python packages (offline)"
& "$InstallRoot\python\python.exe" -m pip install `
    --no-index `
    --find-links "$SRC\wheels" `
    -r "$InstallRoot\requirements-offline.txt" `
    --quiet

Write-Host "==> Registering Windows service"
& "$SRC\deploy\install_service.ps1" -Action install -InstallRoot $InstallRoot

if ($IsUpgrade) {
    Write-Host "==> Upgrade complete. Restart: Restart-Service IllumioOps" -ForegroundColor Green
} else {
    Write-Host "==> Installation complete." -ForegroundColor Green
    Write-Host "    Edit config: notepad $InstallRoot\config\config.json" -ForegroundColor Gray
}
```

- [ ] **Step 7: Update `deploy/install_service.ps1` — prefer bundled python**

Replace the Python-detection block (lines 49–60) with:

```powershell
# Python priority: 1) bundled PBS  2) venv  3) system
$BundledPython = Join-Path $ProjectRoot "python\python.exe"
$VenvPython    = Join-Path $ProjectRoot "venv\Scripts\python.exe"
if (Test-Path $BundledPython) {
    $PythonExe = $BundledPython
    Write-Host "Using bundled Python: $PythonExe" -ForegroundColor Gray
} elseif (Test-Path $VenvPython) {
    $PythonExe = $VenvPython
    Write-Host "Using venv Python: $PythonExe" -ForegroundColor Gray
} else {
    $PythonExe = (Get-Command python -ErrorAction SilentlyContinue).Source
    if (-not $PythonExe) {
        Write-Host "ERROR: Python not found." -ForegroundColor Red
        exit 1
    }
}
```

Also add an `$InstallRoot` parameter at the top of `install_service.ps1` so `install.ps1` can pass the correct path:

```powershell
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("install", "uninstall", "status")]
    [string]$Action,

    [Parameter(Mandatory = $false)]
    [string]$NssmPath = "",

    [Parameter(Mandatory = $false)]
    [int]$Interval = 10,

    [Parameter(Mandatory = $false)]
    [string]$InstallRoot = ""   # if set, overrides $ProjectRoot for Python/EntryScript resolution
)
```

Then immediately after `$ProjectRoot = Split-Path -Parent $PSScriptRoot`, add:

```powershell
if ($InstallRoot -ne "") { $ProjectRoot = $InstallRoot }
```

- [ ] **Step 8: Create `scripts/preflight.sh`** (Linux pre-install check)

```bash
#!/usr/bin/env bash
# Pre-install environment check for illumio_ops offline bundle.
# Run BEFORE install.sh or setup.sh to validate the target host.
# Usage: bash preflight.sh
# Exit: 0 = all PASS/WARN, 1 = at least one FAIL
set -euo pipefail

BUNDLE_DIR="$(cd "$(dirname "$0")" && pwd)"
RED='\033[0;31m'; YEL='\033[1;33m'; GRN='\033[0;32m'; NC='\033[0m'
FAIL_COUNT=0

pass() { echo -e "  ${GRN}PASS${NC}  $1"; }
warn() { echo -e "  ${YEL}WARN${NC}  $1"; }
fail() { echo -e "  ${RED}FAIL${NC}  $1"; FAIL_COUNT=$((FAIL_COUNT + 1)); }

echo "illumio_ops pre-install check"
echo "=============================="

# 1. Architecture
ARCH=$(uname -m)
if [ "$ARCH" = "x86_64" ]; then pass "Architecture: $ARCH"
else fail "Architecture: $ARCH — bundle requires x86_64"; fi

# 2. glibc ≥ 2.17 (required by manylinux_2_17 wheels)
GLIBC_VER=$(ldd --version 2>&1 | head -1 | grep -oP '\d+\.\d+' | head -1 || echo "0.0")
GLIBC_MAJOR=$(echo "$GLIBC_VER" | cut -d. -f1)
GLIBC_MINOR=$(echo "$GLIBC_VER" | cut -d. -f2)
if [ "$GLIBC_MAJOR" -gt 2 ] || { [ "$GLIBC_MAJOR" -eq 2 ] && [ "$GLIBC_MINOR" -ge 17 ]; }; then
    pass "glibc: $GLIBC_VER (≥ 2.17 required)"
else
    fail "glibc: $GLIBC_VER — requires ≥ 2.17 (RHEL 7+)"
fi

# 3. systemd
if systemctl --version &>/dev/null; then pass "systemd: available"
else fail "systemd: not found — required for service registration"; fi

# 4. Disk space ≥ 500 MB at /opt
AVAIL_KB=$(df /opt 2>/dev/null | tail -1 | awk '{print $4}' || echo 0)
AVAIL_MB=$((AVAIL_KB / 1024))
if [ "$AVAIL_MB" -ge 500 ]; then pass "Disk at /opt: ${AVAIL_MB} MB (≥ 500 MB required)"
else fail "Disk at /opt: ${AVAIL_MB} MB — need ≥ 500 MB"; fi

# 5. rsync (used by install.sh)
if command -v rsync &>/dev/null; then pass "rsync: available"
else fail "rsync: not found — install with: dnf install rsync"; fi

# 6. Bundle integrity
if [ -f "$BUNDLE_DIR/VERSION" ]; then pass "Bundle VERSION: $(cat "$BUNDLE_DIR/VERSION")"
else fail "Bundle VERSION file missing — bundle may be corrupt"; fi

for dir in python wheels app deploy; do
    if [ -d "$BUNDLE_DIR/$dir" ]; then pass "Bundle dir: $dir/"
    else fail "Bundle dir missing: $dir/ — bundle may be corrupt"; fi
done

WHEEL_COUNT=$(find "$BUNDLE_DIR/wheels" -name "*.whl" 2>/dev/null | wc -l)
if [ "$WHEEL_COUNT" -ge 20 ]; then pass "Wheels: $WHEEL_COUNT .whl files (≥ 20 required)"
else fail "Wheels: only $WHEEL_COUNT .whl files — expected ≥ 20"; fi

BUNDLED_PY="$BUNDLE_DIR/python/bin/python3"
if [ -x "$BUNDLED_PY" ]; then pass "Bundled Python: $("$BUNDLED_PY" --version 2>&1)"
else fail "Bundled Python not executable: $BUNDLED_PY"; fi

# 7. Upgrade detection (informational)
INSTALL_ROOT="/opt/illumio_ops"
if [ -f "$INSTALL_ROOT/config/config.json" ]; then
    warn "Existing installation at $INSTALL_ROOT — this is an UPGRADE"
    warn "config.json and rule_schedules.json will be preserved"
else
    pass "No existing installation at $INSTALL_ROOT — fresh install"
fi

# 8. Port 5000
if ss -tlnp 2>/dev/null | grep -q ':5000 ' || netstat -tlnp 2>/dev/null | grep -q ':5000 '; then
    warn "Port 5000 is already in use — web UI may not start"
else
    pass "Port 5000: available"
fi

echo ""
echo "=============================="
if [ "$FAIL_COUNT" -gt 0 ]; then
    echo -e "${RED}PREFLIGHT FAILED: $FAIL_COUNT check(s) failed. Resolve before installing.${NC}"
    exit 1
else
    echo -e "${GRN}PREFLIGHT PASSED: Host is ready for installation.${NC}"
    exit 0
fi
```

- [ ] **Step 9: Create `scripts/preflight.ps1`** (Windows pre-install check)

```powershell
<#
.SYNOPSIS
    Pre-install environment check for illumio_ops offline bundle (Windows).
.DESCRIPTION
    Run BEFORE install.ps1 to validate the target host.
    Exit 0 = all PASS/WARN only.  Exit 1 = at least one FAIL.
.EXAMPLE
    .\preflight.ps1
#>

$BundleDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$FailCount = 0

function Pass { param($msg) Write-Host "  PASS  $msg" -ForegroundColor Green }
function Warn { param($msg) Write-Host "  WARN  $msg" -ForegroundColor Yellow }
function Fail { param($msg) Write-Host "  FAIL  $msg" -ForegroundColor Red; $script:FailCount++ }

Write-Host "illumio_ops pre-install check"
Write-Host "=============================="

# 1. OS version (Win10 / Server 2019+)
$osVer = [System.Environment]::OSVersion.Version
$caption = (Get-CimInstance Win32_OperatingSystem).Caption
if ($osVer.Major -ge 10) { Pass "OS: $caption" }
else { Fail "OS: $caption — Windows 10 / Server 2019 or newer required" }

# 2. Architecture
$arch = $env:PROCESSOR_ARCHITECTURE
if ($arch -eq "AMD64") { Pass "Architecture: $arch" }
else { Fail "Architecture: $arch — bundle requires AMD64 (x86_64)" }

# 3. PowerShell ≥ 5.1
$psVer = $PSVersionTable.PSVersion
if ($psVer.Major -gt 5 -or ($psVer.Major -eq 5 -and $psVer.Minor -ge 1)) {
    Pass "PowerShell: $($psVer.ToString())"
} else {
    Fail "PowerShell: $($psVer.ToString()) — requires 5.1+"
}

# 4. Administrator (WARN only — install.ps1 enforces elevation itself)
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole(
    [Security.Principal.WindowsBuiltInRole]::Administrator)
if ($isAdmin) { Pass "Running as Administrator" }
else { Warn "Not running as Administrator — install.ps1 requires elevation" }

# 5. NSSM
$nssmCmd    = Get-Command nssm.exe -ErrorAction SilentlyContinue
$nssmBundle = Join-Path $BundleDir "deploy\nssm.exe"
if ($nssmCmd) { Pass "NSSM: found at $($nssmCmd.Source)" }
elseif (Test-Path $nssmBundle) { Pass "NSSM: found in bundle at $nssmBundle" }
else { Fail "NSSM: not found — download nssm.exe from https://nssm.cc/download and place in PATH or deploy\" }

# 6. Disk space ≥ 500 MB on C:\
$drive = (Get-PSDrive C -ErrorAction SilentlyContinue)
if ($drive -and $drive.Free -ge 524288000) {
    Pass "Disk on C:\: $([int]($drive.Free / 1MB)) MB available (≥ 500 MB required)"
} elseif ($drive) {
    Fail "Disk on C:\: $([int]($drive.Free / 1MB)) MB — need ≥ 500 MB"
} else {
    Warn "Disk space: unable to determine"
}

# 7. Bundle integrity
$versionFile = Join-Path $BundleDir "VERSION"
if (Test-Path $versionFile) { Pass "Bundle VERSION: $((Get-Content $versionFile -Raw).Trim())" }
else { Fail "Bundle VERSION file missing — bundle may be corrupt" }

foreach ($dir in @("python", "wheels", "app", "deploy")) {
    $p = Join-Path $BundleDir $dir
    if (Test-Path $p) { Pass "Bundle dir: $dir\" }
    else { Fail "Bundle dir missing: $dir\ — bundle may be corrupt" }
}

$wheelCount = (Get-ChildItem (Join-Path $BundleDir "wheels") -Filter "*.whl" -ErrorAction SilentlyContinue | Measure-Object).Count
if ($wheelCount -ge 20) { Pass "Wheels: $wheelCount .whl files (≥ 20 required)" }
else { Fail "Wheels: only $wheelCount .whl files — expected ≥ 20" }

$bundledPython = Join-Path $BundleDir "python\python.exe"
if (Test-Path $bundledPython) {
    $pyVer = & $bundledPython --version 2>&1
    Pass "Bundled Python: $pyVer"
} else {
    Fail "Bundled Python not found: $bundledPython"
}

# 8. Upgrade detection
$installRoot = "C:\illumio_ops"
if (Test-Path (Join-Path $installRoot "config\config.json")) {
    Warn "Existing installation at $installRoot — this is an UPGRADE"
    Warn "config.json and rule_schedules.json will be preserved"
} else {
    Pass "No existing installation at $installRoot — fresh install"
}

Write-Host ""
Write-Host "=============================="
if ($FailCount -gt 0) {
    Write-Host "PREFLIGHT FAILED: $FailCount check(s) failed. Resolve before installing." -ForegroundColor Red
    exit 1
} else {
    Write-Host "PREFLIGHT PASSED: Host is ready for installation." -ForegroundColor Green
    exit 0
}
```

- [ ] **Step 10: Commit**

```bash
git add scripts/build_offline_bundle.sh \
        scripts/setup.sh scripts/install.sh scripts/install.ps1 \
        scripts/preflight.sh scripts/preflight.ps1 \
        deploy/illumio-ops.service deploy/install_service.ps1
git commit -m "feat(phase-16): install/uninstall + preflight scripts for Linux + Windows"
```

---

## Task 5: Docs update — User Manual offline install + upgrade sections

**Files:**
- Modify: `docs/User_Manual.md`

- [ ] **Step 1: Insert offline bundle section after `§1.2 RHEL 8+` block**

In `docs/User_Manual.md`, find the existing `#### Red Hat / CentOS (RHEL 8+)` block (around line 14) and insert a new subsection immediately after it:

````markdown
#### Red Hat / CentOS — Offline Bundle (air-gapped install)

Use this method when the target host has no internet access and cannot reach PyPI
or any package mirror. The bundle includes a portable CPython 3.12 interpreter and
all pre-built Python wheels — no `dnf`, no `python3`, no network required on the
target host.

> **Note:** PDF reports (`--format pdf`) are not available in the offline bundle.
> All other formats (HTML, XLSX, CSV) work normally.

##### Build the bundle (on any internet-connected Linux or WSL machine)

```bash
git clone <repo-url>
cd illumio_ops
bash scripts/build_offline_bundle.sh
# Output: dist/illumio_ops-<version>-offline-linux-x86_64.tar.gz
```

Transfer the `.tar.gz` to the air-gapped RHEL host (USB, SCP to a jump host, etc.).

##### First-time installation

```bash
tar xzf illumio_ops-<version>-offline-linux-x86_64.tar.gz
cd illumio_ops-<version>

# Validate the host environment before installing (exits 1 on any FAIL)
bash ./preflight.sh

# Install to /opt/illumio_ops, register systemd unit
sudo ./install.sh

# Fill in PCE API credentials (config.json was created from the example template)
sudo nano /opt/illumio_ops/config/config.json

# Enable and start the service
sudo systemctl enable --now illumio-ops
sudo systemctl status illumio-ops      # should show Active: active (running)
```

##### Upgrading to a new version

`install.sh` detects an existing installation and **never overwrites**:
- `config/config.json` — your PCE API credentials
- `config/rule_schedules.json` — your custom rule schedules

```bash
# 1. Stop the running service
sudo systemctl stop illumio-ops

# 2. Extract the new bundle (alongside the old one is fine)
tar xzf illumio_ops-<new-version>-offline-linux-x86_64.tar.gz
cd illumio_ops-<new-version>

# 3. Run install.sh — config.json and rule_schedules.json are preserved
sudo ./install.sh

# 4. Restart
sudo systemctl start illumio-ops
sudo systemctl status illumio-ops

# 5. Verify the new version
/opt/illumio_ops/python/bin/python3 /opt/illumio_ops/illumio_ops.py --version
```

> **If `report_config.yaml` was customised:** the upgrade replaces it with the
> bundled version (which may add new analysis parameters). Back it up before
> upgrading and re-apply your changes afterwards:
> ```bash
> sudo cp /opt/illumio_ops/config/report_config.yaml \
>         /opt/illumio_ops/config/report_config.yaml.bak
> # then run sudo ./install.sh, then merge your changes back
> ```

##### Verify offline build integrity

```bash
# Confirm weasyprint is absent and all other packages imported successfully
/opt/illumio_ops/python/bin/python3 \
    /opt/illumio_ops/scripts/verify_deps.py --offline-bundle
```
````

- [ ] **Step 2: Insert Windows offline bundle section after the Linux offline section**

Add the following subsection immediately after the Linux offline bundle section:

````markdown
#### Windows — Offline Bundle (air-gapped install)

**Prerequisites:** NSSM (Non-Sucking Service Manager) — download from https://nssm.cc/download
and place `nssm.exe` in your system PATH or in `C:\illumio_ops\deploy\`.

> **Note:** PDF reports (`--format pdf`) are not available in the offline bundle.
> All other formats (HTML, XLSX, CSV) work normally.

##### Build the bundle (on any internet-connected Linux or WSL machine)

```bash
git clone <repo-url>
cd illumio_ops
bash scripts/build_offline_bundle.sh
# Output: dist/illumio_ops-<version>-offline-windows-x86_64.zip
```

Transfer the `.zip` to the air-gapped Windows host.

##### First-time installation (run PowerShell as Administrator)

```powershell
# Extract the bundle (built-in Windows 11 / Server 2019+)
Expand-Archive illumio_ops-<version>-offline-windows-x86_64.zip -DestinationPath C:\

# Validate the host environment before installing (exits 1 on any FAIL)
cd C:\illumio_ops-<version>
.\preflight.ps1

# Install to C:\illumio_ops, register IllumioOps Windows service
.\install.ps1

# Fill in PCE API credentials
notepad C:\illumio_ops\config\config.json

# Verify the service is running
Get-Service IllumioOps
```

##### Upgrading to a new version (PowerShell as Administrator)

`install.ps1` detects an existing installation and **never overwrites**
`config\config.json` or `config\rule_schedules.json`.

```powershell
# 1. Stop the service
Stop-Service IllumioOps

# 2. Extract new bundle
Expand-Archive illumio_ops-<new-version>-offline-windows-x86_64.zip -DestinationPath C:\

# 3. Run install.ps1 — config preserved automatically
cd C:\illumio_ops-<new-version>
.\install.ps1

# 4. Verify
Get-Service IllumioOps   # should show Running
```

> **If `report_config.yaml` was customised:** back it up before upgrading:
> ```powershell
> Copy-Item C:\illumio_ops\config\report_config.yaml `
>           C:\illumio_ops\config\report_config.yaml.bak
> # then run .\install.ps1, then merge changes back
> ```
````

- [ ] **Step 3: Update `§8 Troubleshooting` table**

Add these rows to the existing troubleshooting table:

```markdown
| `PDF export is not available in this build` | Offline bundle excludes weasyprint | Use `--format html` or `--format xlsx` instead |
| After upgrade: old config loaded | `config.json` preserved as-is | Compare with `config.json.example` and add any new fields |
| Windows: `nssm.exe not found` | NSSM not in PATH | Add `nssm.exe` to PATH or place it in `C:\illumio_ops\deploy\` |
```

- [ ] **Step 4: Commit**

```bash
git add docs/User_Manual.md
git commit -m "docs(phase-16): offline bundle Linux + Windows install/upgrade steps in User Manual"
```

---

## Task 6: Baseline validation + update requirements.txt header comment

**Files:**
- Modify: `requirements.txt` (header comment only)

- [ ] **Step 1: Fix the stale header comment in `requirements.txt`**

The current header says `All packages bundled into the offline RPM via PyInstaller`. Replace with the accurate description:

```
# illumio_ops production runtime dependencies.
# For offline bundle packaging: use requirements-offline.txt (excludes weasyprint).
# Pinned to major version ranges; minor/patch upgrades allowed within range.
```

- [ ] **Step 2: Run the full test suite**

```bash
python -m pytest --tb=short -q 2>&1 | tail -10
```

Expected: ≥527 passed (523 baseline + 4 new offline_pdf_degrade tests), 0 failed.

- [ ] **Step 3: Run i18n audit**

```bash
python scripts/audit_i18n_usage.py 2>&1 | tail -5
```

Expected: `0 findings`.

- [ ] **Step 4: Commit**

```bash
git add requirements.txt
git commit -m "docs(phase-16): fix requirements.txt header comment"
```

---

## Task 7: E2E smoke test (manual — requires Rocky 8 or 9 container/WSL)

This task is a manual checklist, not pytest. Run it before tagging the release.

**Prerequisite:** A clean Rocky Linux 8 or 9 container or WSL instance with NO Python installed.

- [ ] **Step 1: Build the bundle on any Linux (WSL Ubuntu is fine)**

```bash
cd /mnt/d/RD/illumio_ops
bash scripts/build_offline_bundle.sh
ls -lh dist/illumio_ops-*-offline-linux-x86_64.tar.gz
```

Expected: file exists, size ≤ 280 MB.

- [ ] **Step 2: Verify archive content**

```bash
tar tzf dist/illumio_ops-*-offline-linux-x86_64.tar.gz | \
  grep -E "^[^/]+/(python|wheels|app|deploy|install\.sh|VERSION)" | \
  sed 's|/.*||' | sort -u
```

Expected output:
```
illumio_ops-<version>
```
(archive root), then inside: `python/`, `wheels/`, `app/`, `deploy/`, `install.sh`, `VERSION`.

- [ ] **Step 3: Verify weasyprint wheel absent**

```bash
tar tzf dist/illumio_ops-*-offline-linux-x86_64.tar.gz | grep -i weasyprint
```

Expected: no output (zero matches).

- [ ] **Step 4: Install on Rocky 8 (no internet)**

```bash
# Inside Rocky 8 container (no python3 installed)
tar xzf /path/to/illumio_ops-*-offline-linux-x86_64.tar.gz
cd illumio_ops-*
sudo ./install.sh
```

Expected: completes without errors, systemd unit installed.

- [ ] **Step 5: Start and verify service**

```bash
sudo systemctl start illumio-ops
sudo systemctl status illumio-ops
# Should show: Active: active (running)
```

- [ ] **Step 6: PDF degrade test on installed instance**

```bash
sudo /opt/illumio_ops/python/bin/python3 \
     /opt/illumio_ops/illumio_ops.py report traffic --format pdf
```

Expected:
```
Error: PDF export is not available in this build. Use --format html or --format xlsx.
```
Exit code: 1.

- [ ] **Step 7: Repeat Steps 4–6 on Rocky 9 using the same Linux .tar.gz**

Expected: identical behaviour (same artifact, no rebuilding).

- [ ] **Step 8: Linux upgrade config-preservation test**

```bash
# Plant a sentinel in config.json, then re-run install.sh
sudo sh -c 'echo "{\"_upgrade_test\": true}" > /opt/illumio_ops/config/config.json'
sudo ./install.sh

# Confirm sentinel survived
sudo grep "_upgrade_test" /opt/illumio_ops/config/config.json
```

Expected: `"_upgrade_test": true` still present.

- [ ] **Step 9: Linux verify_deps check**

```bash
/opt/illumio_ops/python/bin/python3 \
    /opt/illumio_ops/scripts/verify_deps.py --offline-bundle
```

Expected: `Offline bundle dependency check passed.` with no FAIL lines.

- [ ] **Step 10: Windows smoke test (requires Windows 10/11 or Server host)**

```powershell
# As Administrator — extract and install
Expand-Archive illumio_ops-<version>-offline-windows-x86_64.zip -DestinationPath C:\
cd C:\illumio_ops-<version>
.\install.ps1

# Verify service started
Get-Service IllumioOps   # Status should be Running

# Verify bundled python is used
C:\illumio_ops\python\python.exe --version
# Expected: Python 3.12.x

# PDF degrade
C:\illumio_ops\python\python.exe C:\illumio_ops\illumio_ops.py report traffic --format pdf
# Expected: Error: PDF export is not available in this build.
```

- [ ] **Step 11: Windows upgrade config-preservation test**

```powershell
# Plant sentinel
Set-Content C:\illumio_ops\config\config.json '{"_upgrade_test": true}'

# Re-run install.ps1 (upgrade path)
.\install.ps1

# Confirm sentinel survived
Get-Content C:\illumio_ops\config\config.json
# Expected: {"_upgrade_test": true}
```

- [ ] **Step 12: Final tag**

```bash
git tag v3.14.0-offline-bundle
```

---

## Audit Notes (self-review findings, no code changes needed)

- **`chart_renderer.py`** — file does not exist; chart rendering is inline in each HTML/XLSX exporter. No weasyprint dependency outside `pdf_exporter.py`. ✓
- **`src/loguru_config.py:81`** — calls `logging.getLogger("weasyprint").setLevel(WARNING)`. This uses stdlib `logging.getLogger` which is always available regardless of whether weasyprint is installed; it is a no-op in the offline bundle. No change needed. ✓
- **`tests/test_gui_security.py:1022`** — asserts `'pdf' in gui._ALLOWED_REPORT_FORMATS`. The GUI allowlist governs format validation on the web API; PDF requests are silently skipped by the generator's try/except (same as `--format all`). No change needed. ✓

---

## Summary

| Task | Tests Added | Key Files |
|---|---|---|
| T1 | 2 new | `pdf_exporter.py`, `requirements-offline.txt` |
| T2 | 4 new | `src/cli/report.py` |
| T3 | 1 new | `scripts/verify_deps.py` |
| T4 | 0 (manual) | `scripts/build_offline_bundle.sh`, `scripts/preflight.sh`, `scripts/preflight.ps1`, `scripts/setup.sh`, `scripts/install.sh`, `scripts/install.ps1`, `deploy/illumio-ops.service`, `deploy/install_service.ps1` |
| T5 | 0 | `docs/User_Manual.md` (Linux + Windows install/upgrade sections) |
| T6 | 0 | `requirements.txt` (comment only) |
| T7 | 0 (smoke) | Linux ×2 (EL8+EL9) + Windows ×1 |

**Net new tests: +7** (baseline 523 → 530).  
**No existing tests modified** (parity suite, compat matrix, pdf_exporter unchanged).

### Script reference

| Script | Deployment | Platform | Usage |
|---|---|---|---|
| `scripts/preflight.sh` | offline bundle | Linux | `bash ./preflight.sh` (before install) |
| `scripts/preflight.ps1` | offline bundle | Windows | `.\preflight.ps1` (before install) |
| `scripts/setup.sh` | git clone | Linux | `sudo bash scripts/setup.sh` / `--action uninstall` |
| `scripts/install.sh` | offline bundle | Linux | `sudo ./install.sh` / `--action uninstall` |
| `deploy/install_service.ps1` | git clone | Windows | `-Action install` / `-Action uninstall` |
| `scripts/install.ps1` | offline bundle | Windows | `.\install.ps1` (Admin) / `-Action uninstall` |

### Offline bundle artifacts produced

| File | Platform | Install | Uninstall |
|---|---|---|---|
| `illumio_ops-<ver>-offline-linux-x86_64.tar.gz` | RHEL 8 / RHEL 9 | `sudo ./install.sh` | `sudo ./install.sh --action uninstall` |
| `illumio_ops-<ver>-offline-windows-x86_64.zip` | Windows 10/11, Server 2019+ | `.\install.ps1` (Admin) | `.\install.ps1 -Action uninstall` (Admin) |

Both artifacts built from one `bash scripts/build_offline_bundle.sh` run on any Linux/WSL machine.
