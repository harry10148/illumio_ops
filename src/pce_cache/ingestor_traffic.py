from __future__ import annotations

import hashlib
from datetime import datetime, timezone, timedelta
from typing import Optional

import orjson
from loguru import logger
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from src.pce_cache.models import PceTrafficFlowRaw
from src.pce_cache.traffic_filter import TrafficFilter, TrafficSampler
from src.pce_cache.watermark import WatermarkStore


class TrafficIngestor:
    SOURCE = "traffic"

    def __init__(
        self,
        api,
        session_factory: sessionmaker,
        watermark: WatermarkStore,
        traffic_filter: Optional[TrafficFilter] = None,
        sample_ratio_allowed: int = 1,
        max_results: int = 200000,
    ):
        self._api = api
        self._sf = session_factory
        self._wm = watermark
        self._filter = traffic_filter or TrafficFilter()
        self._sampler = TrafficSampler(ratio_allowed=sample_ratio_allowed)
        self._max_results = max_results

    def run_once(self) -> int:
        since = self._since_cursor()
        try:
            flows = self._api.get_traffic_flows_async(
                max_results=self._max_results,
                rate_limit=True,
                since=since,
            )
        except Exception as exc:
            logger.exception("Traffic ingest failed: {}", exc)
            self._wm.record_error(self.SOURCE, str(exc))
            return 0

        inserted = self._insert_batch(flows)
        if flows:
            last = max(f["last_detected"] for f in flows)
            self._wm.advance(self.SOURCE, last_timestamp=_parse_iso(last))
        return inserted

    def _since_cursor(self) -> Optional[str]:
        wm = self._wm.get(self.SOURCE)
        if wm and wm.last_timestamp:
            # Grace window: re-pull 5 minutes back to catch late-arriving flows
            grace = wm.last_timestamp - timedelta(minutes=5)
            return grace.isoformat()
        return None

    def _insert_batch(self, flows: list[dict]) -> int:
        now = datetime.now(timezone.utc)
        count = 0
        for flow in flows:
            if not self._filter.passes(flow):
                continue
            if not self._sampler.keep(flow):
                continue
            fh = _flow_hash(flow)
            try:
                with self._sf.begin() as s:
                    row = PceTrafficFlowRaw(
                        flow_hash=fh,
                        first_detected=_parse_iso(flow["first_detected"]),
                        last_detected=_parse_iso(flow["last_detected"]),
                        src_ip=flow.get("src_ip", ""),
                        src_workload=flow.get("src_workload"),
                        dst_ip=flow.get("dst_ip", ""),
                        dst_workload=flow.get("dst_workload"),
                        port=flow.get("port", 0),
                        protocol=flow.get("protocol", "tcp"),
                        action=flow.get("action", "unknown"),
                        flow_count=flow.get("flow_count", 1),
                        bytes_in=flow.get("bytes_in", 0),
                        bytes_out=flow.get("bytes_out", 0),
                        raw_json=orjson.dumps(flow).decode("utf-8"),
                        ingested_at=now,
                    )
                    s.add(row)
            except IntegrityError:
                continue
            count += 1
        return count


def _flow_hash(flow: dict) -> str:
    key = "|".join([
        flow.get("src_ip", ""),
        flow.get("dst_ip", ""),
        str(flow.get("port", "")),
        flow.get("protocol", ""),
        flow.get("first_detected", ""),
    ])
    return hashlib.sha1(key.encode("utf-8")).hexdigest()


def _parse_iso(s: str) -> datetime:
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    return datetime.fromisoformat(s)
