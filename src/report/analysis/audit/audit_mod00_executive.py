"""
src/report/analysis/audit/audit_mod00_executive.py
Module 0: Executive Summary for Audit Report
Combines insights from mod01, mod02, and mod03.
"""
import pandas as pd
import datetime


def audit_executive_summary(results: dict, df: pd.DataFrame) -> dict:
    mod01 = results.get('mod01', {})
    mod02 = results.get('mod02', {})
    mod03 = results.get('mod03', {})

    kpis = []

    # KPI 1: Total Events Processed
    kpis.append({'label': 'Total Events', 'value': f"{len(df):,}"})

    # KPI 2: System Health Events
    total_health = mod01.get('total_health_events', 0)
    kpis.append({'label': 'System Health Events', 'value': f"{total_health:,}"})

    # KPI 3: Security Concerns (tampering, suspend, clone)
    sec_concerns = mod01.get('security_concern_count', 0)
    kpis.append({'label': 'Security Concerns', 'value': str(sec_concerns)})

    # KPI 4: Agent Connectivity Issues
    conn_issues = mod01.get('connectivity_event_count', 0)
    kpis.append({'label': 'Agent Connectivity', 'value': str(conn_issues)})

    # KPI 5: Failed Logins
    failed_logins = mod02.get('failed_logins', 0)
    kpis.append({'label': 'Failed Logins', 'value': str(failed_logins)})

    # KPI 6: Policy Provisions
    provisions = mod03.get('provision_count', 0)
    kpis.append({'label': 'Policy Provisions', 'value': str(provisions)})

    # KPI 7: Rule Changes
    rule_changes = mod03.get('rule_change_count', 0)
    kpis.append({'label': 'Rule Changes', 'value': str(rule_changes)})

    # Top Event Types overall
    top_events = pd.DataFrame()
    if 'event_type' in df.columns and not df.empty:
        top_events = df['event_type'].value_counts().reset_index().head(15)
        top_events.columns = ['Event Type', 'Count']

    # Severity distribution
    severity_dist = pd.DataFrame()
    if 'severity' in df.columns and not df.empty:
        severity_dist = df['severity'].value_counts().reset_index()
        severity_dist.columns = ['Severity', 'Count']

    return {
        'generated_at': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'kpis': kpis,
        'top_events_overall': top_events,
        'severity_distribution': severity_dist,
    }
