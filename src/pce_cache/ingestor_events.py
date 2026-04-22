from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

import orjson
from loguru import logger
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from src.pce_cache.models import PceEvent
from src.pce_cache.watermark import WatermarkStore


class EventsIngestor:
    SOURCE = "events"

    def __init__(
        self,
        api,
        session_factory: sessionmaker,
        watermark: WatermarkStore,
        async_threshold: int = 10000,
    ):
        self._api = api
        self._sf = session_factory
        self._wm = watermark
        self._async_threshold = async_threshold

    def run_once(self, *, force_async: bool = False) -> int:
        since = self._since_cursor()
        try:
            if force_async:
                events = self._api.get_events_async(since=since, rate_limit=True)
            else:
                events = self._api.get_events(
                    max_results=self._async_threshold,
                    since=since,
                    rate_limit=True,
                )
                if len(events) >= self._async_threshold:
                    logger.info(
                        "Events sync pull hit cap ({}), switching to async",
                        self._async_threshold,
                    )
                    self._wm.advance(self.SOURCE)
                    events = self._api.get_events_async(since=since, rate_limit=True)
        except Exception as exc:
            logger.exception("Events ingest failed: {}", exc)
            self._wm.record_error(self.SOURCE, str(exc))
            return 0

        inserted = self._insert_batch(events)
        if events:
            last = max(e["timestamp"] for e in events)
            last_href = events[-1].get("href", "")
            self._wm.advance(self.SOURCE, last_timestamp=_parse_iso(last), last_href=last_href)
        return inserted

    def _since_cursor(self) -> Optional[str]:
        wm = self._wm.get(self.SOURCE)
        if wm and wm.last_timestamp:
            return wm.last_timestamp.isoformat()
        return None

    def _insert_batch(self, events: list[dict]) -> int:
        now = datetime.now(timezone.utc)
        count = 0
        for ev in events:
            try:
                with self._sf.begin() as s:
                    row = PceEvent(
                        pce_href=ev.get("href", ""),
                        pce_event_id=ev.get("uuid", ev.get("href", ""))[-64:],
                        timestamp=_parse_iso(ev["timestamp"]),
                        event_type=ev.get("event_type", "unknown"),
                        severity=ev.get("severity", "info"),
                        status=ev.get("status", "success"),
                        pce_fqdn=ev.get("pce_fqdn", ""),
                        raw_json=orjson.dumps(ev).decode("utf-8"),
                        ingested_at=now,
                    )
                    s.add(row)
            except IntegrityError:
                continue
            count += 1
        return count


def _parse_iso(s: str) -> datetime:
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    return datetime.fromisoformat(s)
