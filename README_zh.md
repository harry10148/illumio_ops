# Illumio PCE Monitor

![Version](https://img.shields.io/badge/Version-v1.0.0-blue?style=flat-square)
![Python](https://img.shields.io/badge/Python-3.8%2B-yellow?style=flat-square&logo=python&logoColor=white)
![API](https://img.shields.io/badge/Illumio_API-v25.2-green?style=flat-square)

> **[English](README.md)** | **[繁體中文](README_zh.md)**

專為 **Illumio Core (PCE)** 設計的進階 **無 Agent (Agentless)** 監控暨自動化工具。透過 REST API 實現智慧型流量分析、安全事件偵測、工作負載隔離與多通道自動告警。**CLI/Daemon 模式無需安裝外部套件**（僅使用 Python 標準函式庫）。

---

## ✨ 核心特色

| 功能 | 說明 |
|:---|:---|
| **三種執行模式** | 背景守護程序 (`--monitor`)、互動式 CLI 精靈、或 Flask 驅動的 **Web GUI** (`--gui`) |
| **安全事件監控** | 追蹤 PCE 稽核事件，採用時間戳記錨點，保證零重複告警 |
| **高效能流量引擎** | 將所有規則整合為單次 API 查詢，O(1) 記憶體串流處理 |
| **工作負載隔離** | 透過 Quarantine Label（Mild/Moderate/Severe）隔離遭入侵主機 |
| **多通道即時告警** | 同步支援 Email (SMTP)、LINE 通知、Webhooks |
| **多語系介面** | Web GUI 即時切換英文↔繁體中文，無須重新載入 |

---

## 🚀 快速開始

### 1. 系統需求
- **Python 3.8+**
- **核心功能（免安裝）**：CLI 及 Daemon 模式僅使用 Python 標準函式庫，無需任何外部套件
- **選用 — Web GUI**：`flask`
- **選用 — 流量分析報表**：`pandas`、`openpyxl`、`pyyaml`

### 2. 安裝與啟動

```bash
git clone <repo-url>
cd illumio_monitor
cp config.json.example config.json    # 編輯並填入 PCE 憑證

# 互動式 CLI：
python illumio_monitor.py

# Web 視覺化介面（開啟 http://127.0.0.1:5001）：
python illumio_monitor.py --gui

# 背景 Daemon 模式（每 5 分鐘自動檢查）：
python illumio_monitor.py --monitor --interval 5
```

### 3. 基本設定 (`config.json`)

```json
{
    "api": {
        "url": "https://pce.example.com:8443",
        "org_id": "1",
        "key": "api_xxxxxxxxxxxxxx",
        "secret": "your-api-secret-here",
        "verify_ssl": true
    }
}
```

> 完整設定參考請見 [完整使用手冊](docs/User_Manual_zh.md)。

---

## 🏢 企業環境 / 離線安裝

適用於無法連線網際網路的Air-gap環境。

### 方案 A — Red Hat / CentOS（dnf / yum）

Web GUI 及 YAML 相依套件可直接從 **RHEL 8/9 AppStream** 安裝：

```bash
# Web GUI
sudo dnf install python3-flask

# YAML 設定檔（流量報表用）
sudo dnf install python3-pyyaml

# pandas（RHEL 8+ AppStream，版本可能較舊）
sudo dnf install python3-pandas
```

> `openpyxl` **不在** RHEL 官方 Repo 中，請使用方案 B 或 C 安裝。

### 方案 B — 預先下載 Wheel（pip 離線安裝）

在有網路的機器上（作業系統與架構須與目標主機相同，如 `linux_x86_64`）：

```bash
# 下載所有選用套件的 wheel 檔
pip download flask pandas openpyxl pyyaml -d ./offline_packages/
```

將 `offline_packages/` 資料夾複製到離線主機後安裝：

```bash
pip install --no-index --find-links=./offline_packages/ flask pandas openpyxl pyyaml
```

### 方案 C — 內部 PyPI Mirror（Nexus / Artifactory）

若組織已架設 Nexus Repository 或 JFrog Artifactory：

```bash
pip install pandas openpyxl pyyaml flask \
    --index-url https://nexus.internal/repository/pypi-proxy/simple/
```

### 套件來源速查表

| 套件 | RHEL AppStream | Ubuntu `apt` | Wheel 離線 |
|------|:--------------:|:------------:|:----------:|
| `flask` | ✅ `python3-flask` | ✅ `python3-flask` | ✅ |
| `pyyaml` | ✅ `python3-pyyaml` | ✅ `python3-yaml` | ✅ |
| `pandas` | ✅ `python3-pandas`（RHEL 8+）| ✅ `python3-pandas` | ✅ |
| `openpyxl` | ❌ 不在官方 Repo | ✅ `python3-openpyxl` | ✅ |

---


| 文件 | 說明 |
|:---|:---|
| **[完整使用手冊](docs/User_Manual_zh.md)** | 安裝、執行模式、規則建立、告警通道、Web GUI 使用教學 |
| **[專案架構與修改指南](docs/Project_Architecture_zh.md)** | 程式碼設計、模組職責、資料流、如何修改程式 |
| **[API 教學與 SIEM/SOAR 整合指南](docs/API_Cookbook_zh.md)** | 按場景分類的 API 教學（隔離、流量查詢等），可供 Playbook 直接參考 |

---

## 📁 專案結構

```text
illumio_monitor/
├── illumio_monitor.py     # 程式進入點
├── config.json            # 執行時設定（憑證、規則、告警）
├── state.json             # 持久化狀態（上次檢查時間、告警歷史）
├── requirements.txt       # Python 相依套件
├── src/
│   ├── main.py            # CLI 參數解析、Daemon 迴圈、互動選單
│   ├── api_client.py      # Illumio REST API 客戶端（重試、串流、認證）
│   ├── analyzer.py        # 規則引擎：流量/事件比對、指標計算
│   ├── reporter.py        # 告警發送器（Email、LINE、Webhook）
│   ├── config.py          # 設定管理器（原子寫入）
│   ├── gui.py             # Flask Web GUI 後端（路由 + API 端點）
│   ├── settings.py        # CLI 互動選單（規則 CRUD）
│   ├── i18n.py            # 國際化（EN/ZH 翻譯字典）
│   ├── utils.py           # 工具函式（日誌、色碼、單位格式化）
│   ├── templates/         # Jinja2 HTML 模板
│   └── static/            # CSS/JS 前端資源
├── docs/                  # 文件檔案
├── tests/                 # 單元測試 (pytest)
├── logs/                  # 執行時日誌
└── deploy/                # 部署腳本 (NSSM, systemd)
```
