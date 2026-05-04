"""Documentation contracts for deployment/runtime promises."""
from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent


def _read(path: str) -> str:
    return (REPO_ROOT / path).read_text(encoding="utf-8")


def test_docs_do_not_advertise_python38_source_runtime():
    docs = {
        "README.md": _read("README.md"),
        "README_zh.md": _read("README_zh.md"),
        "docs/Installation.md": _read("docs/Installation.md"),
        "docs/Installation_zh.md": _read("docs/Installation_zh.md"),
    }

    for path, text in docs.items():
        assert "Python-3.8" not in text
        assert "Python 3.8+" not in text
        assert "Python 3.8+" not in text

    assert "Python-3.10%2B" in docs["README.md"]
    assert "Python-3.10%2B" in docs["README_zh.md"]
    assert "Source/development runtime: Python 3.10+" in docs["docs/Installation.md"]
    assert "原始碼/開發執行環境：Python 3.10+" in docs["docs/Installation_zh.md"]
    assert "bundled CPython 3.12" in docs["docs/Installation.md"]
    assert "內建 CPython 3.12" in docs["docs/Installation_zh.md"]


def test_docs_list_alerts_json_as_preserved_operator_config():
    docs = {
        "README.md": _read("README.md"),
        "README_zh.md": _read("README_zh.md"),
        "docs/Installation.md": _read("docs/Installation.md"),
        "docs/Installation_zh.md": _read("docs/Installation_zh.md"),
        "docs/User_Manual.md": _read("docs/User_Manual.md"),
        "docs/User_Manual_zh.md": _read("docs/User_Manual_zh.md"),
        "docs/Troubleshooting.md": _read("docs/Troubleshooting.md"),
        "docs/Troubleshooting_zh.md": _read("docs/Troubleshooting_zh.md"),
    }

    for path, text in docs.items():
        assert "alerts.json" in text, f"{path} must document the split alert rules file"

    for path in (
        "docs/Installation.md",
        "docs/Installation_zh.md",
        "docs/User_Manual.md",
        "docs/User_Manual_zh.md",
    ):
        text = docs[path]
        assert "config.json" in text
        assert "alerts.json" in text
        assert "rule_schedules.json" in text

    assert "config.json, alerts.json (rules), and rule_schedules.json are preserved" in docs["docs/Installation.md"]
    assert "config.json、alerts.json（rules）與 rule_schedules.json 會被保留" in docs["docs/Installation_zh.md"]
