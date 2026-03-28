"""
src/report/analysis/audit/audit_mod01_health.py
Module 1: System Health & Agent Status

Based on Illumio Events Monitoring Best Practices:
- system_health: CPU/memory metrics, monitor severity changes (Warning/Error/Fatal)
- agent_missed_heartbeats_check: VENs missing 3+ heartbeats (15 min)
- agent_offline_check: VENs offline after 12 missed heartbeats; removed from policy
- lost_agent.found: Workloads with disconnected VENs requiring re-pairing
- agent.suspend: Unintended suspensions may indicate compromise
- agent.tampering: Firewall tampering detected; suggests potential workload compromise
- agent.update: Monitor for process failures or policy deployment issues
- agent.clone_detected: Severity error/1 indicates intervention needed
"""
import pandas as pd


# Event types recommended by Illumio monitoring best practices
_HEALTH_EVENTS = [
    'system_health',
    'system_task.agent_missed_heartbeats_check',
    'system_task.agent_offline_check',
    'lost_agent.found',
    'agent.suspend',
    'agent.clone_detected',
    'agent.tampering',
    'agent.update',
]

# Events that indicate potential security concerns
_SECURITY_CONCERN_EVENTS = {
    'agent.suspend',
    'agent.tampering',
    'agent.clone_detected',
}

# Events related to agent connectivity
_CONNECTIVITY_EVENTS = {
    'system_task.agent_missed_heartbeats_check',
    'system_task.agent_offline_check',
    'lost_agent.found',
}


def audit_system_health(df: pd.DataFrame) -> dict:
    if df.empty or 'event_type' not in df.columns:
        return {'error': 'No event data available'}

    mask = df['event_type'].isin(_HEALTH_EVENTS)
    target_df = df[mask].copy()

    if target_df.empty:
        return {
            'total_health_events': 0,
            'summary': pd.DataFrame(),
            'severity_breakdown': pd.DataFrame(),
            'connectivity_events': pd.DataFrame(),
            'security_concerns': pd.DataFrame(),
            'recent': pd.DataFrame(),
        }

    # Summary by event type
    summary = target_df['event_type'].value_counts().reset_index()
    summary.columns = ['Event Type', 'Count']

    # Severity breakdown
    severity_breakdown = pd.DataFrame()
    if 'severity' in target_df.columns:
        sev_pivot = target_df.groupby(['event_type', 'severity']).size().reset_index(name='Count')
        sev_pivot.columns = ['Event Type', 'Severity', 'Count']
        severity_breakdown = sev_pivot.sort_values(['Event Type', 'Count'], ascending=[True, False])

    # Agent connectivity events
    conn_mask = target_df['event_type'].isin(_CONNECTIVITY_EVENTS)
    conn_df = target_df[conn_mask]
    connectivity_events = pd.DataFrame()
    if not conn_df.empty:
        cols = ['timestamp', 'event_type', 'severity']
        if 'created_by' in conn_df.columns:
            cols.append('created_by')
        connectivity_events = conn_df[cols].sort_values('timestamp', ascending=False).head(30)

    # Security concern events (tampering, suspend, clone)
    sec_mask = target_df['event_type'].isin(_SECURITY_CONCERN_EVENTS)
    sec_df = target_df[sec_mask]
    security_concerns = pd.DataFrame()
    if not sec_df.empty:
        cols = ['timestamp', 'event_type', 'severity']
        if 'created_by' in sec_df.columns:
            cols.append('created_by')
        security_concerns = sec_df[cols].sort_values('timestamp', ascending=False).head(30)

    # Recent events (all health)
    cols_to_keep = ['timestamp', 'event_type', 'severity']
    if 'created_by' in target_df.columns:
        cols_to_keep.append('created_by')
    recent = target_df[cols_to_keep].sort_values('timestamp', ascending=False).head(50)

    return {
        'total_health_events': len(target_df),
        'security_concern_count': len(sec_df),
        'connectivity_event_count': len(conn_df),
        'summary': summary,
        'severity_breakdown': severity_breakdown,
        'connectivity_events': connectivity_events,
        'security_concerns': security_concerns,
        'recent': recent,
    }
