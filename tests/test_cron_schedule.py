"""Tests for ReportScheduler cron_expr support."""

from __future__ import annotations

import datetime
from unittest.mock import MagicMock, patch

import pytest
from freezegun import freeze_time

from src.report_scheduler import ReportScheduler


def _make_scheduler():
    cm = MagicMock()
    cm.config = {}
    reporter = MagicMock()
    scheduler = ReportScheduler(cm, reporter)
    # Stub state so re-run gap check doesn't block
    scheduler._load_states = MagicMock(return_value={})
    return scheduler


def _sched(cron_expr, enabled=True):
    return {"id": 1, "enabled": enabled, "cron_expr": cron_expr}


class TestCronExpr:
    def test_mon_0800_fires(self):
        """Mon 08:00 UTC should fire for 'every weekday at 08:00'."""
        # 2024-01-01 is a Monday
        with freeze_time("2024-01-01 08:00:00"):
            now = datetime.datetime(2024, 1, 1, 8, 0, 0)
            s = _make_scheduler()
            assert s.should_run(_sched("0 8 * * MON-FRI"), now) is True

    def test_sat_0800_does_not_fire(self):
        """Sat 08:00 UTC should NOT fire for 'every weekday at 08:00'."""
        # 2024-01-06 is a Saturday
        with freeze_time("2024-01-06 08:00:00"):
            now = datetime.datetime(2024, 1, 6, 8, 0, 0)
            s = _make_scheduler()
            assert s.should_run(_sched("0 8 * * MON-FRI"), now) is False

    def test_wrong_hour_does_not_fire(self):
        """Mon 09:00 should not fire for '0 8 * * MON-FRI'."""
        with freeze_time("2024-01-01 09:00:00"):
            now = datetime.datetime(2024, 1, 1, 9, 0, 0)
            s = _make_scheduler()
            assert s.should_run(_sched("0 8 * * MON-FRI"), now) is False

    def test_disabled_schedule_does_not_fire(self):
        with freeze_time("2024-01-01 08:00:00"):
            now = datetime.datetime(2024, 1, 1, 8, 0, 0)
            s = _make_scheduler()
            assert s.should_run(_sched("0 8 * * MON-FRI", enabled=False), now) is False

    def test_invalid_cron_expr_returns_false(self):
        now = datetime.datetime(2024, 1, 1, 8, 0, 0)
        s = _make_scheduler()
        assert s.should_run(_sched("not-a-cron"), now) is False

    def test_rerun_gap_blocks_refiring(self):
        """If last_run is recent, cron_expr schedule must not re-fire."""
        now = datetime.datetime(2024, 1, 1, 8, 0, 0)
        recent = (now - datetime.timedelta(minutes=30)).isoformat()
        s = _make_scheduler()
        s._load_states = MagicMock(return_value={"1": {"last_run": recent}})
        assert s.should_run(_sched("0 8 * * MON-FRI"), now) is False

    def test_legacy_schedule_type_still_works(self):
        """Backward-compat: schedule without cron_expr uses daily/weekly logic."""
        # Monday 08:00 — daily schedule should fire
        now = datetime.datetime(2024, 1, 1, 8, 0, 0)
        s = _make_scheduler()
        legacy = {"id": 2, "enabled": True, "schedule_type": "daily", "hour": 8, "minute": 0}
        assert s.should_run(legacy, now) is True

    def test_daily_at_midnight(self):
        """'0 0 * * *' fires at 00:00."""
        now = datetime.datetime(2024, 6, 15, 0, 0, 0)
        s = _make_scheduler()
        assert s.should_run(_sched("0 0 * * *"), now) is True

    def test_daily_at_midnight_wrong_time(self):
        """'0 0 * * *' does not fire at 01:00."""
        now = datetime.datetime(2024, 6, 15, 1, 0, 0)
        s = _make_scheduler()
        assert s.should_run(_sched("0 0 * * *"), now) is False
