# MODE A: TRAFFIC FLOW REPORT — illumio_monitor 整合開發計畫

**Version 1.0** | 2026-03-23
**Target:** 將 Traffic Flow 安全分析報表功能整合至現有 `illumio_monitor` 專案（無 DB、單次報表生成）
**參考:** Development_Plan.md v1.3（Mode B 獨立專案版本）

---

## 0. MODE A vs MODE B 比較

| 項目 | Mode A (本計畫) | Mode B (Development_Plan.md) |
|------|-----------------|------------------------------|
| **目標** | 整合至 illumio_monitor，作為新功能 | 獨立專案，完整 Web Dashboard |
| **資料來源** | 雙來源：CSV 匯入 + PCE API（複用現有 `api_client.py`） | 同 |
| **持久化** | 無 DB。報表結果輸出為 Excel/HTML 檔案 | PostgreSQL，支援歷史比對、Finding 追蹤 |
| **UI** | 現有 Flask GUI 新增頁面 + CLI 指令 | React + FastAPI 全新前端 |
| **排程** | 複用 illumio_monitor daemon loop 或 CLI 手動觸發 | APScheduler + CSV 目錄監控 |
| **12 分析模組** | 完全相同的分析邏輯 | 同 |
| **Rules Engine** | 完全相同的雙層 rules（Built-in + Semantic） | 同 |
| **部署** | 同 illumio_monitor（pip install） | Docker + PostgreSQL |

---

## 1. 設計原則（與 Mode B 一致）

### 1.1 Label Value 不可假設

```
✅ 可以確定的：
   - key 'role', 'app', 'env', 'loc' 必然存在
   - 可能有額外自訂 key（如 Net, type, CVE, os, Quarantine）
   - API service 物件有 port, proto, process_name, user_name（有收集時）
   - Illumio Ransomware Protection 定義的 20 個高風險 port（結構維度）

❌ 不可假設的：
   - 任何 label value 有特定語義含義
   - role='db' 代表 database、env='prod' 代表 production 等
```

### 1.2 報表設計

所有分析基於三種維度：

1. **結構維度** — port, protocol, managed/unmanaged, enforcement_mode, policy_decision, bytes, process_name, user_name
2. **Label Key 維度** — 4 個確定 key (app, env, loc, role) 作為 groupby，不對 value 做語義判斷
3. **可配置語義維度** — `semantic_config.yaml` 由管理員自行定義（optional）

---

## 2. 現有 illumio_monitor 架構與複用分析

### 2.1 現有元件清單

| 元件 | 檔案 | 可複用部分 | 需要新增/修改 |
|------|------|-----------|-------------|
| **PCE API Client** | `src/api_client.py` (316L) | ✅ `_request()` HTTP 核心、SSL、retry、auth | 新增：`fetch_traffic_for_report()` 簡化介面 |
| **Streaming Traffic Query** | `api_client.py` `query_traffic()` | ✅ Async query + gzip streaming download | 直接複用，已支援 200K max results |
| **Bandwidth/Volume Calc** | `src/analyzer.py` `calculate_mbps()` / `calculate_volume_mb()` | ✅ 計算邏輯完全一致（delta→total fallback） | 抽取為共用 utility |
| **Reporter** | `src/reporter.py` (427L) | ✅ HTML 模板渲染、Email 發送 | 新增：報表 HTML 模板、Excel export |
| **Config** | `src/config.py` (138L) | ✅ ConfigManager、config.json 結構 | 新增 `report` section 到 config.json |
| **Flask GUI** | `src/gui.py` (1669L) | ✅ Flask app factory、API 路由模式 | 新增 report 相關頁面和 API routes |
| **CLI Menu** | `src/main.py` (288L) | ✅ argparse + interactive menu 模式 | 新增 `--report` 命令列參數和選單項 |
| **i18n** | `src/i18n.py` (1272L) | ✅ 800+ 翻譯項 (EN/ZH_TW) | 新增 report 相關翻譯 |
| **Utils** | `src/utils.py` (291L) | ✅ format_unit、Colors、safe_input | 新增：bytes_parser（CSV 字串解析） |

### 2.2 現有 API Client 流量查詢功能

`api_client.py` 已有完整的 async traffic query 實作：

```python
# 現有功能（可直接複用）：
api_client.query_traffic(query_body)  # POST async query
api_client._poll_query(href)          # 輪詢直到完成
api_client._download_results(href)    # gzip streaming 下載
# 支援: max_results=200000, 429 rate limit retry, 502/503/504 retry
```

### 2.3 現有 Analyzer 計算功能

`analyzer.py` 已有的 bandwidth/volume 計算邏輯與 Mode B 完全一致：

```python
# calculate_mbps(flow):
#   Priority 1: delta bytes (dst_dbo+dst_dbi) / ddms → Mbps (Interval)
#   Priority 2: total bytes (dst_tbo+dst_tbi) / tdms → Mbps (Total)
#   Fallback: tdms < 1000 → use interval_sec * 1000

# calculate_volume_mb(flow):
#   Priority 1: delta bytes (dst_dbo+dst_dbi)
#   Priority 2: total bytes (dst_tbo+dst_tbi or dst_bo+dst_bi)
```

---

## 3. UNIFIED DATAFRAME SCHEMA

（與 Mode B 完全一致，見 Development_Plan.md Section 0.5.2）

```
Core identifiers:
  src_ip, src_hostname, src_managed, src_enforcement, src_os_type
  dst_ip, dst_hostname, dst_managed, dst_enforcement, dst_os_type, dst_fqdn

Labels (4 guaranteed keys):
  src_app, src_env, src_loc, src_role
  dst_app, dst_env, dst_loc, dst_role

Labels (dynamic extra):
  src_extra_labels: dict    # e.g., {'Net':'Server-172.16.15', 'CVE':'CVE-2025-53770'}
  dst_extra_labels: dict

Connection:
  port, proto, process_name, user_name, num_connections, state, policy_decision
  first_detected, last_detected

Bytes & Bandwidth:
  bytes_in, bytes_out, bytes_total, bandwidth_mbps
  raw_dst_dbi, raw_dst_dbo, raw_dst_tbi, raw_dst_tbo, raw_ddms, raw_tdms

Metadata:
  data_source ('csv'|'api'), network, flow_direction, transmission
```

---

## 4. 新增檔案結構

在 `illumio_monitor/` 專案中新增以下檔案（不修改現有核心功能）：

```
illumio_monitor/
├── src/
│   ├── api_client.py          # [修改] 新增 fetch_traffic_for_report() 包裝方法
│   ├── analyzer.py            # [修改] 抽取 calculate_mbps/volume 為 importable utils
│   ├── reporter.py            # [修改] 新增 export_report_html(), export_report_excel()
│   ├── config.py              # [修改] config 新增 report section
│   ├── gui.py                 # [修改] 新增 report 頁面路由
│   ├── main.py                # [修改] 新增 --report 命令 + 選單項
│   ├── i18n.py                # [修改] 新增 report 翻譯 (~100 keys)
│   ├── utils.py               # [修改] 新增 bytes_parser 函數
│   │
│   ├── report/                # [全新] Report 子模組
│   │   ├── __init__.py
│   │   ├── parsers/
│   │   │   ├── __init__.py
│   │   │   ├── csv_parser.py          # CSV → Unified DataFrame
│   │   │   ├── api_parser.py          # API JSON → Unified DataFrame
│   │   │   └── validators.py          # Schema validation
│   │   ├── rules_engine.py            # Built-in + Semantic rules
│   │   ├── analysis/
│   │   │   ├── __init__.py
│   │   │   ├── mod01_traffic_overview.py
│   │   │   ├── mod02_policy_decisions.py
│   │   │   ├── mod03_uncovered_flows.py
│   │   │   ├── mod04_ransomware_exposure.py
│   │   │   ├── mod05_remote_access.py
│   │   │   ├── mod06_user_process.py
│   │   │   ├── mod07_cross_label_matrix.py
│   │   │   ├── mod08_unmanaged_hosts.py
│   │   │   ├── mod09_traffic_distribution.py
│   │   │   ├── mod10_allowed_traffic.py
│   │   │   ├── mod11_bandwidth.py
│   │   │   └── mod12_executive_summary.py
│   │   ├── report_generator.py        # 統一報表生成入口
│   │   └── exporters/
│   │       ├── __init__.py
│   │       ├── excel_exporter.py      # DataFrame → Excel (.xlsx)
│   │       └── html_exporter.py       # DataFrame → HTML report
│   │
│   └── templates/
│       └── report/                    # [全新] Report HTML 模板
│           ├── report_full.html       # 完整報表 HTML
│           └── report_email.html      # Email 摘要版本
│
├── config/                            # [全新] Report 設定檔目錄
│   ├── report_config.yaml             # Report thresholds + ransomware ports
│   ├── csv_column_mapping.yaml        # CSV 欄位對應
│   └── semantic_config.yaml           # OPTIONAL: 語義規則 (空模板)
│
├── reports/                           # [全新] 報表輸出目錄
│   └── .gitkeep
│
└── requirements.txt                   # [修改] 新增 pandas, openpyxl, pyyaml
```

---

## 5. 12 分析模組（分析邏輯與 Mode B 完全一致）

> 以下列出每個模組的核心功能。詳細的 groupby 邏輯、計算公式請參考 Development_Plan.md Section 2。

### Module 1: `traffic_overview(df)` — Traffic Overview

KPI 摘要：total connections, policy coverage %, unique IPs, total bytes, managed %, date range。

### Module 2: `policy_decision_analysis(df)` — Policy Decision Breakdown

按 policy_decision 分組：per decision top app→app flows, top ports, managed/unmanaged 比例。

### Module 3: `uncovered_flows(df)` — Policy Coverage Gaps

分析 `policy_decision != 'allowed'` 的流量。Top 20 uncovered (src_app→dst_app:port)。純結構判斷產出 recommendation（intra-app / unmanaged source / cross-app）。

### Module 4: `ransomware_exposure(df)` — Ransomware Exposure Analysis

基於 Illumio Ransomware Protection 20 個高風險 port。純 port-based 結構分析：
- Part A: Risk summary by level (Critical/High/Medium/Low)
- Part B: Per-port detail (connections, host pairs, policy breakdown)
- Part C: Exposure by policy decision
- Part D: Host exposure ranking (dst 被多少 risk port 暴露)

### Module 5: `host_to_host_protocol_analysis(df)` — Remote Access Protocol Analysis

分析 lateral movement ports (RDP/SSH/VNC/SMB/WinRM) 的 host-to-host 連線。Top talkers, top pairs。

### Module 6: `user_process_analysis(df)` — User & Process Activity

分析有 user_name/process_name 的連線。Top users, top processes, user→destination matrix。無 user data 時顯示 'User data not available'。

### Module 7: `cross_label_flow_matrix(df)` — Cross-Label Flow Analysis

對每個 label key (env/app/role/loc) 產出 value×value flow matrix。Same-value vs cross-value breakdown。這是 "Cross-Env DB Access" 的通用替代品。

### Module 8: `unmanaged_traffic(df)` — Unmanaged Host Analysis

`managed=false` 的流量分析。Top unmanaged src/dst IPs, 被最多 unmanaged 來源連線的 managed hosts。

### Module 9: `traffic_distribution(df)` — Traffic Distribution

多維度分布：per label key, per port/service, role→role flow patterns, enforcement mode 分布。

### Module 10: `allowed_traffic(df)` — Allowed Traffic Analysis

已有 policy rule 的流量。Top allowed app flows, audit flag (allowed + unmanaged)。

### Module 11: `bandwidth_analysis(df)` — Bandwidth & Data Volume

- Volume: top connections by bytes, by app, by env, by port
- Bandwidth: API mode 精確計算 Mbps；CSV mode 用 timestamp 差估算
- Anomaly: bytes-per-connection ratio, bandwidth spike

### Module 12: `executive_summary(all_results)` — Auto-Generated Summary

純數據驅動：KPI cards, auto-derived findings, top action items。無 AI 語義。

---

## 6. DUAL-SOURCE PARSERS

### 6.1 CSV Parser (`src/report/parsers/csv_parser.py`)

```
Input:  CSV 檔案路徑 (PCE UI 匯出)
Output: Unified DataFrame (pandas)

核心邏輯:
1. 讀取 CSV → pandas DataFrame
2. 根據 csv_column_mapping.yaml 對應欄位名稱:
   'Source IP'           → src_ip
   'Source Application'  → src_app
   'Destination Role'    → dst_role
   ...
3. 解析 Bytes 字串: '1.2 MB' → 1258291 (int bytes)
4. 動態偵測非標準 label 欄位 → src_extra_labels / dst_extra_labels
5. Protocol 字串保持 ('TCP', 'UDP')
6. CSV 無時間區間欄位 → bandwidth 使用 first/last_detected 差估算
7. data_source = 'csv'
```

### 6.2 API Parser (`src/report/parsers/api_parser.py`)

```
Input:  API JSON (list of flow records, 來自 api_client.query_traffic())
Output: Unified DataFrame (pandas)

核心邏輯:
1. 接收 api_client 返回的 JSON flow list
2. 展平巢狀結構:
   src.ip → src_ip
   src.workload.hostname → src_hostname
   src.workload.labels → 提取 4 guaranteed keys + extra_labels dict
   service.port → port
   service.proto → proto (int → str mapping: 6→TCP, 17→UDP)
   service.user_name → user_name
   service.process_name → process_name
3. Bytes 計算 (複用 analyzer.py 的邏輯):
   delta bytes (dst_dbi + dst_dbo) 優先 → bytes_total
   fallback: total bytes (dst_tbi + dst_tbo or dst_bi + dst_bo)
4. Bandwidth 計算:
   delta_bytes / ddms → Mbps (Interval)
   fallback: total_bytes / tdms → Mbps (Total)
5. data_source = 'api'
```

### 6.3 Bytes String Parser (新增至 `src/utils.py`)

```python
def parse_bytes_string(s: str) -> int:
    """Parse PCE CSV bytes string to integer bytes.
    Examples: '0.0 KB' → 0, '1.2 MB' → 1258291, '3.5 GB' → 3758096384
    """
    # regex: (number) (unit)
    # units: B, KB, MB, GB, TB
```

---

## 7. DUAL-LAYER RULES ENGINE

### 7.1 Built-in Rules (結構維度，所有環境通用)

（與 Mode B 完全一致，見 Development_Plan.md Section 3.2）

| Rule ID | Rule Name | Detection Logic | Severity |
|---------|-----------|----------------|----------|
| B001 | Ransomware Risk Port (Critical) | port ∈ critical risk ports AND not blocked | CRITICAL |
| B002 | Ransomware Risk Port (High) | port ∈ high risk ports AND not blocked | HIGH |
| B003 | Ransomware Risk Port (Medium) — Uncovered | port ∈ medium risk ports AND potentially_blocked | MEDIUM |
| B004 | Unmanaged Source High Activity | src_managed=false AND connections > threshold | MEDIUM |
| B005 | Low Policy Coverage | policy_coverage_pct < min_coverage_pct | MEDIUM |
| B006 | High Lateral Movement | lateral port AND outbound unique dst > threshold | HIGH |
| B007 | Single User High Destinations | user unique dst > threshold | HIGH |
| B008 | High Bandwidth Anomaly | bytes_total > percentile threshold | MEDIUM |
| B009 | Cross-Env Flow Volume | src_env ≠ dst_env AND connections > threshold | INFO |

### 7.2 Semantic Rules (Optional)

`config/semantic_config.yaml` — 管理員自定義。無此檔案系統仍正常運作。結構同 Mode B。

### 7.3 Rules Engine 在 Mode A 的差異

- Mode B: findings 存入 PostgreSQL `security_findings` table，支援歷史追蹤
- **Mode A: findings 存入記憶體 list，直接寫入報表 Excel/HTML。無歷史追蹤。**

---

## 8. 報表輸出格式

### 8.1 Excel Output (`src/report/exporters/excel_exporter.py`)

```
報表名稱: Illumio_Traffic_Report_{YYYY-MM-DD_HHmm}.xlsx

Sheet 結構:
├── Executive Summary      ← Module 12
├── Traffic Overview        ← Module 1
├── Policy Decisions        ← Module 2
├── Uncovered Flows         ← Module 3
├── Ransomware Exposure     ← Module 4
├── Remote Access           ← Module 5
├── User & Process          ← Module 6 (auto-hide if no data)
├── Cross-Label Matrix      ← Module 7 (per label key sub-tables)
├── Unmanaged Hosts         ← Module 8
├── Traffic Distribution    ← Module 9
├── Allowed Traffic         ← Module 10
├── Bandwidth & Volume      ← Module 11 (auto-hide if no bytes data)
├── Security Findings       ← Rules Engine output (all findings)
└── Raw Data                ← Original DataFrame (optional, configurable)

依賴: openpyxl
格式: 帶表頭樣式、條件格式 (risk level 顏色)、自動欄寬
```

### 8.2 HTML Output (`src/report/exporters/html_exporter.py`)

```
單一 HTML 檔案，可在瀏覽器中開啟。
- 包含內嵌 CSS (不依賴外部資源)
- 12 sections 以 nav 目錄導航
- 表格支援排序 (內嵌 JS)
- Cross-Label Matrix 以簡易 heatmap 顏色呈現
- 可直接附在 email 中發送
```

### 8.3 Email 發送（複用現有 Reporter）

```
複用 reporter.py 的 SMTP 發送功能。
- Subject: Illumio Traffic Flow Report — {date}
- Body: Executive Summary (Module 12) 的 HTML 版本
- Attachment: 完整 Excel 報表
```

---

## 9. 整合點：CLI / GUI / Daemon

### 9.1 CLI 命令列 (`src/main.py` 修改)

```bash
# 新增 --report 參數
python illumio_monitor.py --report --source api                  # API 取得資料 → 產出報表
python illumio_monitor.py --report --source csv --file data.csv  # CSV 匯入 → 產出報表
python illumio_monitor.py --report --source api --email          # 產出報表並 email 發送
python illumio_monitor.py --report --source api --output /path/  # 指定輸出目錄
python illumio_monitor.py --report --source api --format excel   # 只產出 Excel (預設)
python illumio_monitor.py --report --source api --format html    # 只產出 HTML
python illumio_monitor.py --report --source api --format all     # Excel + HTML
```

### 9.2 Interactive Menu (`src/main.py` 修改)

```
現有選單新增一項:

Illumio PCE Monitor
┌──────────────────────────────────────────┐
│  ...existing items 1-11...               │
│  12. 📊 Generate Traffic Report          │  ← 新增
│  0.  Exit                                │
└──────────────────────────────────────────┘

選擇 12 後進入子選單:
┌──────────────────────────────────────────┐
│  Traffic Report Generator                │
│  1. Generate from API (fetch current)    │
│  2. Generate from CSV file               │
│  3. Report Settings                      │
│  0. Back                                 │
└──────────────────────────────────────────┘
```

### 9.3 Flask GUI (`src/gui.py` 修改)

```
新增路由:
GET  /report                         → Report 頁面 (SPA)
POST /api/report/generate            → 觸發報表生成 (API source)
POST /api/report/upload-csv          → 上傳 CSV 並生成報表
GET  /api/report/list                → 列出已生成的報表
GET  /api/report/download/<filename> → 下載報表檔案
GET  /api/report/preview/<filename>  → HTML 報表預覽

前端: 在現有 SPA 中新增 Report tab
- CSV 上傳表單 (drag & drop)
- API 生成按鈕 (帶進度顯示)
- 報表列表 (含下載/預覽連結)
- Report Settings 配置面板
```

### 9.4 Daemon Mode（自動排程報表）

```python
# 在現有 run_daemon_loop() 中加入報表排程:
# config.json 新增:
{
    "report": {
        "enabled": true,
        "schedule": "weekly",          # daily|weekly|monthly
        "day_of_week": "monday",       # weekly 用
        "hour": 8,
        "source": "api",
        "format": ["excel"],
        "email_report": true,
        "output_dir": "reports/",
        "include_raw_data": false
    }
}

# Daemon loop 在每個 cycle 檢查是否到達報表生成時間
# 到達時: 執行 report_generator.generate() → export → email
```

---

## 10. CONFIG 修改

### 10.1 config.json 新增 `report` section

```json
{
    "api": { "...existing..." },
    "alerts": { "...existing..." },
    "email": { "...existing..." },
    "smtp": { "...existing..." },
    "settings": { "...existing..." },
    "rules": [ "...existing..." ],
    "report": {
        "enabled": true,
        "schedule": "weekly",
        "day_of_week": "monday",
        "hour": 8,
        "source": "api",
        "format": ["excel"],
        "email_report": true,
        "output_dir": "reports/",
        "include_raw_data": false,
        "max_top_n": 20,
        "api_query": {
            "start_date": null,
            "end_date": null,
            "max_results": 200000,
            "sources_destinations_query_op": "and"
        }
    }
}
```

### 10.2 report_config.yaml (報表專用設定)

```yaml
# Ransomware risk ports (from Illumio Ransomware Protection standard)
ransomware_risk_ports:
  critical:
    - {ports: [135], proto: tcp, service: RPC, control: hard}
    - {ports: [445], proto: tcp, service: SMB, control: hard}
    - {ports: [3389], proto: [tcp, udp], service: RDP, control: easy}
    - {ports: [5985, 5986], proto: tcp, service: WinRM, control: medium}
  high:
    - {ports: [5938], proto: [tcp, udp], service: TeamViewer, control: easy}
    - {ports: [5900], proto: [tcp, udp], service: VNC, control: easy}
    - {ports: [137, 138, 139], proto: [udp, tcp], service: NetBIOS, control: easy}
  medium:
    - {ports: [22], proto: tcp, service: SSH, control: medium}
    - {ports: [2049], proto: [tcp, udp], service: NFS, control: medium}
    - {ports: [20, 21], proto: [tcp, udp], service: FTP, control: easy}
    - {ports: [5353], proto: udp, service: mDNS, control: easy}
    - {ports: [5355], proto: udp, service: LLMNR, control: easy}
    - {ports: [80], proto: tcp, service: HTTP, control: easy}
    - {ports: [3702], proto: udp, service: WSD, control: easy}
    - {ports: [1900], proto: udp, service: SSDP, control: easy}
    - {ports: [23], proto: tcp, service: Telnet, control: easy}
  low:
    - {ports: [110], proto: [tcp, udp], service: POP3, control: easy}
    - {ports: [1723], proto: [tcp, udp], service: PPTP, control: easy}
    - {ports: [111], proto: tcp, service: SunRPC, control: easy}
    - {ports: [4444], proto: [tcp, udp], service: Metasploit, control: easy}

# Lateral movement ports (for Module 5)
lateral_movement_ports: [3389, 5900, 22, 445, 5985, 5986, 5938, 23]

# Thresholds
thresholds:
  min_policy_coverage_pct: 30
  lateral_movement_outbound_dst: 10
  user_destination_threshold: 20
  unmanaged_connection_threshold: 50
  high_bytes_percentile: 95
  high_bandwidth_percentile: 95
  cross_env_connection_threshold: 100
```

---

## 11. REPORT GENERATION FLOW

```
                    ┌─────────────────┐
                    │  Trigger Point   │
                    │  (CLI/GUI/Cron)  │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │ Data Source?     │
                    └───┬─────────┬───┘
                        │         │
              ┌─────────▼──┐  ┌──▼─────────┐
              │ CSV File    │  │ PCE API     │
              │ (upload)    │  │ (query)     │
              └─────────┬──┘  └──┬─────────┘
                        │         │
              ┌─────────▼──┐  ┌──▼─────────┐
              │ CSVParser   │  │ APIParser   │
              └─────────┬──┘  └──┬─────────┘
                        │         │
                    ┌───▼─────────▼───┐
                    │ Unified DataFrame│
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │ Rules Engine     │
                    │ (Built-in +      │
                    │  Semantic)        │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │ 12 Analysis      │
                    │ Modules          │
                    │ (parallel exec)  │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │ Report Generator │
                    │ • Collect results│
                    │ • Module 12 last │
                    └────────┬────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
     ┌────────▼──┐  ┌───────▼──┐  ┌───────▼──┐
     │ Excel     │  │ HTML      │  │ Email     │
     │ Exporter  │  │ Exporter  │  │ (SMTP)    │
     └───────────┘  └──────────┘  └──────────┘
              │              │              │
     ┌────────▼──────────────▼──┐          │
     │     reports/ 目錄         │          │
     └──────────────────────────┘          │
                                    ┌──────▼──────┐
                                    │ Existing     │
                                    │ Reporter     │
                                    │ (SMTP send)  │
                                    └─────────────┘
```

---

## 12. 核心類別設計

### 12.1 ReportGenerator (`src/report/report_generator.py`)

```python
class ReportGenerator:
    """統一報表生成入口 — Mode A (no DB)"""

    def __init__(self, config_manager, api_client=None):
        self.cm = config_manager
        self.api = api_client
        self.report_config = self._load_report_config()
        self.rules_engine = RulesEngine(self.report_config)

    def generate_from_api(self, query_params=None) -> ReportResult:
        """從 PCE API 取得資料並生成報表"""
        # 1. 使用 api_client.query_traffic() 取得 JSON
        # 2. APIParser 轉為 Unified DataFrame
        # 3. 執行 rules engine + 12 modules
        # 4. 返回 ReportResult

    def generate_from_csv(self, csv_path: str) -> ReportResult:
        """從 CSV 檔案生成報表"""
        # 1. CSVParser 讀取 CSV → Unified DataFrame
        # 2. 執行 rules engine + 12 modules
        # 3. 返回 ReportResult

    def _run_analysis(self, df: pd.DataFrame) -> dict:
        """執行所有分析模組"""
        results = {}
        findings = self.rules_engine.evaluate(df)
        results['findings'] = findings

        # Execute modules 1-11
        results['mod01'] = traffic_overview(df)
        results['mod02'] = policy_decision_analysis(df)
        results['mod03'] = uncovered_flows(df)
        results['mod04'] = ransomware_exposure(df, self.report_config)
        results['mod05'] = host_to_host_protocol_analysis(df, self.report_config)
        results['mod06'] = user_process_analysis(df)
        results['mod07'] = cross_label_flow_matrix(df)
        results['mod08'] = unmanaged_traffic(df)
        results['mod09'] = traffic_distribution(df)
        results['mod10'] = allowed_traffic(df)
        results['mod11'] = bandwidth_analysis(df)

        # Module 12 depends on all others
        results['mod12'] = executive_summary(results)
        return results

    def export(self, result: ReportResult, format='excel', output_dir='reports/'):
        """輸出報表檔案"""
        if format in ('excel', 'all'):
            ExcelExporter(result).export(output_dir)
        if format in ('html', 'all'):
            HtmlExporter(result).export(output_dir)


class ReportResult:
    """報表結果容器 (替代 DB 持久化)"""
    def __init__(self):
        self.generated_at: datetime
        self.data_source: str           # 'csv' or 'api'
        self.record_count: int
        self.date_range: tuple
        self.module_results: dict       # module_id → output dict
        self.findings: list             # security findings
        self.dataframe: pd.DataFrame    # raw data (optional, for Raw Data sheet)
```

### 12.2 RulesEngine (`src/report/rules_engine.py`)

```python
class RulesEngine:
    """雙層規則引擎 (Built-in + Semantic)"""

    def __init__(self, report_config: dict):
        self.builtin_rules = self._load_builtin_rules(report_config)
        self.semantic_rules = self._load_semantic_rules()  # from yaml, optional

    def evaluate(self, df: pd.DataFrame) -> list[Finding]:
        findings = []
        # Layer 1: Built-in rules (always run)
        findings.extend(self._eval_builtin(df))
        # Layer 2: Semantic rules (only if semantic_config.yaml exists)
        findings.extend(self._eval_semantic(df))
        # Sort by severity
        findings.sort(key=lambda f: f.severity_rank)
        return findings

    def _eval_builtin(self, df) -> list[Finding]:
        # B001-B009 evaluation logic
        ...

    def _eval_semantic(self, df) -> list[Finding]:
        # Load semantic_config.yaml if exists, else return []
        ...
```

---

## 13. 依賴新增

### requirements.txt 修改

```
# Existing
flask  # optional

# New for Report feature
pandas>=2.0
openpyxl>=3.1         # Excel export
pyyaml>=6.0           # YAML config files
jinja2>=3.1           # HTML report template (Flask 已有)
```

注意：`pandas` 是 Report 功能的核心依賴。若使用者不需要 Report 功能，可以不安裝。建議在 import 時做 optional check（類似現有 Flask 的處理方式）：

```python
try:
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False
```

---

## 14. i18n 翻譯新增

預計新增 ~100 個翻譯 key，範例：

```python
# Report 相關
"report_menu_title": "Traffic Report Generator",
"report_menu_1": "Generate from API",
"report_menu_2": "Generate from CSV file",
"report_menu_3": "Report Settings",
"report_generating": "Generating traffic analysis report...",
"report_complete": "Report generated: {filename}",
"report_no_data": "No traffic data found for the specified period.",
"report_csv_upload": "Select CSV file to import:",
"report_ransomware_critical": "Critical ransomware risk port detected",
"report_section_overview": "Traffic Overview",
"report_section_policy": "Policy Decision Breakdown",
# ... etc
```

---

## 15. DEVELOPMENT MILESTONES

### Phase 0: Config & Infrastructure — 3 days

| # | Task | Details |
|---|------|---------|
| 0.1 | 建立 `src/report/` 目錄結構 | 子目錄: parsers/, analysis/, exporters/ |
| 0.2 | 建立 `config/` 目錄與 YAML 檔案 | report_config.yaml, csv_column_mapping.yaml, semantic_config.yaml (空模板) |
| 0.3 | 修改 config.json 增加 `report` section | schedule, source, format, output_dir |
| 0.4 | 修改 requirements.txt | 新增 pandas, openpyxl, pyyaml |
| 0.5 | 抽取 `calculate_mbps()`/`calculate_volume()` 為共用函數 | 從 analyzer.py 抽取至 utils.py 或 report/utils.py |

### Phase 1: Dual-Source Parsers — 1 week

| # | Task | Details |
|---|------|---------|
| 1.1 | `csv_parser.py` — CSV → Unified DataFrame | 欄位對應、bytes 字串解析、動態 label 偵測 |
| 1.2 | `api_parser.py` — API JSON → Unified DataFrame | 展平巢狀 JSON、label 提取、bytes/bandwidth 計算 |
| 1.3 | `validators.py` — Schema validation | 確保兩種 parser 產出一致的 DataFrame schema |
| 1.4 | `utils.py` — `parse_bytes_string()` | CSV bytes 字串 ('1.2 MB') → int |
| 1.5 | Unit tests: parser 一致性測試 | CSV 和 API 產出 DataFrame 欄位完全一致 |

### Phase 2: Rules Engine — 4 days

| # | Task | Details |
|---|------|---------|
| 2.1 | `rules_engine.py` — Built-in rules (B001-B009) | 純結構維度，不引用 label value |
| 2.2 | Semantic rules loader | 讀取 semantic_config.yaml (optional) |
| 2.3 | Finding model | severity, category, description, recommendation |
| 2.4 | Unit tests: built-in rules | 不需要 semantic_config 就能通過 |

### Phase 3: Analysis Modules — 2 weeks

| # | Task | Details |
|---|------|---------|
| 3.1 | Module 1-3 | Traffic Overview, Policy Decisions, Uncovered Flows |
| 3.2 | Module 4 | Ransomware Exposure (20 high-risk ports) |
| 3.3 | Module 5-6 | Remote Access Protocol, User & Process Activity |
| 3.4 | Module 7 | Cross-Label Flow Matrix（核心模組） |
| 3.5 | Module 8-10 | Unmanaged Hosts, Traffic Distribution, Allowed Traffic |
| 3.6 | Module 11 | Bandwidth & Volume Analysis |
| 3.7 | Module 12 | Executive Summary (depends on all others) |
| 3.8 | Integration test | CSV + API 資料 → 12 modules 完整執行 |

### Phase 4: Export & Integration — 1 week

| # | Task | Details |
|---|------|---------|
| 4.1 | `excel_exporter.py` | DataFrame → multi-sheet Excel (openpyxl) |
| 4.2 | `html_exporter.py` | Single-file HTML report (Jinja2) |
| 4.3 | `report_generator.py` | 統一入口 class |
| 4.4 | Email 發送整合 | 複用 reporter.py SMTP，附加 Excel 附件 |
| 4.5 | End-to-end test | CSV/API → parse → rules → analysis → export → email |

### Phase 5: UI Integration — 1 week

| # | Task | Details |
|---|------|---------|
| 5.1 | CLI: `--report` 命令列參數 | main.py argparse 新增 |
| 5.2 | CLI: interactive menu item 12 | 報表生成子選單 |
| 5.3 | GUI: report 頁面路由 | Flask routes: generate, upload-csv, list, download |
| 5.4 | GUI: 前端報表頁面 | SPA tab: CSV upload, API generate, report list |
| 5.5 | Daemon: 報表排程 | run_daemon_loop 整合週期性報表生成 |
| 5.6 | i18n: 翻譯新增 | ~100 keys (EN + ZH_TW) |

### Phase 6: Testing & Polish — 3 days

| # | Task | Details |
|---|------|---------|
| 6.1 | 使用真實 CSV 樣本測試完整流程 | TrafficData CSV → Excel report |
| 6.2 | 使用真實 API 環境測試 | PCE API query → Excel report |
| 6.3 | 不同環境樣本測試 | 驗證 label-value-agnostic（不同環境不同 label values） |
| 6.4 | 無 semantic_config 測試 | 確認不設定 semantic rules 系統仍正常運作 |
| 6.5 | 文件撰寫 | Report 功能使用說明、semantic_config 配置指南 |

---

## 16. TIMELINE

| Phase | Duration | Cumulative | Milestone |
|-------|----------|-----------|-----------|
| Phase 0: Config | 3 days | Day 3 | 目錄結構 + YAML configs |
| Phase 1: Parsers | 1 week | Day 10 | CSV + API parser 產出一致 DataFrame |
| Phase 2: Rules | 4 days | Day 14 | Built-in rules 全通過 |
| Phase 3: Modules | 2 weeks | Day 28 | 12 modules 完整執行 |
| Phase 4: Export | 1 week | Day 35 | Excel/HTML export + email |
| Phase 5: UI | 1 week | Day 42 | CLI + GUI + daemon 整合 |
| Phase 6: Test | 3 days | Day 45 | UAT 通過 |

**TOTAL: 約 6-7 weeks**（相比 Mode B 的 10-16 weeks，因為不需要 PostgreSQL、FastAPI、React）

---

## 17. Mode A 特有注意事項

### 17.1 無 DB 的影響

| 功能 | Mode B (有 DB) | Mode A (無 DB) 替代方案 |
|------|---------------|----------------------|
| 歷史比對 | DB 中有歷史 report，可 week-over-week | 只能比對同目錄下的歷史報表檔案（optional） |
| Finding 追蹤 | `security_findings` table | 每次獨立生成，不追蹤狀態變化 |
| Dashboard | React real-time | Flask 報表列表頁面 |
| Data retention | DB retention policy | 檔案系統（手動清理或 config 設定保留天數） |

### 17.2 與現有功能的隔離

Report 功能以 `src/report/` 子模組形式存在，與現有 monitoring 功能完全隔離：

- **不影響**現有 event monitoring、traffic alert、bandwidth alert 功能
- **不影響**現有 config.json 中的 rules（report 使用獨立的 report_config.yaml）
- **複用**現有 api_client（同一個 PCE 連線設定）
- **複用**現有 reporter 的 SMTP 發送
- **複用**現有 i18n 框架

### 17.3 Optional Dependency 模式

```python
# 在 main.py 中:
try:
    import pandas
    HAS_REPORT = True
except ImportError:
    HAS_REPORT = False

# CLI --report 時檢查:
if args.report and not HAS_REPORT:
    print("Report feature requires: pip install pandas openpyxl pyyaml")
    sys.exit(1)

# Interactive menu 中 item 12:
if not HAS_REPORT:
    print("(Report feature not available — install: pip install pandas openpyxl pyyaml)")
```

---

## 18. NEXT STEPS

1. **[環境]** 確認 illumio_monitor 專案可正常執行（pip install 現有依賴）
2. **[環境]** 準備測試資料：至少一份 CSV export + 一組 API 存取憑證
3. **[開發]** Phase 0 開始：建立目錄結構 + YAML config 檔案
4. **[開發]** 優先實作 CSVParser（可用現有 TrafficData CSV 測試）
5. **[開發]** 實作 APIParser（可用 api_client.py 取得的 JSON 測試）
6. **[Review]** 確認 12 個 module 的報表結構是否符合需求
7. **[Optional]** 為常用環境編寫 `semantic_config.yaml` 範本
