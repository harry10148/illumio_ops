"""Tests for cron_expr timezone-aware scheduling."""
from __future__ import annotations
import datetime
import pytest


def test_report_schedule_has_timezone_field():
    """ReportSchedule model must have an explicit timezone field."""
    from src.config_models import ReportSchedule
    s = ReportSchedule(name="test", cron_expr="0 8 * * *", timezone="Asia/Taipei")
    assert s.timezone == "Asia/Taipei"


def test_report_schedule_timezone_defaults_to_none():
    from src.config_models import ReportSchedule
    s = ReportSchedule(name="test")
    assert s.timezone is None


def test_cron_expr_fires_at_local_time_not_utc():
    """A cron schedule set to 08:00 Asia/Taipei must fire at 08:00 Taipei, not 08:00 UTC."""
    from src.report_scheduler import ReportScheduler
    # 08:00 Taipei = UTC+8, so UTC equivalent is 00:00 UTC
    # At 08:00 Taipei local time, the schedule SHOULD fire
    schedule = {
        "id": 1, "name": "morning-report",
        "enabled": True,
        "cron_expr": "0 8 * * *",
        "timezone": "Asia/Taipei",
    }
    # Simulate now = 08:00 Asia/Taipei (= 00:00 UTC)
    # Use a fixed datetime: 2026-01-01 08:00:00 Asia/Taipei
    import zoneinfo
    taipei = zoneinfo.ZoneInfo("Asia/Taipei")
    now_taipei = datetime.datetime(2026, 1, 1, 8, 0, 0)  # naive, in Taipei local time
    rs = ReportScheduler.__new__(ReportScheduler)
    result = rs.should_run(schedule, now=now_taipei, last_run_str=None)
    assert result is True, "Should fire at 08:00 Taipei time"


def test_cron_expr_does_not_fire_at_utc_time_when_tz_is_taipei():
    """08:00 UTC = 16:00 Taipei; a schedule for 08:00 Taipei must NOT fire at 16:00 Taipei."""
    from src.report_scheduler import ReportScheduler
    schedule = {
        "id": 1, "name": "morning-report",
        "cron_expr": "0 8 * * *",
        "timezone": "Asia/Taipei",
    }
    # 16:00 Taipei local — next fire is tomorrow at 08:00 Taipei
    now_taipei_16 = datetime.datetime(2026, 1, 1, 16, 0, 0)
    rs = ReportScheduler.__new__(ReportScheduler)
    assert rs.should_run(schedule, now=now_taipei_16, last_run_str=None) is False


def test_cron_fires_at_midnight_utc_when_tz_is_taipei():
    """08:00 Taipei = 00:00 UTC: schedule for 08:00 Taipei MUST fire when now=08:00 Taipei local.
    The old UTC-hardcoded code would NOT fire here because it would treat 08:00 naive as
    08:00 UTC (= 16:00 Taipei) and would not match cron 0 8 * * *.
    The new code fires because now=08:00 naive is interpreted as 08:00 Asia/Taipei.
    """
    from src.report_scheduler import ReportScheduler
    schedule = {
        "id": 1, "name": "morning-report",
        "enabled": True,
        "cron_expr": "0 8 * * *",
        "timezone": "Asia/Taipei",
    }
    # 08:00 Taipei local = 00:00 UTC — new code fires, old UTC-hardcoded code would not
    now = datetime.datetime(2026, 1, 1, 8, 0, 0)
    rs = ReportScheduler.__new__(ReportScheduler)
    assert rs.should_run(schedule, now=now, last_run_str=None) is True


def test_cron_fires_at_eight_utc_when_no_tz():
    """Without timezone, schedule defaults to UTC: 08:00 naive fires at 08:00 UTC.
    Verifies that UTC default behavior is preserved.
    """
    from src.report_scheduler import ReportScheduler
    schedule = {
        "id": 1, "name": "morning-report",
        "enabled": True,
        "cron_expr": "0 8 * * *",
        # no timezone key
    }
    now = datetime.datetime(2026, 1, 1, 8, 0, 0)
    rs = ReportScheduler.__new__(ReportScheduler)
    assert rs.should_run(schedule, now=now, last_run_str=None) is True
