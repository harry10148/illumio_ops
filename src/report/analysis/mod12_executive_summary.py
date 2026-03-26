"""Module 12: Executive Summary — Auto-Generated from All Module Results."""
from __future__ import annotations
import datetime
from typing import Any


def executive_summary(results: dict[str, Any]) -> dict:
    """
    Generates a data-driven executive summary from all other modules' output.
    Must be called AFTER modules 1-11 have completed.

    Returns a dict suitable for the first sheet of the Excel report and
    the email body HTML.
    """
    mod01 = results.get('mod01', {})
    mod03 = results.get('mod03', {})
    mod04 = results.get('mod04', {})
    mod05 = results.get('mod05', {})
    mod08 = results.get('mod08', {})
    mod11 = results.get('mod11', {})
    findings = results.get('findings', [])

    # ── KPI cards ────────────────────────────────────────────────────────────
    kpis = [
        {'label': 'Total Flows', 'value': _fmt(mod01.get('total_flows', 0))},
        {'label': 'Total Connections', 'value': _fmt(mod01.get('total_connections', 0))},
        {'label': 'Unique Source IPs', 'value': _fmt(mod01.get('unique_src_ips', 0))},
        {'label': 'Unique Dest IPs', 'value': _fmt(mod01.get('unique_dst_ips', 0))},
        {'label': 'Policy Coverage', 'value': f"{mod01.get('policy_coverage_pct', 0)}%"},
        {'label': 'Blocked Flows', 'value': _fmt(mod01.get('blocked_flows', 0))},
        {'label': 'Potentially Blocked', 'value': _fmt(mod01.get('potentially_blocked_flows', 0))},
        {'label': 'Unmanaged Src %',
         'value': f"{100 - mod01.get('src_managed_pct', 100):.1f}%"},
        {'label': 'Total Data Volume', 'value': f"{mod01.get('total_mb', 0):.1f} MB"},
        {'label': 'Date Range', 'value': mod01.get('date_range', 'N/A')},
    ]

    # ── Security findings summary ─────────────────────────────────────────────
    findings_summary = {}
    for f in findings:
        findings_summary[f.severity] = findings_summary.get(f.severity, 0) + 1

    # ── Auto-derived key findings (pure data, no AI) ──────────────────────────
    key_findings = []

    coverage = mod01.get('policy_coverage_pct', 100)
    if coverage < 50:
        key_findings.append({
            'severity': 'HIGH',
            'finding': f"Only {coverage:.0f}% of flows are covered by allow policies.",
            'action': "Create segmentation rules for the top uncovered flows."
        })

    ransomware_total = mod04.get('risk_flows_total', 0)
    if ransomware_total > 0:
        key_findings.append({
            'severity': 'CRITICAL' if findings_summary.get('CRITICAL', 0) > 0 else 'HIGH',
            'finding': f"{ransomware_total} flows on ransomware-associated ports detected.",
            'action': "Immediately review ransomware risk port exposure (see Ransomware Exposure sheet)."
        })

    lateral_total = mod05.get('total_lateral_flows', 0) if isinstance(mod05, dict) else 0
    if lateral_total > 0:
        key_findings.append({
            'severity': 'HIGH',
            'finding': f"{lateral_total} remote access / lateral movement flows found.",
            'action': "Apply micro-segmentation to control RDP/SSH/SMB lateral paths."
        })

    unmanaged_count = mod08.get('unique_unmanaged_src', 0) if isinstance(mod08, dict) else 0
    if unmanaged_count > 10:
        key_findings.append({
            'severity': 'MEDIUM',
            'finding': f"{unmanaged_count} unique unmanaged source hosts.",
            'action': "Onboard unmanaged hosts or apply explicit policy for their traffic."
        })

    if mod11.get('bytes_data_available'):
        total_mb = mod11.get('total_mb', 0)
        if total_mb > 1000:
            key_findings.append({
                'severity': 'INFO',
                'finding': f"Total data volume: {total_mb:.0f} MB across the analysis period.",
                'action': "Review high-volume flows for potential data exfiltration (see Bandwidth sheet)."
            })

    # Sort by severity
    _rank = {'CRITICAL': 0, 'HIGH': 1, 'MEDIUM': 2, 'LOW': 3, 'INFO': 4}
    key_findings.sort(key=lambda x: _rank.get(x.get('severity', 'INFO'), 99))

    return {
        'generated_at': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'kpis': kpis,
        'findings_summary': findings_summary,
        'total_findings': len(findings),
        'key_findings': key_findings,
        'findings': findings,
    }


def _fmt(n) -> str:
    """Format integer with thousands separator."""
    try:
        return f'{int(n):,}'
    except (TypeError, ValueError):
        return str(n)
