from __future__ import annotations

from datetime import datetime, timezone, timedelta

from sqlalchemy import delete
from sqlalchemy.orm import sessionmaker

from src.pce_cache.models import (
    DeadLetter, PceEvent, PceTrafficFlowAgg, PceTrafficFlowRaw,
)


class RetentionWorker:
    def __init__(self, session_factory: sessionmaker):
        self._sf = session_factory

    def run_once(
        self,
        events_days: int = 90,
        traffic_raw_days: int = 7,
        traffic_agg_days: int = 90,
        dlq_days: int = 30,
    ) -> dict[str, int]:
        now = datetime.now(timezone.utc)
        results: dict[str, int] = {}

        with self._sf.begin() as s:
            cutoff = now - timedelta(days=events_days)
            r = s.execute(delete(PceEvent).where(PceEvent.ingested_at < cutoff))
            results["events"] = r.rowcount

        with self._sf.begin() as s:
            cutoff = now - timedelta(days=traffic_raw_days)
            r = s.execute(delete(PceTrafficFlowRaw).where(PceTrafficFlowRaw.ingested_at < cutoff))
            results["traffic_raw"] = r.rowcount

        with self._sf.begin() as s:
            cutoff = now - timedelta(days=traffic_agg_days)
            r = s.execute(delete(PceTrafficFlowAgg).where(PceTrafficFlowAgg.bucket_day < cutoff))
            results["traffic_agg"] = r.rowcount

        with self._sf.begin() as s:
            cutoff = now - timedelta(days=dlq_days)
            r = s.execute(delete(DeadLetter).where(DeadLetter.quarantined_at < cutoff))
            results["dead_letter"] = r.rowcount

        return results
