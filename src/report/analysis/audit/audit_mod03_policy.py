"""
src/report/analysis/audit/audit_mod03_policy.py
Module 3: Policy & Rules Modifications

Based on Illumio Events Monitoring Best Practices:
- rule_set.create/update/delete: Monitor for overly broad scopes (null HREF = All)
- sec_rule.create/update/delete: Rules affecting all workloads/services/high-value labels
- sec_policy.create: Monitor workloads_affected field for excessive impact on provision
"""
import pandas as pd


_POLICY_EVENTS = [
    'rule_set.create',
    'rule_set.update',
    'rule_sets.delete',
    'sec_rule.create',
    'sec_rule.update',
    'sec_rule.delete',
    'sec_policy.create',
    'sec_policy.delete',
    'label.create',
    'label.update',
    'label.delete',
    'label_group.create',
    'label_group.update',
    'label_group.delete',
    'ip_list.create',
    'ip_list.update',
    'ip_list.delete',
    'service.create',
    'service.update',
    'service.delete',
]

_PROVISION_EVENTS = {'sec_policy.create', 'sec_policy.delete'}
_RULE_CHANGE_EVENTS = {
    'rule_set.create', 'rule_set.update', 'rule_sets.delete',
    'sec_rule.create', 'sec_rule.update', 'sec_rule.delete',
}


def audit_policy_changes(df: pd.DataFrame) -> dict:
    if df.empty or 'event_type' not in df.columns:
        return {'error': 'No event data available'}

    mask = df['event_type'].isin(_POLICY_EVENTS)
    target_df = df[mask].copy()

    if target_df.empty:
        return {
            'total_policy_events': 0,
            'provision_count': 0,
            'rule_change_count': 0,
            'summary': pd.DataFrame(),
            'per_user': pd.DataFrame(),
            'provisions': pd.DataFrame(),
            'recent': pd.DataFrame(),
        }

    # Summary by event type
    summary = target_df['event_type'].value_counts().reset_index()
    summary.columns = ['Event Type', 'Count']

    # Provision events (high-impact)
    prov_mask = target_df['event_type'].isin(_PROVISION_EVENTS)
    provision_count = int(prov_mask.sum())
    provisions = pd.DataFrame()
    if provision_count > 0:
        prov_df = target_df[prov_mask]
        cols = ['timestamp', 'event_type', 'severity']
        if 'created_by' in prov_df.columns:
            cols.append('created_by')
        provisions = prov_df[cols].sort_values('timestamp', ascending=False).head(30)

    # Rule change count
    rule_mask = target_df['event_type'].isin(_RULE_CHANGE_EVENTS)
    rule_change_count = int(rule_mask.sum())

    # Per-user breakdown
    per_user = pd.DataFrame()
    if 'created_by' in target_df.columns:
        user_stats = target_df.groupby('created_by').agg(
            Total=('event_type', 'size'),
        ).reset_index()
        user_stats.columns = ['User', 'Total Changes']
        user_stats = user_stats.sort_values('Total Changes', ascending=False)
        per_user = user_stats.head(20)

    # Recent events
    cols_to_keep = ['timestamp', 'event_type', 'severity']
    if 'created_by' in target_df.columns:
        cols_to_keep.append('created_by')

    recent = target_df[cols_to_keep].sort_values('timestamp', ascending=False).head(50)

    return {
        'total_policy_events': len(target_df),
        'provision_count': provision_count,
        'rule_change_count': rule_change_count,
        'summary': summary,
        'per_user': per_user,
        'provisions': provisions,
        'recent': recent,
    }
