"""Change Impact: compare current report's KPIs to the previous snapshot."""
from __future__ import annotations

from typing import Optional

LOWER_BETTER = ("pb_uncovered_exposure", "high_risk_lateral_paths", "blocked_flows")
HIGHER_BETTER = ("active_allow_coverage", "microsegmentation_maturity")


def compare(*, current_kpis: dict, previous: Optional[dict]) -> dict:
    if previous is None:
        return {"skipped": True, "reason": "no_previous_snapshot"}
    prev_kpis = previous.get("kpis", {})
    deltas = {}
    improved_count = 0
    regressed_count = 0
    for k, current in current_kpis.items():
        if not isinstance(current, (int, float)):
            continue
        prev = prev_kpis.get(k)
        if not isinstance(prev, (int, float)):
            continue
        delta = current - prev
        direction = _direction(k, delta)
        if direction == "improved":
            improved_count += 1
        elif direction == "regressed":
            regressed_count += 1
        deltas[k] = {"current": current, "previous": prev, "delta": delta, "direction": direction}
    verdict = _verdict(improved_count, regressed_count)
    return {
        "deltas": deltas,
        "improved_count": improved_count,
        "regressed_count": regressed_count,
        "overall_verdict": verdict,
        "previous_snapshot_at": previous.get("generated_at"),
    }


def _direction(kpi: str, delta: float) -> str:
    if delta == 0:
        return "unchanged"
    if kpi in LOWER_BETTER:
        return "improved" if delta < 0 else "regressed"
    if kpi in HIGHER_BETTER:
        return "improved" if delta > 0 else "regressed"
    return "neutral"


def _verdict(improved, regressed):
    if improved > 0 and regressed == 0:
        return "improved"
    if regressed > 0 and improved == 0:
        return "regressed"
    if improved > 0 and regressed > 0:
        return "mixed"
    return "unchanged"  # pragma: no cover
