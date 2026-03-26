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
    kpis.append({'label': 'Total Events', 'value': str(len(df))})
    
    # KPI 2: Total System Alerts
    total_health = mod01.get('total_health_events', 0)
    kpis.append({'label': 'System Health Events', 'value': str(total_health)})
    
    # KPI 3: Failed Logins
    failed_logins = mod02.get('failed_logins', 0)
    kpis.append({'label': 'Failed Logins', 'value': str(failed_logins)})

    # KPI 4: Policy Modifications
    total_policy = mod03.get('total_policy_events', 0)
    kpis.append({'label': 'Policy Modifications', 'value': str(total_policy)})

    # Top Event Types overall
    top_events = pd.DataFrame()
    if 'event_type' in df.columns and not df.empty:
        top_events = df['event_type'].value_counts().reset_index().head(10)
        top_events.columns = ['Event Type', 'Count']

    return {
        'generated_at': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'kpis': kpis,
        'top_events_overall': top_events
    }
