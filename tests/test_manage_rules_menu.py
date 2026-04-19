from __future__ import annotations

from types import SimpleNamespace

import pytest

from src import i18n
from src import settings as settings_module


def _make_cm():
    removed = []
    cm = SimpleNamespace(
        config={
            "rules": [
                {"name": "Event Rule", "type": "event", "threshold_count": 1, "threshold_window": 10},
                {"name": "Traffic Rule", "type": "traffic", "threshold_count": 5, "threshold_window": 10},
                {"name": "Bandwidth Rule", "type": "bandwidth", "threshold_count": 10.0, "threshold_window": 30},
            ]
        }
    )

    def remove_rules_by_index(indices):
        removed.append(indices)

    cm.remove_rules_by_index = remove_rules_by_index
    return cm, removed


def _prepare_menu(monkeypatch, answers):
    inputs = iter(answers)
    monkeypatch.setattr(settings_module.os, "system", lambda *_args, **_kwargs: None)
    monkeypatch.setattr("src.utils.draw_panel", lambda *_args, **_kwargs: None)
    monkeypatch.setattr("src.utils.draw_table", lambda *_args, **_kwargs: None)
    monkeypatch.setattr("builtins.input", lambda *_args, **_kwargs: next(inputs))


@pytest.fixture(autouse=True)
def _english_ui():
    previous = i18n.get_language()
    i18n.set_language("en")
    try:
        yield
    finally:
        i18n.set_language(previous)


def test_manage_rules_menu_help_command_shows_examples(monkeypatch, capsys):
    cm, _removed = _make_cm()
    _prepare_menu(monkeypatch, ["?", "0"])

    settings_module.manage_rules_menu(cm)

    output = capsys.readouterr().out
    assert "Commands: m <index>" in output
    assert "d <index1,index2>" in output


def test_manage_rules_menu_delete_command_accepts_multiple_indices(monkeypatch, capsys):
    cm, removed = _make_cm()
    _prepare_menu(monkeypatch, ["d 1, 2", "", "0"])

    settings_module.manage_rules_menu(cm)

    assert removed == [[1, 2]]
    assert "Done." in capsys.readouterr().out


def test_manage_rules_menu_modify_command_routes_by_rule_type(monkeypatch, capsys):
    cm, removed = _make_cm()
    calls = []
    _prepare_menu(monkeypatch, ["m 1", "", "0"])

    monkeypatch.setattr(settings_module, "add_event_menu", lambda *_args, **_kwargs: calls.append("event"))
    monkeypatch.setattr(settings_module, "add_system_health_menu", lambda *_args, **_kwargs: calls.append("system"))
    monkeypatch.setattr(settings_module, "add_traffic_menu", lambda *_args, **_kwargs: calls.append("traffic"))
    monkeypatch.setattr(settings_module, "add_bandwidth_volume_menu", lambda *_args, **_kwargs: calls.append("bandwidth"))

    settings_module.manage_rules_menu(cm)

    assert removed == []
    assert calls == ["traffic"]
    assert "Modifying rule: Traffic Rule" in capsys.readouterr().out


def test_manage_rules_menu_rejects_invalid_format(monkeypatch, capsys):
    cm, removed = _make_cm()
    _prepare_menu(monkeypatch, ["bad", "", "0"])

    settings_module.manage_rules_menu(cm)

    assert removed == []
    assert "Invalid format. Use m <index> or d <index>[,index...]." in capsys.readouterr().out


def test_manage_rules_menu_rejects_multi_index_modify(monkeypatch, capsys):
    cm, removed = _make_cm()
    _prepare_menu(monkeypatch, ["m 1,2", "", "0"])

    settings_module.manage_rules_menu(cm)

    assert removed == []
    assert "Modify accepts exactly one index." in capsys.readouterr().out


def test_manage_rules_menu_cancelled_modify_keeps_rule(monkeypatch):
    cm, removed = _make_cm()
    original_rule = dict(cm.config["rules"][1])
    _prepare_menu(monkeypatch, ["m 1", "", "0"])

    monkeypatch.setattr(settings_module, "add_event_menu", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(settings_module, "add_system_health_menu", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(settings_module, "add_traffic_menu", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(settings_module, "add_bandwidth_volume_menu", lambda *_args, **_kwargs: None)

    settings_module.manage_rules_menu(cm)

    assert removed == []
    assert cm.config["rules"][1] == original_rule
