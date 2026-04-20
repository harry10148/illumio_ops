# Project Status — illumio_ops

**As of:** 2026-04-20  
**Version:** v3.10.0-polish (Phase 12 Polish complete)  
**Branch:** feature/phase-13-siem-cache (Phase 13 in progress)
**Phase:** 12 phases shipped; Phase 13–15 in progress  
**Code Review Date:** 2026-04-13  
**i18n Overhaul:** 2026-04-18 — see Task.md i18n-P1..P7 (all done)
**CLI Audit Note:** 2026-04-19 — legacy `Rules > Manage` menu command parser fixed: prompt now documents `m`/`d` syntax, `h/?` help now works, invalid formats return actionable guidance, rule edit no longer deletes the original rule before confirmation, and regression tests cover help/delete/modify/error paths.
**CLI Review Note:** 2026-04-19 — broader CLI audit completed. The three follow-up gaps are now fixed: click `report` supports `audit` / `ven-status` / `policy-usage`, legacy `--report-type` is restored for argparse compatibility, `workload list --limit` now rejects non-positive values at parse time, and rule-scheduler management no longer exits on blank Enter. Targeted CLI regression suite: `68 passed`. Additional CLI compatibility matrix verification (legacy flags + click dispatch): `41 passed`.
**GUI IP Allowlist Note:** 2026-04-19 — reviewed the source-IP trust / allowlist path in Web GUI. Root cause for “single IP not effective” was address-format mismatch: exact IPv4 entries such as `192.168.1.1` did not match IPv4-mapped IPv6 remotes such as `::ffff:192.168.1.1`, and loopback variants `127.0.0.1` / `::1` were also treated as different. `src/gui.py` now normalizes addresses/networks before validation and matching. Targeted GUI allowlist verification: `5 passed`.
**Branch Cleanup Note:** 2026-04-20 — all remaining `upgrade/*` branches and worktrees were intentionally removed per operator request. Removed local branches: `upgrade/phase-11-charts-dashboard`, `upgrade/phase-12-polish`, `upgrade/phase-4-web-security`, `upgrade/phase-5-reports-rich`, `upgrade/phase-6-scheduler-aps`. Removed remote branch: `origin/upgrade/phase-11-charts-dashboard`. `git worktree list` now shows only the main worktree.
**Bug Fixes (2026-04-19):**
- `illumio_ops.py`: Added `rule`, `workload`, `config` to `_CLICK_SUBCOMMANDS` — these subcommands were silently falling back to the interactive menu instead of routing to the click CLI.
- `src/utils.py` + `src/settings.py`: Fixed wizard silent-exit bug — `safe_input()` now returns action=`"empty"` (not `"back"`) for empty Enter on int fields; traffic/bandwidth wizard callers distinguish "skip to default" vs "go back" and no longer exit mid-wizard when user presses Enter.

---

## Phase 13–15 — IN PROGRESS (2026-04-20)

New feature: push PCE audit events + traffic flows to SIEM, with a shared local SQLite cache that also serves reports and alerts. Split into three phases for safer rollout.

**Phase 13 T1 Complete (2026-04-20)**: Branch `feature/phase-13-siem-cache` created. Package skeleton scaffolded: `src/pce_cache/`, `src/siem/formatters/`, `src/siem/transports/`. All 465 tests passing, 1 skipped.

**Phase 13 T3 Complete (2026-04-20)**: Token-bucket rate limiter (`src/pce_cache/rate_limiter.py`) with `GlobalRateLimiter`, `get_rate_limiter()` singleton, and `reset_for_tests()`. `ApiClient._request()` gains opt-in `rate_limit=False` parameter; guard reads `pce_cache.rate_limit_per_minute` from config (default 400). 471 passed, 1 skipped.

**Phase 13 T5 Complete (2026-04-20)**: `EventsIngestor` (`src/pce_cache/ingestor_events.py`) — sync pull (≤async_threshold), auto-switch to async when cap hit, duplicate-skip via `IntegrityError` on unique `pce_href`, watermark advance after each batch. `ApiClient` gains `get_events()` wrapper and `get_events_async()` stub. 477 passed, 1 skipped (+3 new tests).

**Phase 13 T6 Complete (2026-04-20)**: `TrafficFilter` + `TrafficSampler` (`src/pce_cache/traffic_filter.py`) — filter passes/rejects flow dicts by actions/ports/protocols/src-IP exclusion, sampler applies deterministic 1:N drop to allowed flows using stable hash(src_ip|dst_ip|port). 482 passed, 1 skipped (+5 new tests).

**Phase 13 T7 Complete (2026-04-20)**: `TrafficIngestor` (`src/pce_cache/ingestor_traffic.py`) — async-only pull via `get_traffic_flows_async`, 200k cap, deduplicates on SHA1 `flow_hash`, filter+sampler applied per flow, watermark advance with 5-min grace window. Also fixed `BigInteger` PK autoincrement on SQLite (changed all id PKs to `Integer` in models.py). `ApiClient` gains `get_traffic_flows_async()` stub. 485 passed, 1 skipped (+3 new tests).

**Phase 13 T9 Complete (2026-04-20)**: `RetentionWorker` (`src/pce_cache/retention.py`) — per-table TTL purge (events/traffic_raw/traffic_agg/dead_letter) with configurable days thresholds (default 90/7/90/30). Each purge runs in its own transaction; `run_once()` returns dict with rowcount per table. 490 passed, 1 skipped (+3 new tests).

**Phase 13 T10 Complete (2026-04-20)**: SIEM formatters (`src/siem/formatters/`) — base ABC, CEF 0.1 (severity map, timestamp→epoch-ms), JSON Lines (orjson), RFC5424 syslog header wrapper. 499 passed, 1 skipped (+9 new tests).

**Phase 13 T11 Complete (2026-04-20)**: SIEM transports (`src/siem/transports/`) — `Transport` ABC, `SyslogUDPTransport` (sendto, MTU warning), `SyslogTCPTransport` (lazy connect, auto-reconnect on broken pipe, thread-safe lock), `SyslogTLSTransport` (ssl.create_default_context, CERT_NONE opt-out, reconnect), `SplunkHECTransport` (requests session, urllib3 Retry 3×, 429/5xx forcelist). 505 passed, 1 skipped (+6 new tests).

**Phase 13 T14 Complete (2026-04-20)**: `illumio-ops siem` CLI group (`src/cli/siem.py`) — 5 subcommands: `test` (synthetic event → destination), `status` (per-dest dispatch count table), `replay` (DLQ → pending requeue), `purge` (delete DLQ entries older than N days), `dlq` (list DLQ entries). Registered in `src/cli/root.py`; `"siem"` added to `_CLICK_SUBCOMMANDS` in `illumio_ops.py`. i18n keys added (EN + ZH). 518 passed, 1 skipped (+4 new tests).

- **Phase 13** — PCE cache (SQLite, 6 tables) + SIEM forwarder (CEF/JSON over UDP/TCP/TLS/HEC) + DLQ. Infrastructure PR. Plan: [docs/superpowers/plans/2026-04-19-phase-13-pce-cache-and-siem.md](docs/superpowers/plans/2026-04-19-phase-13-pce-cache-and-siem.md). Target tag: `v3.11.0-siem-cache`.
- **Phase 14** — `AuditGenerator` + `ReportGenerator` read from cache when range in retention, backfill CLI for out-of-range. Plan: [docs/superpowers/plans/2026-04-19-phase-14-reports-on-cache.md](docs/superpowers/plans/2026-04-19-phase-14-reports-on-cache.md). Target tag: `v3.12.0-reports-cache`.
- **Phase 15** — `Analyzer` + `EventPoller` subscribe to cache via `ingested_at`-cursor; enables 30s monitor tick without breaching PCE 500/min. Plan: [docs/superpowers/plans/2026-04-19-phase-15-alerts-on-cache.md](docs/superpowers/plans/2026-04-19-phase-15-alerts-on-cache.md). Target tag: `v3.13.0-alerts-cache`.
- **Roadmap** — [docs/superpowers/plans/2026-04-19-phase-13-14-15-roadmap.md](docs/superpowers/plans/2026-04-19-phase-13-14-15-roadmap.md) with 15 confirmed design decisions.

Phase 14 and 15 are independent once 13 merges. All three default OFF — no behaviour change until operator enables `pce_cache.enabled` / `siem.enabled` in config.

---

## Phase 12 Complete (v3.10.0-polish)

Polish & advanced. 422 tests passed (baseline 406, +16 new).

- **humanize sweep**: Jinja filters `human_time_ago`/`human_number`/`human_size` registered in `_create_app`. `index.html` header shows rules count, schedule count, config-loaded-ago via filters. `dashboard.js` adds `humanTimeAgo()` helper for schedule last-run (relative time + hover tooltip). audit/ven/policy_usage HTML exporters import `human_number` for summary pill counts.
- **SIEM integration**: `docs/SIEM_Integration.md` with 4 forwarding options (Filebeat, Logstash, rsyslog, Splunk). Ready-to-use sample configs in `deploy/`.
- **GUI rule highlight**: `/api/rules/<idx>/highlight` endpoint returns pygments-highlighted JSON. `pygments.css` generated at startup. `<link>` added to index.html.
- **Persistent scheduler**: `SchedulerSettings.persist=true` switches to `SQLAlchemyJobStore(sqlite:///)`. `SQLAlchemy>=2.0` in requirements.txt. All `add_job()` calls use `replace_existing=True`.
- **Shell completions**: bash/zsh/fish completion scripts in `scripts/completions/`. Entrypoint routes to click when `_ILLUMIO_OPS_COMPLETE` is set.
- **+16 new tests**: humanize coverage (3), SIEM sanity (4), pygments endpoint (4), scheduler persistence (5).

---

## Phase 11 Complete (v3.9.0-dashboard)

Charts, live dashboard, interactive rule editor, cron scheduler. 406 tests passed (baseline 366, +40 new).

- **10 new chart_specs**: mod01/03/04/06/08/09/11/12/13/14 now emit `chart_spec` dicts (all 15 traffic modules now covered).
- **Live plotly dashboard**: `/api/dashboard/chart/<chart_id>` Flask endpoint returns plotly JSON for traffic_timeline, policy_decisions, ven_status, rule_hits. `dashboard.js` auto-refreshes every 60s via `Plotly.react()`.
- **CLI `rule edit`**: `illumio-ops rule edit <id>` — interactive questionary prompts + rich.syntax JSON diff. `--no-preview` skips diff.
- **cron_expr scheduler**: `ReportSchedule.cron_expr: Optional[str]` field; `should_run()` routes to `APScheduler.CronTrigger.from_crontab()` when set; backward-compatible with legacy daily/weekly/monthly.
- **i18n**: 52 new keys (49 chart labels + 3 cron UI) added to en + zh_TW; audit 0 findings.
- **+40 new tests**: chart_spec coverage (20), dashboard endpoint (5), rule edit (5), cron schedule (9), i18n (1 i18n_audit clean).

---

## Phase 10 Complete (v3.8.0-ux)

UX quick wins + report parity. 366 tests passed (baseline 317, +49 new).

- **CSV demoted**: `--format` default is now `html`; CSV is opt-in (`--format csv` or `all`). GUI select preselects html. `gui_fmt_*` i18n keys added.
- **pdf/xlsx parity**: `AuditGenerator`, `VenStatusGenerator`, `PolicyUsageGenerator` now support `pdf`/`xlsx`/`all` dispatch matching `ReportGenerator`. All 4 generators × 5 formats covered by parity tests.
- **Audit chart_specs**: `audit_mod00` (top event types bar), `audit_mod02` (top users by activity bar), `audit_mod03` (top users by policy changes bar).
- **VEN chart_specs**: `ven_status_generator._analyze()` emits `status_chart_spec` (online/offline pie) + `os_chart_spec` (VEN by OS bar).
- **Policy Usage chart_specs**: `pu_mod04` (allow/deny/unused pie), `pu_mod02` (top 10 hit rules bar).
- **CLI `rule list`**: `illumio-ops rule list [--type X] [--enabled-only]` — rich.Table view of monitoring rules.
- **CLI `workload list`**: `illumio-ops workload list [--env X] [--limit N] [--enforcement X] [--managed-only]` — rich.Table with spinner during PCE fetch.
- **rich.progress on async queries**: `_wait_for_async_query` shows elapsed-time spinner in TTY; silent in daemon mode.
- **+49 new tests**: format parity (20), chart_spec coverage (15), rule list (6), workload list (3), format contract (2), plus 3 from other tasks.

---

## Phase 9 Complete (v3.7.0-refactor)

Architecture debt A1/A2/A3/A4/A5 + Q1/Q2/Q3 fully resolved:

- **A5 resolved**: `src/events/shadow.py` evaluated — retained (active GUI endpoint) with full test coverage (17 tests in `test_event_shadow.py`) and clear documentation.
- **Q3 resolved**: Canonical `extract_id()` in `src/href_utils.py`; duplicate copies removed from `analyzer.py` and `rule_scheduler.py`.
- **A4 resolved**: `src/exceptions.py` typed exception hierarchy (IllumioOpsError → APIError/ConfigError/ReportError/AlertError/SchedulerError/EventError); silent fallback sites in `api_client.py`, `analyzer.py`, `gui.py` audited and documented.
- **Q1 resolved**: `Analyzer.run_analysis()` decomposed from 196 lines to ~20-line orchestrator calling `_fetch_traffic()`, `_run_event_analysis()`, `_run_rule_engine()`, `_run_health_check()`, `_dispatch_alerts()`.
- **A3 resolved**: Thread-safety residuals fixed — `_InputState` singleton (`utils.py`), `_I18nState` singleton (`i18n.py`), `deque(maxlen=200)` ring buffer for GUI log history, `_registry` lock in `module_log.py`.
- **A2 + Q2 resolved**: `api_client.py` split from 2569 LOC god-class → 765 LOC facade + 3 domain classes in `src/api/`: `LabelResolver` (labels.py), `AsyncJobManager` (async_jobs.py), `TrafficQueryBuilder` (traffic_query.py). All 50+ public methods preserved via delegation wrappers.
- **A1 resolved**: `src/interfaces.py` with `IApiClient`, `IReporter`, `IEventStore` typing.Protocol definitions; `Analyzer.__init__` type-annotated; mock-free Protocol tests in `test_analyzer_with_mock_api.py`.

New test files: `test_event_shadow.py` (17), `test_analyzer_decomposition.py` (27), `test_analyzer_with_mock_api.py` (4). Total: +48 new tests.

---

## Phase 7 Complete (v3.6.0-loguru, merged)

loguru replaces stdlib logging across 86 src/ files. `src/loguru_config.py` centralises setup (rotating file + TTY-coloured console + optional JSON SIEM sink). `src/utils.py::setup_logger()` signature preserved. stdlib 3rd-party libs intercepted via `_StdLibInterceptHandler`. JSON sink toggled via `config.json logging.json_sink`. +15 new tests; pytest `caplog` bridge added to conftest.py.

---

## Phase 6 Complete (v3.5.2-scheduler, merged)

APScheduler daemon unification. BackgroundScheduler + 3 jobs (monitor/report/rule). RLock on all 5 ApiClient TTLCaches. SIGINT+SIGTERM handlers for graceful shutdown. Resolves A3 + T1.

## Phase 4 Complete (v3.5.0-websec, merged)

Web GUI security: flask-wtf CSRF + flask-limiter rate limit + flask-talisman headers + flask-login + argon2id password. Permissions-Policy restored. 429 JSON errorhandler. Resolves S1/S4/S5/T1.

## Phase 5 Complete (v3.5.1-reports, about to merge)

Reports Excel/PDF/Charts:
- `chart_renderer.py` dual-engine (plotly HTML offline + matplotlib PNG for PDF/Excel)
- `xlsx_exporter.py` multi-sheet + embedded PNG
- `pdf_exporter.py` weasyprint HTML→PDF + CJK CSS
- `code_highlighter.py` pygments JSON/YAML/bash
- 5 analysis modules produce chart_spec (mod02 pie / mod05 bar / mod07 heatmap / mod10 line / mod15 network)
- CLI/GUI format options extended: html/csv/pdf/xlsx/all
- humanize in HTML summaries
- `/api/reports/generate` format allowlist (security hardening)
- Test count: +21 (231 after Wave B integration), 0 regressions, i18n audit 0 findings

---


## Phase 3 Complete (2026-04-18)

Phase 3 — pydantic v2 settings validation — merged into `upgrade/phase-3-settings-pydantic`.

| Task | Status |
|---|---|
| `src/config_models.py` — 12 BaseModel classes | ✅ |
| `ConfigManager.load()` pydantic validation | ✅ |
| `cm.models` typed access attribute | ✅ |
| 70+ `cm.config[...]` call sites preserved (backward-compat tests) | ✅ |
| `src/cli/config.py` — `validate` + `show` subcommands (isolated) | ✅ |
| Test count: baseline 130 → 147 (+17 new, 0 regressions) | ✅ |
| i18n audit: 0 findings | ✅ |
| Code Review D2 (config schema validation) | ✅ **RESOLVED** |

---

## What This Is

**Illumio PCE Ops** — agentless Python 3.8+ monitoring and automation platform for Illumio Core PCE via REST API.  
Entry point: `python illumio_ops.py` -> `src/main.py`

**Execution modes:**
- `python illumio_ops.py` — interactive CLI menu
- `--monitor` — headless daemon (single-threaded event loop)
- `--gui` — Flask web GUI (mandatory login: illumio/illumio)
- `--monitor-gui` — daemon + web GUI combined

---

## Architecture Overview

```
illumio_ops.py              Entry point (argparse -> src/main.py)
src/                        77 Python files, ~19,100 lines
  main.py (870 LOC)         CLI menus, daemon loop, signal handling
  api_client.py (2542 LOC)  PCE REST API (async jobs, native filters, O(1) streaming)
  analyzer.py (1087 LOC)    Traffic/event analysis engine (run_analysis 196-line method)
  reporter.py (1342 LOC)    Multi-channel alert dispatch (SMTP, LINE, Webhook)
  config.py (400 LOC)       ConfigManager (config/config.json, deep merge, defaults)
  settings.py (1938 LOC)    Interactive CLI/GUI settings menus
  gui.py (2662 LOC)         Flask web application (SPA, dashboard, rule mgmt)
  i18n.py (1403 LOC)        i18n engine (en/zh-TW, ~1400+ string keys)
  utils.py (408 LOC)        Colors, safe_input, encoding helpers
  module_log.py (106 LOC)   Per-module ring-buffer logging
  state_store.py (80 LOC)   Persistent JSON state (atomic write + file locking)
  rule_scheduler.py (246)   Auto enable/disable PCE rules (3-layer draft protection)
  rule_scheduler_cli.py (676) Web/CLI interfaces for rule scheduler
  report_scheduler.py (496) Cron-style scheduled report delivery
  events/                   Event processing pipeline
    catalog.py (297)          Vendor-aligned event taxonomy
    matcher.py (84)           Nested field rule matching
    normalizer.py (343)       Event normalization + dedup
    poller.py (110)           PCE event polling with watermark
    shadow.py (87)            Legacy rule matching (candidate for removal)
    stats.py (175)            Event statistics tracking
    throttle.py (148)         Alert throttle with suppression count
  report/                   Report generation subsystem
    report_generator.py (547)   15-module traffic report orchestrator
    audit_generator.py (695)    4-module audit report with DataFrame pipeline
    policy_usage_generator (478) Policy usage hit/miss analysis
    ven_status_generator (240)   VEN inventory report
    rules_engine.py (1058)       Security Findings engine (B/L series rules)
    dashboard_summaries.py (118) GUI dashboard summary builders
    report_metadata.py (75)      Report metadata attachment
    tz_utils.py (60)             Timezone utilities
    analysis/                    Per-module analysis (15 modules)
      mod01_traffic_overview .. mod15_lateral_movement
      attack_posture.py (223)    Attack posture ranking + recommendations
    exporters/                   Output formatters
      html_exporter.py (804)     Traffic report HTML
      audit_html_exporter.py (516) Audit report HTML
      policy_usage_html_exporter.py (337) Policy usage HTML
      ven_html_exporter.py (172) VEN report HTML
      csv_exporter.py (85)       Raw CSV export
      report_css.py (234)        Shared CSS
      report_i18n.py (511)       Report-specific i18n
      table_renderer.py (75)     HTML table builder
  alerts/                   Alert output plugins
    base.py (36)              AlertPlugin ABC
    plugins.py (132)          EMAIL, LINE, WEBHOOK implementations
    metadata.py (103)         Plugin config metadata
    template_utils.py (16)    Alert template helpers
  templates/                Flask HTML templates (2 files)
  static/                   CSS + JS assets
scripts/
  generate_assessment_docx.js (228 LOC)  Node.js branded .docx generator
  audit_i18n_usage.py         i18n key audit script
  generate_alert_mail_samples.py  Alert email sample generator
tests/                      19 test files, pytest suite
config/                     config.json.example, report_config.yaml
docs/                       EN + ZH_TW documentation (10 files)
deploy/                     systemd (Ubuntu/RHEL) + NSSM (Windows) service configs
```

---

## Code Review Summary (2026-04-13)

### Codebase Metrics

| Metric | Value |
|---|---|
| Python source files | 77 |
| Total Python LOC (src/) | ~19,100 |
| Test files | 19 |
| i18n string keys | ~1,400+ |
| Report analysis modules | 15 (mod01-mod15) |
| Security rules (B/L series) | ~19 |
| Documentation files | 10 (EN + ZH_TW) |

### Security Findings

| ID | Severity | Issue | Location |
|---|---|---|---|
| S1 | ✅ **RESOLVED** | argon2id via argon2-cffi; PBKDF2 silent upgrade on login | Phase 4 |
| S2 | **HIGH** | Hardcoded default password fallback ("illumio") | `gui.py:406` |
| S3 | **HIGH** | SMTP password stored plaintext in config.json | `config.py:25`, `alerts/plugins.py:45` |
| S4 | ✅ **RESOLVED** | flask-wtf CSRFProtect; token via X-CSRF-Token header | Phase 4 |
| S5 | ✅ **RESOLVED** | flask-limiter 5/minute on /api/login | Phase 4 |
| S6 | **MEDIUM** | SSL verification disableable via config | `api_client.py:140-144` |
| S7 | ✅ **RESOLVED** | Silent fallback sites audited; `src/exceptions.py` typed hierarchy; intentional fallbacks documented (Phase 9) | `src/exceptions.py` |

### Architecture Issues

| ID | Severity | Issue | Location |
|---|---|---|---|
| A1 | ✅ **RESOLVED** | Protocol interfaces `IApiClient`/`IReporter`/`IEventStore` in `src/interfaces.py`; `Analyzer.__init__` type-annotated (Phase 9) | `src/interfaces.py` |
| A2 | ✅ **RESOLVED** | `api_client.py` split: 765 LOC facade + `src/api/` (LabelResolver, AsyncJobManager, TrafficQueryBuilder) (Phase 9) | `src/api/` |
| A3 | ✅ **RESOLVED** | Daemon loop → APScheduler (Phase 6); thread-safety residuals fixed via singletons + deque (Phase 9) | `src/utils.py`, `src/i18n.py`, `src/gui.py`, `src/module_log.py` |
| A4 | ✅ **RESOLVED** | `src/exceptions.py` typed hierarchy; silent fallback sites audited + documented (Phase 9) | `src/exceptions.py` |
| A5 | ✅ **RESOLVED** | `events/shadow.py` evaluated, retained as active GUI endpoint with full test coverage (Phase 9) | `src/events/shadow.py` |

### Code Quality Issues

| ID | Severity | Issue | Location |
|---|---|---|---|
| Q1 | ✅ **RESOLVED** | `run_analysis()` decomposed to ~20-line orchestrator + 5 private methods (Phase 9) | `analyzer.py` |
| Q2 | ✅ **RESOLVED** | `api_client.py` split 2569→765 LOC facade; 3 domain classes in `src/api/` (Phase 9) | `src/api/` |
| Q3 | ✅ **RESOLVED** | Canonical `extract_id()` in `src/href_utils.py`; duplicate copies removed (Phase 9) | `src/href_utils.py` |
| Q4 | **LOW** | Inconsistent naming (tz_str vs timezone_str vs _tz_str) | Across codebase |
| Q5 | ✅ **FIXED** | Label cache now uses TTLCache(ttl=900) — stale data resolved | `api_client.py` — Phase 2 |

### Test Coverage Assessment

| Area | Coverage | Assessment |
|---|---|---|
| api_client.py | Excellent | 11 tests: native filters, async jobs, retry, caching |
| analyzer.py | Good | 6 tests: flow matching, threshold, cooldown |
| events/* | Excellent | Normalization, rule matching, watermark, throttle |
| gui.py (security) | Excellent | Login, IP allowlist, CSRF, password hashing |
| audit_generator.py | Excellent | DataFrame pipeline, enrichment, metadata |
| attack_posture.py | Good | Ranking, schema validation, determinism |
| i18n.py | Good | Placeholder validation, EN/ZH_TW completeness |
| report modules (mod01-15) | **None** | No unit tests for individual analysis modules |
| alerts/plugins.py | **None** | No tests for EMAIL/LINE/WEBHOOK dispatch |
| rule_scheduler_cli.py | **None** | No tests for scheduler web/CLI interface |
| settings.py | **None** | No tests for interactive configuration |
| HTML/CSV exporters | **None** | No tests for report formatting |
| Overall estimate | ~60-70% | Strong core coverage; significant gaps in report/alert modules |

### Concurrency Issues

| ID | Issue | Location |
|---|---|---|
| T1 | ✅ **RESOLVED** | `_login_attempts` / `_LOGIN_ATTEMPTS` removed; flask-limiter handles it | Phase 4 |
| T2 | Module-level globals (`_current_lang`, `_registry`) not thread-safe | `i18n.py`, `module_log.py` |
| T3 | ✅ **RESOLVED** | Daemon loop blocking — APScheduler ThreadPoolExecutor (Phase 6) | `src/scheduler/` |

### Documentation Status

| Document | Status | Accuracy |
|---|---|---|
| README.md (EN) | Good | Current (v3.1.0) |
| README_zh.md (ZH_TW) | Good | Mirrors EN |
| User_Manual (EN/ZH) | Good | Installation + execution modes |
| Project_Architecture (EN/ZH) | Good | Mermaid diagrams, module guide |
| Security_Rules_Reference (EN/ZH) | Fair | Rule names listed; no threshold tuning docs |
| API_Cookbook (EN/ZH) | Fair | Only 2 scenarios; needs expansion |

### Dependency Status (Phase 0 — 2026-04-18)

**Production** (pinned in `requirements.txt`, bundled into future RPM):

| Package | Phase | Pinned? |
|---|---|---|
| flask | existing | ✓ >=3.0,<4.0 |
| pandas | existing (**mandatory** — 41 files, 338 DataFrame ops) | ✓ >=2.0,<3.0 |
| pyyaml | existing (**mandatory** — report_config.yaml) | ✓ >=6.0,<7.0 |
| rich, questionary, click, humanize | Phase 1 (CLI UX) | ✓ |
| requests, orjson, cachetools | Phase 2 (HTTP + cache) | ✓ **used** |
| pydantic, pydantic-settings | Phase 3 (Settings) | ✓ |
| flask-wtf, flask-limiter, flask-talisman, flask-login, argon2-cffi | Phase 4 (Web security) | ✓ **used** |
| openpyxl, weasyprint, matplotlib, plotly, pygments | Phase 5 (Reports) | ✓ |
| APScheduler | Phase 6 (Scheduler) | ✓ **used** |
| loguru | Phase 7 (Logging) | ✓ **used** |

**Dev-only** (`requirements-dev.txt`, NOT bundled):
pytest, pytest-cov, responses, freezegun, ruff, mypy, build, pyinstaller

**CI gate**: `tests/test_dependency_baseline.py` runs `scripts/verify_deps.py` + enforces pin discipline (3 tests, all passing).

---

## Strengths

1. **Zero-dependency CLI core** — stdlib-only for daemon/CLI; optional deps for GUI/reports
2. **Full i18n coverage** — EN + ZH_TW across CLI, GUI, reports, and alerts (~1400+ keys)
3. **Secure deployment** — systemd hardening (`ProtectSystem=strict`, `NoNewPrivileges=true`)
4. **Comprehensive event pipeline** — catalog, normalization, dedup, throttle, watermark persistence
5. **Strong API client** — async job management, native filter resolution, retry with backoff
6. **Multi-platform deployment** — Linux systemd (Ubuntu/RHEL) + Windows NSSM

## Key Risks

1. ~~Password security (SHA256 → should be bcrypt/argon2)~~ **Resolved Phase 4 — argon2id**
2. No dependency version pinning — production drift risk
3. Single-threaded daemon — blocking risk under load
4. God class pattern in api_client.py (2542 LOC)
5. Report module analysis (mod01-15) has zero test coverage
