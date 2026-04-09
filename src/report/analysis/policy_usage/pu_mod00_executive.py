"""
pu_mod00_executive.py
Executive summary KPIs and execution metadata for the Policy Usage report.
"""
import datetime
from collections import Counter


def pu_executive_summary(results: dict, lookback_days: int) -> dict:
    """Aggregate KPIs, attention items, and query execution stats."""
    mod01 = results.get("mod01", {})
    mod03 = results.get("mod03", {})
    execution = (results.get("meta", {}) or {}).get("execution_stats", {}) or {}

    total = mod01.get("total_rules", 0)
    hit = mod01.get("hit_count", 0)
    unused = mod01.get("unused_count", 0)
    rate = mod01.get("hit_rate_pct", 0.0)

    cached = int(execution.get("cached_rules", 0) or 0)
    submitted = int(execution.get("submitted_rules", 0) or 0)
    pending = int(execution.get("pending_jobs", 0) or 0)
    failed = int(execution.get("failed_jobs", 0) or 0)
    top_hit_ports = execution.get("top_hit_ports", []) or []
    top_port_label = top_hit_ports[0].get("port_proto", "N/A") if top_hit_ports else "N/A"

    kpis = [
        {"label": "Total Rules", "value": str(total)},
        {"label": "Hit Rules", "value": str(hit)},
        {"label": "Unused Rules", "value": str(unused)},
        {"label": "Hit Rate", "value": f"{rate}%"},
        {"label": "Lookback", "value": f"{lookback_days} days"},
        {"label": "Cached Reuse", "value": str(cached)},
        {"label": "New Queries", "value": str(submitted)},
        {"label": "Top Hit Port", "value": top_port_label},
    ]

    attention_items = []
    unused_df = mod03.get("unused_df")
    if unused_df is not None and not unused_df.empty and "Ruleset" in unused_df.columns:
        counts = Counter(unused_df["Ruleset"].tolist())
        for rs_name, cnt in counts.most_common(5):
            attention_items.append({"ruleset": rs_name, "unused_count": cnt})

    execution_notes = []
    if cached:
        execution_notes.append(f"Reused {cached} completed async summaries.")
    if submitted:
        execution_notes.append(f"Submitted {submitted} new async queries.")
    if pending:
        execution_notes.append(f"{pending} async queries were still pending at timeout.")
    if failed:
        execution_notes.append(f"{failed} async queries failed.")
    if top_hit_ports:
        top_summary = ", ".join(
            f"{item.get('port_proto', '')} ({int(item.get('flow_count', 0) or 0)})"
            for item in top_hit_ports[:3]
        )
        execution_notes.append(f"Top observed hit ports: {top_summary}.")

    return {
        "generated_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "lookback_days": lookback_days,
        "kpis": kpis,
        "attention_items": attention_items,
        "execution_stats": execution,
        "execution_notes": execution_notes,
    }
