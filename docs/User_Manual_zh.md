# Illumio PCE Ops — 使用手冊

<!-- BEGIN:doc-map -->
| Document | EN | 中文 |
|---|---|---|
| README | [README.md](../README.md) | [README_zh.md](../README_zh.md) |
| User Manual | [User_Manual.md](./User_Manual.md) | [User_Manual_zh.md](./User_Manual_zh.md) |
| Architecture | [Architecture.md](./Architecture.md) | [Architecture_zh.md](./Architecture_zh.md) |
| Security Rules | [Security_Rules_Reference.md](./Security_Rules_Reference.md) | [Security_Rules_Reference_zh.md](./Security_Rules_Reference_zh.md) |
<!-- END:doc-map -->

---

## 1. 安裝與必要條件

### 1.1 系統需求
- **Python 3.8+**（已測試至 3.12）
- 可透過 HTTPS 連線至 Illumio PCE（預設埠 `8443`）
- **安裝：** `pip install -r requirements.txt` — 約 25 個鎖定套件，涵蓋 Flask + 安全中介層（`flask-wtf`、`flask-limiter`、`flask-talisman`、`flask-login`）、報表 + 圖表（`pandas`、`pyyaml`、`openpyxl`、`reportlab`、`matplotlib`、`plotly`、`pygments`）、HTTP 客戶端（`requests`、`orjson`、`cachetools`）、設定驗證（`pydantic`）、排程 + 快取（`APScheduler`、`SQLAlchemy`）、結構化日誌（`loguru`）、CLI UX（`rich`、`questionary`、`click`、`humanize`）。
- **離線隔離目標：** 使用 `scripts/build_offline_bundle.sh` 產生含所有預建 wheel 的自包含 tarball；完整 bundle 工作流程請見 [§1.2](#12-安裝)。
- **PDF 匯出：** `reportlab` 預設包含（純 Python；不需 WeasyPrint / Pango / Cairo / GTK / GDK-PixBuf）。PDF 內容為靜態英文摘要；HTML 與 XLSX 是完整本地化內容的建議格式。

### 1.2 安裝

#### Red Hat / CentOS（RHEL 8+）

```bash
git clone <repo-url>
cd illumio_ops
cp config/config.json.example config/config.json

# 從 AppStream 安裝選用相依套件（無需 EPEL）
sudo dnf install python3-flask python3-pandas python3-pyyaml
```

#### Red Hat / CentOS — 離線 Bundle（air-gapped 安裝）

當目標主機無法連線網際網路且無法存取 PyPI 或任何套件鏡像時，請使用此方式。Bundle 包含可攜式 CPython 3.12 直譯器及所有預建的 Python wheel — 目標主機上無需 `dnf`、`python3` 或網路連線。

> **注意：** 離線 bundle 不支援 PDF 報表（`--format pdf`）。
> PDF 匯出使用 ReportLab（純 Python），不需要 WeasyPrint、Pango、Cairo、GTK 或 GDK-PixBuf，
> 但 ReportLab wheel 已從 air-gapped bundle 中排除以縮小 bundle 體積。
> 所有其他格式（HTML、XLSX、CSV）均可正常使用。

##### 建置 bundle（在任何可連線網際網路的 Linux 或 WSL 機器上執行）

```bash
git clone <repo-url>
cd illumio_ops
bash scripts/build_offline_bundle.sh
# Output: dist/illumio_ops-<version>-offline-linux-x86_64.tar.gz
```

將 `.tar.gz` 傳輸至 air-gapped RHEL 主機（USB、SCP 至跳板機等）。

##### 首次安裝

```bash
tar xzf illumio_ops-<version>-offline-linux-x86_64.tar.gz
cd illumio_ops-<version>

# Validate the host environment before installing (exits 1 on any FAIL)
bash ./preflight.sh

# Install to /opt/illumio_ops, register systemd unit
sudo ./install.sh

# Fill in PCE API credentials (config.json was created from the example template)
sudo nano /opt/illumio_ops/config/config.json

# Enable and start the service
sudo systemctl enable --now illumio-ops
sudo systemctl status illumio-ops      # should show Active: active (running)
```

##### 升級至新版本

`install.sh` 偵測到現有安裝時**絕不覆寫**：
- `config/config.json` — 您的 PCE API 憑證
- `config/rule_schedules.json` — 您的自訂規則排程

```bash
# 1. Stop the running service
sudo systemctl stop illumio-ops

# 2. Extract the new bundle (alongside the old one is fine)
tar xzf illumio_ops-<new-version>-offline-linux-x86_64.tar.gz
cd illumio_ops-<new-version>

# 3. Run install.sh — config.json and rule_schedules.json are preserved
sudo ./install.sh

# 4. Restart
sudo systemctl start illumio-ops
sudo systemctl status illumio-ops

# 5. Verify the new version
/opt/illumio_ops/python/bin/python3 /opt/illumio_ops/illumio_ops.py --version
```

> **若 `report_config.yaml` 已自訂：** 升級時會以 bundle 內附版本覆寫（可能新增分析參數）。升級前請先備份並在之後重新套用您的修改：
> ```bash
> sudo cp /opt/illumio_ops/config/report_config.yaml \
>         /opt/illumio_ops/config/report_config.yaml.bak
> # then run sudo ./install.sh, then merge your changes back
> ```

##### 驗證離線 bundle 完整性

```bash
# Confirm reportlab is absent (offline bundle) and all other packages imported successfully
/opt/illumio_ops/python/bin/python3 \
    /opt/illumio_ops/scripts/verify_deps.py --offline-bundle
```

#### Windows — 離線 Bundle（air-gapped 安裝）

**必要條件：** NSSM（Non-Sucking Service Manager）— 從 https://nssm.cc/download 下載，
並將 `nssm.exe` 放入系統 PATH 或 bundle 的 `deploy\` 目錄。

> **注意：** 離線 bundle 不支援 PDF 報表（`--format pdf`）。
> PDF 匯出使用 ReportLab（純 Python），不需要 WeasyPrint、Pango、Cairo、GTK 或 GDK-PixBuf，
> 但 ReportLab wheel 已從 air-gapped bundle 中排除以縮小 bundle 體積。
> 所有其他格式（HTML、XLSX、CSV）均可正常使用。

##### 建置 bundle（在任何可連線網際網路的 Linux 或 WSL 機器上執行）

```bash
git clone <repo-url>
cd illumio_ops
bash scripts/build_offline_bundle.sh
# Output: dist/illumio_ops-<version>-offline-windows-x86_64.zip
```

將 `.zip` 傳輸至 air-gapped Windows 主機。

##### 首次安裝（以系統管理員身分執行 PowerShell）

```powershell
# Extract the bundle (built-in Windows 11 / Server 2019+)
Expand-Archive illumio_ops-<version>-offline-windows-x86_64.zip -DestinationPath C:\

# Validate the host environment before installing (exits 1 on any FAIL)
cd C:\illumio_ops-<version>
.\preflight.ps1

# Install to C:\illumio_ops, register IllumioOps Windows service
.\install.ps1

# Fill in PCE API credentials
notepad C:\illumio_ops\config\config.json

# Verify the service is running
Get-Service IllumioOps
```

##### 升級至新版本（以系統管理員身分執行 PowerShell）

`install.ps1` 偵測到現有安裝時**絕不覆寫**
`config\config.json` 或 `config\rule_schedules.json`。

```powershell
# 1. Stop the service
Stop-Service IllumioOps

# 2. Extract new bundle
Expand-Archive illumio_ops-<new-version>-offline-windows-x86_64.zip -DestinationPath C:\

# 3. Run install.ps1 — config preserved automatically
cd C:\illumio_ops-<new-version>
.\install.ps1

# 4. Verify
Get-Service IllumioOps   # should show Running
```

> **若 `report_config.yaml` 已自訂：** 升級前先備份：
> ```powershell
> Copy-Item C:\illumio_ops\config\report_config.yaml `
>           C:\illumio_ops\config\report_config.yaml.bak
> # then run .\install.ps1, then merge changes back
> ```

#### Ubuntu / Debian

現代 Ubuntu（22.04+）與 Debian（12+）實施 **PEP 668** — 直接 `pip install` 會被系統封鎖以保護系統 Python 環境。請使用虛擬環境：

```bash
# Install venv support if not already present
sudo apt install python3-venv

git clone <repo-url>
cd illumio_ops
cp config/config.json.example config/config.json

# Create and activate a virtual environment inside the project directory
python3 -m venv venv
source venv/bin/activate          # bash/zsh
# source venv/bin/activate.fish   # Fish shell

pip install -r requirements.txt
```

> **注意**：每次開啟新終端機視窗後，執行應用程式前需先重新啟動虛擬環境（`source venv/bin/activate`）。

#### macOS / 其他（pip）

```bash
git clone <repo-url>
cd illumio_ops
pip install -r requirements.txt
```

#### 自訂安裝根目錄

`install.sh` 支援 `--install-root` 以部署至非預設路徑：

```bash
sudo ./install.sh --install-root /opt/custom_path
```

systemd 單元檔案會自動更新以參照所選路徑。

#### 升級時保留設定

升級時，`install.sh` 偵測到 `config/config.json` 後會跳過整個 `config/` 樹（原始碼中的備註：*「升級時保留所有 config/ — 絕不覆寫操作者擁有的檔案」*）。僅更新 `*.example` 範本，讓操作者可以 diff 確認新增的設定鍵：

```bash
diff /opt/illumio_ops/config/config.json.example \
     /opt/illumio_ops/config/config.json
```

#### 解除安裝

安裝程式會將 `uninstall.sh` 放置於安裝根目錄中，使移除作業可自給自足。

```bash
# Preserve config/ (default — safe for re-install)
sudo /opt/illumio_ops/uninstall.sh

# Remove everything, including config/ (--purge)
sudo /opt/illumio_ops/uninstall.sh --purge

# When running from a bundle directory, or with a custom install root
sudo ./uninstall.sh --install-root /opt/custom_path
```

兩種方式均會停止並停用 `illumio-ops` systemd 單元、移除服務檔案，並刪除 `illumio_ops` 系統使用者。預設（不含 `--purge`）會保留 `config/` — 之後執行 `sudo rm -rf /opt/illumio_ops` 以完成完全移除。

### 1.3 設定檔（`config.json`）

複製範例設定檔後填入 PCE API 憑證：

```bash
cp config/config.json.example config/config.json
```

| 欄位 | 說明 | 範例 |
|:---|:---|:---|
| `api.url` | PCE 主機名稱含連接埠 | `https://pce.lab.local:8443` |
| `api.org_id` | 組織 ID | `"1"` |
| `api.key` | API Key 使用者名稱 | `"api_1a2b3c4d5e6f"` |
| `api.secret` | API Key 密鑰 | `"your-secret-here"` |
| `api.verify_ssl` | SSL 憑證驗證 | `true` 或 `false` |

> **如何取得 API Key**：在 PCE 網頁主控台點選 **使用者選單 → My API Keys → Add**。選擇適當角色（監控最低需 `read_only`，隔離操作需 `owner`）。

---

## 2. 執行模式

### 2.1 互動式 CLI

```bash
python illumio_ops.py
```

啟動文字選單介面，可管理規則、設定及手動執行檢查。

```text
╭── Illumio PCE Ops
│ API: https://pce.lab.local:8443 | Rules: 16
│ Shortcuts: Enter=default | 0=back | -1=cancel | h/?=help
├────────────────────────────────────────────────────
│  1. Alert Rules
│  2. Report Generation
│  3. Rule Scheduler
│  4. System Settings
│  5. Launch Web GUI
│  6. View System Logs
│  7. Web GUI Security
│  0. Exit
╰────────────────────────────────────────────────────
```

選擇 **1. Alert Rules** 進入子選單：

```text
│ 1. Add Event Rule
│ 2. Add Traffic Rule
│ 3. Add Bandwidth & Volume Rule
│ 4. Manage Rules
│ 5. Load Official Best Practices
│ 6. Send Test Alert
│ 7. Run Analysis & Send Alerts
│ 8. Rule Simulation & Debug Mode
│ 0. Back
```

選擇 **2. Report Generation** 進入子選單：

```text
│ 1. Generate Traffic Flow Report
│ 2. Generate Audit Log Report
│ 3. Generate VEN Status Report
│ 4. Generate Policy Usage Report
│ 5. Report Schedule Management
│ 0. Back
```

選擇 **3. Rule Scheduler** 進入子選單：

```text
│ 1. Schedule Management (Add/Delete)
│ 2. Run Schedule Check Now
│ 3. Scheduler Settings (Enable/Disable Daemon, Interval)
│ 0. Back
```

> **注意**：**4. System Settings**、**5. Launch Web GUI** 與 **6. View System Logs** 為單步驟操作，無子選單。


### 2.2 Web GUI

```bash
python illumio_ops.py --gui
python illumio_ops.py --gui --port 8080    # 自訂連接埠
```

於 `http://127.0.0.1:5001` 開啟瀏覽器儀表板，包含以下分頁：

| 分頁 | 功能 |
|:---|:---|
| **Dashboard** | API 連線狀態、規則摘要、PCE 健康檢查；流量分析器含 Top-10 小工具（依頻寬 / 流量量 / 連線數）；已儲存的儀表板查詢 |
| **Rules** | Event/Traffic/Bandwidth/Volume 規則的完整 CRUD 操作、批次刪除、行內編輯 |
| **Reports** | 產生 Traffic、Audit、VEN Status 及 **Policy Usage** 報表；**批次刪除**支援多選；下載 HTML/CSV 原始資料 ZIP；保留期管理 |
| **Report Schedules** | 建立/編輯/切換週期排程（每日/每週/每月）含 Email 寄送；可手動觸發；查看執行歷史 |
| **Rule Scheduler** | 瀏覽所有 PCE 規則集；啟用/停用個別規則並可設定 TTL；佈建變更 |
| **Workload Search** | 依主機名稱/IP/標籤搜尋；套用隔離標籤（單一或批次） |
| **Settings** | API 憑證、告警通道、時區、語言/主題切換、**PCE 設定檔管理** |
| **Actions** | 執行單次監控、除錯模式、測試告警、載入最佳實務 |

### 2.3 背景 Daemon

```bash
python illumio_ops.py --monitor                 # 預設：每 10 分鐘
python illumio_ops.py --monitor --interval 5     # 每 5 分鐘
```

在背景無人值守運行。可正確處理 `SIGINT`/`SIGTERM` 訊號以進行乾淨關閉。

### 2.4 持續運行模式（Daemon + Web GUI）

```bash
python illumio_ops.py --monitor-gui --interval 10 --port 5001
```

此模式在單一程序中同時執行**背景 Daemon** 與 **Web GUI**。
- Daemon 在背景執行緒中運行。
- Flask Web GUI 在主執行緒中運行。
- **強制安全性**：驗證與 IP 過濾機制嚴格執行。
- **受限操作**：此模式下 `/api/shutdown` 端點被停用，以防止意外終止持續運行的服務。

### 2.5 命令列參考

```bash
python illumio_ops.py [OPTIONS]
```

| 參數 | 預設值 | 說明 |
|:---|:---|:---|
| `--monitor` | — | 以無頭 Daemon 模式執行 |
| `--monitor-gui` | — | 同時執行 Daemon + Web GUI（持續運行模式） |
| `-i` / `--interval N` | `10` | 監控間隔（分鐘） |
| `--gui` | — | 啟動獨立 Web GUI |
| `-p` / `--port N` | `5001` | Web GUI 連接埠 |
| `--report` | — | 從命令列產生報表 |
| `--report-type TYPE` | `traffic` | 報表類型：`traffic`、`audit`、`ven_status`、`policy_usage` |
| `--source api\|csv` | `api` | 報表資料來源 |
| `--file PATH` | — | CSV 檔案路徑（搭配 `--source csv` 使用） |
| `--format html\|csv\|all` | `html` | 報表輸出格式 |
| `--email` | — | 產生報表後透過 Email 寄送 |
| `--output-dir PATH` | `reports/` | 報表輸出目錄 |

**範例：**

```bash
# Generate HTML traffic report for the last 7 days and email it
python illumio_ops.py --report --format html --email

# Generate audit report
python illumio_ops.py --report --report-type audit

# Generate VEN status report
python illumio_ops.py --report --report-type ven_status

# Generate policy usage report from CSV export
python illumio_ops.py --report --report-type policy_usage --source csv --file workloader_export.csv

# Generate report from CSV export and save both HTML + raw CSV
python illumio_ops.py --report --source csv --file traffic_export.csv --format all

# Web GUI on a custom port
python illumio_ops.py --gui --port 8080
```

#### `illumio-ops` click 子命令

此套件同時提供 `illumio-ops` 入口點 CLI，包含以下子命令：

| 子命令 | 說明 | 範例 |
|---|---|---|
| `cache` | 管理本地 PCE 快取：backfill、狀態、保留期 | `illumio-ops cache backfill --source events --since 2026-01-01` |
| `monitor` | 執行單次監控循環（非 Daemon） | `illumio-ops monitor` |
| `gui` | 啟動獨立 Web GUI | `illumio-ops gui --port 8080` |
| `report` | 從 CLI 產生報表 | `illumio-ops report --type traffic --format html` |
| `rule` | 檢視已設定的監控規則 | `illumio-ops rule list --type traffic` |
| `siem` | 管理 SIEM 目的地：測試、清空、狀態 | `illumio-ops siem test splunk-hec` |
| `workload` | 取得並顯示 PCE workloads | `illumio-ops workload list --env prod --limit 100` |
| `config` | 驗證或顯示 `config.json` | `illumio-ops config validate` |
| `status` | 顯示 Daemon / 排程器 / 設定狀態 | `illumio-ops status` |
| `version` | 列印已安裝版本 | `illumio-ops version` |

> **Daemon 模式注意：** 使用 `--monitor-gui` 同時啟動排程器與 Web GUI（持續運行模式，建議用於正式環境）。僅使用 `--monitor` 時為不含 GUI 的無頭排程器。

> **SIEM 操作命令：** `illumio-ops siem test`、`illumio-ops siem flush`、`illumio-ops siem status`。

#### `illumio-ops cache` 子命令

| 命令 | 選項 | 說明 |
|---|---|---|
| `cache backfill` | `--source events\|traffic`、`--since YYYY-MM-DD`、`--until YYYY-MM-DD` | 從 PCE API 將歷史日期範圍的資料回填至本地 SQLite 快取 |
| `cache status` | — | 顯示 events、traffic_raw 及 traffic_agg 表的行數與最後攝入時間戳 |
| `cache retention` | — | 顯示已設定的保留政策（events、raw、aggregated） |

```bash
# Backfill the last 30 days of audit events
illumio-ops cache backfill --source events --since 2026-03-28

# Backfill traffic flows for a specific window
illumio-ops cache backfill --source traffic --since 2026-03-01 --until 2026-03-31

# Check cache health
illumio-ops cache status
```

快取必須在 `config.json` 中啟用（`pce_cache.enabled: true`）後，backfill 命令才能成功執行。

#### `illumio-ops siem` 子命令

| 命令 | 選項 | 說明 |
|---|---|---|
| `siem test <name>` | 目的地名稱引數 | 傳送合成 `siem.test` 事件至指定目的地；成功時回報延遲 |
| `siem status` | — | 顯示各目的地的待傳送 / 已傳送 / 失敗數量及 DLQ 深度 |
| `siem dlq --dest <name>` | `--limit N`（預設 50） | 列出指定目的地的死信佇列項目 |
| `siem replay --dest <name>` | `--limit N`（預設 100） | 將 DLQ 項目重新排入待傳送佇列 |
| `siem purge --dest <name>` | `--older-than N`（預設 30 天） | 刪除超過 N 天的 DLQ 項目 |

```bash
# Test a Splunk HEC destination
illumio-ops siem test splunk-hec

# Check dispatch health
illumio-ops siem status

# Inspect the DLQ
illumio-ops siem dlq --dest splunk-hec --limit 20

# Replay up to 500 entries after fixing the root cause
illumio-ops siem replay --dest splunk-hec --limit 500

# Clean up entries older than 7 days
illumio-ops siem purge --dest splunk-hec --older-than 7
```

#### `illumio-ops rule` 子命令

| 命令 | 選項 | 說明 |
|---|---|---|
| `rule list` | `--type event\|traffic\|bandwidth\|volume\|system\|all`、`--enabled-only` | 列出所有已設定的監控規則，可依類型過濾 |

```bash
# List all rules
illumio-ops rule list

# List only traffic rules
illumio-ops rule list --type traffic

# List only enabled traffic rules
illumio-ops rule list --type traffic --enabled-only
```

#### `illumio-ops workload` 子命令

| 命令 | 選項 | 說明 |
|---|---|---|
| `workload list` | `--env <value>`、`--limit N`（預設 50）、`--enforcement full\|selective\|visibility_only\|idle\|all`、`--managed-only` | 從 PCE 取得並顯示 workloads，可選擇性過濾 |

```bash
# List production workloads
illumio-ops workload list --env prod

# List all VEN-managed workloads in full enforcement
illumio-ops workload list --enforcement full --managed-only --limit 200
```

#### `illumio-ops config` 子命令

| 命令 | 選項 | 說明 |
|---|---|---|
| `config validate` | `--file <path>` | 依 Pydantic schema 驗證 `config.json`；成功時退出代碼 0，失敗時列印錯誤 |
| `config show` | `--section <name>` | 格式化列印目前設定（或指定區段：`api`、`smtp`、`web_gui` 等） |

```bash
# Validate the default config.json
illumio-ops config validate

# Validate a specific file
illumio-ops config validate --file /opt/illumio_ops/config/config.json

# Show only the web_gui section
illumio-ops config show --section web_gui
```

---

## 3. 規則類型與設定

### 3.1 事件規則

監控 PCE 稽核事件（例如 `agent.tampering`、`user.sign_in`）。

| 參數 | 說明 | 範例 |
|:---|:---|:---|
| **Event Type** | PCE 事件識別碼 | `agent.tampering` |
| **Threshold Type** | `immediate`（首次出現即告警）或 `count`（累計） | `count` |
| **Threshold Count** | 觸發告警前需達到的次數 | `5` |
| **Time Window** | 滾動時間窗口（分鐘） | `10` |
| **Cooldown** | 重複告警的最小間隔 | `30` |

**內建事件目錄**（可透過 CLI/GUI 存取）：

| 分類 | 事件 |
|:---|:---|
| Agent Health | `agent_missed_heartbeats`、`agent_offline`、`agent_tampering` |
| Authentication | `login_failed`、`authentication_failed` |
| Policy Changes | `ruleset_create/update`、`rule_create/delete`、`policy_provision` |
| Workloads | `workload_create`、`workload_delete` |

> **登入失敗告警**會在告警內文中包含使用者名稱與來源 IP 位址，以利快速分類處理。

### 3.2 流量規則

透過計算匹配的流量記錄來偵測連線異常。

| 參數 | 說明 |
|:---|:---|
| **Policy Decision** | `Blocked (2)`、`Potentially Blocked (1)`、`Allowed (0)` 或 `All (3)` |
| **Port / Protocol** | 依目的埠（例如 `443`）或 IP 協定號（例如 TCP 為 `6`）過濾 |
| **Source/Dest Label** | 精確標籤匹配，格式為 `key=value`（例如 `role=Web`） |
| **Source/Dest IP** | IP 位址或 CIDR 範圍（例如 `10.0.0.0/24`） |
| **Filter Direction** | `src_and_dst`（預設，雙方皆須匹配）或 `src_or_dst`（任一方匹配） |
| **Excludes** | 排除過濾器：標籤（`ex_src_labels`、`ex_dst_labels`）、IP（`ex_src_ip`、`ex_dst_ip`）或埠 |

**過濾方向選項：**

| 模式 | 行為 |
|:---|:---|
| **Src AND Dst**（預設） | 來源與目的端的標籤/IP 須同時匹配各自的過濾條件 |
| **Src only** | 僅指定來源過濾條件 — 目的端不限 |
| **Dst only** | 僅指定目的端過濾條件 — 來源端不限 |
| **Src OR Dst** | 指定的標籤出現在來源端或目的端任一方即匹配 |

### 3.3 頻寬與流量量規則

偵測資料外洩模式。

| 類型 | 指標 | 單位 | 計算方式 |
|:---|:---|:---|:---|
| **Bandwidth** | 峰值傳輸速率 | 自動調整（bps/Kbps/Mbps/Gbps） | 所有匹配流量的最大值 |
| **Volume** | 累計資料傳輸量 | 自動調整（B/KB/MB/GB） | 所有匹配流量的總和 |

> **混合計算**：系統優先使用「差量間隔」指標。對於無可測量差量的長期連線，會回退使用「生命週期總量」，以防止外洩行為逃脫偵測。

> **自動調整單位**：頻寬與流量量的值會自動格式化為最適當的單位（例如 1500 bps → "1.5 Kbps"、2048 MB → "2.0 GB"）。

---

## 4. Web GUI 安全性

所有 Web GUI 模式均需要驗證，並支援來源 IP 限制。

### 首次登入

預設帳號密碼：**帳號 `illumio`** / **密碼 `illumio`**。

1. 使用預設帳號密碼登入。
2. 登入後**立即至 Settings → Security 頁面修改密碼**。
3. 建議設定 **IP 允許清單**以限制存取來源。

> **密碼重設**：若遺失密碼，請直接編輯 `config/config.json` 中的 `web_gui.password` 為新值（或刪除該欄位以回退至預設值 `illumio`）。該值為明文。

### 4.1 身份驗證

- **密碼儲存**：明文儲存於 `config.json` 的 `web_gui.password`。設計理由：illumio_ops 專為離線隔離的 PCE 管理網路設計，所有其他設定密鑰（PCE API key/secret、LINE/SMTP/webhook token）均已為明文；僅對 GUI 密碼加密無實質防禦效果。首次登入後請務必變更預設值 `illumio`。
- **登入速率限制**：每個 IP 每分鐘最多 5 次嘗試（超過回傳 HTTP 429），由 flask-limiter 管理。
- **CSRF 防護**：flask-wtf CSRFProtect — token 透過 `X-CSRF-Token` 回應標頭及 `<meta>` 標籤傳遞；所有變更請求（POST/PUT/DELETE）均需驗證。
- **安全標頭**：flask-talisman 自動設定 `Content-Security-Policy`、`X-Frame-Options: DENY`、`X-Content-Type-Options: nosniff`、`Referrer-Policy: strict-origin-when-cross-origin`；啟用 TLS 時自動開啟 HSTS。
- **Session 管理**：flask-login session 保護（strong 模式）；安全簽章 Cookie（密鑰自動產生於 `config.json` 中）。
- **設定方式**：透過 **CLI 選單 7. Web GUI Security** 或 Web GUI **Settings** 頁面變更帳密。
- **SMTP 憑證**：可設定 `ILLUMIO_SMTP_PASSWORD` 環境變數，避免在設定檔中儲存密碼

### 4.2 IP 允許清單

限制僅特定管理工作站或子網路可存取。
- **格式**：支援單一 IP（例如 `192.168.1.50`）或 CIDR 區塊（例如 `10.0.0.0/24`）。
- **預設**：若清單為空，則所有 IP 皆可存取（前提是通過身份驗證）。
- **執行方式**：中介軟體於每次請求時檢查 `X-Forwarded-For` 或遠端位址。

---

## 5. 告警通道

三個通道可同時運作。在 `config.json` → `alerts.active` 中啟用：

```json
{
    "alerts": {
        "active": ["mail", "line", "webhook"]
    }
}
```

### 5.1 Email（SMTP）

```json
{
    "email": { "sender": "monitor@company.com", "recipients": ["soc@company.com"] },
    "smtp": { "host": "smtp.company.com", "port": 587, "user": "", "password": "", "enable_auth": true, "enable_tls": true }
}
```

### 5.2 LINE Messaging API

```json
{
    "alerts": {
        "line_channel_access_token": "YOUR_TOKEN",
        "line_target_id": "USER_OR_GROUP_ID"
    }
}
```

### 5.3 Webhook

```json
{
    "alerts": {
        "webhook_url": "https://hooks.slack.com/services/xxx/yyy/zzz"
    }
}
```

傳送標準化 JSON 酬載，包含 `health_alerts`、`event_alerts`、`traffic_alerts` 及 `metric_alerts` 陣列。相容於 Slack、Microsoft Teams 及自訂 SOAR 端點。

---

## 6. 隔離（Workload 隔離）

隔離功能讓您能以嚴重性標籤標記受損的 workloads，這些標籤可用於 Illumio 政策規則中以限制其網路存取。

### 工作流程

1. 透過 Web GUI → **Workload Search** **搜尋**目標 workload（依主機名稱、IP 或標籤）
2. **選擇**一個或多個 workloads，然後選擇隔離等級：`Mild`、`Moderate` 或 `Severe`
3. 系統會在 PCE 中**自動建立** Quarantine 標籤類型（若尚不存在）
4. 系統會將 Quarantine 標籤**附加**至每個 workload 的現有標籤上（保留所有其他標籤）

**單一 vs. 批次套用**：選擇單一 workload 後點選 **Apply Quarantine** 進行個別隔離。勾選多個 workloads 後點選 **Bulk Quarantine** 以平行方式隔離（最多 5 個並行 API 呼叫）。

> **重要**：隔離標籤本身不會阻擋流量。您必須在 PCE 中建立對應的 **Enforcement Boundaries** 或 **Deny Rules**，引用 `Quarantine` 標籤鍵才能實際限制流量。

---

## 7. 多 PCE Profile 管理

系統支援透過 Profile 管理同時監控多個 PCE 實例。

### 7.1 概觀

Profile 儲存 PCE 連線憑證（URL、org ID、API key、secret），可在執行時切換而無需重新啟動應用程式。

### 7.2 設定

透過以下方式管理 Profile：
- **Web GUI**：Settings → PCE Profiles 區段（新增、編輯、刪除、啟用）
- **CLI**：System Settings 選單
- **config.json**：直接編輯 `pce_profiles` 陣列與 `active_pce_id`

```json
{
    "active_pce_id": "production",
    "pce_profiles": [
        {
            "name": "production",
            "url": "https://pce-prod.company.com:8443",
            "org_id": "1",
            "key": "api_xxx",
            "secret": "xxx"
        },
        {
            "name": "lab",
            "url": "https://pce-lab.company.com:8443",
            "org_id": "1",
            "key": "api_yyy",
            "secret": "yyy"
        }
    ]
}
```

### 7.3 Profile 切換

當您啟用一個 Profile 時，系統會：
1. 將該 Profile 的憑證複製至頂層 `api` 區段
2. 以新憑證重新初始化 `ApiClient`
3. 後續所有 API 呼叫使用新的 PCE 連線

> **注意**：所有規則與報表排程適用於目前啟用的 PCE Profile。切換 Profile 不會重設現有規則。

---

## 8. 進階部署

### 8.1 Windows 服務（NSSM）

```powershell
nssm install IllumioOps "C:\Python312\python.exe" "C:\illumio_ops\illumio_ops.py" --monitor --interval 5
nssm set IllumioOps AppDirectory "C:\illumio_ops"
nssm start IllumioOps
```

### 8.2 Linux systemd

> **建議的 Daemon 參數：** 使用 `--monitor-gui` 在單一程序中同時執行排程器與 Web GUI（持續運行模式）。僅使用 `--monitor` 時為不含 GUI 的無頭 Daemon。

#### RHEL / CentOS（系統 Python）

```ini
# /etc/systemd/system/illumio-ops.service
[Unit]
Description=Illumio PCE Ops
After=network.target

[Service]
Type=simple
User=illumio
WorkingDirectory=/opt/illumio_ops
ExecStart=/usr/bin/python3 illumio_ops.py --monitor-gui --interval 5
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

#### Ubuntu / Debian（venv）

先建立 venv，然後將 `ExecStart` 指向 venv 直譯器：

```bash
cd /opt/illumio_ops
python3 -m venv venv
venv/bin/pip install -r requirements.txt
```

```ini
# /etc/systemd/system/illumio-ops.service
[Unit]
Description=Illumio PCE Ops
After=network.target

[Service]
Type=simple
User=illumio
WorkingDirectory=/opt/illumio_ops
ExecStart=/opt/illumio_ops/venv/bin/python illumio_ops.py --monitor-gui --interval 5
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now illumio-ops
```

---

## 9. 流量報表與安全發現

> **背景 — 報表使用的 Illumio 概念：** 本章節的報表使用 Illumio 的四維標籤系統（Role、Application、Environment、Location）對流量記錄進行分組與過濾，並參照各 workload 的執行模式（Idle、Visibility Only、Selective、Full）來說明為何流量顯示為「potentially blocked」而非 blocked。標籤維度與執行模式的定義請參閱 [docs/Architecture.md — 背景 — Illumio Platform](Architecture.md#background--illumio-platform)。

### 9.1 產生報表

報表可從以下三處觸發：

| 位置 | 操作方式 |
|:---|:---|
| Web GUI → Reports 分頁 | 點選 **Traffic Report**、**Audit Summary**、**VEN Status** 或 **Policy Usage** |
| CLI → **2. Report Generation** 子選單項目 1–4 | 選擇報表類型與日期範圍 |
| Daemon 模式 | 透過 CLI **2. Report Generation → 5. Report Schedule Management** 設定 — 報表自動產生並可透過 Email 寄送 |
| 命令列 | `python illumio_ops.py --report --report-type traffic\|audit\|ven_status\|policy_usage` |

報表儲存至 `reports/` 目錄，依格式設定產生 `.html`（格式化報表）及/或 `_raw.zip`（CSV 原始資料）。

**所需相依套件：**
```bash
pip install pandas pyyaml
```

### 從快取讀取報表資料

當 `config.json` 中 `pce_cache.enabled = true` 時，稽核與流量報表會自動從本地 SQLite 快取讀取資料（若請求的日期範圍在保留期限內）。這可降低 PCE API 負載並加速報表產生。

若請求範圍超出保留期限，報表會自動回退至即時 PCE API。

如需匯入超出保留期限的歷史資料，請使用 backfill 命令：

```bash
illumio-ops cache backfill --source events --since YYYY-MM-DD --until YYYY-MM-DD
```

詳見 `docs/PCE_Cache.md`。

### 9.2 報表類型總覽

| 報表類型 | 資料來源 | 模組數 | 說明 |
|:---|:---|:---|:---|
| **Traffic** | PCE 非同步流量查詢或 CSV | 15 模組 + 19 安全發現 | 全面的流量安全分析 |
| **Audit** | PCE events API | 4 模組 | 系統健康、使用者活動、政策變更 |
| **VEN Status** | PCE workloads API | 單一產生器 | VEN 清冊含線上/離線分類 |
| **Policy Usage** | PCE rulesets + 流量查詢，或 Workloader CSV | 4 模組 | 逐規則流量命中分析 |

### 9.3 報表章節（Traffic Report）

流量報表包含 **15 個分析模組**加上安全發現章節：

| 章節 | 說明 |
|:---|:---|
| Executive Summary | KPI 卡片：總流量數、政策覆蓋率 %、重要發現 |
| 1 - Traffic Overview | 總流量數、允許/阻擋/PB 分佈、熱門埠 |
| 2 - Policy Decisions | 逐決策分佈含入站/出站拆分及逐埠覆蓋率 % |
| 3 - Uncovered Flows | 無允許規則的流量；埠缺口排名；未覆蓋服務（應用程式+埠） |
| 4 - Ransomware Exposure | **調查目標**（在關鍵/高風險埠上有 ALLOWED 流量的目的主機）醒目標示；逐埠明細；主機暴露排名 |
| 5 - Remote Access | SSH/RDP/VNC/TeamViewer 流量分析 |
| 6 - User & Process | 流量記錄中出現的使用者帳號與程序 |
| 7 - Cross-Label Matrix | 環境/應用/角色標籤組合間的流量矩陣 |
| 8 - Unmanaged Hosts | 來自/前往非 PCE 管理主機的流量；逐應用與逐埠明細 |
| 9 - Traffic Distribution | 埠與協定分佈 |
| 10 - Allowed Traffic | 熱門允許流量；稽核旗標 |
| 11 - Bandwidth & Volume | 依位元組排名的熱門流量 + 頻寬（自動調整單位）；Max/Avg/P95 統計卡片；異常偵測（多連線流量的 P95） |
| 13 - Enforcement Readiness | 0–100 分含因子分解與修復建議 |
| 14 - Infrastructure Scoring | 節點中心性評分以識別關鍵服務（入度、出度、介數中心性） |
| 15 - Lateral Movement Risk | 橫向移動模式分析與高風險路徑 |
| **Security Findings** | **自動化規則評估 — 詳見第 9.5 節** |

### 9.4 安全發現規則

安全發現章節對每個流量資料集執行 **19 條自動偵測規則**，並依嚴重性（CRITICAL → INFO）與分類群組顯示結果。

**規則系列概觀：**

| 系列 | 規則 | 重點 |
|:---|:---|:---|
| **B 系列** | B001–B009 | 勒索軟體暴露、政策覆蓋缺口、行為異常 |
| **L 系列** | L001–L010 | 橫向移動、憑證竊取、爆炸半徑路徑、資料外洩 |

**快速參考：**

| 規則 | 嚴重性 | 偵測內容 |
|:---|:---|:---|
| B001 | CRITICAL | 勒索軟體常用埠（SMB/RDP/WinRM/RPC）未阻擋 |
| B002 | HIGH | 遠端存取工具（TeamViewer/VNC/NetBIOS）被允許 |
| B003 | MEDIUM | 勒索軟體常用埠處於測試模式 — 未執行阻擋 |
| B004 | MEDIUM | 來自未管理（非 PCE）主機的大量流量 |
| B005 | MEDIUM | 政策覆蓋率低於閾值 |
| B006 | HIGH | 單一來源在橫向移動埠上的扇出行為 |
| B007 | HIGH | 單一使用者觸及異常大量的目的端 |
| B008 | MEDIUM | 高頻寬異常（潛在外洩/備份） |
| B009 | INFO | 跨環境流量量超過閾值 |
| L001 | HIGH | 使用明文協定（Telnet/FTP） |
| L002 | MEDIUM | 網路探索協定未阻擋（LLMNR/NetBIOS/mDNS） |
| L003 | HIGH | 資料庫埠可從過多應用層級存取 |
| L004 | HIGH | 資料庫流量跨越環境邊界 |
| L005 | HIGH | Kerberos/LDAP 可從過多來源應用存取 |
| L006 | HIGH | 高爆炸半徑橫向路徑（BFS 圖分析） |
| L007 | HIGH | 未管理主機存取資料庫/身份/管理埠 |
| L008 | HIGH | 橫向移動埠處於測試模式 — 政策存在但未執行 |
| L009 | HIGH | 資料外洩模式（管理 → 未管理，高位元組數） |
| L010 | CRITICAL | 橫向移動埠跨環境邊界被允許 |

完整規則文件 — 包含觸發條件、攻擊技術背景及調整指南 — 請參閱 **[Security Rules Reference](Security_Rules_Reference.md)**。

### 9.5 稽核報表章節

稽核報表包含 **4 個模組**：

| 模組 | 說明 |
|:---|:---|
| Executive Summary | 依嚴重性與分類的事件數量；熱門事件類型 |
| 1 - System Health Events | `agent.tampering`、離線 agents、心跳失敗 |
| 2 - User Activity | 身份驗證事件、登入失敗、帳號變更 |
| 3 - Policy Changes | Ruleset 與規則的建立/更新/刪除、政策佈建 |

### 9.6 VEN 狀態報表

VEN 狀態報表盤點所有 PCE 管理的 workloads，並分類 VEN 連線狀態：

| 章節 | 說明 |
|:---|:---|
| KPI Summary | VEN 總數、線上數、離線數 |
| Online VENs | agent 狀態為 active **且**最後心跳 ≤ 1 小時前的 VEN |
| Offline VENs | 已暫停/停止的 VEN，或 active 但心跳 > 1 小時前 |
| Lost (last 24 h) | 最後心跳在過去 24 小時內的離線 VEN |
| Lost (24–48 h ago) | 最後心跳在 24–48 小時前的離線 VEN |

每一列包含：主機名稱、IP、標籤、VEN 狀態、距上次心跳的小時數、最後心跳時間戳、政策接收時間戳、VEN 版本。

> **線上偵測**：PCE 的 `agent.status.status = "active"` 僅反映**管理**狀態。VEN 可能在無法連線（無心跳）時仍維持 `"active"`。報表使用 `hours_since_last_heartbeat` — VEN 僅在最後心跳 ≤ 1 小時前時才被視為線上。此行為與 PCE Web Console 一致。

### 9.7 Policy Usage 報表

Policy Usage 報表分析每條 PCE 安全規則的實際使用情況，透過比對實際流量記錄來評估。

| 模組 | 說明 |
|:---|:---|
| Executive Summary | 規則總數、有流量命中的規則數、覆蓋率百分比 |
| Overview | 啟用/停用分佈、active/draft 狀態 |
| Executive Summary（`pu_mod00_executive`） | 規則總數、有流量命中的規則數、覆蓋率百分比 |
| Overview（`pu_mod01_overview`） | 啟用/停用分佈、active/draft 狀態 |
| Hit Detail（`pu_mod02_hit_detail`） | 有匹配流量的規則；每條規則的熱門流量 |
| Unused Detail（`pu_mod03_unused_detail`） | 流量命中為零的規則；清理候選項 |
| Deny Effectiveness（`pu_mod04_deny_effectiveness`） | 確認 deny/override-deny 規則正在積極阻擋不需要的流量 |
| Draft Policy Decision（`pu_mod05_draft_pd`） | 逐規則 draft policy decision 風險 — 可見性風險、draft 衝突及三種角度的 draft 覆蓋缺口 |

**資料來源：**
- **API 模式**：從 PCE 取得活躍 rulesets，然後對每條規則執行平行非同步流量查詢以計算匹配流量數
- **CSV 模式**：匯入含預先計算流量數的 Workloader CSV 匯出檔（供離線分析使用）

### 9.8 調整安全規則

所有偵測閾值位於 `config/report_config.yaml`：

```yaml
thresholds:
  min_policy_coverage_pct: 30         # B005
  lateral_movement_outbound_dst: 10   # B006
  db_unique_src_app_threshold: 5      # L003
  blast_radius_threshold: 5           # L006
  exfil_bytes_threshold_mb: 100       # L009
  cross_env_lateral_threshold: 5      # L010
  # ... (see Security_Rules_Reference.md for complete list)
```

編輯此檔案後重新產生報表即可套用新閾值 — 無需重新啟動。

### 9.9 報表排程

透過 CLI **2. Report Generation → 5. Report Schedule Management** 或 Web GUI **Report Schedules** 分頁設定自動週期報表：

| 欄位 | 說明 |
|:---|:---|
| Report Type | Traffic Flow / Audit / VEN Status / **Policy Usage** |
| Frequency | Daily / Weekly（星期幾） / Monthly（每月幾號） |
| Time | 小時與分鐘 — 以您**設定的時區**輸入（自動以 UTC 儲存） |
| Lookback Days | 包含多少天的流量資料 |
| Output Format | HTML / CSV Raw ZIP / Both |
| Send by Email | 使用 SMTP 設定將報表附加至 Email 寄送 |
| Custom Recipients | 覆寫此排程的預設收件者 |

> **時區注意**：CLI 與 Web GUI 中的時間欄位始終以 Settings → Timezone 設定的時區顯示。底層以 UTC 儲存，因此即使變更時區設定，排程仍會正確執行。

Daemon 迴圈每 60 秒檢查排程，並執行任何已到達設定時間的排程。

每次成功執行後，舊報表檔案會根據**保留政策**自動清理 — 詳見第 11.3 節。

### 9.10 R3 智能模組

這些模組作為 Traffic Report 管線的一部分自動執行，並在 HTML 輸出中以專屬章節呈現。

| 模組 | 用途 | 輸入 | 輸出 | 相關設定 |
|---|---|---|---|---|
| `mod_change_impact` | 比較目前報表 KPI 與前次快照；針對每個 KPI 輸出 `improved` / `regressed` / `neutral` 判斷 | 目前 KPI 字典 + 前次 JSON 快照 | Delta 表格 + 整體判斷 + 前次快照時間戳 | `report.snapshot_retention_days` |
| `mod_draft_actions` | 針對需要人工審查的 draft policy decision 子類別提供可行的修復建議：Override Deny、Allowed Across Boundary、what-if | 含 `draft_policy_decision` 欄位的 Flows DataFrame | `override_deny` 區塊、`allowed_across_boundary` 區塊、`what_if_summary` | `report.draft_actions_enabled` |
| `mod_draft_summary` | 計算所有 7 種 draft policy decision 子類型並列出每種子類型的熱門 workload 配對 | 含 `draft_policy_decision` 欄位的 Flows DataFrame | `counts` 字典（7 個子類型）+ 每種子類型的 `top_pairs` | — |
| `mod_enforcement_rollout` | 依就緒分數排列應用程式，評估移至完整 enforcement 的優先順序 | 含 app 標籤（`src_app` / `dst_app`）的 Flows DataFrame + 選用 draft / readiness 摘要 | 含分數、`why_now` 理由、必要允許規則、風險降低的優先化應用清單 | — |
| `mod_exfiltration_intel` | 標記具有高位元組流量的受管至未管理流量；選用性地與已知惡意 IP 的 CSV 進行威脅情報比對 | 含 `src_managed` / `dst_managed` + 選用 `bytes` 欄位的 Flows DataFrame | `high_volume_exfil` 清單、`managed_to_unmanaged_count`、`threat_intel_matches` | `report.threat_intel_csv_path` |
| `mod_ringfence` | 每個應用程式的依賴 Profile + 微分段的候選允許規則；無特定目標應用時顯示熱門應用摘要 | 含 `src_app` / `dst_app` 標籤的 Flows DataFrame | 每個應用：應用內流量、跨應用流量、跨環境流量、候選允許規則；或熱門 20 個應用清單 | — |

**威脅情報 CSV 格式（`mod_exfiltration_intel`）：**

選用的 `report.threat_intel_csv_path` 檔案必須包含至少一個名為 `ip` 的欄位（已知惡意 IP 位址）。任何額外欄位（例如 `threat_category`、`confidence`、`source`）均會保留並顯示於威脅比對輸出中：

```csv
ip,threat_category,confidence,source
185.220.101.1,tor_exit_node,high,abuse.ch
203.0.113.45,c2_server,critical,custom_intel
```

在 `config.json` 中設定路徑：

```json
{
    "report": {
        "threat_intel_csv_path": "/opt/illumio_ops/data/threat_intel.csv"
    }
}
```

若未設定路徑或檔案不存在，`mod_exfiltration_intel` 仍會執行 — 它會回報高流量的受管→未管理流量，但回傳空的 `threat_intel_matches` 清單。

**應用程式 Ringfence 使用方式（`mod_ringfence`）：**

在撰寫微分段規則前，使用此模組隔離單一應用程式的依賴 Profile：

1. 執行 Traffic Report（模組預設產生熱門 20 個應用摘要）。
2. 從熱門應用清單中識別目標應用程式。
3. 重新執行聚焦於單一應用的報表 — 模組會回傳應用內流量、跨應用流量、跨環境流量及候選允許規則清單。
4. 使用候選允許規則清單作為在 PCE 中建立標籤式規則的基礎。

若流量資料集中不存在 `src_app` 或 `dst_app` 標籤，模組會靜默跳過。

### 9.11 Draft Policy Decision 行為

**`compute_draft` 自動啟用：** 當 ruleset 包含使用 `requires_draft_pd` 邏輯的規則時（即 ruleset 有待定的 draft 變更），報表管線會自動為該 ruleset 的流量啟用 draft policy decision 計算。

**HTML 報表標頭標籤：** 當 draft 計算啟用時，Traffic Report HTML 標頭會顯示「Draft Policy Active」指示標籤，讓 draft 範圍一目了然。

**`draft_breakdown` 交叉表（來自 `mod_draft_summary`）：** 顯示每種 draft policy decision 子類型流量數量的 7 欄交叉表：

| 子類型 | 意義 |
|---|---|
| `allowed` | 流量在 draft ruleset 下會被允許 |
| `potentially_blocked` | 流量無匹配的 draft 規則；預設 deny 會阻擋它 |
| `blocked_by_boundary` | 在 draft 中被 boundary 規則阻擋 |
| `blocked_by_override_deny` | 在 draft 中被 Override Deny 規則阻擋 |
| `potentially_blocked_by_boundary` | 在 visibility workload 上；draft boundary 在 enforcement 時會阻擋 |
| `potentially_blocked_by_override_deny` | 在 visibility workload 上；draft override deny 在 enforcement 時會阻擋 |
| `allowed_across_boundary` | 儘管跨越應用邊界仍被允許 — 需要審查 |

**`draft_enforcement_gap`（來自 `mod_draft_summary` / `mod_draft_actions`）：** `policy_decision = potentially_blocked` 但 draft 解析為 `allowed` 或 `blocked_by_boundary` 的流量集合 — 即目前無規則但在 draft 佈建後將被覆蓋（或明確阻擋）的流量。此缺口量化了下次 Provision 時將生效的執行落差。

### 9.12 變更影響工作流程

`mod_change_impact` 模組比較目前報表的 KPI 與最近保存的快照。這讓跨報表執行的趨勢追蹤無需手動比對。

**快照運作方式：**

1. 每次產生 Traffic Report 時，引擎會保存一個包含報表 KPI 值與 `generated_at` 時間戳的快照 JSON。
2. 下次報表執行時，`mod_change_impact` 載入前次快照並計算各 KPI 的差值。
3. 超過 `report.snapshot_retention_days`（預設 90）的快照會自動刪除。

**KPI 方向語意：**

| KPI | 方向 | 較佳時 |
|---|---|---|
| `pb_uncovered_exposure` | 越低越好 | 降低 = 未覆蓋流量減少 |
| `high_risk_lateral_paths` | 越低越好 | 降低 = 橫向移動風險降低 |
| `blocked_flows` | 越低越好 | 降低 = 阻擋/丟棄流量減少 |
| `active_allow_coverage` | 越高越好 | 提升 = 更多流量有明確的允許規則 |
| `microsegmentation_maturity` | 越高越好 | 提升 = 更接近完整 enforcement |

**判斷邏輯：**

| 判斷 | 條件 |
|---|---|
| `improved` | 改善的 KPI 數量多於退步的 |
| `regressed` | 退步的 KPI 數量多於改善的 |
| `neutral` | 改善與退步的 KPI 數量相等 |

若無前次快照（首次報表執行），模組回傳 `skipped: true` 並附 `reason: no_previous_snapshot`。

**操作使用：** 以固定排程執行報表（例如每週），並監控 `overall_verdict` 趨勢。政策變更後持續出現 `regressed` 判斷表示該變更引入了新的覆蓋缺口或啟用了不需要的流量模式，應進行調查。

### 9.13 執行推進規劃

`mod_enforcement_rollout` 模組依就緒分數排列流量資料集中所有應用程式，評估在 PCE 中移至完整 enforcement 模式的準備程度。

**評分公式：**

```
score = (allowed_flows / total_flows) - (potentially_blocked_flows / total_flows)
```

高分表示大多數流量已有允許規則覆蓋（高分子）且較少流量會因啟用預設 deny 而中斷（低分母）。分數接近 1.0 表示應用程式已準備好以最小的操作風險進行 enforcement。

**每個應用程式的輸出：**

| 欄位 | 說明 |
|---|---|
| `app` | 應用程式標籤值 |
| `priority` | 排名順序（1 = 最就緒） |
| `why_now` | 此排名的人類可讀理由 |
| `expected_default_deny_impact` | 將被丟棄的 `potentially_blocked` 流量數量 |
| `required_allow_rules` | enforcement 前需要允許規則的推斷埠/來源配對清單 |
| `risk_reduction` | enforcement 後預估的橫向移動暴露降低量 |

使用優先順序清單建立 enforcement 路線圖：從優先順序 1 的應用程式開始（已完整覆蓋），逐步處理需要額外允許規則的低優先順序應用程式。

---

## 10. 規則排程器

規則排程器根據時間窗口自動啟用或停用 PCE 安全規則（Rule 或 Ruleset）。適用場景包括維護窗口、僅限營業時間的存取政策，以及具自動到期功能的暫時允許規則。

### 10.1 排程類型

| 類型 | 說明 | 範例 |
|:---|:---|:---|
| **Recurring** | 在指定日期的時間窗口內重複執行 | 週一至週五 09:00–17:00 |
| **One-time** | 在指定到期日時間前有效，之後自動還原 | 於 2026-04-10 18:00 到期 |

> **午夜跨越**：循環排程支援跨越午夜的時間窗口（例如 22:00–06:00）。系統可正確判斷「現在」是否位於跨越窗口內。

### 10.2 CLI

透過 CLI 主選單 **3. Rule Scheduler** 存取：
- **1. Schedule Management** — 瀏覽所有 Rulesets/Rules 並新增/移除排程
- **2. Run Schedule Check Now** — 手動觸發排程引擎
- **3. Scheduler Settings** — 啟用/停用背景 Daemon 並設定檢查間隔

### 10.3 Web GUI

透過 **Rule Scheduler** 分頁存取：
- 瀏覽所有 Rulesets 並展開個別 Rules
- 依名稱快速搜尋 Rulesets
- 建立 **Recurring**（基於時間窗口）或 **One-time**（自動到期）排程
- 在 **Logs** 子分頁中查看即時排程日誌

### 10.4 Draft 政策保護

> **重要**：Illumio PCE 的 Provision 操作會**一次性部署所有 draft 政策變更**。若排程執行 Provision 時某條規則處於 Draft 狀態（表示有人正在編輯），**該政策版本中所有未完成的 draft 變更都會被部署** — 這是潛在的嚴重安全風險。

系統實作了**多層 Draft 狀態保護**：

| 保護層 | 位置 | 行為 |
|:---|:---|:---|
| **CLI — Add Schedule** | `rule_scheduler_cli.py` | 若規則**或其父 Ruleset** 處於 Draft 狀態，則阻止排程建立；顯示錯誤訊息 |
| **Web GUI — Add Schedule** | `gui.py` API | 相同檢查；以 `Unprovisioned rules cannot be scheduled` 拒絕 POST 請求 |
| **Scheduler Engine — At Runtime** | `rule_scheduler.py` | 若排程的規則在執行時被發現處於 Draft 狀態，跳過 Provision 並寫入 `[SKIP]` 日誌 |
| **API Client Layer** | `api_client.has_draft_changes()` | 核心輔助方法：檢查規則本身**及**其父 Ruleset 是否有待定的 Draft 變更 |

#### 偵測邏輯（父 Ruleset 優先）

```
1. 取得規則的 Draft 版本 → 若 update_type 非空 → DRAFT（停止）
2. 若為子規則（href 包含 /sec_rules/）→ 取得父 Ruleset 的 Draft 版本
   → 若父 Ruleset 的 update_type 非空 → DRAFT（停止）
3. 兩者皆無 Draft 變更 → 可安全繼續
```

#### 日誌輸出

- Draft 阻止排程**設定嘗試** → 僅在畫面上顯示錯誤，不寫入日誌檔
- Draft 阻止排程**執行** → 寫入 `WARNING` 等級日誌條目以供稽核

```
[SKIP] CoreServices_Rule_1499 (ID:1499) is in DRAFT state. Operation aborted.
```

---

## 11. 設定參考

### 11.1 時區

時區設定控制報表及排程輸入欄位中時間戳的顯示方式。可在 Web GUI → **Settings → Timezone** 中設定，或直接編輯 `config.json`：

```json
{
    "settings": {
        "timezone": "UTC+8"
    }
}
```

支援格式：`local`（系統時區）、`UTC`、`UTC+8`、`UTC-5`、`UTC+5.5`

> 排程時間在內部始終以 **UTC 儲存**。CLI 精靈與 Web GUI 排程視窗會自動轉換至您設定的時區進行顯示。

### 11.2 儀表板查詢

Dashboard 分頁支援儲存自訂流量查詢以供重複使用。每個已儲存的查詢會記錄過濾參數（政策決策、埠、標籤、IP 範圍、過濾方向），並可從 Dashboard 隨時執行以填入 Top-10 小工具。

查詢儲存於 `config.json` → `settings.dashboard_queries`，完全透過 Web GUI 管理。

### 11.3 報表輸出

控制報表的儲存位置與保留時間。

| 設定 | 預設值 | 說明 |
|:---|:---|:---|
| `report.output_dir` | `reports/` | 產生報表的目錄（相對於專案根目錄，或絕對路徑） |
| `report.retention_days` | `30` | 每次排程執行後，自動刪除超過此天數的 `.html`/`.zip` 報表。設為 `0` 停用。 |

**從 Web GUI 設定**：Settings → **Report Output** 欄位群組
**從 CLI 設定**：System Settings 選單 → **4. System Settings**
**從 `config.json` 設定**：
```json
{
    "report": {
        "output_dir": "reports/",
        "retention_days": 30
    }
}
```

### 11.4 Web GUI

`config.json` 中的 `web_gui` 區塊控制驗證與網頁伺服器綁定設定。

| 鍵 | 類型 | 預設值 | 說明 |
|---|---|---|---|
| `web_gui.username` | string | `illumio` | 單一管理員帳號的登入使用者名稱 |
| `web_gui.password` | string | `illumio` | **明文。** 預設值 `illumio`；**首次登入後請立即變更**。GUI 直接將此字串與表單輸入比對 — 不進行雜湊。 |
| `web_gui.allowed_ips` | list | `[]` | IP 允許清單 — 空清單允許所有來源 |
| `web_gui.tls.enabled` | bool | `false` | 啟用 HTTPS（需要 `cert_file` + `key_file` 或 `self_signed: true`） |

**連接埠：** GUI 連接埠透過命令列 `--port N` 設定（預設 `5001`）；不儲存於 `config.json`。

**綁定主機：** GUI 綁定位址透過命令列 `--host` 設定（預設 `127.0.0.1`）；不儲存於 `config.json`。

> **安全注意：** 預設憑證 `illumio` / `illumio` 記錄於 `config.json.example`。請在首次登入後立即透過 Web GUI → **Settings → Web GUI Security** 變更。

### 11.5 報表智能

這些鍵位於 `config.json` 的 `report` 區塊下，控制進階報表行為。

| 鍵 | 類型 | 預設值 | 說明 |
|---|---|---|---|
| `report.snapshot_retention_days` | int | `90` | 變更影響（`mod_change_impact`）KPI 快照在自動刪除前保留的天數 |
| `report.threat_intel_csv_path` | string | `null` | 選用的已知惡意 IP CSV 的絕對路徑，由 `mod_exfiltration_intel` 用於威脅比對 |
| `report.draft_actions_enabled` | bool | `true` | `mod_draft_actions` 是否在 Traffic Report 中產生逐流量的修復建議 |

`config.json` 範例片段：

```json
{
    "report": {
        "snapshot_retention_days": 90,
        "threat_intel_csv_path": "/opt/illumio_ops/data/threat_intel.csv",
        "draft_actions_enabled": true
    }
}
```

### 11.6 PCE 快取

`pce_cache` 區塊控制本地 SQLite 快取，用於儲存事件與流量記錄以供快速離線分析。

| 鍵 | 類型 | 預設值 | 說明 |
|---|---|---|---|
| `pce_cache.enabled` | bool | `false` | 啟用從 PCE 的背景攝入 |
| `pce_cache.db_path` | string | `data/pce_cache.sqlite` | SQLite 資料庫檔案路徑（相對於專案根目錄或絕對路徑） |
| `pce_cache.events_retention_days` | int | `90` | 保留稽核事件的天數 |
| `pce_cache.traffic_raw_retention_days` | int | `7` | 保留原始逐流量記錄的天數 |
| `pce_cache.traffic_agg_retention_days` | int | `90` | 保留小時聚合流量的天數 |
| `pce_cache.events_poll_interval_seconds` | int | `300` | 事件輪詢器從 PCE 取得新事件的頻率（秒） |
| `pce_cache.traffic_poll_interval_seconds` | int | `3600` | 流量輪詢器執行非同步查詢的頻率（秒） |
| `pce_cache.rate_limit_per_minute` | int | `400` | 每分鐘最大 PCE API 呼叫數（最多 500） |

**啟用快取：**

```json
{
    "pce_cache": {
        "enabled": true,
        "db_path": "data/pce_cache.sqlite",
        "events_retention_days": 90,
        "traffic_raw_retention_days": 7,
        "traffic_agg_retention_days": 90,
        "events_poll_interval_seconds": 300,
        "traffic_poll_interval_seconds": 3600,
        "rate_limit_per_minute": 400
    }
}
```

> **SIEM 相依性：** SIEM 轉送器需要啟用 PCE 快取。流量與事件資料先攝入至 `pce_cache.sqlite`，再從 `siem_dispatch` 表發送至 SIEM 目的地。

> **磁碟空間估算：** 原始流量記錄預設僅保留 7 天。對於每天有 200,000 筆流量的典型 PCE，預計每 7 天窗口約佔 1 GB。聚合流量（小時摘要）使用原始儲存的約 5%。

### 11.7 告警通道參考

| 通道 | 設定鍵 | 驗證需求 |
|---|---|---|
| Email（SMTP） | `smtp.host`、`smtp.port`、`smtp.user`、`smtp.password`、`smtp.enable_tls` | 視伺服器而定；`smtp.enable_auth: false` 用於未驗證的中繼 |
| LINE Messaging API | `alerts.line_channel_access_token`、`alerts.line_target_id` | LINE Developer Console：Channel Access Token + User/Group ID |
| Webhook | `alerts.webhook_url` | 呼叫端提供包含任何 auth token 的完整 URL |

透過將識別碼加入 `alerts.active` 來啟用通道：

```json
{
    "alerts": {
        "active": ["mail", "line", "webhook"]
    }
}
```

未列入 `alerts.active` 的通道即使已填入憑證也會靜默跳過。

**告警內文欄位**（無論通道為何，每則告警均包含）：

| 欄位 | 說明 |
|---|---|
| `rule_name` | 觸發規則的名稱 |
| `rule_type` | `event`、`traffic`、`bandwidth` 或 `volume` |
| `trigger_value` | 導致告警的測量值 |
| `threshold` | 已超過的設定閾值 |
| `timestamp` | 觸發事件的 UTC ISO-8601 時間戳 |
| `pce_url` | 提供背景資訊的活躍 PCE Profile URL |

> **登入失敗告警**包含來自 PCE 稽核事件的來源 IP 與使用者名稱，無需另外查詢 PCE Console 即可快速分類。

> **Cooldown：** 每條規則均有可設定的 cooldown 期間（分鐘）。在 cooldown 到期前，相同規則不會再次觸發告警，防止重複相同事件造成告警風暴。

> **測試告警：** 使用 CLI 選項 **1. Alert Rules → 6. Send Test Alert** 或 `illumio-ops` Web GUI → **Actions → Test Alert** 在正式環境使用前驗證告警通道已正確設定且可連線。

---

## 12. 疑難排解

| 症狀 | 原因 | 解決方案 |
|:---|:---|:---|
| `Connection refused` | PCE 無法連線 | 確認 `api.url` 與網路連線 |
| `401 Unauthorized` | API 憑證無效 | 在 PCE Console 重新產生 API Key |
| `410 Gone` | 非同步查詢已過期 | 流量查詢結果已被清理；重新執行查詢 |
| `429 Too Many Requests` | API 速率限制 | 系統會自動以退避策略重試；若持續發生請降低查詢頻率 |
| Web GUI 無法啟動 | 相依套件未安裝 | **Ubuntu/Debian**：使用 venv — `venv/bin/pip install -r requirements.txt`。**RHEL**：`python3 -m venv venv && venv/bin/pip install -r requirements.txt` |
| `externally-managed-environment` pip 錯誤 | Ubuntu/Debian PEP 668 | 建立 venv：`python3 -m venv venv && venv/bin/pip install -r requirements.txt` |
| 未收到告警 | 通道未啟用 | 確認 `alerts.active` 陣列包含您的通道 |
| 報表顯示所有 VEN 均為線上 | 舊的快取狀態 | 確認您的 PCE 版本有回傳 `hours_since_last_heartbeat`；檢查 PCE API 回應中的 `agent.status` 欄位 |
| Rule Scheduler 顯示 `[SKIP]` 日誌 | 規則或父 Ruleset 處於 Draft 狀態 | 在 PCE Console 完成並 Provision 政策編輯；排程將自動恢復 |
| PCE Profile 切換無效果 | ApiClient 未重新初始化 | 使用 GUI「Activate」按鈕或 CLI Profile 切換，會觸發重新初始化 |
| Policy Usage 報表顯示 0 命中 | 規則僅為 draft 狀態 | 僅查詢 active（已佈建）的規則；請先佈建 draft 規則 |
| `PDF export is not available in this build` | 離線 bundle 排除了 reportlab（純 Python；不需要 WeasyPrint/Pango/Cairo/GTK） | 改用 `--format html` 或 `--format xlsx` |
| 升級後：載入舊設定 | `config.json` 依原樣保留 | 與 `config.json.example` 比較並新增任何新欄位 |
| Windows：`nssm.exe not found` | NSSM 不在 PATH 或 bundle deploy\ 中 | 將 `nssm.exe` 加入 PATH 或放置於 bundle `deploy\` 資料夾 |
| `Cache database not configured` | `pce_cache.enabled` 為 false 或 `db_path` 不正確 | 設定 `pce_cache.enabled: true` 並確認 `db_path` 可寫入 |
| SIEM 測試事件失敗顯示 `Destination not found` | 目的地名稱不符或 `enabled: false` | 確認 `siem.destinations[].name` 與引數一致；確認 `enabled: true` |
| `mod_change_impact` 顯示 `skipped: no_previous_snapshot` | 首次報表執行或快照已刪除 | 在首次報表後再產生一次；快照保留 `report.snapshot_retention_days` 天 |
| `config validate` 以非零退出並出現 pydantic 錯誤 | `config.json` 中有未知鍵或類型錯誤 | 修正回報的欄位；參閱 `config.json.example` 作為參考 |
| 解除安裝後重新安裝，Web GUI 登入失敗 | 保留了含舊明文 `web_gui.password` 的 `config.json` | 明文密碼在升級間保留；使用先前設定的密碼登入，或直接編輯 `web_gui.password` 為新值。 |
| `--purge` 意外移除設定 | 執行了 `uninstall.sh --purge` | `--purge` 旗標文件記載為具破壞性；請從備份還原。不含 `--purge` 時設定始終保留。 |

---

# 5. SIEM 整合

# SIEM 轉送器

> [!WARNING]
> 狀態：**預覽**（2026-04-23）。
> 現有部署可繼續使用 SIEM 轉送以維持相容性，但完整正式環境推出應等到執行管線缺口補齊後再進行。
>
> Task.md 中追蹤的已知缺口：
> - 執行時攝入路徑尚未自動排入 SIEM 派送列。
> - 排程器派送路徑尚未接線至完整的端對端消費迴圈。
> - 酬載建置失敗目前可能導致列留在持久性 `pending` 狀態。

## 架構

```
PCE API
  └─► EventsIngestor / TrafficIngestor
           │  (rate-limited, watermarked)
           ▼
      pce_cache.sqlite
           │
     siem_dispatch table
           │
      SiemDispatcher (tick every 5s)
           │
      ┌────┴───────────────────┐
      │         Formatter      │
      │  CEF 0.1 / JSON Lines  │
      │  + RFC5424 syslog hdr  │
      └────┬───────────────────┘
           │
      ┌────┴───────────────────┐
      │       Transport        │
      │  UDP / TCP / TLS / HEC │
      └────────────────────────┘
           │  (failure → DLQ)
           ▼
      SIEM / Splunk / Elastic
```

## 必要條件

必須先啟用 PCE 快取（`pce_cache.enabled: true`）。

## 啟用

在 `config/config.json` 中新增：

```json
"siem": {
  "enabled": true,
  "destinations": [
    {
      "name": "splunk-hec",
      "transport": "hec",
      "format": "json",
      "endpoint": "https://splunk.example.com:8088",
      "hec_token": "your-hec-token-here",
      "source_types": ["audit", "traffic"],
      "max_retries": 10
    }
  ]
}
```

## 全域 `siem` 設定區塊

`config.json` 中的頂層 `siem` 區段控制轉送器執行時行為：

| 鍵 | 類型 | 預設值 | 說明 |
|---|---|---|---|
| `siem.enabled` | bool | `false` | 啟用 SIEM 轉送器 |
| `siem.destinations` | list | `[]` | 目的地物件清單（見下方 schema） |
| `siem.dlq_max_per_dest` | int | `10000` | 每個目的地在最舊列被驅逐前的最大死信佇列深度 |
| `siem.dispatch_tick_seconds` | int | `5` | 派送器檢查待傳送列的頻率（秒） |

**操作命令：** `illumio-ops siem test <name>`（傳送合成事件）、`illumio-ops siem status`（顯示各目的地派送數量）、`illumio-ops siem replay --dest <name>`（重新排入 DLQ 項目）、`illumio-ops siem dlq --dest <name>`（列出死信事件）、`illumio-ops siem purge --dest <name>`（移除超過 N 天的 DLQ 項目）。

## 目的地設定 Schema

| 欄位 | 類型 | 預設值 | 說明 |
|---|---|---|---|
| `name` | string | 必填 | 唯一識別碼（1–64 字元） |
| `transport` | udp\|tcp\|tls\|hec | 必填 | 傳輸線路協定 |
| `format` | cef\|json\|syslog_cef\|syslog_json | `cef` | 日誌行格式 |
| `endpoint` | string | 必填 | syslog 的 `host:port`；HEC 的完整 URL |
| `tls_verify` | bool | `true` | 驗證 TLS 憑證（僅開發環境停用） |
| `tls_ca_bundle` | string | null | 自訂 PKI 的 CA bundle 路徑 |
| `hec_token` | string | null | Splunk HEC token（`transport: hec` 時必填） |
| `batch_size` | int | 100 | 每個派送器 tick 的列數 |
| `source_types` | list | `["audit","traffic"]` | 要轉送的資料類型 |
| `max_retries` | int | 10 | 移至隔離前的重試次數 |

## 格式範例

**CEF（稽核事件）：**
```
CEF:0|Illumio|PCE|3.11|policy.update|policy.update|3|rt=1745049600000 dvchost=pce.example.com externalId=uuid-abc outcome=success
```

**JSON Lines（流量記錄）：**
```json
{"src_ip":"10.0.0.1","dst_ip":"10.0.0.2","port":443,"protocol":"tcp","action":"blocked","flow_count":5}
```

**RFC5424 syslog 封裝（包裝任何格式）：**
```
<14>1 2026-04-19T10:00:00.000Z pce.example.com illumio-ops - - - CEF:0|Illumio|PCE|...
```

使用 `format: syslog_cef` 或 `format: syslog_json` 啟用 RFC5424 封裝。

## 測試目的地

```bash
illumio-ops siem test splunk-hec
```

傳送一個合成 `siem.test` 事件，並回報成功或失敗及錯誤訊息。

## DLQ 操作指南

當目的地連續失敗 `max_retries` 次時，派送列會移至 `dead_letter` 表。使用以下命令檢查：

```bash
illumio-ops siem dlq --dest splunk-hec
```

修復根本原因（錯誤 token、網路分區等）後，重新排入：

```bash
illumio-ops siem replay --dest splunk-hec --limit 1000
```

清除不再需要的舊項目：

```bash
illumio-ops siem purge --dest splunk-hec --older-than 30
```

## 傳輸層選擇指南

| 傳輸層 | 可靠性 | 順序 | 加密 | 使用場景 |
|---|---|---|---|---|
| UDP | 盡力傳送 | 否 | 否 | 低價值、高流量；即發即忘 |
| TCP | 至少一次 | 是 | 否 | 內部網路，不需要 TLS |
| TLS | 至少一次 | 是 | 是 | 正式環境**建議** |
| HEC | 至少一次 | 是 | 是（HTTPS） | Splunk 環境 |

UDP 可用但**不建議用於正式環境** — 設定 UDP 目的地時，GUI 會顯示警告橫幅。

## 退避排程

失敗的傳送以指數退避策略重試，上限為 1 小時：

| 重試 | 等待 |
|---|---|
| 1 | 10s |
| 2 | 20s |
| 3 | 40s |
| 4 | 80s |
| 5 | 160s |
| 6 | 320s |
| 7 | 640s |
| 8 | 1280s |
| 9 | 2560s |
| 10 | 3600s（上限） |

---

# 附錄 A — 報表模組清單

> 從 `docs/report_module_inventory_zh.md`（ed20df0~1）翻譯 — Phase B 更新。

# 報表模組清單與導讀指南

本文盤點 illumio_ops 既有報表模組的實務價值，並定義每個章節應補充的導讀內容。目標是讓報表讀者不只看到圖表和表格，而是能理解「這章在回答什麼問題」、「哪些現象需要注意」、「下一步該做什麼」。

## NotebookLM 佐證摘要

根據 Illumio 筆記本中的手冊、API guide 與微分段技術說明，Traffic / Flow Visibility 在微分段專案中通常同時服務多個角色：

- 資安/SOC：威脅獵捕、異常偵測、事件回應、橫向移動與資料外洩調查。
- 網管/平台團隊：掌握連線相依性、建立 label-based allow rules、排查未納管或未知依賴。
- DevOps / DevSecOps：理解服務間連線，避免 CI/CD 或微服務變更破壞安全策略。
- App Owner：確認應用上下游依賴，審核合理白名單需求。

因此 Traffic Report 不應只是一份大而全報表。建議拆成兩種 profile：

- Security Risk Traffic Report：聚焦異常、危險流量、橫向移動、勒索軟體高風險埠、PB exposure、blocked/denied patterns、外部威脅或外洩跡象。
- Network Inventory Traffic Report：聚焦應用相依性、label matrix、candidate allow rules、shared infrastructure usage、unmanaged/unknown dependencies、enforcement readiness。

NotebookLM 也建議每個章節採固定導讀格式：

- 本章目的：這章回答什麼業務或資安問題。
- 要注意的訊號：哪些值、趨勢、組合代表異常或需要處理。
- 判讀方式：如何理解圖表、Policy Decision、label matrix 或風險分數。
- 建議行動：讀者看完後應調查、建規則、修 label、隔離、清理規則或修 VEN。

## 評分標準

| 分數 | 意義 |
| ---: | --- |
| 5 | 直接支援風險降低、事件調查、規則制定、enforcement 推進或治理決策。 |
| 4 | 對特定 persona 很有價值，但應 profile-specific 或摘要化。 |
| 3 | 有背景價值，但主報表中需要簡化或只在有異常時顯示。 |
| 2 | 適合 appendix / XLSX / CSV，不適合作為主要章節。 |
| 1 | 實務價值低、重複或容易誤導，除非重新設計否則應移除。 |

建議處置：

- `keep-main`：保留為主章節。
- `keep-profile-specific`：依 Security Risk / Network Inventory profile 決定是否主顯示。
- `redesign`：保留目的，但重寫摘要、圖表或導讀。
- `simplify`：保留但縮短。
- `conditional`：只有資料存在或偵測到異常時顯示。
- `appendix`：移到附錄、XLSX 或 CSV。
- `merge/remove`：合併到其他章節或移除。

## Traffic Report 模組盤點

| Module | 實務價值 | 建議 | 主要受眾 | 章節應表達什麼 |
| --- | ---: | --- | --- | --- |
| `mod01_traffic_overview` | 3 | `simplify` | mixed | 說明資料範圍、流量規模、時間範圍與政策決策概況；不應變成主要決策章節。 |
| `mod02_policy_decisions` | 5 | `keep-profile-specific` | security/network | 說明 allowed / blocked / potentially_blocked 的真實比例。資安看未授權或危險流量；網管看規則覆蓋與 enforcement 影響。 |
| `mod03_uncovered_flows` | 5 | `keep-main` | security/network | 說明哪些流量缺乏 allow policy，進入 enforcement 後可能被 default-deny 影響。PB 必須被視為 gap，不是 staged coverage。 |
| `mod04_ransomware_exposure` | 5 | `keep-profile-specific` | security | 找出 SMB、RDP、SSH 等高風險橫向移動通道，協助資安優先調查或限制。 |
| `mod05_remote_access` | 2 | `merge/remove` | security | 已被 `mod15_lateral_movement` 整併，不建議恢復成獨立主章節，避免重複。 |
| `mod06_user_process` | 3 | `conditional` | security | 當 user/process 欄位存在時，找出異常執行程序、非預期使用者或可疑高活動行為。無資料時不應空顯示。 |
| `mod07_cross_label_matrix` | 4 | `keep-profile-specific` | network/app_owner | 把 observed flows 轉成 label-to-label 依賴矩陣，支援規則制定。資安版只應顯示 risky crossing。 |
| `mod08_unmanaged_hosts` | 5 | `keep-main` | security/network | 找出受管 workload 與 unknown/unmanaged destination 的連線。這同時是風險盲點與規則制定阻礙。 |
| `mod09_traffic_distribution` | 2 | `appendix` | network | Port/protocol 分布本身不是決策；只有出現異常集中、陌生服務或趨勢變化時才適合主顯示。 |
| `mod10_allowed_traffic` | 4 | `keep-profile-specific` | network/security | 網管用於建立 allow rules；資安只看 high-risk allowed paths 或跨區域高風險 allowed traffic。 |
| `mod11_bandwidth` | 3 | `conditional` | security/network | 高流量可用於外洩或容量判讀，但一般 Top Talkers 應進 appendix。 |
| `mod12_executive_summary` | 5 | `redesign` | executive/mixed | 應依 profile 產出不同摘要。風險版講 top risks/actions；盤點版講 rule readiness/dependency gaps。 |
| `mod13_readiness` | 5 | `keep-main` | network/executive | 評估哪些 app/env 可推 enforcement、哪些 label/rule/unknown dependency 還沒準備好。 |
| `mod14_infrastructure` | 5 | `keep-profile-specific` | security/network | 找出 DNS、AD、NTP、DB、proxy、backup、logging 等 shared/crown-jewel service 的暴露與依賴。 |
| `mod15_lateral_movement` | 5 | `keep-profile-specific` | security/network | 資安版用來看橫向移動與 blast radius；盤點版用來理解跨 app/env 依賴與 enforcement 邊界。 |
| `attack_posture.py` | 5 | `keep-supporting` | security/executive | 應作為風險評分與 Top Actions 來源，而不是再產生一個讀者不懂的獨立章節。 |

## Audit Report 模組盤點

| Module | 實務價值 | 建議 | 章節應表達什麼 |
| --- | ---: | --- | --- |
| `audit_mod00_executive` | 4 | `keep-main` | 說明 audit 期間是否有高風險操作、異常控制面活動、需立即關注的事件。 |
| `audit_mod01_health` | 4 | `keep-main` | 說明 PCE/API/audit 資料是否可信，是否有同步、健康或資料完整性問題。 |
| `audit_mod02_users` | 3 | `conditional` | 只在出現高權限、非預期、離峰或異常大量操作時主顯示；一般 top users 應 appendix。 |
| `audit_mod03_policy` | 5 | `keep-main` | 說明 policy/rule set 變更是否合理、是否過寬、是否可能造成風險或斷線。 |
| `audit_mod04_correlation` | 5 | `keep-main` | 把 auth failure、policy change、VEN change、provision 等事件串成可調查故事。 |
| `audit_risk.py` | 5 | `keep-supporting` | 支撐 audit risk scoring 與 attention required，不應讓讀者只看到分數但不知道原因。 |

## Policy Usage Report 模組盤點

| Module | 實務價值 | 建議 | 章節應表達什麼 |
| --- | ---: | --- | --- |
| `pu_mod00_executive` | 4 | `redesign` | 應說明可清理規則、有效 deny、過寬 allow 與查詢信心，而不是只列總數。 |
| `pu_mod01_overview` | 3 | `simplify` | 保留查詢範圍與資料品質，不應成為主要章節。 |
| `pu_mod02_hit_detail` | 4 | `appendix/main-summary` | Top hit rules 可主顯示；完整 hit detail 應進 XLSX/CSV。 |
| `pu_mod03_unused_detail` | 5 | `keep-main` | 直接支援規則清理與 policy hygiene，是高價值章節。 |
| `pu_mod04_deny_effectiveness` | 5 | `keep-main` | 證明 deny/override deny 是否有效阻擋不想要的流量，支援控制有效性。 |

## VEN Status Report 盤點

| Section | 實務價值 | 建議 | 章節應表達什麼 |
| --- | ---: | --- | --- |
| VEN summary | 5 | `keep-main` | 說明整體 agent 健康、enforcement 進度與 segmentation blind spots。 |
| Offline / lost heartbeat | 5 | `keep-main` | 失聯 workload 會造成控制盲點，應優先依 app/env/role 影響排序。 |
| Policy sync status | 5 | `keep-main` | Policy 未同步代表控制狀態可能與 PCE 不一致，應列出需修復對象。 |
| Enforcement mode | 5 | `keep-main` | 追蹤 visibility_only/selective/full 推進狀態，支援微分段專案進度管理。 |
| Online inventory | 2 | `appendix` | 完整線上清單適合 XLSX，不適合主報表。 |

## 建議章節導讀格式

每個主要章節都應在圖表或表格前加入導讀區塊。

```text
本章目的：
說明這章回答的問題，以及它和微分段/風險/規則制定的關係。

要注意的訊號：
列出應優先關注的數值、趨勢、異常組合或資料缺口。

判讀方式：
解釋圖表、Policy Decision、label matrix、風險分數或狀態欄位應如何解讀。

建議行動：
提供讀者下一步，例如調查、確認 App Owner、建立 allow rule、修 label、隔離主機、清理規則或修復 VEN。
```

## 高優先章節導讀範例

### Potentially Blocked / Uncovered Flows

本章目的：找出目前因 workload 尚未進入完整 enforcement 而仍可通過，但缺乏 matching allow rule 的流量。

要注意的訊號：PB 流量集中在核心服務、高風險 port、跨 env、跨 app、unmanaged destination，或在近期變更後突然上升。

判讀方式：`potentially_blocked` 不是「規則已準備好」，而是「目前沒有對應 allow/deny rule；若進入 default-deny enforcement，這類流量可能被阻擋」。

建議行動：與 App Owner 確認是否為合法依賴。合法流量應轉成 label-based allow rule；不合法或未知流量應保留為未來 enforcement 的阻擋候選。

### Application Dependency / Cross-Label Matrix

本章目的：把 observed east-west flows 轉成可制定微分段規則的 app/env/role/service 依賴。

要注意的訊號：Dev 到 Prod、跨 app 直連 DB、unknown destination、unmanaged dependency、過多 any-to-any 類型連線。

判讀方式：矩陣不是要展示所有流量，而是要幫網管和 App Owner 確認「哪些 label group 之間需要 allow rule」。

建議行動：將合法依賴整理成候選 allow rules；補齊缺失 label；將 unknown IP 建成 IP List 或 unmanaged workload；移除不符合架構的依賴。

### Lateral Movement

本章目的：找出可能擴大攻擊面或支援橫向移動的 east-west path。

要注意的訊號：SMB/RDP/SSH/WinRM 等高風險 port、單一來源連大量目的地、跨 zone/cross-env 通訊、連向 crown-jewel infrastructure。

判讀方式：節點和邊的數量代表 blast radius；高風險服務和跨邊界連線應比一般流量優先處理。

建議行動：對可疑來源啟動事件調查；對合法但高風險依賴建立最小權限規則；必要時 quarantine 或先以 deny/boundary 限縮。

### Draft Policy

本章目的：在 provision 前模擬規則變更對現有流量的影響。

要注意的訊號：Draft View 中關鍵業務流量仍為 not allowed / potentially blocked，或新規則 scope 過寬。

判讀方式：Reported View 是目前實際狀態；Draft View 是草稿規則生效後的預期狀態。兩者差異應被視為變更影響分析。

建議行動：Provision 前先確認必要流量已被 allow；縮小過寬規則；把仍會被阻擋的合法流量補成候選規則。

### VEN Status

本章目的：確認 segmentation control plane 是否能實際作用到 workload。

要注意的訊號：offline、lost heartbeat、degraded、policy not synced、host firewall tampering、長期停留 visibility_only。

判讀方式：沒有健康 VEN，就算 PCE 有正確 policy，也可能無法有效執行。VEN 問題應視為 segmentation blind spot。

建議行動：優先修復 crown-jewel 或高風險 app 的 VEN；檢查 PCE 連線、憑證、service 狀態與 policy sync；將健康且規則完整的 workload 推進 enforcement。


## 延伸閱讀

- [Architecture](./Architecture.md) — 系統概觀、模組地圖、PCE 快取、REST API 手冊
- [Security Rules Reference](./Security_Rules_Reference.md) — R-Series 規則與 `compute_draft` 行為
- [README](../README_zh.md) — 專案入口與快速上手
