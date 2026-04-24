"""Tests for AuditGenerator cache-first data sourcing."""
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch
import pytest


def _make_mock_api():
    api = MagicMock()
    api.get_events.return_value = []
    return api


def _make_cache_reader(cover_state="full", events=None):
    cr = MagicMock()
    cr.cover_state.return_value = cover_state
    cr.read_events.return_value = events or [{"event_type": "policy.update", "timestamp": "2026-01-01T00:00:00Z"}]
    return cr


def test_audit_generator_uses_cache_when_full(tmp_path):
    """When cover_state=full, AuditGenerator reads from cache and does NOT call api.get_events."""
    from src.report.audit_generator import AuditGenerator
    api = _make_mock_api()
    cache = _make_cache_reader(cover_state="full")
    gen = AuditGenerator(api=api, cache_reader=cache)
    start = datetime.now(timezone.utc) - timedelta(days=1)
    end = datetime.now(timezone.utc)
    gen._fetch_events(start, end)
    cache.read_events.assert_called_once()
    api.get_events.assert_not_called()


def test_audit_generator_bypasses_cache_when_none(tmp_path):
    """When cache_reader=None, AuditGenerator falls through to api.get_events."""
    from src.report.audit_generator import AuditGenerator
    api = _make_mock_api()
    gen = AuditGenerator(api=api, cache_reader=None)
    start = datetime.now(timezone.utc) - timedelta(days=1)
    end = datetime.now(timezone.utc)
    gen._fetch_events(start, end)
    api.get_events.assert_called_once()


def test_audit_generator_falls_back_on_partial(tmp_path):
    """When cover_state=partial, AuditGenerator falls back to api.get_events."""
    from src.report.audit_generator import AuditGenerator
    api = _make_mock_api()
    cache = _make_cache_reader(cover_state="partial")
    gen = AuditGenerator(api=api, cache_reader=cache)
    start = datetime.now(timezone.utc) - timedelta(days=1)
    end = datetime.now(timezone.utc)
    gen._fetch_events(start, end)
    api.get_events.assert_called_once()


def test_audit_generator_falls_back_on_miss(tmp_path):
    """When cover_state=miss, AuditGenerator falls back to api.get_events."""
    from src.report.audit_generator import AuditGenerator
    api = _make_mock_api()
    cache = _make_cache_reader(cover_state="miss")
    gen = AuditGenerator(api=api, cache_reader=cache)
    start = datetime.now(timezone.utc) - timedelta(days=1)
    end = datetime.now(timezone.utc)
    gen._fetch_events(start, end)
    api.get_events.assert_called_once()
