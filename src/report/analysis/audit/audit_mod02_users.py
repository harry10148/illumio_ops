"""
src/report/analysis/audit/audit_mod02_users.py
Module 2: User Activity & Authentication
"""
import pandas as pd

def audit_user_activity(df: pd.DataFrame) -> dict:
    if df.empty or 'event_type' not in df.columns:
        return {'error': 'No event data available'}

    # Target Events
    user_events = [
        'user.sign_in',
        'user.login',
        'user.login_failed',
        'user.sign_out',
        'user.logout.success'
    ]
    
    mask = df['event_type'].isin(user_events)
    target_df = df[mask].copy()

    if target_df.empty:
        return {'total_user_events': 0, 'failed_logins': 0, 'summary': pd.DataFrame(), 'recent': pd.DataFrame()}

    # Extract user identity if available (depends on API field, typically created_by.href or info.username)
    # Group by event type
    summary = target_df['event_type'].value_counts().reset_index()
    summary.columns = ['Event Type', 'Count']
    
    failed_logins = len(target_df[target_df['event_type'] == 'user.login_failed'])

    # Get details
    cols_to_keep = ['timestamp', 'event_type', 'severity']
    if 'created_by' in target_df.columns:
        cols_to_keep.append('created_by')
        
    recent = target_df[cols_to_keep].sort_values('timestamp', ascending=False).head(50)

    return {
        'total_user_events': len(target_df),
        'failed_logins': failed_logins,
        'summary': summary,
        'recent': recent
    }
