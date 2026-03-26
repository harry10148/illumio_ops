# Report Schedule 功能強化實作計劃

## 目標

為 Illumio PCE Monitor 加入排程寄送報表的完整功能：
- **定時自動產生報表**（Traffic / Audit / VEN Status）
- **透過 Email 自動寄送報表**（附件 + HTML 摘要）
- **CLI 與 GUI 皆可管理排程設定**
- **引入 MCP Server 的分析算法**強化報表內容

---

## 現況分析

### 已有基礎
| 元件 | 狀態 | 說明 |
|------|------|------|
| `config.json` → `report` block | ✅ 已有結構，但未實作 | `enabled`, `schedule`, `day_of_week`, `hour` 等欄位存在但沒有執行邏輯 |
| `reporter.py` → `send_report_email()` | ✅ 已有方法 | SMTP 附件寄送功能已存在 |
| `src/report/` 報表引擎 | ✅ 完整 | 3 種報表 × HTML/Excel 輸出 |
| Daemon Loop (`main.py`) | ✅ 有間隔計時器 | 目前只做 analysis+alert，沒有排程報表 |
| GUI 報表頁 (`index.html`) | ✅ 基礎已有 | 有手動產生報表的 UI，缺少排程管理頁 |

### 缺少的部分
1. **Scheduler Engine** — 沒有 cron 式的排程執行器
2. **多個排程設定** — 目前只有一個 `report` block，無法設定多個不同的排程
3. **排程狀態追蹤** — 沒有記錄上次執行時間、執行結果
4. **CLI 排程管理** — 無 wizard/menu 可新增/刪除排程
5. **GUI 排程管理頁** — 無排程清單、新增、啟停的介面

---

## MCP Server 值得借鑑的元素

來自 `/Users/harry/Documents/illumio-mcp-server/src/illumio_mcp/server.py`：

### 1. `to_dataframe()` — 流量資料豐富化
- 將 API flow 物件轉為 pandas DataFrame，自動補齊 `src_app`, `dst_app`, `src_env`, `dst_env`
- **用途**：強化 report 資料前處理，統一欄位命名

### 2. `summarize_traffic(df)` — Email 友好的文字摘要
- 將 DataFrame 聚合成 "From [app] to [app] on port [X]: [count] connections" 的自然語言摘要
- **用途**：產生排程郵件的 Executive Summary 段落

### 3. Infrastructure Scoring 算法
- 以 in-degree / out-degree / betweenness centrality 評分，識別核心基礎設施 (AD, DNS, DB)
- **用途**：加入 `mod_infrastructure.py` 新分析模組，或補充 mod01 的 KPI

### 4. Enforcement Readiness Score (0-100)
- 40% policy coverage + 20% ringfence exists + 20% enforcement mode + 10% no blocked + 10% all apps covered
- **用途**：在排程郵件頂部加入「安全態勢評分」KPI 卡片

### 5. Policy Coverage Analysis
- 分別計算 inbound/outbound 覆蓋率，識別未覆蓋的 service/port
- **用途**：強化 mod02_policy_decisions.py 的分析深度

### 6. `compare-draft-active` 模式 (變更偵測)
- 找出 pending draft 與 active policy 的差異（新增/修改/刪除）
- **用途**：新增 Audit 報表的「政策變更摘要」段落，適合週報

---

## 新增功能設計

### Config 結構擴充

```json
"report_schedules": [
  {
    "id": 1700000000,
    "name": "Weekly Traffic Report",
    "enabled": true,
    "report_type": "traffic",
    "schedule_type": "weekly",
    "day_of_week": "monday",
    "hour": 8,
    "minute": 0,
    "lookback_days": 7,
    "format": ["excel", "html"],
    "email_report": true,
    "email_recipients": [],
    "output_dir": "reports/",
    "last_run": null,
    "last_status": null
  }
]
```

> `email_recipients` 若為空則沿用 `email.recipients`
> `schedule_type`: `daily` | `weekly` | `monthly`
> `report_type`: `traffic` | `audit` | `ven_status`
> `last_run` / `last_status` 寫入 `state.json`（不寫 config.json）

---

## 實作步驟

### Phase 1 — 後端排程引擎（Backend Scheduler）

#### Step 1.1 — 新增 `src/report_scheduler.py`

**功能職責：**
- `ReportScheduler` 類別：持有所有排程設定
- `should_run(schedule, now)` — 判斷此刻是否應執行（含 last_run 防重複）
- `run_schedule(schedule)` — 執行報表產生 + Email 寄送
- `tick()` — 由 daemon loop 每分鐘呼叫一次
- 狀態寫入 `state.json`（`report_schedule_states`）

**關鍵邏輯：**
```python
def should_run(self, sched: dict, now: datetime) -> bool:
    if not sched.get("enabled"):
        return False
    last_run = state.get(sched["id"], {}).get("last_run")
    if last_run:
        # 防止同一窗口重複觸發（1小時緩衝）
        if (now - datetime.fromisoformat(last_run)).total_seconds() < 3600:
            return False
    # 依 schedule_type 判斷
    if sched["schedule_type"] == "daily":
        return now.hour == sched["hour"] and now.minute == sched.get("minute", 0)
    elif sched["schedule_type"] == "weekly":
        return (now.strftime("%A").lower() == sched["day_of_week"]
                and now.hour == sched["hour"]
                and now.minute == sched.get("minute", 0))
    elif sched["schedule_type"] == "monthly":
        return (now.day == sched.get("day_of_month", 1)
                and now.hour == sched["hour"]
                and now.minute == sched.get("minute", 0))
    return False
```

#### Step 1.2 — 修改 `src/main.py` daemon loop

```python
# 在 run_daemon_loop() 中，每次 tick 加入：
scheduler = ReportScheduler(config, reporter)
while not shutdown_event.is_set():
    # 既有邏輯
    analyzer.run_analysis()
    reporter.send_alerts()
    # 新增：每分鐘 tick 報表排程
    scheduler.tick()
    shutdown_event.wait(timeout=60)  # 改為 60 秒基準
```

#### Step 1.3 — 強化 `src/reporter.py` 排程報表郵件

新增 `send_scheduled_report_email(schedule, report_result, attachment_paths)` 方法：
- 郵件主旨：`[Illumio Monitor] {schedule.name} - {date}`
- HTML 內文：
  - 頂部：執行時間、資料來源、資料筆數
  - KPI 卡片：Policy Coverage %、Blocked Flows、Top Risks
  - Executive Summary 段落（借鑑 MCP `summarize_traffic()` 文字格式）
  - 附件說明（Excel/HTML 報表）
- 附件：Excel + HTML（依 format 設定）

#### Step 1.4 — 擴充 `src/config.py`

- `_DEFAULT_CONFIG` 加入 `report_schedules: []`
- 新增 CRUD 方法：
  - `add_report_schedule(sched)` — 產生 id = int(time.time()*1000)
  - `update_report_schedule(id, updates)`
  - `remove_report_schedule(id)`
  - `get_report_schedules()` → list

---

### Phase 2 — CLI 排程管理

#### Step 2.1 — 修改 `src/main.py` 互動式選單

在主選單加入項目（現有 menu item 12-14 後面）：

```
[15] Report Schedules / 報表排程管理
```

#### Step 2.2 — 新增 `src/settings.py` 排程管理 wizard

```python
def manage_report_schedules(config):
    """報表排程管理選單"""
    while True:
        # 顯示現有排程清單（表格）
        # 選項：
        # [A] 新增排程
        # [E] 編輯排程
        # [T] 啟用/停用排程
        # [D] 刪除排程
        # [R] 立即執行排程
        # [B] 返回

def add_report_schedule_wizard(config):
    """互動式新增排程 wizard"""
    # 1. 報表類型（traffic/audit/ven_status）
    # 2. 排程名稱
    # 3. 執行頻率（daily/weekly/monthly）
    # 4. 執行時間（hour/minute，或 day_of_week，或 day_of_month）
    # 5. 回溯天數（lookback_days，預設 7）
    # 6. 輸出格式（excel/html/all）
    # 7. 是否 Email 寄送（y/n）
    # 8. 收件人（可覆蓋預設）
```

---

### Phase 3 — GUI 排程管理頁

#### Step 3.1 — 新增 Flask API endpoints（`src/gui.py`）

```
GET    /api/report-schedules          → 列出所有排程
POST   /api/report-schedules          → 新增排程
PUT    /api/report-schedules/<id>     → 更新排程
DELETE /api/report-schedules/<id>     → 刪除排程
POST   /api/report-schedules/<id>/run → 立即執行
POST   /api/report-schedules/<id>/toggle → 啟用/停用
GET    /api/report-schedules/<id>/history → 執行歷史
```

#### Step 3.2 — GUI 新增 Tab（`src/templates/index.html`）

在現有 Reports Tab 下方加入 **"Report Schedules" sub-section** 或獨立 Tab：

**排程清單卡片（Table）：**
| 名稱 | 報表類型 | 頻率 | 下次執行 | 上次執行 | 狀態 | 操作 |
|------|---------|------|---------|---------|------|------|
| Weekly Traffic | Traffic | Mon 08:00 | 2026-03-30 | 2026-03-23 | ✅ 成功 | [執行][編輯][停用][刪除] |

**新增/編輯 Modal：**
- 報表類型 select
- 排程名稱 input
- 頻率 select（daily/weekly/monthly）
- 時間 picker（hour/minute + day_of_week/day_of_month）
- 回溯天數 number input
- 輸出格式 checkbox group
- Email 寄送 toggle
- 收件人 textarea（每行一個）

---

### Phase 4 — i18n 補充

在 `src/i18n.py` 補充新 key（EN / ZH_TW）：

```python
"report_schedules": ("Report Schedules", "報表排程"),
"add_report_schedule": ("Add Report Schedule", "新增報表排程"),
"edit_report_schedule": ("Edit Report Schedule", "編輯報表排程"),
"schedule_type_daily": ("Daily", "每日"),
"schedule_type_weekly": ("Weekly", "每週"),
"schedule_type_monthly": ("Monthly", "每月"),
"lookback_days": ("Lookback Days", "回溯天數"),
"email_recipients_override": ("Email Recipients (leave empty to use default)", "收件人（留空使用預設）"),
"schedule_last_run": ("Last Run", "上次執行"),
"schedule_next_run": ("Next Run", "下次執行"),
"schedule_run_now": ("Run Now", "立即執行"),
"schedule_toggle_enabled": ("Enable/Disable", "啟用/停用"),
"schedule_status_success": ("Success", "成功"),
"schedule_status_failed": ("Failed", "失敗"),
"schedule_status_running": ("Running", "執行中"),
```

---

## 從 MCP Server 引入的強化模組（可選 Phase 5）

### 新增 `src/report/analysis/mod_readiness.py`

借鑑 MCP `enforcement-readiness` 評分邏輯：

```python
def calculate_readiness_score(traffic_result, audit_result):
    """
    計算安全態勢整備度分數 (0-100)
    - 40% Policy Coverage Rate
    - 20% No blocked flows
    - 20% All apps in selective/full enforcement
    - 10% No lateral movement risk ports
    - 10% No unmanaged workload traffic
    """
```

**用途**：在排程郵件頂部顯示「本週安全評分：78/100」

### 強化 `mod02_policy_decisions.py`

借鑑 MCP `get-policy-coverage-report` 的 inbound/outbound 拆分邏輯：
- 分別計算 inbound 覆蓋率 vs outbound 覆蓋率
- 識別覆蓋率最低的 Top 5 應用程式

### 強化排程郵件 Executive Summary

借鑑 MCP `summarize_traffic()` 文字格式，自動生成：
> "Top traffic: From Production/web to Production/db on port 5432: 12,847 connections"

---

## 執行順序建議

```
Phase 1 (後端核心) → Phase 2 (CLI) → Phase 3 (GUI) → Phase 4 (i18n) → Phase 5 (強化)
```

**最小可行版本 (MVP)**：Phase 1 + Phase 2 即可讓 daemon 模式自動排程寄送報表

---

## 檔案異動清單

| 檔案 | 異動類型 | 說明 |
|------|---------|------|
| `src/report_scheduler.py` | **新增** | 排程引擎核心 |
| `src/config.py` | 修改 | 加入 `report_schedules` 預設值與 CRUD 方法 |
| `src/main.py` | 修改 | daemon loop 加入 scheduler.tick()；選單加入排程管理 |
| `src/settings.py` | 修改 | 加入排程管理 wizard |
| `src/reporter.py` | 修改 | 加入排程報表郵件方法 |
| `src/gui.py` | 修改 | 加入 7 個排程管理 API endpoints |
| `src/templates/index.html` | 修改 | 加入排程管理 UI section |
| `src/i18n.py` | 修改 | 加入 ~15 個新翻譯 key |
| `src/report/analysis/mod_readiness.py` | **新增**（Phase 5） | 安全態勢整備度評分模組 |
| `config.json.example` | 修改 | 補充 `report_schedules` 範例 |

---

## 測試計劃

1. **單元測試** (`tests/test_report_scheduler.py`)：
   - `should_run()` 邊界條件（daily/weekly/monthly）
   - 防重複觸發（1小時緩衝）
   - state.json 讀寫正確

2. **整合測試** (`test_report_schedule.py`)：
   - 使用 DummyApiClient，模擬完整排程執行
   - 驗證 Email 寄送（mock SMTP）
   - 驗證報表檔案產生

3. **GUI 測試**：
   - 手動測試 CRUD endpoints
   - 測試「立即執行」觸發背景任務

---

## 參考資源

| 資源 | 路徑 |
|------|------|
| MCP Server 原始碼 | `/Users/harry/Documents/illumio-mcp-server/src/illumio_mcp/server.py` |
| MCP `to_dataframe()` | server.py line 6841-6908 |
| MCP `summarize_traffic()` | server.py line 6910-6986 |
| MCP enforcement readiness | server.py line 5715-5761 |
| MCP policy coverage | server.py line 6035-6081 |
| 現有報表引擎 | `src/report/report_generator.py` |
| 現有 Email 基礎設施 | `src/reporter.py` → `send_report_email()` |
| 現有排程設定（未實作） | `src/config.py` line 28-44 |
