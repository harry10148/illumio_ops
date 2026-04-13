# Active Tasks — illumio_ops

**As of:** 2026-04-13  
**Source:** Code Review (full project analysis)

---

## Phase 1: Security Hardening ✅ DONE

- [x] **S1: Replace SHA256 with PBKDF2-HMAC-SHA256 (260k iterations, stdlib)**
  - `src/config.py` — new `hash_password()` / `verify_password()` with `pbkdf2:` prefix
  - Legacy SHA256 hashes upgraded automatically on next successful login
  - No new external dependency

- [x] **S2: Remove hardcoded default password fallback**
  - `src/gui.py` — removed `"illumio"` default; no-hash config now rejects all logins
  - First-run generates a random password stored as `_initial_password` in config

- [x] **S3: SMTP password env var override**
  - `src/alerts/plugins.py` — `ILLUMIO_SMTP_PASSWORD` env var takes precedence over config

- [x] **S4: CSRF token — synchronizer token pattern**
  - `src/gui.py` — cookie removed; token injected into `<meta name="csrf-token">` in `index.html`
  - `src/static/js/utils.js` — `_csrfToken()` now reads from meta tag (no XSS-readable cookie)
  - Login response JSON now includes `csrf_token` for API clients / tests

- [x] **S5: Login rate limiting**
  - `src/gui.py` — 5 attempts per 60 seconds per IP; returns HTTP 429

---

## Phase 2: Architecture Improvements (Priority: MEDIUM)

- [x] **A4 (partial): Fix silent exception swallowing**
  - `src/api_client.py:2293` — async job poll parse failure now logs warning
  - `src/api_client.py:2537` — provision state check failure now logs debug
  - Remaining `except: pass` in analyzer.py are intentional (format fallback chains)

- [ ] **A1: Decompose `run_analysis()` method (196 lines)**
  - File: `src/analyzer.py:436-632`
  - Extract: `_fetch_and_analyze_traffic()`, `_analyze_events()`, `_dispatch_alerts()`

- [ ] **A2: Split `api_client.py` god class (2542 LOC)**
  - Consider extracting: `TrafficQueryBuilder`, `AsyncJobManager`, `LabelResolver`
  - Keep `ApiClient` as facade

- [ ] **A3: Resolve global mutable state**
  - `src/utils.py:21` — `_LAST_INPUT_ACTION`
  - `src/i18n.py:8,14` — `_current_lang`
  - `src/gui.py:184` — `_rs_log_history`
  - Wrap in thread-safe singletons or use `threading.local()`

- [ ] **A4: Standardize error handling**
  - Define exception hierarchy: `IllumioOpsError -> APIError, ConfigError, ReportError, AlertError`
  - Replace silent `except: pass` with logged exceptions
  - Key locations: `api_client.py:2293,2537`, `analyzer.py:823,975`, `gui.py:170,223,1097`

- [ ] **A5: Evaluate `events/shadow.py` for removal**
  - Appears to duplicate `events/matcher.py` logic
  - If deprecated, remove and update imports

---

## Phase 3: Test Coverage Expansion (Priority: MEDIUM)

- [ ] **T1: Add tests for report analysis modules (mod01-mod15)**
  - 15 modules with zero unit test coverage
  - Priority: mod12 (executive summary), mod13 (readiness), mod15 (lateral movement)

- [ ] **T2: Add tests for alert plugin dispatch**
  - File: `src/alerts/plugins.py`
  - Test EMAIL, LINE, WEBHOOK with mock transport

- [ ] **T3: Add tests for HTML/CSV exporters**
  - Files: `src/report/exporters/*.py`
  - Verify output structure, CSS injection safety, table rendering

- [ ] **T4: Add integration test for daemon loop**
  - File: `src/main.py:37-119`
  - Test monitor + report scheduler + rule scheduler interaction

- [ ] **T5: Add negative test cases for API client**
  - Network timeouts, malformed JSON, max-retry exhaustion
  - Partial async job responses, cache corruption

---

## Phase 4: Dependency & Config Hardening (Priority: LOW)

- [x] **D1: Pin dependency versions in requirements.txt**
  - `flask>=3.0,<4.0` (tested on 3.1.3)
  - pandas/pyyaml constraints added as comments (installed via OS packages on RHEL)

- [ ] **D2: Add config schema validation on load**
  - File: `src/config.py:80-92`
  - Validate required fields, types, value ranges at startup
  - Fail fast with clear error messages

- [ ] **D3: Add label cache TTL to api_client**
  - File: `src/api_client.py:118-122`
  - Labels cached without expiry; stale data risk in long-running daemon
  - Add TTL (e.g., 15 minutes) or explicit invalidation

---

## Phase 5: Documentation Updates

- [x] **DOC0: Full documentation refresh (2026-04-13)**
  - All 10 docs + 2 READMEs updated to v3.2.0
  - Default credentials → random first-login password flow
  - Security sections updated: PBKDF2, rate limiting, CSRF synchronizer token, SMTP env var
  - API Cookbook: removed hardcoded "illumio" passwords from code examples
  - Version alignment across all files

- [ ] **DOC1: Expand API_Cookbook with more scenarios**
  - Currently only covers health check, quarantine, traffic queries; add: rule enable/disable, label operations

- [ ] **DOC2: Add Security_Rules_Reference threshold tuning guide**
  - Document B/L series rule thresholds and how to customize via report_config.yaml

- [ ] **DOC3: Document rule scheduler state machine**
  - 3-layer draft protection system not explained anywhere

- [ ] **DOC4: Add individual report module descriptions**
  - 15 traffic analysis modules listed in README but not described

---

## Staged Changes Awaiting Commit

- [ ] Commit `scripts/generate_assessment_docx.js` (new Node.js docx generator)
- [ ] Commit deletion of `CLAUDE.md` (removed from repo root)

---

## Recently Completed (reference)

- [x] Merge `codex/policy-usage-traffic-updates` — policy usage report, attack posture analysis
- [x] Deterministic attack summary text + UI polish
- [x] Traffic query cache invalidation and policy usage port insights
- [x] Vendor-aligned event engine refactor
- [x] i18n rebuild and unification across reports, GUI, alerts
- [x] **Full project code review (2026-04-13)** — 77 source files analyzed
- [x] **Code review fixes (2026-04-13)** — Phase 1 Security (S1–S5) + A4 partial + D1 implemented; 116/116 tests passing
