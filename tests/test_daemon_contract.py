"""Freeze daemon loop behavior before migrating to APScheduler."""
import inspect
import pytest
from unittest.mock import MagicMock, patch


def test_run_daemon_loop_callable():
    from src.main import run_daemon_loop
    assert callable(run_daemon_loop)


def test_daemon_accepts_interval_minutes():
    """run_daemon_loop(interval_minutes: int) — signature stable."""
    from src.main import run_daemon_loop
    sig = inspect.signature(run_daemon_loop)
    assert "interval_minutes" in sig.parameters


def test_run_daemon_loop_registers_sigint_handler(monkeypatch):
    """Regression: C1 signal.signal() must be called for SIGINT (was missing)."""
    import signal
    from src import main as main_mod

    registered = {}
    orig_signal = signal.signal

    def fake_signal(signum, handler):
        registered[signum] = handler
        # Restore the original default to avoid permanently altering signal state
        return orig_signal(signum, signal.SIG_DFL)

    monkeypatch.setattr(signal, "signal", fake_signal)

    # Arrange scheduler to exit immediately after start(); patch at source since
    # run_daemon_loop imports build_scheduler locally via 'from src.scheduler import ...'
    class FakeSched:
        running = False

        def start(self):
            self.running = True
            raise KeyboardInterrupt()

        def shutdown(self, wait=True):
            pass

    import src.scheduler as _sched_mod
    import src.scheduler.jobs as _jobs_mod
    monkeypatch.setattr(_sched_mod, "build_scheduler", lambda *a, **kw: FakeSched())
    monkeypatch.setattr(_jobs_mod, "run_monitor_cycle", lambda cm: None)

    try:
        main_mod.run_daemon_loop(interval_minutes=1)
    except (KeyboardInterrupt, SystemExit):
        pass

    assert signal.SIGINT in registered, "SIGINT handler not registered (C1 regression)"
