from datetime import datetime, timedelta, timezone
import json
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.pce_cache.models import PceEvent


@pytest.fixture
def session_factory(tmp_path):
    from src.pce_cache.schema import init_schema
    engine = create_engine(f"sqlite:///{tmp_path / 'c.sqlite'}")
    init_schema(engine)
    return sessionmaker(engine)


def _seed_event(sf, ts):
    with sf.begin() as s:
        s.add(PceEvent(
            pce_href=f"/orgs/1/events/{ts.isoformat()}",
            pce_event_id=ts.isoformat(),
            timestamp=ts,
            event_type="policy.update",
            severity="info",
            status="success",
            pce_fqdn="pce.example.com",
            raw_json=json.dumps({"event_type": "policy.update"}),
            ingested_at=ts,
        ))


def test_cover_state_full_when_range_in_retention(session_factory):
    from src.pce_cache.reader import CacheReader
    now = datetime.now(timezone.utc)
    _seed_event(session_factory, now - timedelta(days=1))
    rd = CacheReader(session_factory, events_retention_days=90, traffic_raw_retention_days=7)
    assert rd.cover_state("events", now - timedelta(days=2), now) == "full"


def test_cover_state_partial_when_start_before_cutoff(session_factory):
    from src.pce_cache.reader import CacheReader
    now = datetime.now(timezone.utc)
    rd = CacheReader(session_factory, events_retention_days=90, traffic_raw_retention_days=7)
    assert rd.cover_state("events", now - timedelta(days=120), now) == "partial"


def test_cover_state_miss_when_entirely_before_cutoff(session_factory):
    from src.pce_cache.reader import CacheReader
    now = datetime.now(timezone.utc)
    rd = CacheReader(session_factory, events_retention_days=90, traffic_raw_retention_days=7)
    assert rd.cover_state("events", now - timedelta(days=200), now - timedelta(days=150)) == "miss"


def test_read_events_returns_dict_rows(session_factory):
    from src.pce_cache.reader import CacheReader
    now = datetime.now(timezone.utc)
    _seed_event(session_factory, now - timedelta(hours=1))
    rd = CacheReader(session_factory, events_retention_days=90, traffic_raw_retention_days=7)
    rows = rd.read_events(now - timedelta(hours=2), now)
    assert len(rows) == 1
    assert rows[0]["event_type"] == "policy.update"


def test_read_events_rejects_miss_range(session_factory):
    from src.pce_cache.reader import CacheReader
    now = datetime.now(timezone.utc)
    rd = CacheReader(session_factory, events_retention_days=90, traffic_raw_retention_days=7)
    with pytest.raises(ValueError, match="cache-miss"):
        rd.read_events(now - timedelta(days=200), now - timedelta(days=150))
