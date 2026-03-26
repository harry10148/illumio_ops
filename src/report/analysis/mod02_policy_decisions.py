"""Module 2: Policy Decision Breakdown."""
from __future__ import annotations
import pandas as pd


def policy_decision_analysis(df: pd.DataFrame, top_n: int = 20) -> dict:
    """
    Breakdown of traffic by policy_decision. Per decision: top app→app flows,
    top ports, managed/unmanaged ratio, inbound/outbound split, per-port coverage.
    """
    if df.empty:
        return {'error': 'No data'}

    total = len(df)
    results = {}

    for decision in ('allowed', 'blocked', 'potentially_blocked', 'unknown'):
        sub = df[df['policy_decision'] == decision]
        if sub.empty:
            results[decision] = {'count': 0}
            continue

        sub = sub.copy()
        sub['flow_pair'] = sub['src_app'].fillna('') + ' → ' + sub['dst_app'].fillna('')

        # Top app→app flows
        top_app_flows = (sub.groupby('flow_pair')['num_connections'].sum()
                         .nlargest(top_n).reset_index()
                         .rename(columns={'flow_pair': 'Flow (src_app→dst_app)',
                                          'num_connections': 'Connections'}))

        # Top ports
        top_ports = (sub[sub['port'] > 0].groupby('port')['num_connections'].sum()
                     .nlargest(top_n).reset_index()
                     .rename(columns={'port': 'Port', 'num_connections': 'Connections'}))

        # Managed ratio
        managed_count = int(sub['src_managed'].sum())
        unmanaged_count = len(sub) - managed_count

        # Inbound vs outbound split (dst_managed=True → inbound to a VEN)
        inbound_mask = sub['dst_managed'] == True if 'dst_managed' in sub.columns else pd.Series(False, index=sub.index)
        outbound_mask = ~inbound_mask
        inbound_count = int(inbound_mask.sum())
        outbound_count = int(outbound_mask.sum())

        # Per-direction top ports
        top_inbound_ports = (
            sub[inbound_mask & (sub['port'] > 0)]
            .groupby('port')['num_connections'].sum()
            .nlargest(10).reset_index()
            .rename(columns={'port': 'Port', 'num_connections': 'Connections'})
        ) if inbound_count > 0 else pd.DataFrame()

        top_outbound_ports = (
            sub[outbound_mask & (sub['port'] > 0)]
            .groupby('port')['num_connections'].sum()
            .nlargest(10).reset_index()
            .rename(columns={'port': 'Port', 'num_connections': 'Connections'})
        ) if outbound_count > 0 else pd.DataFrame()

        results[decision] = {
            'count': len(sub),
            'pct_of_total': round(len(sub) / total * 100, 1) if total > 0 else 0.0,
            'top_app_flows': top_app_flows,
            'top_ports': top_ports,
            'managed_src_count': managed_count,
            'unmanaged_src_count': unmanaged_count,
            'inbound_count': inbound_count,
            'outbound_count': outbound_count,
            'top_inbound_ports': top_inbound_ports,
            'top_outbound_ports': top_outbound_ports,
        }

    # Per-port coverage: for each port, what % of flows are allowed
    port_coverage = _compute_port_coverage(df, top_n=top_n)
    results['port_coverage'] = port_coverage

    # Summary table
    summary = pd.DataFrame([
        {
            'Decision': d,
            'Flows': results[d]['count'],
            '% of Total': results[d].get('pct_of_total', 0.0),
            'Inbound': results[d].get('inbound_count', 0),
            'Outbound': results[d].get('outbound_count', 0),
        }
        for d in ('allowed', 'blocked', 'potentially_blocked', 'unknown')
    ])
    results['summary'] = summary
    return results


def _compute_port_coverage(df: pd.DataFrame, top_n: int = 20) -> pd.DataFrame:
    """For each high-traffic port: allowed vs blocked counts and coverage %."""
    port_df = df[df['port'] > 0].copy()
    if port_df.empty:
        return pd.DataFrame()

    grouped = port_df.groupby(['port', 'policy_decision'])['num_connections'].sum().unstack(fill_value=0)
    allowed = grouped.get('allowed', pd.Series(0, index=grouped.index))
    blocked = grouped.get('blocked', pd.Series(0, index=grouped.index))
    pb = grouped.get('potentially_blocked', pd.Series(0, index=grouped.index))

    total_per_port = grouped.sum(axis=1)
    coverage = (allowed / total_per_port.replace(0, 1) * 100).round(1)

    result = pd.DataFrame({
        'Port': grouped.index,
        'Total Flows': total_per_port.values,
        'Allowed': allowed.values,
        'Blocked': (blocked + pb).values,
        'Coverage %': coverage.values,
    }).sort_values('Total Flows', ascending=False).head(top_n).reset_index(drop=True)

    return result
