"""Tests for /api/rules/<idx>/highlight pygments endpoint."""

from __future__ import annotations

from unittest.mock import MagicMock, patch


def _make_client():
    from src.gui import _create_app

    cm = MagicMock()
    cm.config = {
        "settings": {"language": "en"},
        "api": {"url": "https://pce.example.com:8443"},
        "rules": [
            {"type": "traffic", "name": "Test Rule", "threshold": 100},
        ],
        "report": {"output_dir": "/tmp/test-reports"},
        "web_gui": {"secret_key": "test"},
    }
    cm.load = MagicMock()
    app = _create_app(cm)
    app.config["TESTING"] = True
    return app.test_client(), app


class TestRuleHighlightEndpoint:
    def _authed(self, app):
        return patch("flask_login.utils._get_user", return_value=MagicMock(is_authenticated=True))

    def test_valid_index_returns_html(self):
        client, app = _make_client()
        with self._authed(app):
            resp = client.get("/api/rules/0/highlight")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "html" in data
        assert "Test Rule" in data["html"]

    def test_out_of_range_returns_404(self):
        client, app = _make_client()
        with self._authed(app):
            resp = client.get("/api/rules/99/highlight")
        assert resp.status_code == 404

    def test_pygments_css_served(self):
        client, app = _make_client()
        resp = client.get("/static/pygments.css")
        assert resp.status_code == 200
        assert b"highlight" in resp.data or b".hll" in resp.data or b"background" in resp.data

    def test_index_html_links_pygments_css(self):
        from pathlib import Path
        html = Path("src/templates/index.html").read_text(encoding="utf-8")
        assert "pygments.css" in html
