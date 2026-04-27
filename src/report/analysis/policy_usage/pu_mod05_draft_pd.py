"""
Policy Usage Module 05: Draft Policy Decision Risk (Comprehensive)

Three lenses:
  visibility_risk  – potentially_blocked_by_boundary / _by_override_deny
                     (enforcement tightening risk on visibility-mode workloads)
  draft_conflicts  – blocked_by_override_deny / allowed_across_boundary
                     (draft introduces Override Deny or anomalous cross-boundary allow)
  draft_coverage   – policy_decision=potentially_blocked AND draft resolves it to
                     allowed or blocked_by_boundary
                     (flows currently unruled that now have a decision in draft)
"""
from __future__ import annotations

from collections import Counter

import pandas as pd

_GROUP_A = frozenset({"potentially_blocked_by_boundary", "potentially_blocked_by_override_deny"})
_GROUP_B = frozenset({"blocked_by_override_deny", "allowed_across_boundary"})
_GROUP_C_DRAFT = frozenset({"allowed", "blocked_by_boundary"})


def pu_draft_pd_summary(rows: list[dict]) -> dict:
    if not rows:
        return {"skipped": True, "reason": "no flows returned"}

    group_a = [r for r in rows if r.get("draft_policy_decision") in _GROUP_A]
    group_b = [r for r in rows if r.get("draft_policy_decision") in _GROUP_B]
    group_c = [
        r for r in rows
        if r.get("policy_decision") == "potentially_blocked"
        and r.get("draft_policy_decision") in _GROUP_C_DRAFT
    ]

    return {
        "total": len(group_a) + len(group_b) + len(group_c),
        "visibility_risk": _build_group(group_a),
        "draft_conflicts": _build_group(group_b),
        "draft_coverage": _build_group(group_c),
    }


def _build_group(rows: list[dict]) -> dict:
    if not rows:
        return {"total": 0, "by_subtype": {}, "top_pairs": pd.DataFrame()}

    by_subtype = dict(Counter(r["draft_policy_decision"] for r in rows))

    pair_counter: Counter = Counter()
    for r in rows:
        src_wl = r.get("src", {}).get("workload", {})
        dst_wl = r.get("dst", {}).get("workload", {})
        src_name = src_wl.get("name") or r.get("src", {}).get("ip", "?")
        dst_name = dst_wl.get("name") or r.get("dst", {}).get("ip", "?")
        port = r.get("service", {}).get("port", "?")
        dpd = r["draft_policy_decision"]
        pair_counter[(src_name, dst_name, port, dpd)] += int(r.get("num_connections", 1))

    top_pairs = pd.DataFrame([
        {"Src": src, "Dst": dst, "Port": port, "Draft Decision": dpd, "Connections": cnt}
        for (src, dst, port, dpd), cnt in pair_counter.most_common(20)
    ])
    return {"total": len(rows), "by_subtype": by_subtype, "top_pairs": top_pairs}
