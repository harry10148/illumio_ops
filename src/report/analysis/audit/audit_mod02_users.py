"""
src/report/analysis/audit/audit_mod02_users.py
Module 2: User Activity & Authentication

Monitors login/logout events to detect:
- Repeated login failures (potential brute-force / credential stuffing)
- Unusual login patterns per user
- User session activity overview
"""
import pandas as pd


_USER_EVENTS = [
    'user.sign_in',
    'user.login',
    'user.login_failed',
    'user.sign_out',
    'user.logout.success',
    'user.password_change',
    'user.use_expired_password',
    'user.invitation',
]

_FAILURE_EVENTS = {'user.login_failed', 'user.use_expired_password'}


def audit_user_activity(df: pd.DataFrame) -> dict:
    if df.empty or 'event_type' not in df.columns:
        return {'error': 'No event data available'}

    mask = df['event_type'].isin(_USER_EVENTS)
    target_df = df[mask].copy()

    if target_df.empty:
        return {
            'total_user_events': 0,
            'failed_logins': 0,
            'summary': pd.DataFrame(),
            'per_user': pd.DataFrame(),
            'recent': pd.DataFrame(),
        }

    # Summary by event type
    summary = target_df['event_type'].value_counts().reset_index()
    summary.columns = ['Event Type', 'Count']

    # Failed logins
    failed_mask = target_df['event_type'].isin(_FAILURE_EVENTS)
    failed_logins = int(failed_mask.sum())

    # Per-user breakdown (if created_by is available)
    per_user = pd.DataFrame()
    if 'created_by' in target_df.columns:
        user_stats = target_df.groupby('created_by').agg(
            Total=('event_type', 'size'),
            Failures=('event_type', lambda x: x.isin(_FAILURE_EVENTS).sum()),
        ).reset_index()
        user_stats.columns = ['User', 'Total Events', 'Failures']
        user_stats = user_stats.sort_values('Failures', ascending=False)
        per_user = user_stats.head(20)

    # Recent events
    cols_to_keep = ['timestamp', 'event_type', 'severity']
    if 'created_by' in target_df.columns:
        cols_to_keep.append('created_by')

    recent = target_df[cols_to_keep].sort_values('timestamp', ascending=False).head(50)

    return {
        'total_user_events': len(target_df),
        'failed_logins': failed_logins,
        'summary': summary,
        'per_user': per_user,
        'recent': recent,
    }
