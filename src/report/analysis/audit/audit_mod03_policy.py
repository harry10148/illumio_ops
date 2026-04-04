"""
src/report/analysis/audit/audit_mod03_policy.py
Module 3: Policy & Rules Modifications

Illumio Policy Lifecycle:
  - DRAFT changes (rule_set.*, sec_rule.*): Edits to policy drafts only.
    NO firewall rules pushed to VENs yet.
  - PROVISION (sec_policy.create): Policy activated and pushed to workloads.
    Check workloads_affected for impact scope.

Enhanced fields from audit_generator:
  - src_ip: which IP the admin connected from when making changes
  - change_detail: human-readable summary of resource_changes (before → after)
  - workloads_affected: extracted from resource_changes and/or notifications
  - api_method: HTTP method used (PUT/POST/DELETE)

Based on Illumio Events Monitoring Best Practices:
- rule_set.create/update/delete: Monitor for overly broad scopes (null HREF = All)
- sec_rule.create/update/delete: Rules affecting all workloads/services/high-value labels
- sec_policy.create: Monitor workloads_affected field for excessive impact on provision
"""
import pandas as pd


_POLICY_EVENTS = [
    # Draft changes (not yet enforced)
    'rule_set.create', 'rule_set.update', 'rule_sets.delete', 'rule_set.delete',
    'sec_rule.create', 'sec_rule.update', 'sec_rule.delete',
    # Provision (policy activation — pushed to VENs)
    'sec_policy.create', 'sec_policy.delete', 'sec_policy.restore',
    # Supporting objects
    'label.create', 'label.update', 'label.delete',
    'label_group.create', 'label_group.update', 'label_group.delete',
    'ip_list.create', 'ip_list.update', 'ip_list.delete',
    'service.create', 'service.update', 'service.delete',
    'enforcement_boundary.create', 'enforcement_boundary.update', 'enforcement_boundary.delete',
    'api_key.create', 'api_key.update', 'api_key.delete',
    'authentication_settings.update',
    'firewall_settings.update',
    'workloads.unpair', 'agents.unpair',
    'pairing_profile.create', 'pairing_profile.delete',
]

_PROVISION_EVENTS = {'sec_policy.create', 'sec_policy.delete', 'sec_policy.restore'}

_DRAFT_RULE_EVENTS = {
    'rule_set.create', 'rule_set.update', 'rule_sets.delete', 'rule_set.delete',
    'sec_rule.create', 'sec_rule.update', 'sec_rule.delete',
}

_HIGH_RISK_EVENTS = {
    'workloads.unpair', 'agents.unpair',
    'authentication_settings.update', 'firewall_settings.update',
    'api_key.create', 'api_key.delete',
}

# Provision with workloads_affected above this threshold is flagged as high-impact
_HIGH_IMPACT_THRESHOLD = 50

# Optional enrichment columns to include when available
_EXTRA_COLS = ('src_ip', 'change_detail', 'api_method')


def _select_cols(df: pd.DataFrame, base_cols: list[str],
                 extra_cols: tuple[str, ...] = _EXTRA_COLS) -> list[str]:
    """Build column list: base + status + created_by + enrichment columns."""
    cols = list(base_cols)
    for col in ('status', 'created_by'):
        if col in df.columns:
            cols.append(col)
    for col in extra_cols:
        if col in df.columns and df[col].astype(str).str.strip().ne('').any():
            cols.append(col)
    return cols


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
            'high_risk_count': 0,
            'summary': pd.DataFrame(),
            'per_user': pd.DataFrame(),
            'provisions': pd.DataFrame(),
            'draft_events': pd.DataFrame(),
            'recent': pd.DataFrame(),
            'total_workloads_affected': 0,
            'max_workloads_affected': 0,
            'high_impact_provisions': [],
            'high_impact_threshold': _HIGH_IMPACT_THRESHOLD,
        }

    # ── Summary by event type ─────────────────────────────────────────────────
    summary = target_df['event_type'].value_counts().reset_index()
    summary.columns = ['Event Type', 'Count']

    # ── Draft rule changes (with change_detail for before → after diffs) ─────
    draft_mask = target_df['event_type'].isin(_DRAFT_RULE_EVENTS)
    rule_change_count = int(draft_mask.sum())
    draft_events = pd.DataFrame()
    if rule_change_count > 0:
        draft_df = target_df[draft_mask]
        cols = _select_cols(draft_df, ['timestamp', 'event_type', 'severity'],
                            extra_cols=('src_ip', 'change_detail'))
        draft_events = draft_df[cols].sort_values('timestamp', ascending=False).head(50)

    # ── Provision events (sec_policy.create / delete / restore) ──────────────
    prov_mask = target_df['event_type'].isin(_PROVISION_EVENTS)
    provision_count = int(prov_mask.sum())
    provisions = pd.DataFrame()
    total_workloads_affected = 0
    max_workloads_affected = 0
    high_impact_provisions = []

    if provision_count > 0:
        prov_df = target_df[prov_mask].copy()

        # workloads_affected is pre-extracted in audit_generator._build_dataframe
        if 'workloads_affected' not in prov_df.columns:
            prov_df['workloads_affected'] = 0

        total_workloads_affected = int(prov_df['workloads_affected'].sum())
        max_workloads_affected = int(prov_df['workloads_affected'].max())

        # Build provisions display table
        cols = ['timestamp', 'event_type', 'workloads_affected', 'severity']
        for col in ('status', 'created_by', 'src_ip', 'change_detail'):
            if col in prov_df.columns and prov_df[col].astype(str).str.strip().ne('').any():
                cols.append(col)
        provisions = prov_df[cols].sort_values('timestamp', ascending=False).head(30)

        # Identify high-impact provisions
        high_impact_mask = prov_df['workloads_affected'] >= _HIGH_IMPACT_THRESHOLD
        for _, row in prov_df[high_impact_mask].iterrows():
            actor = str(row.get('created_by', '—')) if 'created_by' in row else '—'
            src_ip = str(row.get('src_ip', '')) if 'src_ip' in row else ''
            high_impact_provisions.append({
                'timestamp': str(row.get('timestamp', '')),
                'event_type': str(row.get('event_type', '')),
                'workloads_affected': int(row.get('workloads_affected', 0)),
                'actor': actor,
                'src_ip': src_ip,
                'status': str(row.get('status', '')) if 'status' in row else '',
            })

    # ── High-risk event count ─────────────────────────────────────────────────
    high_risk_count = int(target_df['event_type'].isin(_HIGH_RISK_EVENTS).sum())

    # ── Per-user breakdown ────────────────────────────────────────────────────
    per_user = pd.DataFrame()
    if 'created_by' in target_df.columns:
        user_stats = target_df.groupby('created_by').agg(
            Total=('event_type', 'size'),
        ).reset_index()
        user_stats.columns = ['User', 'Total Changes']

        # Add unique source IPs per user if available
        if 'src_ip' in target_df.columns:
            ip_counts = (
                target_df[target_df['src_ip'].astype(str).str.strip() != '']
                .groupby('created_by')['src_ip']
                .nunique()
                .reset_index()
            )
            ip_counts.columns = ['User', 'Source IPs']
            user_stats = user_stats.merge(ip_counts, on='User', how='left')
            user_stats['Source IPs'] = user_stats['Source IPs'].fillna(0).astype(int)

        user_stats = user_stats.sort_values('Total Changes', ascending=False)
        per_user = user_stats.head(20)

    # ── Recent events (all policy events) ────────────────────────────────────
    cols_to_keep = _select_cols(
        target_df, ['timestamp', 'event_type', 'severity'],
        extra_cols=('src_ip', 'change_detail'),
    )
    recent = target_df[cols_to_keep].sort_values('timestamp', ascending=False).head(50)

    return {
        'total_policy_events': len(target_df),
        'provision_count': provision_count,
        'rule_change_count': rule_change_count,
        'high_risk_count': high_risk_count,
        'total_workloads_affected': total_workloads_affected,
        'max_workloads_affected': max_workloads_affected,
        'high_impact_threshold': _HIGH_IMPACT_THRESHOLD,
        'high_impact_provisions': high_impact_provisions,
        'summary': summary,
        'per_user': per_user,
        'provisions': provisions,
        'draft_events': draft_events,
        'recent': recent,
    }
