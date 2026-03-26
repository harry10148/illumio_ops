"""Module 14: Infrastructure Scoring — Graph-based application criticality."""
from __future__ import annotations
import pandas as pd
from collections import defaultdict


def infrastructure_scoring(df: pd.DataFrame, top_n: int = 20) -> dict:
    """
    Score application nodes by infrastructure criticality using directed graph analysis.

    Methodology (inspired by MCP server graph approach):
    - Build directed app→app communication graph from traffic flows
    - In-degree  = number of unique apps that depend on this app (consumer count)
    - Out-degree = number of unique apps this app communicates with (provider count)
    - Dual-pattern score = weighted combination of in-degree (criticality as provider)
      and out-degree (blast radius as consumer)
    - Betweenness proxy = apps that appear as intermediary (both high in+out degree)

    Returns ranked application nodes with scores and role classification.
    """
    if df.empty:
        return {'error': 'No data'}

    # Filter to flows between known managed apps only
    app_flows = df[
        df['src_app'].notna() & df['src_app'].ne('') &
        df['dst_app'].notna() & df['dst_app'].ne('')
    ].copy()

    if app_flows.empty:
        return {'error': 'No app-labeled flows found'}

    # Build adjacency: src_app → dst_app with connection weight
    edge_weights: dict[tuple[str, str], int] = defaultdict(int)
    for _, row in app_flows.iterrows():
        edge_weights[(row['src_app'], row['dst_app'])] += int(row.get('num_connections', 1))

    # Compute per-node metrics
    in_degree: dict[str, int] = defaultdict(int)    # how many unique apps point TO this node
    out_degree: dict[str, int] = defaultdict(int)   # how many unique apps this node points TO
    in_weight: dict[str, int] = defaultdict(int)    # total connections received
    out_weight: dict[str, int] = defaultdict(int)   # total connections sent
    all_apps: set[str] = set()

    for (src, dst), w in edge_weights.items():
        all_apps.add(src)
        all_apps.add(dst)
        in_degree[dst] += 1
        out_degree[src] += 1
        in_weight[dst] += w
        out_weight[src] += w

    # Normalise degrees for scoring
    max_in = max(in_degree.values(), default=1)
    max_out = max(out_degree.values(), default=1)

    rows = []
    for app in all_apps:
        ind = in_degree.get(app, 0)
        outd = out_degree.get(app, 0)
        inw = in_weight.get(app, 0)
        outw = out_weight.get(app, 0)

        # Provider criticality: heavily depended-upon apps score higher
        provider_score = round((ind / max_in) * 60 + (inw / max(in_weight.values(), default=1)) * 40, 1)
        # Consumer blast-radius: apps that talk to many others → larger blast radius if compromised
        consumer_score = round((outd / max_out) * 60 + (outw / max(out_weight.values(), default=1)) * 40, 1)
        # Combined infrastructure score
        infra_score = round(provider_score * 0.6 + consumer_score * 0.4, 1)

        # Role classification
        if ind > 3 and outd > 3:
            role = 'Hub'
        elif ind > outd * 1.5:
            role = 'Provider'
        elif outd > ind * 1.5:
            role = 'Consumer'
        else:
            role = 'Peer'

        rows.append({
            'Application': app,
            'In-Degree': ind,
            'Out-Degree': outd,
            'Connections In': inw,
            'Connections Out': outw,
            'Provider Score': provider_score,
            'Consumer Score': consumer_score,
            'Infra Score': infra_score,
            'Role': role,
        })

    scored = (pd.DataFrame(rows)
              .sort_values('Infra Score', ascending=False)
              .reset_index(drop=True))

    top_apps = scored.head(top_n)

    # Top edges by traffic volume
    edge_df = pd.DataFrame([
        {'Source App': src, 'Destination App': dst, 'Connections': w}
        for (src, dst), w in edge_weights.items()
    ]).nlargest(top_n, 'Connections').reset_index(drop=True)

    # Role distribution summary
    role_summary = (scored.groupby('Role').size()
                    .reset_index(name='Count')
                    .sort_values('Count', ascending=False))

    # Hub apps (high in + out degree) — these are highest blast-radius targets
    hub_apps = scored[scored['Role'] == 'Hub'].head(10)

    return {
        'total_apps': len(all_apps),
        'total_edges': len(edge_weights),
        'top_apps': top_apps,
        'top_edges': edge_df,
        'role_summary': role_summary,
        'hub_apps': hub_apps,
    }
