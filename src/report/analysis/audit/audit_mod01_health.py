"""
src/report/analysis/audit/audit_mod01_health.py
Module 1: System Health & Agent Status
"""
import pandas as pd

def audit_system_health(df: pd.DataFrame) -> dict:
    if df.empty or 'event_type' not in df.columns:
        return {'error': 'No event data available'}

    # Target Events
    health_events = [
        'system_health',
        'system_task.agent_missed_heartbeats_check',
        'system_task.agent_offline_check',
        'lost_agent.found',
        'agent.suspend',
        'agent.clone_detected',
        'agent.tampering'
    ]
    
    mask = df['event_type'].isin(health_events)
    target_df = df[mask].copy()

    if target_df.empty:
        return {'total_health_events': 0, 'summary': pd.DataFrame(), 'recent': pd.DataFrame()}

    # Group by event type
    summary = target_df['event_type'].value_counts().reset_index()
    summary.columns = ['Event Type', 'Count']
    
    # Get details (top 50)
    cols_to_keep = ['timestamp', 'event_type', 'severity']
    if 'created_by' in target_df.columns:
        cols_to_keep.append('created_by')
    
    recent = target_df[cols_to_keep].sort_values('timestamp', ascending=False).head(50)

    return {
        'total_health_events': len(target_df),
        'summary': summary,
        'recent': recent
    }
