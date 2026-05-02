"""Regression test: every best-practice rule defined in config.py must have
matching `_desc` and `_rec` i18n keys in BOTH languages.

The static i18n audit (`scripts/audit_i18n_usage.py`) cannot catch missing
keys when callers concatenate suffixes at runtime, e.g.
`t(name_key + "_desc", default=...)`. Strict-prefix keys with `rule_` will
short-circuit to `[MISSING:<key>]` (ignoring the default) — which is what
the user sees in LINE / mail alerts when a key is absent.

This test loads the live `_best_practice_rules` definitions and asserts the
two derived keys exist in each i18n file.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent
_EVENT_SPECS_RE = re.compile(
    r'\(\s*"(rule_[a-z_]+)"\s*,\s*"[^"]+",\s*"[^"]+"',
)


def _extract_event_spec_keys() -> list[str]:
    text = (_REPO_ROOT / "src" / "config.py").read_text(encoding="utf-8")
    return _EVENT_SPECS_RE.findall(text)


@pytest.fixture(scope="module")
def en_messages():
    return json.loads((_REPO_ROOT / "src" / "i18n_en.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def zh_messages():
    return json.loads((_REPO_ROOT / "src" / "i18n_zh_TW.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("suffix", ["_desc", "_rec"])
def test_every_best_practice_rule_has_translation(en_messages, zh_messages, suffix):
    rule_keys = _extract_event_spec_keys()
    assert rule_keys, "Could not parse event_specs from src/config.py"
    missing_en = [k for k in rule_keys if (k + suffix) not in en_messages]
    missing_zh = [k for k in rule_keys if (k + suffix) not in zh_messages]
    assert not missing_en, (
        f"i18n_en.json missing rule keys with suffix {suffix!r}: {missing_en}. "
        f"src/config.py:_best_practice_rules constructs these dynamically via "
        f"t(name_key + '{suffix}', default=...) — but strict-prefix keys "
        f"return [MISSING:<key>] when absent (default is ignored)."
    )
    assert not missing_zh, (
        f"i18n_zh_TW.json missing rule keys with suffix {suffix!r}: {missing_zh}."
    )
