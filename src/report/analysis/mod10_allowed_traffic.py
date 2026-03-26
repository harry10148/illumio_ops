"""Module 10: Allowed Traffic Analysis."""
from __future__ import annotations
import pandas as pd


def allowed_traffic(df: pd.DataFrame, top_n: int = 20) -> dict:
    """
    Analyse flows with policy_decision='allowed':
    - Top allowed app→app flows
    - Allowed but unmanaged source (audit flag)
    - Top allowed ports
    """
    if df.empty:
        return {'error': 'No data'}

    allowed = df[df['policy_decision'] == 'allowed'].copy()
    if allowed.empty:
        return {'total_allowed': 0, 'note': 'No allowed flows in dataset'}

    # Top allowed app→app flows
    allowed['flow_pair'] = (allowed['src_app'].fillna('') + ' → ' +
                            allowed['dst_app'].fillna(''))
    top_app_flows = (allowed.groupby('flow_pair')['num_connections'].sum()
                     .reset_index().nlargest(top_n, 'num_connections')
                     .rename(columns={'flow_pair': 'Flow (src_app→dst_app)',
                                      'num_connections': 'Connections'}))

    # Allowed + unmanaged source = potential audit flag
    audit_flags = allowed[allowed['src_managed'] == False].copy()
    if not audit_flags.empty:
        audit_table = (audit_flags.groupby(['src_ip', 'dst_ip', 'port'])['num_connections']
                       .sum().reset_index().nlargest(top_n, 'num_connections')
                       .rename(columns={'src_ip': 'Unmanaged Source',
                                        'dst_ip': 'Destination',
                                        'port': 'Port',
                                        'num_connections': 'Connections'}))
    else:
        audit_table = pd.DataFrame()

    # Top allowed ports
    top_ports = (allowed[allowed['port'] > 0].groupby('port')['num_connections'].sum()
                 .reset_index().nlargest(top_n, 'num_connections')
                 .rename(columns={'port': 'Port', 'num_connections': 'Connections'}))

    return {
        'total_allowed': len(allowed),
        'top_app_flows': top_app_flows,
        'audit_flags': audit_table,
        'audit_flag_count': len(audit_flags),
        'top_allowed_ports': top_ports,
    }
