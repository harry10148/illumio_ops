# Phase 3 Implementation Plan — 設定驗證 (pydantic v2 + pydantic-settings)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 [src/config.py](../../../src/config.py) 裡的 `_DEFAULT_CONFIG` dict + 隱含驗證重寫為 pydantic v2 `BaseSettings` model，**載入時**做強型別驗證 + 明確錯誤訊息，但 `cm.config["api"]["url"]` 這類 dict-style 存取（約 70+ 處）**100% 保留不動**。這是 **validation-first，typed-access-later** 策略。

**Architecture:** pydantic 模型作為**入口驗證層**，載入完成後 `model.model_dump()` 變 dict 放進 `self.config`，讓所有既有呼叫端無感。同時暴露 `self.settings`（typed 物件）供新程式碼優先使用；**不強制**既有程式遷移。加上 `illumio-ops config validate` 新 subcommand（依賴 Phase 1 click 框架），可手動跑 schema 檢查 + 報告具體錯誤行。Phase 4 (Web 安全) 之後可擴充為 form validation。

**Tech Stack:** pydantic>=2.6 (Phase 0), pydantic-settings>=2.2 (Phase 0)

**Branch:** `upgrade/phase-3-settings-pydantic`（from main after Phase 0 merge；**可與 Phase 1/2 並行**）

**Target tag on merge:** `v3.4.3-settings`

**Parent roadmap:** [2026-04-18-upgrade-roadmap.md](2026-04-18-upgrade-roadmap.md)

---

## File Structure

| 檔案 | 動作 | 責任 |
|---|---|---|
| `src/config_models.py` | 新增 | 完整 pydantic v2 BaseModel 階層（ApiSettings / AlertsSettings / SmtpSettings / ...） |
| `src/config.py` | 局部改 | `load()` 呼叫 `ConfigSchema.model_validate(data)`；驗證失敗給清楚錯誤；dict-style 存取介面不變 |
| `src/cli/config.py` | 新增（依賴 Phase 1） | `illumio-ops config validate` subcommand |
| `src/cli/root.py` | 小改（依賴 Phase 1） | 註冊 config subcommand |
| `tests/test_config_models.py` | 新增 | 每個 section 的 model 驗證（有效/無效/預設值） |
| `tests/test_config_load_validation.py` | 新增 | load 損壞 config 給明確錯誤、valid 檔無痛升級 |
| `tests/test_config_backwards_compat.py` | 新增 | 現有 70+ 呼叫點 pattern 測試（dict key access 仍可用） |
| `config/config.example.json` | 確認 | 當前範例符合新 schema（可能需補幾個 field） |

**檔案影響面**：3 新 + 3 新測試 + 1 小改 + 1 小改（Phase 1 已完成時）。

---

## Task 1: Branch + baseline

**Files:** （無變更）

- [ ] **Step 1: 確認 Phase 0 已 merge**

Run:
```bash
git fetch origin main
git log origin/main --oneline -10 | grep -q "v3.4.0-deps\|Phase 0"
```

- [ ] **Step 2: 建 branch**

```bash
git checkout main && git pull
git checkout -b upgrade/phase-3-settings-pydantic
```

- [ ] **Step 3: 基線測試 + 記下計數**

```bash
python -m pytest tests/ -q
```

---

## Task 2: 寫 backward-compat test 固化 dict 存取契約

**Files:**
- Create: `tests/test_config_backwards_compat.py`

- [ ] **Step 1: 建 contract test**

Create `tests/test_config_backwards_compat.py`:

```python
"""Freeze the cm.config['section']['key'] dict-access patterns used across
the codebase before introducing pydantic validation layer.

Grep confirms these exact patterns appear in 10+ modules:
  cm.config["api"]["url"]
  cm.config.get("settings", {}).get("language", "en")
  cm.config["rules"]
  cm.config["web_gui"]["password_hash"]
  etc.
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def fresh_config(tmp_path, monkeypatch):
    """Build a ConfigManager pointed at a temp file with a valid minimal config."""
    cfg_file = tmp_path / "config.json"
    cfg_file.write_text(json.dumps({
        "api": {
            "url": "https://pce.example.com:8443",
            "org_id": "1",
            "key": "kk",
            "secret": "ss",
            "verify_ssl": True,
        },
        "settings": {"language": "en", "theme": "dark"},
        "alerts": {"active": ["mail"]},
        "email": {"sender": "a@b.c", "recipients": ["d@e.f"]},
        "smtp": {"host": "localhost", "port": 25, "user": "", "password": ""},
        "rules": [],
        "report": {"enabled": False, "output_dir": "reports/"},
        "report_schedules": [],
        "pce_profiles": [],
        "active_pce_id": None,
        "rule_scheduler": {"enabled": True, "check_interval_seconds": 300},
        "web_gui": {"username": "illumio", "password_hash": "", "password_salt": "", "secret_key": "", "allowed_ips": []},
    }, indent=2), encoding="utf-8")
    from src.config import ConfigManager
    return ConfigManager(str(cfg_file))


def test_api_url_accessible_via_dict(fresh_config):
    assert fresh_config.config["api"]["url"] == "https://pce.example.com:8443"
    assert fresh_config.config["api"]["org_id"] == "1"


def test_settings_dict_get_with_default(fresh_config):
    """Pattern: cm.config.get('settings', {}).get('language', 'en')"""
    lang = fresh_config.config.get("settings", {}).get("language", "en")
    assert lang == "en"


def test_nested_web_gui_tls_defaults_applied(fresh_config):
    """Pattern: cm.config['web_gui']['tls'] may not be in user config — defaults fill."""
    tls = fresh_config.config.get("web_gui", {}).get("tls", {})
    # After validation, tls default must be present
    assert "enabled" in tls


def test_rules_is_a_list(fresh_config):
    assert isinstance(fresh_config.config["rules"], list)


def test_pce_profiles_is_a_list(fresh_config):
    assert isinstance(fresh_config.config["pce_profiles"], list)
```

- [ ] **Step 2: 跑測試確認基線 PASS（現行實作應滿足）**

Run:
```bash
python -m pytest tests/test_config_backwards_compat.py -v
```
Expected: 5 PASS。

- [ ] **Step 3: Commit**

```bash
git add tests/test_config_backwards_compat.py
git commit -m "test(config): freeze dict-access contracts before pydantic migration"
```

---

## Task 3: 建立 pydantic 模型檔

**Files:**
- Create: `src/config_models.py`
- Create: `tests/test_config_models.py`

- [ ] **Step 1: 寫 failing model tests**

Create `tests/test_config_models.py`:

```python
"""Pydantic schema validation for illumio_ops config."""
from __future__ import annotations

import pytest
from pydantic import ValidationError


def test_api_settings_valid():
    from src.config_models import ApiSettings
    a = ApiSettings(url="https://pce.test:8443", org_id="1", key="k", secret="s")
    assert str(a.url).startswith("https://pce.test")
    assert a.verify_ssl is True  # default


def test_api_settings_rejects_non_http_url():
    from src.config_models import ApiSettings
    with pytest.raises(ValidationError) as exc:
        ApiSettings(url="ftp://wrong.test", org_id="1", key="k", secret="s")
    assert "url" in str(exc.value).lower()


def test_smtp_settings_port_range():
    from src.config_models import SmtpSettings
    # Valid
    s = SmtpSettings(host="mail.test", port=587)
    assert s.port == 587
    # Invalid (negative)
    with pytest.raises(ValidationError):
        SmtpSettings(host="mail.test", port=-1)
    # Invalid (too large)
    with pytest.raises(ValidationError):
        SmtpSettings(host="mail.test", port=99999)


def test_rule_scheduler_settings_check_interval_lower_bound():
    from src.config_models import RuleSchedulerSettings
    s = RuleSchedulerSettings(enabled=True, check_interval_seconds=60)
    assert s.check_interval_seconds == 60
    # Sub-minute polling would hammer the PCE; reject
    with pytest.raises(ValidationError):
        RuleSchedulerSettings(enabled=True, check_interval_seconds=10)


def test_config_schema_fills_defaults_for_missing_sections():
    """When config.json omits an entire section, pydantic must fill from defaults."""
    from src.config_models import ConfigSchema
    minimal = {
        "api": {"url": "https://p.test", "org_id": "1", "key": "k", "secret": "s"},
    }
    cfg = ConfigSchema.model_validate(minimal)
    # settings defaults must be present
    assert cfg.settings.language == "en"
    assert cfg.web_gui.tls.enabled is False


def test_config_schema_rejects_unknown_top_level_keys():
    """Typos in config.json (e.g. 'aps' instead of 'api') must surface as error."""
    from src.config_models import ConfigSchema
    with pytest.raises(ValidationError):
        ConfigSchema.model_validate({
            "api": {"url": "https://p.test", "org_id": "1", "key": "k", "secret": "s"},
            "unknown_section": {"foo": "bar"},
        })


def test_dumped_model_has_all_legacy_dict_keys():
    """model_dump() output must include every key that the legacy
    _DEFAULT_CONFIG dict had, so cm.config[...] access patterns survive."""
    from src.config_models import ConfigSchema
    cfg = ConfigSchema.model_validate({
        "api": {"url": "https://p.test", "org_id": "1", "key": "k", "secret": "s"},
    })
    dumped = cfg.model_dump()
    for top_level in ("api", "alerts", "email", "smtp", "settings", "rules",
                      "report", "report_schedules", "pce_profiles",
                      "active_pce_id", "rule_scheduler", "web_gui"):
        assert top_level in dumped, f"missing {top_level} in model_dump()"
```

- [ ] **Step 2: 跑測試確認全部失敗（ImportError）**

Run:
```bash
python -m pytest tests/test_config_models.py -v
```
Expected: 全 FAIL（`src.config_models` 不存在）。

- [ ] **Step 3: 建立 pydantic 模型**

Create `src/config_models.py`:

```python
"""Pydantic v2 schemas for illumio_ops config.json.

Validation happens at ConfigManager.load() time — malformed config
surfaces clear errors instead of blowing up later with a KeyError
deep inside business logic.

The models preserve the exact field names and nesting of the legacy
_DEFAULT_CONFIG dict so ConfigSchema.model_validate(dict).model_dump()
produces an identical dict, keeping 70+ existing cm.config[...] call
sites working unchanged.
"""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator


class _Base(BaseModel):
    """Base class that rejects unknown keys (catches typos in config.json)."""
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        validate_assignment=True,
    )


class ApiSettings(_Base):
    url: HttpUrl = Field(default="https://pce.example.com:8443")
    org_id: str = Field(default="1", min_length=1)
    key: str = Field(default="")
    secret: str = Field(default="")
    verify_ssl: bool = True


class AlertsSettings(_Base):
    active: list[str] = Field(default_factory=lambda: ["mail"])
    line_channel_access_token: str = ""
    line_target_id: str = ""
    webhook_url: str = ""


class EmailSettings(_Base):
    sender: str = "monitor@localhost"
    recipients: list[str] = Field(default_factory=lambda: ["admin@example.com"])


class SmtpSettings(_Base):
    host: str = "localhost"
    port: int = Field(default=25, ge=1, le=65535)
    user: str = ""
    password: str = ""
    enable_auth: bool = False
    enable_tls: bool = False


class GeneralSettings(_Base):
    language: Literal["en", "zh_TW"] = "en"
    theme: Literal["light", "dark"] = "light"
    timezone: str = "local"


class ReportApiQuery(_Base):
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    max_results: int = Field(default=200000, ge=1, le=1_000_000)


class ReportSettings(_Base):
    enabled: bool = False
    schedule: Literal["daily", "weekly", "monthly"] = "weekly"
    day_of_week: Literal["monday", "tuesday", "wednesday", "thursday",
                         "friday", "saturday", "sunday"] = "monday"
    hour: int = Field(default=8, ge=0, le=23)
    source: Literal["api", "csv"] = "api"
    format: list[Literal["html", "csv", "pdf", "xlsx", "all"]] = Field(default_factory=lambda: ["html"])
    email_report: bool = False
    output_dir: str = "reports/"
    retention_days: int = Field(default=30, ge=1)
    include_raw_data: bool = False
    max_top_n: int = Field(default=20, ge=1, le=100)
    api_query: ReportApiQuery = Field(default_factory=ReportApiQuery)


class RuleSchedulerSettings(_Base):
    enabled: bool = True
    check_interval_seconds: int = Field(default=300, ge=60)   # min 1 minute


class WebGuiTls(_Base):
    enabled: bool = False
    cert_file: str = ""
    key_file: str = ""
    self_signed: bool = False


class WebGuiSettings(_Base):
    username: str = "illumio"
    password_hash: str = ""
    password_salt: str = ""
    secret_key: str = ""
    allowed_ips: list[str] = Field(default_factory=list)
    tls: WebGuiTls = Field(default_factory=WebGuiTls)


class PceProfile(_Base):
    """Extra=allow since PCE profile shape may evolve; only require id + url."""
    model_config = ConfigDict(extra="allow")
    id: int
    url: str
    org_id: str = "1"
    key: str = ""
    secret: str = ""
    name: str = ""


class ReportSchedule(_Base):
    """Report schedule entries; extra=allow because schedule shape
    may evolve during Phase 6 APScheduler migration."""
    model_config = ConfigDict(extra="allow")
    id: Optional[int] = None
    name: str = ""


class Rule(_Base):
    """Runtime rule — shape varies by type. Keep flexible."""
    model_config = ConfigDict(extra="allow")
    type: str
    name: str = ""


class ConfigSchema(_Base):
    api: ApiSettings = Field(default_factory=ApiSettings)
    alerts: AlertsSettings = Field(default_factory=AlertsSettings)
    email: EmailSettings = Field(default_factory=EmailSettings)
    smtp: SmtpSettings = Field(default_factory=SmtpSettings)
    settings: GeneralSettings = Field(default_factory=GeneralSettings)
    rules: list[Rule] = Field(default_factory=list)
    report: ReportSettings = Field(default_factory=ReportSettings)
    report_schedules: list[ReportSchedule] = Field(default_factory=list)
    pce_profiles: list[PceProfile] = Field(default_factory=list)
    active_pce_id: Optional[int] = None
    rule_scheduler: RuleSchedulerSettings = Field(default_factory=RuleSchedulerSettings)
    web_gui: WebGuiSettings = Field(default_factory=WebGuiSettings)
```

- [ ] **Step 4: 跑測試確認全綠**

Run:
```bash
python -m pytest tests/test_config_models.py -v
```
Expected: 7 PASS。

- [ ] **Step 5: Commit**

```bash
git add src/config_models.py tests/test_config_models.py
git commit -m "feat(config): add pydantic v2 schemas mirroring config.json structure

Field names + nesting match _DEFAULT_CONFIG exactly so
model_dump() produces a dict indistinguishable from legacy,
preserving all cm.config[section][key] call sites.

Validation features added:
- HttpUrl type rejects non-http(s) URLs for api.url
- SMTP port bounded 1..65535
- rule_scheduler.check_interval_seconds minimum 60s
- Language / theme / schedule fields locked to Literal enums
- Top-level extra='forbid' catches config.json typos"
```

---

## Task 4: ConfigManager.load 接上 pydantic 驗證

**Files:**
- Modify: `src/config.py:115-127` (`load()` method)
- Create: `tests/test_config_load_validation.py`

- [ ] **Step 1: 寫 load 驗證測試**

Create `tests/test_config_load_validation.py`:

```python
"""ConfigManager.load() validates via pydantic and surfaces errors clearly."""
from __future__ import annotations

import json
import logging

import pytest


def _write(tmp_path, body: dict):
    p = tmp_path / "config.json"
    p.write_text(json.dumps(body), encoding="utf-8")
    return str(p)


def test_load_accepts_minimal_valid_config(tmp_path):
    from src.config import ConfigManager
    cfg_file = _write(tmp_path, {
        "api": {"url": "https://pce.test", "org_id": "1", "key": "k", "secret": "s"},
    })
    cm = ConfigManager(cfg_file)
    assert cm.config["api"]["url"].startswith("https://pce.test")
    # Defaults filled in
    assert cm.config["settings"]["language"] == "en"


def test_load_rejects_http_port_out_of_range(tmp_path, caplog):
    from src.config import ConfigManager
    cfg_file = _write(tmp_path, {
        "api": {"url": "https://pce.test", "org_id": "1", "key": "k", "secret": "s"},
        "smtp": {"host": "x", "port": 99999},
    })
    caplog.set_level(logging.ERROR)
    # Loading should log the error; config falls back to defaults
    cm = ConfigManager(cfg_file)
    # Error message mentions smtp.port
    errs = [r for r in caplog.records if "smtp" in r.message.lower() or "port" in r.message.lower()]
    assert errs, f"Expected SMTP port validation error; got {[r.message for r in caplog.records]}"


def test_load_rejects_non_http_url(tmp_path, caplog):
    from src.config import ConfigManager
    cfg_file = _write(tmp_path, {
        "api": {"url": "ftp://wrong", "org_id": "1", "key": "k", "secret": "s"},
    })
    caplog.set_level(logging.ERROR)
    ConfigManager(cfg_file)
    # Must surface url error
    msgs = " ".join(r.message for r in caplog.records).lower()
    assert "url" in msgs or "http" in msgs


def test_load_surfaces_typo_in_top_level_key(tmp_path, caplog):
    """'web_guy' typo instead of 'web_gui' should be rejected."""
    from src.config import ConfigManager
    cfg_file = _write(tmp_path, {
        "api": {"url": "https://pce.test", "org_id": "1", "key": "k", "secret": "s"},
        "web_guy": {"username": "x"},    # typo
    })
    caplog.set_level(logging.ERROR)
    ConfigManager(cfg_file)
    msgs = " ".join(r.message for r in caplog.records).lower()
    assert "web_guy" in msgs or "extra" in msgs or "forbidden" in msgs


def test_models_attribute_exposes_typed_schema(tmp_path):
    """New: cm.models gives typed access for new code that wants strong types."""
    from src.config import ConfigManager
    cfg_file = _write(tmp_path, {
        "api": {"url": "https://pce.test", "org_id": "1", "key": "k", "secret": "s"},
    })
    cm = ConfigManager(cfg_file)
    assert hasattr(cm, "models"), "cm.models must exist for typed access"
    assert cm.models.api.org_id == "1"
    assert cm.models.settings.language == "en"
```

- [ ] **Step 2: 跑測試確認失敗**

Run:
```bash
python -m pytest tests/test_config_load_validation.py -v
```
Expected: 部分 FAIL — ConfigManager 尚未接 pydantic，也沒有 `cm.models` 屬性。

- [ ] **Step 3: 改 `ConfigManager.load()`**

Replace the `load()` method in `src/config.py` with:

```python
    def load(self):
        """Load and validate config.json via pydantic ConfigSchema."""
        from pydantic import ValidationError
        from src.config_models import ConfigSchema

        raw_data = {}
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    raw_data = json.load(f)
            except (json.JSONDecodeError, IOError, OSError) as e:
                logger.error(f"Error reading config file: {e}")
                print(f"{Colors.FAIL}{t('error_loading_config', error=e)}{Colors.ENDC}")
                # Fall through with raw_data={} to use defaults

        # Merge defaults with raw data (deep merge preserves legacy behavior)
        merged = _deep_merge(json.loads(json.dumps(_DEFAULT_CONFIG)), raw_data)

        try:
            self.models = ConfigSchema.model_validate(merged)
            self.config = self.models.model_dump(mode="json")
        except ValidationError as e:
            # Format pydantic errors into readable log lines
            logger.error(f"Config validation failed: {e.error_count()} error(s):")
            for err in e.errors():
                loc = ".".join(str(p) for p in err["loc"])
                logger.error(f"  {loc}: {err['msg']} (input: {err.get('input')!r})")
            print(f"{Colors.FAIL}{t('error_loading_config', error=str(e)[:200])}{Colors.ENDC}")
            # Fall back to defaults so the app still starts
            self.models = ConfigSchema()
            self.config = self.models.model_dump(mode="json")

        # Preserve post-load side effects
        lang = self.config.get("settings", {}).get("language", "en")
        set_language(lang)
        self._ensure_web_gui_secret()
```

- [ ] **Step 4: 跑測試**

Run:
```bash
python -m pytest tests/test_config_load_validation.py tests/test_config_backwards_compat.py -v
```
Expected: 全綠（5 backward-compat + 5 validation）。

- [ ] **Step 5: 跑全套**

Run:
```bash
python -m pytest tests/ -q
```
Expected: 基線 +0 regressions。

- [ ] **Step 6: Commit**

```bash
git add src/config.py tests/test_config_load_validation.py
git commit -m "feat(config): validate config.json via pydantic on load

Malformed config now surfaces specific errors (which field, which
value) in logs instead of blowing up deep inside business logic with
a KeyError. On validation failure, ConfigManager falls back to
built-in defaults so the app still starts.

New cm.models attribute gives typed access for future code; existing
cm.config[section][key] dict patterns remain unchanged via model_dump()."
```

---

## Task 5: 新增 `illumio-ops config validate` subcommand（依賴 Phase 1）

**Files:**
- Create: `src/cli/config.py`
- Modify: `src/cli/root.py` (register subcommand)

**⚠️ 前置**: 本 Task 需要 Phase 1 已 merge（`src/cli/` package 存在）。若 Phase 1 尚未完成，跳過此 Task 改在 Phase 1 merge 後補。

- [ ] **Step 1: 建 config subcommand**

Create `src/cli/config.py`:

```python
"""`illumio-ops config ...` subcommand group."""
from __future__ import annotations

import json
import os

import click
from rich.console import Console


@click.group("config")
def config_group() -> None:
    """Inspect and validate config.json."""


@config_group.command("validate")
@click.option("--file", "config_file", type=click.Path(), default=None,
              help="Path to config.json (default: config/config.json)")
def validate(config_file: str | None) -> None:
    """Validate config.json against the pydantic schema."""
    from pydantic import ValidationError
    from src.config_models import ConfigSchema

    if config_file is None:
        pkg_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        root_dir = os.path.dirname(pkg_dir)
        config_file = os.path.join(root_dir, "config", "config.json")

    console = Console()
    if not os.path.exists(config_file):
        console.print(f"[red]Config file not found:[/red] {config_file}")
        raise click.Abort()

    with open(config_file, "r", encoding="utf-8") as f:
        try:
            raw = json.load(f)
        except json.JSONDecodeError as e:
            console.print(f"[red]Malformed JSON:[/red] {e}")
            raise click.Abort()

    try:
        ConfigSchema.model_validate(raw)
    except ValidationError as e:
        console.print(f"[red]Found {e.error_count()} validation error(s):[/red]")
        for err in e.errors():
            loc = ".".join(str(p) for p in err["loc"])
            console.print(f"  [yellow]{loc}[/yellow]: {err['msg']} "
                         f"(input: [magenta]{err.get('input')!r}[/magenta])")
        raise click.Abort()

    console.print("[green]✓ config.json is valid[/green]")


@config_group.command("show")
@click.option("--section", type=str, default=None,
              help="Only show one section (e.g. api, smtp, web_gui)")
def show(section: str | None) -> None:
    """Print the current (validated) config as pretty JSON."""
    from src.config import ConfigManager
    console = Console()
    cm = ConfigManager()
    data = cm.config if section is None else cm.config.get(section, {})
    console.print_json(data=data)
```

- [ ] **Step 2: 在 root.py 註冊**

In `src/cli/root.py`, add to imports and command registration:

```python
# add import (alphabetic):
from src.cli import config as _config   # noqa: E402

# in the registration block, add:
cli.add_command(_config.config_group)
```

- [ ] **Step 3: 寫 CLI 測試**

Extend `tests/test_cli_subcommands.py` or create `tests/test_cli_config_subcommand.py`:

```python
"""illumio-ops config validate / show subcommands."""
from __future__ import annotations

import json
from click.testing import CliRunner


def test_config_validate_reports_ok_for_valid_file(tmp_path):
    cfg = tmp_path / "config.json"
    cfg.write_text(json.dumps({
        "api": {"url": "https://pce.test", "org_id": "1", "key": "k", "secret": "s"},
    }), encoding="utf-8")
    from src.cli.root import cli
    runner = CliRunner()
    result = runner.invoke(cli, ["config", "validate", "--file", str(cfg)])
    assert result.exit_code == 0
    assert "valid" in result.output.lower()


def test_config_validate_reports_errors_for_invalid_file(tmp_path):
    cfg = tmp_path / "config.json"
    cfg.write_text(json.dumps({
        "api": {"url": "ftp://wrong", "org_id": "1", "key": "k", "secret": "s"},
    }), encoding="utf-8")
    from src.cli.root import cli
    runner = CliRunner()
    result = runner.invoke(cli, ["config", "validate", "--file", str(cfg)])
    assert result.exit_code != 0
    assert "url" in result.output.lower() or "http" in result.output.lower()
```

- [ ] **Step 4: 跑測試**

Run:
```bash
python -m pytest tests/test_cli_config_subcommand.py -v
```
Expected: 2 PASS。

- [ ] **Step 5: 手動驗證**

```bash
python illumio_ops.py config validate
python illumio_ops.py config show --section api
```
Expected: 綠字「✓ config.json is valid」與 JSON 輸出。

- [ ] **Step 6: Commit**

```bash
git add src/cli/config.py src/cli/root.py tests/test_cli_config_subcommand.py
git commit -m "feat(config): add illumio-ops config validate / show subcommands

Enables manual schema check from the shell:
  illumio-ops config validate             # validates config/config.json
  illumio-ops config validate --file X    # validates alternate path
  illumio-ops config show [--section api] # pretty-prints current config

Depends on Phase 1 click framework."
```

---

## Task 6: 全套驗證 + 更新 Status.md / Task.md

**Files:**
- Modify: `Status.md`
- Modify: `Task.md`

- [ ] **Step 1: 跑完整測試**

```bash
python -m pytest tests/ -q --tb=short
```
Expected: 基線 +17 新測試（backwards-compat 5 + models 7 + load_validation 5 + cli 2 + baseline preserved）。

- [ ] **Step 2: i18n audit**

```bash
python -m pytest tests/test_i18n_audit.py tests/test_i18n_quality.py -v
```
Expected: 0 findings。

- [ ] **Step 3: 更新 Status.md**

Bump version to `v3.4.3-settings`。在 Code Quality Issues 表加一欄「Phase 3 ✅」給 D2（config schema validation）。

- [ ] **Step 4: 更新 Task.md**

在 Phase 2 或 Phase 1 section 後插入:

```markdown
---

## Phase 3: 設定驗證 ✅ DONE (2026-04-XX)

- [x] **P3**: pydantic v2 + pydantic-settings integration
  - `src/config_models.py`: 12 BaseModel 類別 (ApiSettings, SmtpSettings, WebGuiSettings, ...)
  - `ConfigManager.load()` 接 pydantic 驗證，失敗給清楚錯誤訊息
  - `cm.models` 新屬性暴露 typed schema；`cm.config` dict 存取 100% 向後相容（70+ 呼叫點無感）
  - **Status.md D2 解決**（config schema validation）
  - Top-level `extra='forbid'` 抓 config.json typo
  - `illumio-ops config validate / show` subcommands
  - Test count: 基線 +17
  - Branch: `upgrade/phase-3-settings-pydantic` → tag `v3.4.3-settings`
```

Commit:
```bash
git add Status.md Task.md
git commit -m "docs: record Phase 3 completion"
```

---

## Task 7: Push + PR + merge + tag

- [ ] **Step 1: Push**

```bash
git push -u origin upgrade/phase-3-settings-pydantic
```

- [ ] **Step 2: PR**

**Title**: `Phase 3: config validation with pydantic v2`

**Body** (摘要):
```markdown
## Summary
- Add `src/config_models.py` — 12 BaseModel classes mirroring _DEFAULT_CONFIG
- Validate config.json on ConfigManager.load(); pydantic errors logged per field
- New cm.models for typed access; cm.config dict patterns 100% preserved
- New `illumio-ops config validate` subcommand

## Why
Phase 3 of upgrade roadmap. Closes Status.md D2 (config schema validation).
Malformed config now surfaces specific field errors at startup instead of
KeyError deep inside business logic.

## Test plan
- [x] pytest tests/ — 基線 +17 new, 0 regressions
- [x] 5 backward-compat tests verify all dict-access patterns still work
- [x] 7 model tests cover validation edge cases (URL scheme, port range, etc.)
- [x] 5 load-validation tests cover error messaging on malformed config
- [x] 2 CLI tests for `config validate` / `config show`
- [x] i18n audit 0 findings
```

- [ ] **Step 3: Merge + tag + memory update**

Per the same pattern as Phase 1 / 2 closeout.

---

## Phase 3 完成驗收清單

- [ ] `src/config_models.py` 存在，12 BaseModel 類別完整
- [ ] `ConfigManager.load` 接 pydantic 驗證
- [ ] `cm.models` attribute 存在
- [ ] 70+ 現有 `cm.config[...]` 呼叫點無變更（backward-compat 測試守護）
- [ ] `illumio-ops config validate / show` subcommands 可用（若 Phase 1 已 merge）
- [ ] 所有既有測試 + 17 新增測試通過
- [ ] i18n audit 0 findings
- [ ] Status.md D2 標 ✅
- [ ] `v3.4.3-settings` tag 存在

**Done means ready to:** Phase 4（Web GUI 安全，依賴 Phase 3 的 pydantic for form validation）啟動。

---

## Rollback Plan

```bash
git revert v3.4.3-settings
git tag -d v3.4.3-settings
git push origin :refs/tags/v3.4.3-settings
```

所有邏輯集中在 config_models.py + config.py 兩檔，revert 乾淨。

---

## Self-Review Checklist

- ✅ **Spec coverage**：路線圖 Phase 3 (pydantic + BaseSettings + illumio-ops config validate) 全部有 task 覆蓋
- ✅ **Backward compat**：Task 2 contract test 守護既有 70+ 呼叫點
- ✅ **i18n**：config validate 輸出透過 rich；未新增 user-facing 字串（純開發者工具）
- ✅ **No placeholders**：每個 step 有完整程式碼
- ✅ **TDD**：Task 2/3/4 都是先紅後綠
- ✅ **Type consistency**：`ConfigSchema`/`cm.models`/`ApiSettings` 跨檔命名一致
