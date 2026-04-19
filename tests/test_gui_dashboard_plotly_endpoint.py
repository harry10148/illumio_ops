"""Tests for /api/dashboard/chart/<chart_id> plotly JSON endpoint."""

from __future__ import annotations

from unittest.mock import MagicMock, patch


def _make_client():
    from src.gui import _create_app

    cm = MagicMock()
    cm.config = {
        "settings": {"language": "en"},
        "api": {"url": "https://pce.example.com:8443"},
        "rules": [],
        "report": {"output_dir": "/tmp/test-reports"},
    }
    cm.load = MagicMock()
    app = _create_app(cm)
    app.config["TESTING"] = True
    # Bypass login_required by patching current_user
    with app.test_request_context():
        pass
    return app.test_client(), app


def _login(client, app):
    """Inject a logged-in session."""
    from flask_login import login_user

    with app.test_request_context():
        pass
    # Directly patch login_required to always allow
    from unittest.mock import patch as _patch
    return _patch("flask_login.utils._get_user", return_value=MagicMock(is_authenticated=True))


class TestDashboardChartEndpoint:
    def _get_authed_client(self):
        """Return (client, ctx_patch) — caller must use ctx_patch as context manager."""
        client, app = _make_client()
        ctx = _login(client, app)
        return client, ctx

    def test_traffic_timeline_returns_plotly_json(self):
        client, app = _make_client()
        with patch("flask_login.utils._get_user",
                   return_value=MagicMock(is_authenticated=True)):
            with patch("src.gui._load_state_for_charts", return_value={"event_timeline": [
                {"timestamp": "2024-01-01T00:00:00Z", "kind": "pce_ok", "title": "ok", "details": {}},
                {"timestamp": "2024-01-02T00:00:00Z", "kind": "pce_ok", "title": "ok", "details": {}},
            ]}):
                resp = client.get("/api/dashboard/chart/traffic_timeline")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "data" in data
        assert "layout" in data

    def test_policy_decisions_returns_plotly_json(self):
        client, app = _make_client()
        with patch("flask_login.utils._get_user",
                   return_value=MagicMock(is_authenticated=True)):
            resp = client.get("/api/dashboard/chart/policy_decisions")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "data" in data
        assert "layout" in data

    def test_ven_status_returns_plotly_json(self):
        client, app = _make_client()
        with patch("flask_login.utils._get_user",
                   return_value=MagicMock(is_authenticated=True)):
            with patch("src.gui._load_state_for_charts",
                       return_value={"pce_stats": {"health_status": "ok"}}):
                resp = client.get("/api/dashboard/chart/ven_status")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "data" in data

    def test_rule_hits_returns_plotly_json(self):
        client, app = _make_client()
        with patch("flask_login.utils._get_user",
                   return_value=MagicMock(is_authenticated=True)):
            with patch("src.gui._load_state_for_charts", return_value={"event_timeline": [
                {"timestamp": "2024-01-01T00:00:00Z", "kind": "rule_trigger",
                 "title": "Rule A", "details": {}},
            ]}):
                resp = client.get("/api/dashboard/chart/rule_hits")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "data" in data

    def test_unknown_chart_id_returns_404(self):
        client, app = _make_client()
        with patch("flask_login.utils._get_user",
                   return_value=MagicMock(is_authenticated=True)):
            resp = client.get("/api/dashboard/chart/nonexistent")
        assert resp.status_code == 404
