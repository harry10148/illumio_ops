from datetime import datetime, timezone, timedelta

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from src.pce_cache.models import DeadLetter, SiemDispatch


@pytest.fixture
def sf(tmp_path):
    from src.pce_cache.schema import init_schema
    engine = create_engine(f"sqlite:///{tmp_path / 'c.sqlite'}")
    init_schema(engine)
    return sessionmaker(engine)


def _seed_dlq(sf, count=3, dest="dest1", days_old=0):
    ts = datetime.now(timezone.utc) - timedelta(days=days_old)
    with sf.begin() as s:
        for i in range(count):
            s.add(DeadLetter(
                source_table="pce_events", source_id=i,
                destination=dest, retries=10,
                last_error="fail", payload_preview="...",
                quarantined_at=ts,
            ))


def test_dlq_list_entries(sf):
    from src.siem.dlq import DeadLetterQueue
    _seed_dlq(sf, count=3)
    dlq = DeadLetterQueue(sf)
    entries = dlq.list_entries("dest1")
    assert len(entries) == 3


def test_dlq_replay_creates_dispatch_rows(sf):
    from src.siem.dlq import DeadLetterQueue
    _seed_dlq(sf, count=2)
    dlq = DeadLetterQueue(sf)
    count = dlq.replay("dest1", limit=10)
    assert count == 2
    with sf() as s:
        rows = s.execute(select(SiemDispatch)).scalars().all()
    assert len(rows) == 2
    assert all(r.status == "pending" for r in rows)


def test_dlq_purge_removes_old_entries(sf):
    from src.siem.dlq import DeadLetterQueue
    _seed_dlq(sf, count=3, days_old=60)
    _seed_dlq(sf, count=1, days_old=0)
    dlq = DeadLetterQueue(sf)
    removed = dlq.purge("dest1", older_than_days=30)
    assert removed == 3
    with sf() as s:
        remaining = s.execute(select(DeadLetter)).scalars().all()
    assert len(remaining) == 1
