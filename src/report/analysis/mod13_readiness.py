"""Module 13: Enforcement Readiness Score (0-100)."""
from __future__ import annotations
import pandas as pd


# Score weights (total = 100)
_WEIGHTS = {
    'policy_coverage': 40,
    'ringfence_ratio': 20,
    'enforcement_mode': 20,
    'no_blocked_flows': 10,
    'remote_app_coverage': 10,
}

# Well-known remote access ports — used for remote app coverage sub-score
_REMOTE_PORTS = {22, 3389, 5900, 5901, 5938, 3283}


def enforcement_readiness(df: pd.DataFrame, workloads: list | None = None,
                          top_n: int = 20) -> dict:
    """
    Compute a 0-100 enforcement readiness score across 5 factors:

    1. Policy Coverage (40 pts)  — % of flows with policy_decision = 'allowed'
    2. Ringfence Ratio  (20 pts) — % of app→app flows where both src/dst have same app label
    3. Enforcement Mode (20 pts) — % of managed workloads in 'enforced' mode (requires workloads list)
    4. No Blocked Flows (10 pts) — penalises blocked/PB flows proportionally
    5. Remote App Coverage (10 pts) — % of remote-access-port flows that are 'allowed'

    Returns score breakdown per factor plus ranked remediation recommendations.
    """
    if df.empty:
        return {'error': 'No data'}

    total = len(df)

    # ── Factor 1: Policy Coverage ──────────────────────────────────────────────
    allowed_count = int((df['policy_decision'] == 'allowed').sum())
    coverage_ratio = allowed_count / total if total else 0
    f1_score = round(_WEIGHTS['policy_coverage'] * coverage_ratio, 1)

    # ── Factor 2: Ringfence Ratio ──────────────────────────────────────────────
    # Flows where src_app == dst_app and both non-empty (intra-app) indicate
    # that applications are scoped — a proxy for ring-fencing maturity.
    has_app = df[(df['src_app'].notna() & df['src_app'].ne('')) &
                 (df['dst_app'].notna() & df['dst_app'].ne(''))]
    if len(has_app) > 0:
        intra_app_count = int((has_app['src_app'] == has_app['dst_app']).sum())
        ringfence_ratio = intra_app_count / len(has_app)
    else:
        ringfence_ratio = 0.0
    f2_score = round(_WEIGHTS['ringfence_ratio'] * ringfence_ratio, 1)

    # ── Factor 3: Enforcement Mode ─────────────────────────────────────────────
    if workloads:
        enforced = sum(1 for w in workloads
                       if w.get('enforcement_mode') in ('full', 'selective'))
        enforce_ratio = enforced / len(workloads) if workloads else 0
    else:
        # Estimate from traffic: managed workloads with only allowed traffic
        managed_ips = set(df[df['src_managed'] == True]['src_ip'].dropna().unique())
        if managed_ips:
            blocked_ips = set(
                df[(df['src_managed'] == True) &
                   (df['policy_decision'].isin(['blocked', 'potentially_blocked']))]
                ['src_ip'].dropna().unique()
            )
            enforce_ratio = (len(managed_ips) - len(blocked_ips)) / len(managed_ips)
        else:
            enforce_ratio = 0.5  # neutral when no data
    f3_score = round(_WEIGHTS['enforcement_mode'] * enforce_ratio, 1)

    # ── Factor 4: No Blocked Flows ─────────────────────────────────────────────
    blocked_count = int(df['policy_decision'].isin(['blocked', 'potentially_blocked']).sum())
    blocked_ratio = blocked_count / total if total else 0
    f4_score = round(_WEIGHTS['no_blocked_flows'] * (1 - blocked_ratio), 1)

    # ── Factor 5: Remote App Coverage ─────────────────────────────────────────
    remote = df[df['port'].isin(_REMOTE_PORTS)]
    if len(remote) > 0:
        remote_allowed = int((remote['policy_decision'] == 'allowed').sum())
        remote_cov = remote_allowed / len(remote)
    else:
        remote_cov = 1.0  # no remote access flows → full score
    f5_score = round(_WEIGHTS['remote_app_coverage'] * remote_cov, 1)

    total_score = round(f1_score + f2_score + f3_score + f4_score + f5_score, 1)

    # ── Factor breakdown table ─────────────────────────────────────────────────
    factor_table = pd.DataFrame([
        {'Factor': 'Policy Coverage', 'Weight': _WEIGHTS['policy_coverage'],
         'Score': f1_score, 'Ratio %': round(coverage_ratio * 100, 1)},
        {'Factor': 'Ringfence Ratio', 'Weight': _WEIGHTS['ringfence_ratio'],
         'Score': f2_score, 'Ratio %': round(ringfence_ratio * 100, 1)},
        {'Factor': 'Enforcement Mode', 'Weight': _WEIGHTS['enforcement_mode'],
         'Score': f3_score, 'Ratio %': round(enforce_ratio * 100, 1)},
        {'Factor': 'No Blocked Flows', 'Weight': _WEIGHTS['no_blocked_flows'],
         'Score': f4_score, 'Ratio %': round((1 - blocked_ratio) * 100, 1)},
        {'Factor': 'Remote App Coverage', 'Weight': _WEIGHTS['remote_app_coverage'],
         'Score': f5_score, 'Ratio %': round(remote_cov * 100, 1)},
    ])

    # ── Remediation recommendations ────────────────────────────────────────────
    recommendations = _build_recommendations(
        df=df,
        coverage_ratio=coverage_ratio,
        ringfence_ratio=ringfence_ratio,
        enforce_ratio=enforce_ratio,
        blocked_ratio=blocked_ratio,
        remote_cov=remote_cov,
        top_n=top_n,
    )

    # ── Grade ──────────────────────────────────────────────────────────────────
    grade = _score_to_grade(total_score)

    return {
        'total_score': total_score,
        'grade': grade,
        'factor_scores': {
            'policy_coverage': f1_score,
            'ringfence_ratio': f2_score,
            'enforcement_mode': f3_score,
            'no_blocked_flows': f4_score,
            'remote_app_coverage': f5_score,
        },
        'factor_table': factor_table,
        'recommendations': recommendations,
    }


def _score_to_grade(score: float) -> str:
    if score >= 90:
        return 'A'
    if score >= 75:
        return 'B'
    if score >= 60:
        return 'C'
    if score >= 45:
        return 'D'
    return 'F'


def _build_recommendations(df, coverage_ratio, ringfence_ratio, enforce_ratio,
                            blocked_ratio, remote_cov, top_n=20) -> pd.DataFrame:
    """Generate prioritised remediation items based on score gaps."""
    items = []

    if coverage_ratio < 0.9:
        gap_flows = df[df['policy_decision'] != 'allowed']
        top_gap = (gap_flows.groupby(['src_app', 'dst_app', 'port'])['num_connections']
                   .sum().nlargest(top_n).reset_index())
        for _, row in top_gap.iterrows():
            items.append({
                'Priority': 'High',
                'Factor': 'Policy Coverage',
                'Issue': f"No policy: {row['src_app'] or '?'} → {row['dst_app'] or '?'} port {int(row['port'])}",
                'Connections': int(row['num_connections']),
                'Action': 'Add allow rule in matching rule-set',
            })

    if ringfence_ratio < 0.5:
        items.append({
            'Priority': 'Medium',
            'Factor': 'Ringfence Ratio',
            'Issue': f"Only {round(ringfence_ratio*100,1)}% of flows are intra-app",
            'Connections': None,
            'Action': 'Review application scope labels; add intra-scope rules',
        })

    if enforce_ratio < 0.8:
        items.append({
            'Priority': 'High',
            'Factor': 'Enforcement Mode',
            'Issue': f"Only {round(enforce_ratio*100,1)}% of workloads estimated in enforced mode",
            'Connections': None,
            'Action': 'Switch remaining workloads from visibility/test to selective/full enforcement',
        })

    if blocked_ratio > 0.05:
        blocked_ports = (df[df['policy_decision'].isin(['blocked', 'potentially_blocked'])]
                         [df['port'] > 0].groupby('port')['num_connections']
                         .sum().nlargest(5).reset_index())
        for _, row in blocked_ports.iterrows():
            items.append({
                'Priority': 'Medium',
                'Factor': 'No Blocked Flows',
                'Issue': f"Port {int(row['port'])} has {int(row['num_connections'])} blocked/PB flows",
                'Connections': int(row['num_connections']),
                'Action': 'Determine if block is intentional; document or add allow rule',
            })

    if remote_cov < 0.9:
        items.append({
            'Priority': 'High',
            'Factor': 'Remote App Coverage',
            'Issue': f"Remote access port coverage only {round(remote_cov*100,1)}%",
            'Connections': None,
            'Action': 'Add explicit allow rules for SSH/RDP/VNC to authorised sources only',
        })

    return pd.DataFrame(items) if items else pd.DataFrame(
        columns=['Priority', 'Factor', 'Issue', 'Connections', 'Action'])
