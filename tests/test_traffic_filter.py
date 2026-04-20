from src.pce_cache.traffic_filter import TrafficFilter, TrafficSampler


def _flow(action="blocked", port=443, proto="tcp", src_ip="10.0.0.1",
          src_workload="web", dst_workload="db"):
    return {
        "action": action, "port": port, "protocol": proto,
        "src_ip": src_ip, "src_workload": src_workload, "dst_workload": dst_workload,
    }


def test_filter_passes_when_action_allowed():
    f = TrafficFilter(actions=["blocked"])
    assert f.passes(_flow(action="blocked")) is True
    assert f.passes(_flow(action="allowed")) is False


def test_filter_honours_port_whitelist():
    f = TrafficFilter(actions=["blocked", "allowed"], ports=[22, 3389])
    assert f.passes(_flow(action="blocked", port=22)) is True
    assert f.passes(_flow(action="blocked", port=443)) is False


def test_filter_excludes_src_ip():
    f = TrafficFilter(actions=["blocked"], exclude_src_ips=["10.0.0.1"])
    assert f.passes(_flow(src_ip="10.0.0.1")) is False
    assert f.passes(_flow(src_ip="10.0.0.2")) is True


def test_sampler_never_drops_blocked():
    s = TrafficSampler(ratio_allowed=10)
    flows = [_flow(action="blocked") for _ in range(100)]
    kept = [f for f in flows if s.keep(f)]
    assert len(kept) == 100


def test_sampler_drops_allowed_at_configured_ratio():
    s = TrafficSampler(ratio_allowed=10)
    flows = [_flow(action="allowed", src_ip=f"10.0.{i}.1", port=i+1) for i in range(100)]
    kept = [f for f in flows if s.keep(f)]
    assert 5 <= len(kept) <= 20
