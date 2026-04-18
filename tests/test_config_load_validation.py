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
