"""Module 15: Lateral Movement Risk Detection."""
from __future__ import annotations
import pandas as pd
from collections import defaultdict, deque


# Ports commonly exploited for lateral movement
_LATERAL_PORTS = {
    445: 'SMB',
    135: 'RPC',
    139: 'NetBIOS',
    3389: 'RDP',
    22: 'SSH',
    5985: 'WinRM-HTTP',
    5986: 'WinRM-HTTPS',
    23: 'Telnet',
    2049: 'NFS',
    111: 'RPC Portmapper',
    389: 'LDAP',
    636: 'LDAPS',
    88: 'Kerberos',
    1433: 'MSSQL',
    3306: 'MySQL',
    5432: 'PostgreSQL',
}


def lateral_movement_risk(df: pd.DataFrame, top_n: int = 20) -> dict:
    """
    Detect lateral movement risk patterns in traffic data.

    Methodology:
    1. Lateral-port exposure: flows on known lateral movement ports
    2. Fan-out detection: single source talking to many destinations on lateral ports
       (classic lateral movement scanning / worm propagation pattern)
    3. Chain detection: A→B→C paths on lateral ports (reachability via BFS)
    4. Articulation points (proxy via high connectivity): nodes whose removal would
       disconnect large segments (critical chokepoints)
    5. Risk scoring per source IP and per application

    Returns risk scores, top risky flows, fan-out offenders, and chain paths.
    """
    if df.empty:
        return {'error': 'No data'}

    # ── Lateral port flows ─────────────────────────────────────────────────────
    lateral = df[df['port'].isin(_LATERAL_PORTS)].copy()
    lateral['service'] = lateral['port'].map(_LATERAL_PORTS)
    total_lateral = len(lateral)
    lateral_pct = round(total_lateral / len(df) * 100, 1) if len(df) else 0

    # ── Lateral port summary by service ───────────────────────────────────────
    service_summary = (lateral.groupby(['port', 'service', 'policy_decision'])
                       .agg(connections=('num_connections', 'sum'),
                            unique_src=('src_ip', 'nunique'),
                            unique_dst=('dst_ip', 'nunique'))
                       .reset_index()
                       .nlargest(top_n, 'connections')
                       .rename(columns={'port': 'Port', 'service': 'Service',
                                        'policy_decision': 'Decision',
                                        'connections': 'Connections',
                                        'unique_src': 'Unique Sources',
                                        'unique_dst': 'Unique Destinations'}))

    # ── Fan-out detection: sources with high destination spread ───────────────
    fan_out = _detect_fan_out(lateral, top_n=top_n)

    # ── App-level lateral path chains (BFS reachability) ─────────────────────
    app_chains = _detect_app_chains(lateral, max_depth=3, top_n=top_n)

    # ── Articulation proxies: high betweenness nodes ──────────────────────────
    articulation = _detect_articulation_proxies(lateral, top_n=top_n)

    # ── Per-source risk scoring ────────────────────────────────────────────────
    source_risk = _score_sources(lateral, top_n=top_n)

    # ── Allowed lateral flows (highest risk — explicit permits for LM ports) ──
    allowed_lateral = (lateral[lateral['policy_decision'] == 'allowed']
                       .groupby(['src_app', 'dst_app', 'port', 'service'])
                       .agg(connections=('num_connections', 'sum'),
                            unique_src=('src_ip', 'nunique'))
                       .reset_index()
                       .nlargest(top_n, 'connections')
                       .rename(columns={'src_app': 'Source App', 'dst_app': 'Destination App',
                                        'port': 'Port', 'service': 'Service',
                                        'connections': 'Connections',
                                        'unique_src': 'Unique Sources'}))

    return {
        'total_lateral_flows': total_lateral,
        'lateral_pct': lateral_pct,
        'service_summary': service_summary,
        'fan_out_sources': fan_out,
        'app_chains': app_chains,
        'articulation_proxies': articulation,
        'source_risk_scores': source_risk,
        'allowed_lateral_flows': allowed_lateral,
    }


def _detect_fan_out(lateral: pd.DataFrame, threshold: int = 5,
                    top_n: int = 20) -> pd.DataFrame:
    """Sources communicating to many destinations on lateral ports — high fan-out = suspicious."""
    if lateral.empty:
        return pd.DataFrame()
    fan = (lateral.groupby('src_ip')
           .agg(unique_dst=('dst_ip', 'nunique'),
                unique_ports=('port', 'nunique'),
                connections=('num_connections', 'sum'),
                services=('service', lambda x: ', '.join(sorted(set(x)))))
           .reset_index()
           .query(f'unique_dst >= {threshold}')
           .nlargest(top_n, 'unique_dst')
           .rename(columns={'src_ip': 'Source IP', 'unique_dst': 'Unique Destinations',
                            'unique_ports': 'Lateral Ports', 'connections': 'Connections',
                            'services': 'Services'}))
    # Add risk tier
    if not fan.empty:
        fan['Risk'] = fan['Unique Destinations'].apply(
            lambda x: 'Critical' if x >= 20 else ('High' if x >= 10 else 'Medium'))
    return fan.reset_index(drop=True)


def _detect_app_chains(lateral: pd.DataFrame, max_depth: int = 3,
                       top_n: int = 20) -> pd.DataFrame:
    """
    BFS from each app node: find apps reachable within max_depth hops on lateral ports.
    High reachability = high blast radius if that app is compromised.
    """
    if lateral.empty:
        return pd.DataFrame()

    # Build app→app adjacency (only allowed flows for reachability)
    allowed = lateral[lateral['policy_decision'] == 'allowed']
    if allowed.empty:
        return pd.DataFrame()

    adj: dict[str, set[str]] = defaultdict(set)
    for _, row in allowed.iterrows():
        src = str(row.get('src_app') or '')
        dst = str(row.get('dst_app') or '')
        if src and dst and src != dst:
            adj[src].add(dst)

    if not adj:
        return pd.DataFrame()

    rows = []
    all_nodes = set(adj.keys()) | {d for dsts in adj.values() for d in dsts}

    for start in all_nodes:
        visited: set[str] = {start}
        queue: deque[tuple[str, int]] = deque([(start, 0)])
        reachable = []
        while queue:
            node, depth = queue.popleft()
            if depth >= max_depth:
                continue
            for neighbor in adj.get(node, set()):
                if neighbor not in visited:
                    visited.add(neighbor)
                    reachable.append(neighbor)
                    queue.append((neighbor, depth + 1))
        rows.append({
            'Source App': start,
            'Reachable Apps (lateral)': len(reachable),
            'Max Depth': max_depth,
            'Apps in Blast Radius': ', '.join(sorted(reachable)[:5]) + ('...' if len(reachable) > 5 else ''),
        })

    chains = (pd.DataFrame(rows)
              .query('`Reachable Apps (lateral)` > 0')
              .nlargest(top_n, 'Reachable Apps (lateral)')
              .reset_index(drop=True))
    return chains


def _detect_articulation_proxies(lateral: pd.DataFrame, top_n: int = 20) -> pd.DataFrame:
    """
    Proxy for articulation points: IP nodes with both high in-degree and out-degree
    on lateral ports are likely chokepoints — disrupting them would affect many paths.
    """
    if lateral.empty:
        return pd.DataFrame()

    in_deg: dict[str, int] = defaultdict(int)
    out_deg: dict[str, int] = defaultdict(int)
    in_conn: dict[str, int] = defaultdict(int)
    out_conn: dict[str, int] = defaultdict(int)

    for _, row in lateral.iterrows():
        src = str(row.get('src_ip') or '')
        dst = str(row.get('dst_ip') or '')
        w = int(row.get('num_connections', 1))
        if src:
            out_deg[src] += 1
            out_conn[src] += w
        if dst:
            in_deg[dst] += 1
            in_conn[dst] += w

    all_ips = set(in_deg) | set(out_deg)
    rows = []
    for ip in all_ips:
        ind = in_deg.get(ip, 0)
        outd = out_deg.get(ip, 0)
        if ind >= 2 and outd >= 2:
            rows.append({
                'IP': ip,
                'In-Degree': ind,
                'Out-Degree': outd,
                'Connections In': in_conn.get(ip, 0),
                'Connections Out': out_conn.get(ip, 0),
                'Chokepoint Score': ind + outd,
            })

    if not rows:
        return pd.DataFrame()

    return (pd.DataFrame(rows)
            .nlargest(top_n, 'Chokepoint Score')
            .reset_index(drop=True))


def _score_sources(lateral: pd.DataFrame, top_n: int = 20) -> pd.DataFrame:
    """Score each source IP by lateral movement risk (0-100)."""
    if lateral.empty:
        return pd.DataFrame()

    src_stats = (lateral.groupby('src_ip')
                 .agg(connections=('num_connections', 'sum'),
                      unique_dst=('dst_ip', 'nunique'),
                      unique_ports=('port', 'nunique'),
                      allowed=('policy_decision', lambda x: (x == 'allowed').sum()),
                      blocked=('policy_decision', lambda x: (x.isin(['blocked', 'potentially_blocked'])).sum()),
                      services=('service', lambda x: ', '.join(sorted(set(x)))))
                 .reset_index())

    max_conn = src_stats['connections'].max() or 1
    max_dst = src_stats['unique_dst'].max() or 1
    max_ports = src_stats['unique_ports'].max() or 1

    def _score(row):
        conn_score = (row['connections'] / max_conn) * 30
        dst_score = (row['unique_dst'] / max_dst) * 40
        port_score = (row['unique_ports'] / max_ports) * 20
        # Penalty: if many flows are blocked → active scanning
        total = row['connections'] or 1
        block_ratio = row['blocked'] / total
        block_penalty = block_ratio * 10
        return round(conn_score + dst_score + port_score + block_penalty, 1)

    src_stats['Risk Score'] = src_stats.apply(_score, axis=1)
    src_stats['Risk Level'] = src_stats['Risk Score'].apply(
        lambda s: 'Critical' if s >= 70 else ('High' if s >= 50 else ('Medium' if s >= 30 else 'Low')))

    return (src_stats.nlargest(top_n, 'Risk Score')
            .rename(columns={'src_ip': 'Source IP', 'connections': 'Connections',
                             'unique_dst': 'Unique Destinations', 'unique_ports': 'Lateral Ports',
                             'allowed': 'Allowed', 'blocked': 'Blocked/PB',
                             'services': 'Services'})
            .reset_index(drop=True))
