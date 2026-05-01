"""Phase 3 security header contracts: CSP nonce, Cross-Origin headers, Server header, rate limits."""
from __future__ import annotations

import json
import pytest


@pytest.fixture
def client(tmp_path):
    cfg = tmp_path / "config.json"
    cfg.write_text(json.dumps({
        "api": {"url": "https://pce.test", "org_id": "1", "key": "k", "secret": "s"},
        "web_gui": {"username": "illumio", "password": "illumio",
                    "secret_key": "", "allowed_ips": []},
    }), encoding="utf-8")
    from src.config import ConfigManager
    from src.gui import build_app
    app = build_app(ConfigManager(str(cfg)))
    app.config["TESTING"] = True
    return app.test_client()


def _parse_csp(headers) -> dict[str, str]:
    """Parse CSP header into a dict keyed by directive name."""
    csp = headers.get("Content-Security-Policy", "")
    result: dict[str, str] = {}
    for part in csp.split(";"):
        part = part.strip()
        if not part:
            continue
        tokens = part.split(None, 1)
        key = tokens[0].lower()
        value = tokens[1] if len(tokens) > 1 else ""
        result[key] = value
    return result


def test_csp_script_src_allows_unsafe_inline(client):
    """script-src carries 'unsafe-inline' so 40+ dynamically-injected
    inline onclick handlers across the JS codebase keep working while the
    M1 dispatcher migration is incomplete. See the CSP comment in
    src/gui/__init__.py for the trade-off and compensating controls."""
    r = client.get("/login")
    csp = _parse_csp(r.headers)
    assert "'unsafe-inline'" in csp.get("script-src", ""), \
        "script-src must allow 'unsafe-inline' (see src/gui/__init__.py CSP comment)"


def test_csp_style_src_allows_unsafe_inline(client):
    """style-src allows 'unsafe-inline' for the 344+ inline style="..."
    attributes throughout the templates. Style injection cannot execute
    scripts."""
    r = client.get("/login")
    csp = _parse_csp(r.headers)
    assert "'unsafe-inline'" in csp.get("style-src", ""), \
        "style-src must allow 'unsafe-inline' (see src/gui/__init__.py CSP comment)"


def test_csp_no_nonce_anywhere(client):
    """Per CSP Level 3, a nonce in any directive suppresses 'unsafe-inline'
    in that same directive. Since both script-src and style-src rely on
    'unsafe-inline', neither directive may carry a nonce."""
    r = client.get("/login")
    csp = _parse_csp(r.headers)
    for directive in ("script-src", "style-src"):
        assert "'nonce-" not in csp.get(directive, ""), \
            f"{directive} must not contain a nonce (would suppress 'unsafe-inline'); got: {csp.get(directive)!r}"


def test_server_header_removed(client):
    r = client.get("/login")
    assert "Server" not in r.headers, \
        f"Server header must be stripped; got: {r.headers.get('Server')!r}"


def test_cross_origin_opener_policy(client):
    r = client.get("/login")
    assert r.headers.get("Cross-Origin-Opener-Policy") == "same-origin"


def test_cross_origin_resource_policy(client):
    r = client.get("/login")
    assert r.headers.get("Cross-Origin-Resource-Policy") == "same-site"


def test_rate_limit_login_returns_429(client):
    """Exhaust /api/login limit (5 per minute) and confirm 429."""
    for _ in range(5):
        client.post("/api/login", json={"username": "x", "password": "y"})
    r = client.post("/api/login", json={"username": "x", "password": "y"})
    assert r.status_code == 429
