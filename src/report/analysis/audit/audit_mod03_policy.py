"""
src/report/analysis/audit/audit_mod03_policy.py
Module 3: Policy & Rules Modifications
"""
import pandas as pd

def audit_policy_changes(df: pd.DataFrame) -> dict:
    if df.empty or 'event_type' not in df.columns:
        return {'error': 'No event data available'}

    # Target Events
    policy_events = [
        'rule_set.create',
        'rule_set.update',
        'rule_sets.delete',
        'sec_rule.create',
        'sec_rule.update',
        'sec_rule.delete',
        'sec_policy.create'
    ]
    
    mask = df['event_type'].isin(policy_events)
    target_df = df[mask].copy()

    if target_df.empty:
        return {'total_policy_events': 0, 'summary': pd.DataFrame(), 'recent': pd.DataFrame()}

    summary = target_df['event_type'].value_counts().reset_index()
    summary.columns = ['Event Type', 'Count']
    
    cols_to_keep = ['timestamp', 'event_type', 'severity']
    if 'created_by' in target_df.columns:
        cols_to_keep.append('created_by')
        
    recent = target_df[cols_to_keep].sort_values('timestamp', ascending=False).head(50)

    # Note: For sec_policy.create, we might want to flag "provision" specifically if available in 'info'

    return {
        'total_policy_events': len(target_df),
        'summary': summary,
        'recent': recent
    }
