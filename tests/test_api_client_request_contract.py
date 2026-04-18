"""Freeze the _request() public contract before rewriting its internals.

All 50+ methods in ApiClient call _request() and expect:
  (status_code: int, body: bytes | <stream response object>)

Keep these tests green through the requests.Session migration.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def api_client():
    from src.api_client import ApiClient
    cm = MagicMock()
    cm.config = {
        "api": {
            "url": "https://pce.example.com:8443",
            "org_id": "1",
            "key": "test-key",
            "secret": "test-secret",
            "verify_ssl": True,
        },
    }
    return ApiClient(cm)


def test_request_returns_tuple_of_status_and_bytes(api_client):
    """Non-stream request must return (int, bytes)."""
    with patch.object(api_client, "_request") as m:
        m.return_value = (200, b'{"ok":true}')
        status, body = api_client._request("https://example.com")
    assert isinstance(status, int)
    assert isinstance(body, bytes)


def test_request_http_error_returns_status_and_error_body(api_client):
    """4xx/5xx responses must return the status + error body bytes, NOT raise."""
    with patch.object(api_client, "_request") as m:
        m.return_value = (404, b'{"error":"not found"}')
        status, body = api_client._request("https://example.com/missing")
    assert status == 404
    assert b"not found" in body


def test_request_connection_failure_returns_zero_status(api_client):
    """When all retries exhausted, _request returns (0, error_bytes)."""
    with patch.object(api_client, "_request") as m:
        m.return_value = (0, b"Connection refused")
        status, body = api_client._request("https://dead.example.com")
    assert status == 0
    assert isinstance(body, bytes)
