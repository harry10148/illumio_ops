"""
src/report/analysis/audit/audit_mod02_users.py
Module 2: User Activity & Authentication

Monitors login/logout events to detect:
- Repeated login failures (potential brute-force / credential stuffing)
- Unusual login patterns per user
- User session activity overview
- Source IPs of admin/API access (insider threat tracking)
- supplied_username from failed login notifications

Enhanced fields from audit_generator:
- src_ip: admin's source IP (action.src_ip)
- notification_detail: supplied_username and other details from notifications
"""
import pandas as pd


_USER_EVENTS = [
    'user.sign_in', 'user.login', 'user.authenticate',
    'user.sign_out', 'user.logout',
    'user.create', 'user.delete', 'user.update',
    'user.reset_password', 'user.update_password', 'user.use_expired_password',
    'user.invite', 'user.accept_invitation',
    'request.authentication_failed', 'request.authorization_failed',
]

# Auth request events are always failures by definition
_ALWAYS_FAILURE_EVENTS = {'request.authentication_failed', 'request.authorization_failed'}


def _is_failure(row) -> bool:
    """Determine if an event row represents a failure."""
    if row.get('event_type') in _ALWAYS_FAILURE_EVENTS:
        return True
    return str(row.get('status', '')).lower() == 'failure'


def audit_user_activity(df: pd.DataFrame) -> dict:
    if df.empty or 'event_type' not in df.columns:
        return {'error': 'No event data available'}

    mask = df['event_type'].isin(_USER_EVENTS)
    target_df = df[mask].copy()

    if target_df.empty:
        return {
            'total_user_events': 0,
            'failed_logins': 0,
            'unique_src_ips': 0,
            'summary': pd.DataFrame(),
            'per_user': pd.DataFrame(),
            'failed_login_detail': pd.DataFrame(),
            'recent': pd.DataFrame(),
        }

    # ── Failure detection ─────────────────────────────────────────────────────
    has_status = 'status' in target_df.columns
    if has_status:
        fail_mask = (
            target_df['event_type'].isin(_ALWAYS_FAILURE_EVENTS) |
            (target_df['status'].str.lower() == 'failure')
        )
    else:
        fail_mask = target_df['event_type'].isin(_ALWAYS_FAILURE_EVENTS)

    failed_logins = int(fail_mask.sum())

    # ── Unique source IPs ─────────────────────────────────────────────────────
    unique_src_ips = 0
    has_src_ip = 'src_ip' in target_df.columns
    if has_src_ip:
        non_empty_ips = target_df['src_ip'].astype(str).str.strip().replace('', pd.NA).dropna()
        unique_src_ips = int(non_empty_ips.nunique())

    # ── Summary by event type ─────────────────────────────────────────────────
    summary = target_df['event_type'].value_counts().reset_index()
    summary.columns = ['Event Type', 'Count']

    # ── Per-user breakdown ────────────────────────────────────────────────────
    per_user = pd.DataFrame()
    if 'created_by' in target_df.columns:
        target_df['_is_failure'] = fail_mask
        user_stats = target_df.groupby('created_by').agg(
            Total=('event_type', 'size'),
            Failures=('_is_failure', 'sum'),
        ).reset_index()
        user_stats.columns = ['User', 'Total Events', 'Failures']
        user_stats['Failures'] = user_stats['Failures'].astype(int)

        # Add unique source IPs per user if available
        if has_src_ip:
            ip_counts = (
                target_df[target_df['src_ip'].astype(str).str.strip() != '']
                .groupby('created_by')['src_ip']
                .nunique()
                .reset_index()
            )
            ip_counts.columns = ['User', 'Source IPs']
            user_stats = user_stats.merge(ip_counts, on='User', how='left')
            user_stats['Source IPs'] = user_stats['Source IPs'].fillna(0).astype(int)

        user_stats = user_stats.sort_values('Failures', ascending=False)
        per_user = user_stats.head(20)

    # ── Failed login detail (enriched with src_ip & notification context) ────
    failed_login_detail = pd.DataFrame()
    if failed_logins > 0:
        fail_df = target_df[fail_mask]
        detail_cols = ['timestamp', 'event_type']
        for col in ('created_by', 'src_ip', 'notification_detail', 'severity'):
            if col in fail_df.columns:
                # Only include column if it has meaningful data
                if fail_df[col].astype(str).str.strip().ne('').any():
                    detail_cols.append(col)
        failed_login_detail = (
            fail_df[detail_cols]
            .sort_values('timestamp', ascending=False)
            .head(30)
        )

    # ── Recent events ─────────────────────────────────────────────────────────
    cols_to_keep = ['timestamp', 'event_type', 'severity']
    for col in ('status', 'created_by', 'src_ip'):
        if col in target_df.columns and target_df[col].astype(str).str.strip().ne('').any():
            cols_to_keep.append(col)

    recent = (target_df[[c for c in cols_to_keep if c in target_df.columns]]
              .sort_values('timestamp', ascending=False)
              .head(50))

    return {
        'total_user_events': len(target_df),
        'failed_logins': failed_logins,
        'unique_src_ips': unique_src_ips,
        'summary': summary,
        'per_user': per_user,
        'failed_login_detail': failed_login_detail,
        'recent': recent,
    }
