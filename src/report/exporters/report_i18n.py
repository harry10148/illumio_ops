"""
src/report/exporters/report_i18n.py
Shared internationalisation helpers for HTML report exporters.

Provides:
  STRINGS       – dict of translatable label keys → {"en": "...", "zh_TW": "..."}
  make_i18n_js()  – returns an embedded <script> block with the full i18n dict,
                    applyI18n() and _toggleReportLang() functions.
  lang_btn_html() – returns the fixed-position language-toggle button HTML.
"""
from __future__ import annotations
import json

STRINGS: dict[str, dict[str, str]] = {
    # ── Common ───────────────────────────────────────────────────────────────
    "rpt_generated":    {"en": "Generated:",        "zh_TW": "產生時間："},
    "rpt_period":       {"en": "Period:",            "zh_TW": "資料區間："},
    "rpt_key_metrics":  {"en": "Key Metrics",        "zh_TW": "關鍵指標"},
    "rpt_key_findings": {"en": "Key Findings",       "zh_TW": "關鍵發現"},
    "rpt_no_data":      {"en": "— No data —",        "zh_TW": "— 無資料 —"},
    "rpt_no_records":   {"en": "— No records —",     "zh_TW": "— 無紀錄 —"},
    "rpt_no_findings":  {"en": "No key findings.",   "zh_TW": "無關鍵發現。"},
    "rpt_no_lateral":   {"en": "No lateral movement traffic found.", "zh_TW": "未發現橫向移動流量。"},
    "rpt_no_user_proc": {"en": "No user/process data.",             "zh_TW": "無使用者/程序資料。"},
    "rpt_no_matrix":    {"en": "No label matrix data.",             "zh_TW": "無標籤矩陣資料。"},

    # ── Traffic report – title + nav ─────────────────────────────────────────
    "rpt_tr_title":           {"en": "Illumio Traffic Flow Report",  "zh_TW": "Illumio 流量分析報表"},
    "rpt_tr_nav_summary":     {"en": "📊 Executive Summary",         "zh_TW": "📊 執行摘要"},
    "rpt_tr_nav_overview":    {"en": "1 Traffic Overview",           "zh_TW": "1 流量總覽"},
    "rpt_tr_nav_policy":      {"en": "2 Policy Decisions",           "zh_TW": "2 策略判定"},
    "rpt_tr_nav_uncovered":   {"en": "3 Uncovered Flows",            "zh_TW": "3 未覆蓋流量"},
    "rpt_tr_nav_ransomware":  {"en": "4 Ransomware Exposure",        "zh_TW": "4 勒索軟體風險"},
    "rpt_tr_nav_remote":      {"en": "5 Remote Access",              "zh_TW": "5 遠端存取"},
    "rpt_tr_nav_user":        {"en": "6 User & Process",             "zh_TW": "6 使用者與程序"},
    "rpt_tr_nav_matrix":      {"en": "7 Cross-Label Matrix",         "zh_TW": "7 跨標籤矩陣"},
    "rpt_tr_nav_unmanaged":   {"en": "8 Unmanaged Hosts",            "zh_TW": "8 非受管主機"},
    "rpt_tr_nav_distribution":{"en": "9 Traffic Distribution",       "zh_TW": "9 流量分佈"},
    "rpt_tr_nav_allowed":     {"en": "10 Allowed Traffic",           "zh_TW": "10 允許流量"},
    "rpt_tr_nav_bandwidth":   {"en": "11 Bandwidth & Volume",        "zh_TW": "11 頻寬與傳輸量"},
    "rpt_tr_nav_findings":    {"en": "🔍 Findings",                  "zh_TW": "🔍 發現項目"},

    # ── Traffic report – section headings ────────────────────────────────────
    "rpt_tr_sec_overview":    {"en": "1 · Traffic Overview",         "zh_TW": "1 · 流量總覽"},
    "rpt_tr_sec_policy":      {"en": "2 · Policy Decisions",         "zh_TW": "2 · 策略判定"},
    "rpt_tr_sec_uncovered":   {"en": "3 · Uncovered Flows",          "zh_TW": "3 · 未覆蓋流量"},
    "rpt_tr_sec_ransomware":  {"en": "4 · Ransomware Exposure",      "zh_TW": "4 · 勒索軟體風險"},
    "rpt_tr_sec_remote":      {"en": "5 · Remote Access",            "zh_TW": "5 · 遠端存取"},
    "rpt_tr_sec_user":        {"en": "6 · User & Process",           "zh_TW": "6 · 使用者與程序"},
    "rpt_tr_sec_matrix":      {"en": "7 · Cross-Label Matrix",       "zh_TW": "7 · 跨標籤矩陣"},
    "rpt_tr_sec_unmanaged":   {"en": "8 · Unmanaged Hosts",          "zh_TW": "8 · 非受管主機"},
    "rpt_tr_sec_distribution":{"en": "9 · Traffic Distribution",     "zh_TW": "9 · 流量分佈"},
    "rpt_tr_sec_allowed":     {"en": "10 · Allowed Traffic",         "zh_TW": "10 · 允許流量"},
    "rpt_tr_sec_bandwidth":   {"en": "11 · Bandwidth & Volume",      "zh_TW": "11 · 頻寬與傳輸量"},
    "rpt_tr_sec_findings":    {"en": "🔍 Security Findings",         "zh_TW": "🔍 安全發現項目"},

    # ── Traffic report – module labels ───────────────────────────────────────
    "rpt_tr_policy_coverage": {"en": "Policy Coverage",                     "zh_TW": "策略覆蓋率"},
    "rpt_tr_flow_breakdown":  {"en": "Allowed / Blocked / Potential",        "zh_TW": "允許 / 阻斷 / 潛在阻斷"},
    "rpt_tr_total_data":      {"en": "Total Data",                           "zh_TW": "總傳輸量"},
    "rpt_tr_date_range":      {"en": "Date Range",                           "zh_TW": "資料區間"},
    "rpt_tr_top_ports":       {"en": "Top Ports",                            "zh_TW": "Top 通訊埠"},
    "rpt_tr_uncovered_label": {"en": "Uncovered:",                           "zh_TW": "未覆蓋："},
    "rpt_tr_coverage_label":  {"en": "Coverage:",                            "zh_TW": "覆蓋率："},
    "rpt_tr_top_uncovered":   {"en": "Top Uncovered Flows",                  "zh_TW": "未覆蓋流量 Top N"},
    "rpt_tr_risk_flows":      {"en": "Total risk flows:",                    "zh_TW": "風險流量總數："},
    "rpt_tr_risk_summary":    {"en": "Risk Level Summary",                   "zh_TW": "風險等級摘要"},
    "rpt_tr_per_port":        {"en": "Per-Port Detail",                      "zh_TW": "各通訊埠明細"},
    "rpt_tr_host_exposure":   {"en": "Host Exposure Ranking",                "zh_TW": "主機暴露排名"},
    "rpt_tr_top_talkers":     {"en": "Top Talkers",                          "zh_TW": "最高通訊量主機"},
    "rpt_tr_top_users":       {"en": "Top Users",                            "zh_TW": "主要使用者"},
    "rpt_tr_top_processes":   {"en": "Top Processes",                        "zh_TW": "主要程序"},
    "rpt_tr_label_key":       {"en": "Label Key:",                           "zh_TW": "標籤鍵："},
    "rpt_tr_unmanaged_flows": {"en": "Unmanaged flows:",                     "zh_TW": "非受管流量："},
    "rpt_tr_top_unmanaged":   {"en": "Top Unmanaged Sources",                "zh_TW": "非受管來源 Top N"},
    "rpt_tr_port_dist":       {"en": "Port Distribution",                    "zh_TW": "通訊埠分佈"},
    "rpt_tr_proto_dist":      {"en": "Protocol Distribution",                "zh_TW": "協定分佈"},
    "rpt_tr_audit_flags":     {"en": "Audit Flags",                          "zh_TW": "稽核標記"},
    "rpt_tr_top_app_flows":   {"en": "Top App Flows",                        "zh_TW": "應用程式流量 Top N"},
    "rpt_tr_top_by_bw":       {"en": "Top by Bandwidth (Mbps)",              "zh_TW": "最高頻寬流量 (Mbps)"},
    "rpt_tr_top_by_bytes":    {"en": "Top by Total Bytes",                   "zh_TW": "最高傳輸量"},
    "rpt_tr_anomalies":       {"en": "Anomalies (High Bytes/Conn)",          "zh_TW": "異常流量（高位元組/連線比）"},
    "rpt_tr_anomalies_note":  {"en": "Flows with bytes-per-connection ratio above P95 (connections > 1 only) — potential large transfers or data exfiltration candidates.",
                               "zh_TW": "每連線傳輸量高於 P95 的流量（僅計算連線數 > 1），可能為大量傳輸或資料外洩候選項目。"},
    "rpt_tr_total_volume":    {"en": "Total Volume",                         "zh_TW": "總傳輸量"},
    "rpt_tr_max_bw":          {"en": "Max Bandwidth",                        "zh_TW": "最高頻寬"},
    "rpt_tr_avg_bw":          {"en": "Avg Bandwidth",                        "zh_TW": "平均頻寬"},
    "rpt_tr_investigation_title": {"en": "⚠ Hosts Requiring Investigation",
                                   "zh_TW": "⚠ 需要調查的目標主機"},
    "rpt_tr_investigation_desc":  {
        "en": "The following destination hosts have ALLOWED traffic on critical or high-risk ports. Verify whether this is intentional or block the traffic.",
        "zh_TW": "以下目標主機在重大或高風險通訊埠上有被允許的流量，應進行驗證或考慮封鎖。",
    },
    "rpt_tr_no_investigation":    {"en": "✅ No allowed traffic on critical/high-risk ports detected.",
                                   "zh_TW": "✅ 未發現重大/高風險通訊埠上的允許流量。"},
    "rpt_tr_host_exposure_note":  {
        "en": "Destination hosts ranked by number of distinct risk ports contacted (all policy decisions).",
        "zh_TW": "依接觸風險通訊埠數量排序的目標主機，包含所有決策（含阻斷）。",
    },
    "rpt_tr_footer":          {"en": "Illumio PCE Ops — Traffic Flow Report",
                               "zh_TW": "Illumio PCE Ops — 流量分析報表"},

    # ── Security Findings – no data ──────────────────────────────────────────
    "rpt_no_findings_detail": {
        "en":    "No security findings were triggered for this dataset. This may indicate good policy coverage or that thresholds need tuning.",
        "zh_TW": "此資料集未觸發任何安全發現項目，可能代表策略覆蓋率良好，或需要調整偵測閾值。",
    },

    # ── Security Findings – category names & descriptions ────────────────────
    "rpt_cat_ransomware_name": {"en": "🦠 Ransomware Exposure", "zh_TW": "🦠 勒索軟體風險"},
    "rpt_cat_ransomware_desc": {
        "en":    "Rules detecting traffic patterns associated with ransomware attack chains: critical lateral-spread ports (SMB, RDP, WinRM, RPC), remote-access persistence tools, and policy gaps that leave high-risk ports unblocked or only in test mode.",
        "zh_TW": "偵測與勒索軟體攻擊鏈相關的流量模式：關鍵橫向擴散通訊埠（SMB、RDP、WinRM、RPC）、遠端存取持久化工具，以及使高風險通訊埠暴露於測試模式或未阻斷狀態的策略缺口。",
    },
    "rpt_cat_lateralmovement_name": {"en": "↔ Lateral Movement", "zh_TW": "↔ 橫向移動"},
    "rpt_cat_lateralmovement_desc": {
        "en":    "Rules targeting attacker pivoting techniques inside the network. Covers: cleartext credential exposure (Telnet/FTP), network discovery poisoning (LLMNR/NetBIOS), database over-exposure, identity infrastructure (Kerberos/LDAP) access, graph-based blast-radius analysis, enforcement gaps, exfiltration patterns, and cross-environment boundary breaks — the full lateral movement kill-chain.",
        "zh_TW": "偵測攻擊者在網路內部橫向滲透的技術。涵蓋：明文憑證暴露（Telnet/FTP）、網路探索協定投毒（LLMNR/NetBIOS）、資料庫過度暴露、身份基礎架構（Kerberos/LDAP）存取、圖形化爆炸半徑分析、執行模式落差、資料外洩模式，以及跨環境邊界突破——完整的橫向移動殺傷鏈。",
    },
    "rpt_cat_unmanagedhost_name": {"en": "🖥 Unmanaged Hosts", "zh_TW": "🖥 非受管主機"},
    "rpt_cat_unmanagedhost_desc": {
        "en":    "Rules triggered by traffic from hosts not enrolled in the PCE. These hosts operate outside your zero-trust boundary with no VEN enforcement — they are blind spots that cannot be protected by Illumio micro-segmentation rules.",
        "zh_TW": "偵測來自未納入 PCE 管理主機的流量。這些主機在零信任邊界之外運行，缺乏 VEN 執行機制——它們是無法受 Illumio 微分段規則保護的盲點。",
    },
    "rpt_cat_policy_name": {"en": "📋 Policy Coverage", "zh_TW": "📋 策略覆蓋率"},
    "rpt_cat_policy_desc": {
        "en":    "Rules evaluating the completeness of your segmentation policy: overall coverage percentage, cross-environment traffic volume, and gaps in rule-set coverage that leave workloads unprotected.",
        "zh_TW": "評估微分段策略的完整性：整體覆蓋率百分比、跨環境流量量，以及使工作負載處於未受保護狀態的規則集缺口。",
    },
    "rpt_cat_useractivity_name": {"en": "👤 User Activity", "zh_TW": "👤 使用者活動"},
    "rpt_cat_useractivity_desc": {
        "en":    "Rules detecting anomalous user account behaviour — a single account reaching an unusually high number of distinct destinations, which may indicate credential abuse, a compromised account, or data staging before exfiltration.",
        "zh_TW": "偵測異常使用者帳戶行為——單一帳戶連線至異常多的不同目標，可能表示憑證遭濫用、帳戶被盜，或資料外洩前的資料暫存。",
    },
    "rpt_cat_bandwidth_name": {"en": "📶 Bandwidth Anomaly", "zh_TW": "📶 頻寬異常"},
    "rpt_cat_bandwidth_desc": {
        "en":    "Rules flagging flows with abnormally high byte volume relative to the dataset baseline. Sudden large transfers from unexpected sources are a key indicator of data exfiltration, unauthorised backups, or attacker data staging.",
        "zh_TW": "偵測位元組傳輸量相對於資料集基準值異常偏高的流量。來自非預期來源的突發大量傳輸是資料外洩、未授權備份或攻擊者資料暫存的關鍵指標。",
    },

    # ── Security Findings – shared labels ────────────────────────────────────
    "rpt_rule_check_label": {"en": "What this rule checks:", "zh_TW": "此規則檢查項目："},
    "rpt_recommendation_label": {"en": "Recommendation:", "zh_TW": "建議措施："},

    # ── Security Findings – rule how-text (B-series) ──────────────────────────
    "rpt_rule_B001_how": {
        "en":    "Checks for traffic on ransomware's primary attack ports (SMB 445, RPC 135, RDP 3389, WinRM 5985/5986) that is NOT blocked. These are the exact ports used in EternalBlue, NotPetya, and WannaCry-class attacks for network-wide lateral spread.",
        "zh_TW": "檢查勒索軟體主要攻擊通訊埠（SMB 445、RPC 135、RDP 3389、WinRM 5985/5986）上未被阻斷的流量。這些正是 EternalBlue、NotPetya 和 WannaCry 類攻擊用於全網橫向擴散的通訊埠。",
    },
    "rpt_rule_B002_how": {
        "en":    "Detects allowed flows on secondary remote-access ports (TeamViewer 5938, VNC 5900, NetBIOS 137-139). Ransomware operators and APT groups use these for C2 persistence and remote control after initial compromise.",
        "zh_TW": "偵測次要遠端存取通訊埠（TeamViewer 5938、VNC 5900、NetBIOS 137-139）上的允許流量。勒索軟體操作者和 APT 組織在初始入侵後利用這些通訊埠進行 C2 持久化與遠端控制。",
    },
    "rpt_rule_B003_how": {
        "en":    "Detects medium-risk ports (SSH 22, NFS 2049, FTP 20/21, HTTP 80) showing as potentially_blocked. This means the segmentation rule exists but the workload is in visibility/test mode — the block is NOT enforced and traffic flows freely.",
        "zh_TW": "偵測中等風險通訊埠（SSH 22、NFS 2049、FTP 20/21、HTTP 80）顯示為 potentially_blocked 的情形。這表示微分段規則存在但工作負載處於可見度/測試模式——阻斷未生效，流量仍可自由通過。",
    },
    "rpt_rule_B004_how": {
        "en":    "Counts flows from hosts not enrolled in the PCE. Unmanaged hosts have no VEN and therefore no micro-segmentation enforcement — they are outside the zero-trust boundary and represent uncontrolled attack surface.",
        "zh_TW": "計算來自未納入 PCE 管理主機的流量筆數。非受管主機沒有 VEN，因此缺乏微分段執行機制——它們在零信任邊界之外，代表無法控制的攻擊面。",
    },
    "rpt_rule_B005_how": {
        "en":    "Measures the percentage of observed flows with an active allow policy. Coverage below 30% means most traffic is uncontrolled — a sign that segmentation is in early stages and large attack surface remains exposed.",
        "zh_TW": "衡量擁有主動允許策略的觀測流量百分比。覆蓋率低於 30% 表示大部分流量未受管控——這是微分段仍處於初期階段且大量攻擊面仍暴露的訊號。",
    },
    "rpt_rule_B006_how": {
        "en":    "Detects source IPs that connect to an abnormally high number of distinct destinations on lateral movement ports. This fan-out pattern (one source → many destinations) is the hallmark of worm propagation and attacker pivoting after initial compromise.",
        "zh_TW": "偵測來源 IP 在橫向移動通訊埠上連線至異常多個不同目標的情形。此扇出模式（單一來源 → 多個目標）是蠕蟲傳播和攻擊者在初始入侵後橫向移動的典型特徵。",
    },
    "rpt_rule_B007_how": {
        "en":    "Detects individual user accounts connecting to unusually many unique destination IPs. This may indicate a compromised account being used for automated reconnaissance, credential stuffing, or data staging before exfiltration.",
        "zh_TW": "偵測個別使用者帳戶連線至異常多個不同目標 IP 的情形。這可能表示帳戶遭入侵並被用於自動化偵察、憑證填充，或資料外洩前的資料暫存。",
    },
    "rpt_rule_B008_how": {
        "en":    "Flags individual flows exceeding the 95th percentile of byte volume in the dataset. Sudden high-volume transfers from unexpected sources are a key indicator of data staging, exfiltration, or unsanctioned large-scale backups.",
        "zh_TW": "標記位元組傳輸量超過資料集第 95 百分位的個別流量。來自非預期來源的突發高量傳輸是資料暫存、外洩或未授權大規模備份的關鍵指標。",
    },
    "rpt_rule_B009_how": {
        "en":    "Tracks the number of flows crossing environment boundaries (e.g. Production → Development). Excessive cross-env traffic may indicate lateral movement from a compromised lower-security zone into production.",
        "zh_TW": "追蹤跨越環境邊界（例如生產環境 → 開發環境）的流量筆數。過多的跨環境流量可能表示攻擊者從安全性較低的環境橫向移動至生產環境。",
    },

    # ── Security Findings – rule how-text (L-series) ──────────────────────────
    "rpt_rule_L001_how": {
        "en":    "Detects any traffic on Telnet (23) or FTP (20/21). These protocols transmit credentials and data without encryption. Any attacker with network access can perform a man-in-the-middle or ARP poisoning attack to harvest passwords in plaintext — enabling instant credential reuse for lateral movement.",
        "zh_TW": "偵測 Telnet（23）或 FTP（20/21）上的任何流量。這些協定在傳輸憑證和資料時不加密。任何具有網路存取權的攻擊者都可以執行中間人攻擊或 ARP 毒化來擷取明文密碼——讓其得以立即重複使用憑證進行橫向移動。",
    },
    "rpt_rule_L002_how": {
        "en":    "Detects unblocked flows on broadcast/discovery protocols: NetBIOS (137/138), mDNS (5353), LLMNR (5355), SSDP (1900). Tools like Responder and Inveigh exploit these to perform hostname poisoning and capture NTLMv2 hashes without any authentication — then crack or relay those hashes for lateral movement.",
        "zh_TW": "偵測廣播/探索協定的未阻斷流量：NetBIOS（137/138）、mDNS（5353）、LLMNR（5355）、SSDP（1900）。Responder 和 Inveigh 等工具利用這些協定執行主機名稱投毒並擷取 NTLMv2 雜湊值，無需任何驗證——隨後可用於破解或轉發以進行橫向移動。",
    },
    "rpt_rule_L003_how": {
        "en":    "Checks whether database ports (MSSQL 1433, MySQL 3306, PostgreSQL 5432, Oracle 1521, MongoDB 27017, Redis 6379, Elasticsearch 9200) are reachable from many distinct application labels. Databases should only be reachable from their direct app tier. Wide exposure provides direct data access after a single lateral move.",
        "zh_TW": "檢查資料庫通訊埠（MSSQL 1433、MySQL 3306、PostgreSQL 5432、Oracle 1521、MongoDB 27017、Redis 6379、Elasticsearch 9200）是否可從多個不同應用程式標籤存取。資料庫應只能從其直接應用程式層存取；廣泛暴露使攻擊者只需一次橫向移動即可直接存取資料。",
    },
    "rpt_rule_L004_how": {
        "en":    "Detects allowed database flows crossing environment boundaries (e.g. Dev app → Production database). Environment boundaries are the macro-segmentation layer. Breaching them allows an attacker in a low-security Dev environment to directly access Production data stores.",
        "zh_TW": "偵測跨越環境邊界的允許資料庫流量（例如開發應用程式 → 生產資料庫）。環境邊界是巨觀分段層；突破這些邊界使攻擊者得以從安全性較低的開發環境直接存取生產資料庫。",
    },
    "rpt_rule_L005_how": {
        "en":    "Detects Kerberos (88), LDAP (389/636), and Global Catalog (3268/3269) traffic from many source applications. Active Directory is the domain's authentication authority. Excessive access enables domain enumeration (BloodHound), Kerberoasting, Golden/Silver Ticket attacks, and full domain takeover.",
        "zh_TW": "偵測來自多個來源應用程式的 Kerberos（88）、LDAP（389/636）和全域目錄（3268/3269）流量。Active Directory 是網域的驗證中心；過度存取使攻擊者得以進行網域列舉（BloodHound）、Kerberoasting、Golden/Silver Ticket 攻擊，乃至完全接管網域。",
    },
    "rpt_rule_L006_how": {
        "en":    "Uses BFS graph traversal on allowed lateral-port connections to find apps that can reach many others through a chain of pivots. High reachability = high blast radius. An attacker who compromises a top-ranked app can traverse the entire reachable subgraph.",
        "zh_TW": "使用廣度優先搜尋（BFS）圖形遍歷分析允許橫向通訊埠連線，找出可通過多段橫向移動連鏈接觸多個其他應用程式的節點。高可及性 = 高爆炸半徑；被入侵的頂級排名應用程式可能讓攻擊者遍歷整個可及子圖。",
    },
    "rpt_rule_L007_how": {
        "en":    "Detects unmanaged (non-PCE) hosts communicating on database, identity (Kerberos/LDAP), or Windows management ports to managed workloads. Unmanaged hosts have no VEN enforcement — they are outside zero-trust. If they can reach critical services, they represent uncontrolled lateral movement entry points.",
        "zh_TW": "偵測非受管（非 PCE）主機在資料庫、身份識別（Kerberos/LDAP）或 Windows 管理通訊埠上與受管工作負載的通訊。非受管主機沒有 VEN 執行機制——它們在零信任邊界外，若能存取關鍵服務，即代表無法控制的橫向移動入口點。",
    },
    "rpt_rule_L008_how": {
        "en":    "Identifies 'potentially_blocked' flows on lateral movement ports. This means the policy rule exists but the destination workload is in visibility/test mode — the block is not active. These are live, traversable attack paths right now.",
        "zh_TW": "識別橫向移動通訊埠上的 potentially_blocked 流量。這表示策略規則存在但目標工作負載處於可見度/測試模式——阻斷未生效，這些是現在就可被橫穿的攻擊路徑，是「我們有策略但仍遭入侵」事件中最常見的原因。",
    },
    "rpt_rule_L009_how": {
        "en":    "Detects managed workloads transferring significant data volume to unmanaged (external/unknown) destinations. This is the post-lateral-movement exfiltration phase: attacker has pivoted to a high-value host and is now staging or exfiltrating data to an external C2 or drop server outside PCE visibility.",
        "zh_TW": "偵測受管工作負載向非受管（外部/未知）目標傳輸大量資料的情形。這是橫向移動後的資料外洩階段：攻擊者已橫向移動至高價值主機，正在向 PCE 可見範圍外的外部 C2 或投放伺服器暫存或外洩資料。",
    },
    "rpt_rule_L010_how": {
        "en":    "CRITICAL: Detects lateral movement ports (SMB 445, RDP 3389, WinRM 5985/5986, RPC 135) allowed between different environments. Environment segmentation is the macro-security boundary. If lateral ports cross it, an attacker who compromises Dev/Test can directly pivot into Production.",
        "zh_TW": "重大：偵測橫向移動通訊埠（SMB 445、RDP 3389、WinRM 5985/5986、RPC 135）在不同環境間的允許流量。環境分段是巨觀安全邊界；若橫向通訊埠可跨越此邊界，入侵開發/測試環境的攻擊者即可直接使用相同技術橫向移動至生產環境。",
    },

    # ── Audit report ─────────────────────────────────────────────────────────
    "rpt_au_title":         {"en": "Illumio Audit & System Events Report",
                             "zh_TW": "Illumio 稽核與系統事件報表"},
    "rpt_au_nav_summary":   {"en": "📊 Executive Summary",               "zh_TW": "📊 執行摘要"},
    "rpt_au_nav_health":    {"en": "1 System Health",                    "zh_TW": "1 系統健康"},
    "rpt_au_nav_users":     {"en": "2 User Activity",                    "zh_TW": "2 使用者活動"},
    "rpt_au_nav_policy":    {"en": "3 Policy Changes",                   "zh_TW": "3 策略變更"},
    "rpt_au_sec_health":    {"en": "1 · System Health & Agent",          "zh_TW": "1 · 系統健康與 Agent"},
    "rpt_au_sec_users":     {"en": "2 · User Activity & Authentication", "zh_TW": "2 · 使用者活動與認證"},
    "rpt_au_sec_policy":    {"en": "3 · Policy Modifications",           "zh_TW": "3 · 策略修改"},
    "rpt_au_top_events":    {"en": "Top Event Types",                    "zh_TW": "主要事件類型"},
    "rpt_au_severity_dist": {"en": "Severity Distribution",              "zh_TW": "嚴重程度分佈"},
    "rpt_au_total_health":  {"en": "Total Health Events:",               "zh_TW": "系統健康事件總數："},
    "rpt_au_summary_type":  {"en": "Summary by Event Type",              "zh_TW": "依事件類型摘要"},
    "rpt_au_recent":        {"en": "Recent Events (up to 50)",           "zh_TW": "最近事件（最多 50 筆）"},
    "rpt_au_severity_breakdown": {"en": "Severity Breakdown",            "zh_TW": "嚴重程度細分"},
    "rpt_au_security_concerns":  {"en": "Security Concerns:",            "zh_TW": "安全疑慮："},
    "rpt_au_connectivity_issues":{"en": "Agent Connectivity:",           "zh_TW": "Agent 連線："},
    "rpt_au_connectivity_title": {"en": "Agent Connectivity Events",     "zh_TW": "Agent 連線事件"},
    "rpt_au_sec_concern_title":  {"en": "⚠ Security Concern Events",     "zh_TW": "⚠ 安全疑慮事件"},
    "rpt_au_sec_concern_desc": {
        "en": "agent.tampering, agent.suspend, and agent.clone_detected events may indicate compromised workloads or unauthorized changes. Investigate immediately.",
        "zh_TW": "agent.tampering、agent.suspend 及 agent.clone_detected 事件可能表示工作負載遭入侵或未經授權的變更，請立即調查。",
    },
    "rpt_au_bp_health": {
        "en": "<b>Illumio Best Practice:</b> Monitor system_health events for severity changes (Warning → Error → Fatal). Investigate agent.tampering and agent.suspend events immediately — unintended suspensions or firewall tampering may indicate workload compromise. Track agent_missed_heartbeats_check (3+ missed = 15 min) and agent_offline_check (12 missed = removed from policy).",
        "zh_TW": "<b>Illumio 最佳實踐：</b>監控 system_health 事件的嚴重程度變化（Warning → Error → Fatal）。立即調查 agent.tampering 和 agent.suspend 事件 — 非預期的暫停或防火牆篡改可能代表工作負載遭到入侵。追蹤 agent_missed_heartbeats_check（3 次以上未回應 = 15 分鐘）和 agent_offline_check（12 次未回應 = 從策略中移除）。",
    },
    "rpt_au_total_user":    {"en": "Total User Events:",                 "zh_TW": "使用者事件總數："},
    "rpt_au_failed_logins": {"en": "Failed Logins:",                     "zh_TW": "登入失敗次數："},
    "rpt_au_per_user":      {"en": "Activity by User",                   "zh_TW": "使用者活動統計"},
    "rpt_au_bp_users": {
        "en": "<b>Illumio Best Practice:</b> Monitor login failures for patterns indicating brute-force or credential stuffing attacks. Investigate repeated failures from the same user or sudden spikes in authentication events.",
        "zh_TW": "<b>Illumio 最佳實踐：</b>監控登入失敗的模式以偵測暴力破解或憑證填充攻擊。調查同一使用者的重複失敗或認證事件的突然激增。",
    },
    "rpt_au_total_policy":  {"en": "Total Policy Events:",               "zh_TW": "策略事件總數："},
    "rpt_au_provisions":    {"en": "Provisions:",                        "zh_TW": "策略部署："},
    "rpt_au_rule_changes":  {"en": "Rule Changes:",                      "zh_TW": "規則變更："},
    "rpt_au_provision_title":{"en": "Policy Provision Events",           "zh_TW": "策略部署事件"},
    "rpt_au_provision_desc": {
        "en": "Policy provisions push draft changes to active enforcement. Review for unintended scope or excessive workload impact.",
        "zh_TW": "策略部署將草稿變更推送至執行中的策略。請檢視是否有非預期的範圍或過大的工作負載影響。",
    },
    "rpt_au_per_user_policy":{"en": "Changes by User",                   "zh_TW": "使用者變更統計"},
    "rpt_au_bp_policy": {
        "en": "<b>Illumio Best Practice:</b> Review rule_set and sec_rule changes for overly broad scopes (null HREF = All Applications/Environments/Locations). When sec_policy.create (provision) events occur, check workloads_affected — a high number may indicate unintended policy impact. Monitor sec_rule.delete events to detect unauthorized policy weakening.",
        "zh_TW": "<b>Illumio 最佳實踐：</b>審查 rule_set 和 sec_rule 變更是否範圍過大（null HREF = 所有應用程式/環境/位置）。當 sec_policy.create（部署）事件發生時，請檢查 workloads_affected — 數量過高可能表示非預期的策略影響。監控 sec_rule.delete 事件以偵測未經授權的策略弱化。",
    },

    # ── Policy Lifecycle concept explanation ─────────────────────────────────
    "rpt_au_lifecycle_title": {
        "en": "📘 Illumio Policy Lifecycle: Draft vs Provision",
        "zh_TW": "📘 Illumio 策略生命週期：草稿 vs 正式部署",
    },
    "rpt_au_lifecycle_draft_title": {
        "en": "1️⃣ Draft Changes (Not Yet Enforced)",
        "zh_TW": "1️⃣ 草稿變更（尚未生效）",
    },
    "rpt_au_lifecycle_draft_body": {
        "en": (
            "When an admin creates, edits, or deletes a rule in the PCE console <b>without clicking Provision</b>, "
            "the system logs <code>rule_set.*</code> and <code>sec_rule.*</code> events. "
            "These only represent changes to the policy <em>draft</em> — "
            "<b>no firewall rules have been pushed to any VEN yet.</b><br><br>"
            "⚠ <b>Watch for:</b> Broad scopes such as <em>All Applications / All Environments / All Locations</em> "
            "(displayed as <code>null</code> in the API). A draft with such scope, once provisioned, "
            "could affect a large number of workloads."
        ),
        "zh_TW": (
            "當管理員在 PCE 主控台中新增、修改或刪除規則，但<b>尚未點擊「Provision（部署）」</b>時，"
            "系統會記錄 <code>rule_set.*</code> 和 <code>sec_rule.*</code> 事件。"
            "這些事件僅代表策略<em>草稿</em>的變動 — "
            "<b>目前仍未有任何防火牆規則被推送至任何 VEN。</b><br><br>"
            "⚠ <b>注意：</b>草稿若範圍過大（如「所有應用程式 / 所有環境 / 所有位置」，API 顯示為 <code>null</code>），"
            "一旦部署，可能影響大量工作負載。"
        ),
    },
    "rpt_au_lifecycle_prov_title": {
        "en": "2️⃣ Provision — Policy Goes Live (sec_policy.create)",
        "zh_TW": "2️⃣ 正式部署 — 策略生效（sec_policy.create）",
    },
    "rpt_au_lifecycle_prov_body": {
        "en": (
            "When an admin clicks <b>Provision</b>, all draft changes are packaged into a new versioned policy "
            "and pushed to workload VENs. The PCE logs a <code>sec_policy.create</code> event — "
            "not <code>update</code>, because each provision creates a <em>new policy version</em>.<br><br>"
            "🔑 <b>Key field to check:</b> <code>workloads_affected</code> — "
            "this tells you exactly how many hosts received the new policy. "
            "A surprisingly large number signals that the provisioned rules may have an unexpectedly broad scope. "
            "<b>If this was not a planned large-scale change, investigate immediately.</b>"
        ),
        "zh_TW": (
            "當管理員點擊 <b>Provision（部署）</b>，所有草稿變更將被封裝成一個帶有唯一版本號的新策略，"
            "並推送至各工作負載的 VEN。PCE 記錄 <code>sec_policy.create</code> 事件 — "
            "而非 <code>update</code>，因為每次部署都會建立一個<em>全新的策略版本</em>。<br><br>"
            "🔑 <b>關鍵欄位：</b><code>workloads_affected</code> — "
            "明確記錄本次部署影響了幾台主機。"
            "若數字異常龐大，代表新策略的影響範圍超出預期。"
            "<b>如果這並非計畫中的大規模變更，請立即介入調查。</b>"
        ),
    },
    "rpt_au_draft_section":   {"en": "Draft Rule Changes",              "zh_TW": "草稿規則變更"},
    "rpt_au_draft_desc": {
        "en": "These events represent policy edits in draft state. No enforcement changes have occurred yet — they only take effect after Provision.",
        "zh_TW": "以下事件代表尚在草稿狀態的策略編輯。目前無任何執行變更 — 必須等到 Provision（部署）後才會生效。",
    },
    "rpt_au_workloads_affected": {"en": "Workloads Affected",           "zh_TW": "受影響工作負載數"},
    "rpt_au_high_impact_title": {
        "en": "🚨 High-Impact Provisions",
        "zh_TW": "🚨 高影響範圍部署",
    },
    "rpt_au_high_impact_desc": {
        "en": "The following provision events affected an unusually large number of workloads. Verify these were intended large-scale policy changes.",
        "zh_TW": "以下部署事件影響了異常大量的工作負載，請確認這些是預期中的大規模策略變更。",
    },
    "rpt_au_provision_impact_stat": {
        "en": "Total Workloads Affected (all provisions):",
        "zh_TW": "所有部署累計影響工作負載數：",
    },

    # ── Audit report — enhanced context labels ──────────────────────────────
    "rpt_au_unique_src_ips":    {"en": "Unique Admin IPs:",               "zh_TW": "不重複管理 IP："},
    "rpt_au_failed_detail":     {"en": "Failed Login Details",            "zh_TW": "登入失敗詳情"},
    "rpt_au_failed_detail_desc": {
        "en": "Enriched with source IP and notification context. Check for brute-force patterns or suspicious source IPs.",
        "zh_TW": "包含來源 IP 與通知上下文。請檢查暴力破解模式或可疑來源 IP。",
    },
    "rpt_au_src_ip_note": {
        "en": "<b>Source IP Tracking:</b> The <code>src_ip</code> column shows where the admin/API connected from. "
              "Multiple logins or policy changes from unexpected IPs may indicate compromised credentials or insider threats.",
        "zh_TW": "<b>來源 IP 追蹤：</b><code>src_ip</code> 欄位顯示管理員/API 的連線來源。"
              "若從非預期 IP 發起多次登入或策略變更，可能表示憑證遭竊或內部威脅。",
    },
    "rpt_au_change_detail_note": {
        "en": "<b>Change Tracking:</b> The <code>change_detail</code> column shows before → after values for "
              "modified resources. Look for changes to broad scopes (null = All) or sensitive labels (Production, PCI).",
        "zh_TW": "<b>變更追蹤：</b><code>change_detail</code> 欄位顯示修改前 → 修改後的值。"
              "注意範圍過大的變更（null = 全部）或涉及敏感標籤（Production、PCI）的修改。",
    },
    "rpt_au_footer":        {"en": "Illumio PCE Ops — Audit Report", "zh_TW": "Illumio PCE Ops — 稽核報表"},
    "rpt_au_attention_title": {"en": "⚠ Attention Required",         "zh_TW": "⚠ 需關注項目"},
    "rpt_au_actor":           {"en": "Actor",                         "zh_TW": "操作者"},
    "rpt_au_rec":             {"en": "Recommendation",                "zh_TW": "建議處理"},
    "rpt_au_risk_critical":   {"en": "CRITICAL",                      "zh_TW": "嚴重"},
    "rpt_au_risk_high":       {"en": "HIGH",                          "zh_TW": "高"},
    "rpt_au_risk_medium":     {"en": "MEDIUM",                        "zh_TW": "中"},
    "rpt_au_risk_low":        {"en": "LOW",                           "zh_TW": "低"},
    "rpt_au_risk_info":       {"en": "INFO",                          "zh_TW": "資訊"},
    "rpt_au_status":          {"en": "Status",                        "zh_TW": "狀態"},
    "rpt_au_high_risk":       {"en": "High-Risk Events",              "zh_TW": "高風險事件"},
    "rpt_au_no_attention":    {
        "en":    "No critical or high-risk events detected in this period.",
        "zh_TW": "本期間未發現嚴重或高風險事件。",
    },

    # ── VEN report ───────────────────────────────────────────────────────────
    "rpt_ven_title":          {"en": "Illumio VEN Status Inventory Report",
                               "zh_TW": "Illumio VEN 狀態盤點報表"},
    "rpt_ven_nav_summary":    {"en": "📊 Executive Summary",             "zh_TW": "📊 執行摘要"},
    "rpt_ven_nav_online":     {"en": "✅ Online VENs",                   "zh_TW": "✅ Online VEN"},
    "rpt_ven_nav_offline":    {"en": "❌ Offline VENs",                  "zh_TW": "❌ Offline VEN"},
    "rpt_ven_nav_lost_today": {"en": "🔴 Lost Today (<24h)",             "zh_TW": "🔴 今日失聯 (<24h)"},
    "rpt_ven_nav_lost_yest":  {"en": "🟠 Lost Yesterday",                "zh_TW": "🟠 昨日失聯"},
    "rpt_ven_sec_online":     {"en": "✅ Online VENs",                   "zh_TW": "✅ Online VEN"},
    "rpt_ven_sec_offline":    {"en": "❌ Offline VENs",                  "zh_TW": "❌ Offline VEN"},
    "rpt_ven_sec_lost_today": {"en": "🔴 Lost Connection in Last 24h",   "zh_TW": "🔴 近 24 小時內失聯"},
    "rpt_ven_sec_lost_yest":  {"en": "🟠 Lost Connection 24–48h Ago",    "zh_TW": "🟠 24–48 小時前失聯"},
    "rpt_ven_desc_today":     {
        "en": "VENs currently offline whose last heartbeat was within the past 24 hours.",
        "zh_TW": "目前離線且最後一次心跳在過去 24 小時內的 VEN。",
    },
    "rpt_ven_desc_yest": {
        "en": "VENs currently offline whose last heartbeat was 24–48 hours ago.",
        "zh_TW": "目前離線且最後一次心跳在 24–48 小時前的 VEN。",
    },
    "rpt_ven_footer": {
        "en": "Illumio PCE Ops — VEN Status Report",
        "zh_TW": "Illumio PCE Ops — VEN 狀態報表",
    },

    # ── Policy Usage Report ───────────────────────────────────────────────────
    "rpt_pu_title":         {"en": "Illumio Policy Usage Report",       "zh_TW": "Illumio 策略使用率報表"},
    "rpt_pu_nav_summary":   {"en": "📊 Executive Summary",              "zh_TW": "📊 執行摘要"},
    "rpt_pu_nav_overview":  {"en": "1 Usage Overview",                  "zh_TW": "1 使用率總覽"},
    "rpt_pu_nav_hit":       {"en": "2 Hit Rules",                       "zh_TW": "2 已命中規則"},
    "rpt_pu_nav_unused":    {"en": "3 Unused Rules",                    "zh_TW": "3 未使用規則"},
    "rpt_pu_sec_overview":  {"en": "1 · Policy Usage Overview",         "zh_TW": "1 · 策略使用率總覽"},
    "rpt_pu_sec_hit":       {"en": "2 · Hit Rules Detail",              "zh_TW": "2 · 已命中規則明細"},
    "rpt_pu_sec_unused":    {"en": "3 · Unused Rules Detail",           "zh_TW": "3 · 未使用規則明細"},
    "rpt_pu_footer":        {"en": "Illumio PCE Ops — Policy Usage Report", "zh_TW": "Illumio PCE Ops — 策略使用率報表"},
    "rpt_pu_total_rules":   {"en": "Total Active Rules",                "zh_TW": "有效規則總數"},
    "rpt_pu_hit_rules":     {"en": "Hit Rules",                         "zh_TW": "已命中規則"},
    "rpt_pu_unused_rules":  {"en": "Unused Rules",                      "zh_TW": "未使用規則"},
    "rpt_pu_hit_rate":      {"en": "Hit Rate",                          "zh_TW": "命中率"},
    "rpt_pu_lookback":      {"en": "Lookback Period",                   "zh_TW": "回溯期間"},
    "rpt_pu_attention":     {"en": "Top Rulesets by Unused Rules",      "zh_TW": "未使用規則最多的規則集"},
    "rpt_pu_caveat_title":  {"en": "⚠ Retention Period Caveat",         "zh_TW": "⚠ 流量保留期限說明"},
    "rpt_pu_caveat_body": {
        "en":    "Rules with zero traffic hits in the analysed period. "
                 "This classification is limited by the PCE traffic retention period — "
                 "a rule that had hits before the lookback window will appear as unused. "
                 "Review carefully before removing any rule.",
        "zh_TW": "未使用的判定受限於 PCE 流量保留期限。"
                 "在回溯期間之前命中的規則將顯示為未使用。"
                 "刪除任何規則前請務必謹慎評估。",
    },
    "rpt_pu_no_hit_rules":    {"en": "No rules were hit during this period.", "zh_TW": "此期間沒有任何規則被命中。"},
    "rpt_pu_no_unused_rules": {"en": "All rules had traffic hits — no unused rules found.", "zh_TW": "所有規則均有流量命中，沒有未使用規則。"},

    # ── VEN Status Report column headers ─────────────────────────────────────
    "rpt_col_ip":              {"en": "IP",              "zh_TW": "IP 位址"},
    "rpt_col_labels":         {"en": "Labels",           "zh_TW": "標籤"},
    "rpt_col_policy_sync":    {"en": "Policy Sync",      "zh_TW": "策略同步"},
    "rpt_col_last_heartbeat": {"en": "Last Heartbeat",   "zh_TW": "最後心跳"},
    "rpt_col_policy_received":{"en": "Policy Received",  "zh_TW": "策略更新時間"},
    "rpt_col_paired_at":      {"en": "Paired At",        "zh_TW": "配對時間"},
    "rpt_col_ven_version":    {"en": "VEN Version",      "zh_TW": "VEN 版本"},

    # ── Policy Usage column headers ───────────────────────────────────────────
    "rpt_col_rule_no":     {"en": "No",           "zh_TW": "No"},
    "rpt_col_rule_name":   {"en": "Rule ID",     "zh_TW": "規則 ID"},
    "rpt_col_description": {"en": "Description", "zh_TW": "描述"},
    "rpt_col_ruleset":     {"en": "Ruleset",      "zh_TW": "規則集"},
    "rpt_col_providers":   {"en": "Destination",  "zh_TW": "目的"},
    "rpt_col_consumers":   {"en": "Source",       "zh_TW": "來源"},
    "rpt_col_hit_count":   {"en": "Hit Count",    "zh_TW": "命中次數"},
    "rpt_col_created_at":  {"en": "Created At",   "zh_TW": "建立時間"},
    "rpt_col_status":      {"en": "Status",       "zh_TW": "狀態"},
    "rpt_col_percentage":  {"en": "Percentage",   "zh_TW": "佔比"},

    # ── Column header translations (used by _df_to_html) ──────────────────────
    "rpt_col_port":               {"en": "Port",                "zh_TW": "通訊埠"},
    "rpt_col_protocol":           {"en": "Protocol",            "zh_TW": "協定"},
    "rpt_col_proto":              {"en": "Proto",               "zh_TW": "協定"},
    "rpt_col_connections":        {"en": "Connections",         "zh_TW": "連線數"},
    "rpt_col_flow_count":         {"en": "Flow Count",          "zh_TW": "流量筆數"},
    "rpt_col_flows":              {"en": "Flows",               "zh_TW": "流量筆數"},
    "rpt_col_decision":           {"en": "Decision",            "zh_TW": "策略判定"},
    "rpt_col_risk_level":         {"en": "Risk Level",          "zh_TW": "風險等級"},
    "rpt_col_service":            {"en": "Service",             "zh_TW": "服務"},
    "rpt_col_services":           {"en": "Services",            "zh_TW": "服務"},
    "rpt_col_control":            {"en": "Control",             "zh_TW": "管控狀態"},
    "rpt_col_total_flows":        {"en": "Total Flows",         "zh_TW": "總流量"},
    "rpt_col_allowed":            {"en": "Allowed",             "zh_TW": "允許"},
    "rpt_col_blocked":            {"en": "Blocked",             "zh_TW": "阻斷"},
    "rpt_col_potentially_blocked": {"en": "Potentially Blocked", "zh_TW": "潛在阻斷"},
    "rpt_col_pct_of_total":       {"en": "% of Total",          "zh_TW": "佔比 %"},
    "rpt_col_inbound":            {"en": "Inbound",             "zh_TW": "入站"},
    "rpt_col_outbound":           {"en": "Outbound",            "zh_TW": "出站"},
    "rpt_col_coverage_pct":       {"en": "Coverage %",          "zh_TW": "覆蓋率 %"},
    "rpt_col_gap_pct":            {"en": "Gap %",               "zh_TW": "缺口 %"},
    "rpt_col_category":           {"en": "Category",            "zh_TW": "分類"},
    "rpt_col_recommendation":     {"en": "Recommendation",      "zh_TW": "建議"},
    "rpt_col_flow":               {"en": "Flow",                "zh_TW": "流量"},
    "rpt_col_flow_app":           {"en": "Flow (src_app→dst_app)", "zh_TW": "流量 (來源→目標應用)"},
    "rpt_col_unique_ports":       {"en": "Unique Ports",        "zh_TW": "不重複通訊埠"},
    "rpt_col_unique_dst_hosts":   {"en": "Unique Dst Hosts",    "zh_TW": "不重複目標主機"},
    "rpt_col_unique_src_ips":     {"en": "Unique Src IPs",      "zh_TW": "不重複來源 IP"},
    "rpt_col_unique_dst_ips":     {"en": "Unique Dst IPs",      "zh_TW": "不重複目標 IP"},
    "rpt_col_unique_src":         {"en": "Unique Src",          "zh_TW": "不重複來源"},
    "rpt_col_unique_dst":         {"en": "Unique Dst",          "zh_TW": "不重複目標"},
    "rpt_col_unique_destinations": {"en": "Unique Destinations", "zh_TW": "不重複目標數"},
    "rpt_col_unique_sources":     {"en": "Unique Sources",      "zh_TW": "不重複來源數"},
    "rpt_col_unique_risk_ports":  {"en": "Unique Risk Ports",   "zh_TW": "不重複風險通訊埠"},
    "rpt_col_unique_source_apps": {"en": "Unique Source Apps",  "zh_TW": "不重複來源應用"},
    "rpt_col_unique_unmanaged_src": {"en": "Unique Unmanaged Src", "zh_TW": "不重複非受管來源"},
    "rpt_col_unique_unmanaged_sources": {"en": "Unique Unmanaged Sources", "zh_TW": "不重複非受管來源"},
    "rpt_col_destination_ip":     {"en": "Destination IP",      "zh_TW": "目標 IP"},
    "rpt_col_destination_app":    {"en": "Destination App",     "zh_TW": "目標應用"},
    "rpt_col_destination":        {"en": "Destination",         "zh_TW": "目標"},
    "rpt_col_target_ip":          {"en": "Target IP",           "zh_TW": "目標 IP"},
    "rpt_col_exposed_ports":      {"en": "Exposed Ports",       "zh_TW": "暴露通訊埠"},
    "rpt_col_exposed_services":   {"en": "Exposed Services",    "zh_TW": "暴露服務"},
    "rpt_col_allowed_flows":      {"en": "Allowed Flows",       "zh_TW": "允許流量"},
    "rpt_col_uncovered_flows":    {"en": "Uncovered Flows",     "zh_TW": "未覆蓋流量"},
    "rpt_col_source_ip":          {"en": "Source IP",           "zh_TW": "來源 IP"},
    "rpt_col_src_ip":             {"en": "Src IP",              "zh_TW": "來源 IP"},
    "rpt_col_dst_ip":             {"en": "Dst IP",              "zh_TW": "目標 IP"},
    "rpt_col_src_host":           {"en": "Src Host",            "zh_TW": "來源主機"},
    "rpt_col_dst_host":           {"en": "Dst Host",            "zh_TW": "目標主機"},
    "rpt_col_hostname":           {"en": "Hostname",            "zh_TW": "主機名稱"},
    "rpt_col_host_pair":          {"en": "Host Pair",           "zh_TW": "主機配對"},
    "rpt_col_user_name":          {"en": "User Name",           "zh_TW": "使用者名稱"},
    "rpt_col_process":            {"en": "Process",             "zh_TW": "程序"},
    "rpt_col_bytes":              {"en": "Bytes",               "zh_TW": "位元組"},
    "rpt_col_bytes_total":        {"en": "Bytes Total",         "zh_TW": "位元組總量"},
    "rpt_col_total_bytes":        {"en": "Total Bytes",         "zh_TW": "總位元組"},
    "rpt_col_bytes_conn":         {"en": "Bytes/Conn",          "zh_TW": "位元組/連線"},
    "rpt_col_bandwidth_mbps":     {"en": "Bandwidth (Mbps)",    "zh_TW": "頻寬 (Mbps)"},
    "rpt_col_source_app":         {"en": "Source App",          "zh_TW": "來源應用"},
    "rpt_col_source_env":         {"en": "Source Env",          "zh_TW": "來源環境"},
    "rpt_col_enforcement_mode":   {"en": "Enforcement Mode",    "zh_TW": "執行模式"},
    "rpt_col_decision_types":     {"en": "Decision Types",      "zh_TW": "判定類型"},
    "rpt_col_dst_apps":           {"en": "Dst Apps",            "zh_TW": "目標應用"},
    "rpt_col_unmanaged_source_ip": {"en": "Unmanaged Source IP", "zh_TW": "非受管來源 IP"},
    "rpt_col_unmanaged_dst_ip":   {"en": "Unmanaged Dst IP",    "zh_TW": "非受管目標 IP"},
    "rpt_col_unmanaged_source":   {"en": "Unmanaged Source",    "zh_TW": "非受管來源"},
    "rpt_col_managed_dest_ip":    {"en": "Managed Destination IP", "zh_TW": "受管目標 IP"},
    "rpt_col_conn_from_unmanaged": {"en": "Connections from Unmanaged Src", "zh_TW": "來自非受管來源連線數"},
    "rpt_col_event_type":              {"en": "Event Type",             "zh_TW": "事件類型"},
    "rpt_col_count":                   {"en": "Count",                  "zh_TW": "數量"},
    "rpt_col_status":                  {"en": "Status",                 "zh_TW": "狀態"},
    "rpt_col_workloads_affected":      {"en": "Workloads Affected",     "zh_TW": "受影響工作負載數"},
    "rpt_col_src_ip":                  {"en": "Source IP",              "zh_TW": "來源 IP"},
    "rpt_col_change_detail":           {"en": "Change Detail",          "zh_TW": "變更明細"},
    "rpt_col_api_method":              {"en": "API Method",             "zh_TW": "API 方法"},
    "rpt_col_agent_hostname":          {"en": "Agent Host",             "zh_TW": "Agent 主機"},
    "rpt_col_notification_detail":     {"en": "Details",                "zh_TW": "詳細資訊"},
    "rpt_col_source_ips":              {"en": "Source IPs",             "zh_TW": "來源 IP 數"},

    # ── Dynamic column headers (cross-label matrix, traffic distribution) ─────
    "rpt_col_src_env":            {"en": "Src Env",             "zh_TW": "來源環境"},
    "rpt_col_dst_env":            {"en": "Dst Env",             "zh_TW": "目標環境"},
    "rpt_col_src_app":            {"en": "Src App",             "zh_TW": "來源應用"},
    "rpt_col_dst_app":            {"en": "Dst App",             "zh_TW": "目標應用"},
    "rpt_col_src_role":           {"en": "Src Role",            "zh_TW": "來源角色"},
    "rpt_col_dst_role":           {"en": "Dst Role",            "zh_TW": "目標角色"},
    "rpt_col_src_loc":            {"en": "Src Loc",             "zh_TW": "來源位置"},
    "rpt_col_dst_loc":            {"en": "Dst Loc",             "zh_TW": "目標位置"},

    # ── Module subtitles missing data-i18n ────────────────────────────────────
    # Module 2 (Policy Decisions)
    "rpt_tr_port_coverage":       {"en": "Per-Port Coverage",                       "zh_TW": "各通訊埠覆蓋率"},
    "rpt_tr_top_inbound_ports":   {"en": "Top Inbound Ports",                      "zh_TW": "主要入站通訊埠"},
    "rpt_tr_top_outbound_ports":  {"en": "Top Outbound Ports",                     "zh_TW": "主要出站通訊埠"},
    # Module 3 (Uncovered Flows)
    "rpt_tr_overall_coverage":    {"en": "Overall Coverage",                        "zh_TW": "整體覆蓋率"},
    "rpt_tr_inbound_coverage":    {"en": "Inbound Coverage",                        "zh_TW": "入站覆蓋率"},
    "rpt_tr_outbound_coverage":   {"en": "Outbound Coverage",                       "zh_TW": "出站覆蓋率"},
    # Module 7 (Cross-Label Matrix)
    "rpt_tr_same_value":          {"en": "Same-value:",                             "zh_TW": "同值："},
    "rpt_tr_cross_value":         {"en": "Cross-value:",                            "zh_TW": "跨值："},
    # Module 8 (Unmanaged Hosts)
    "rpt_tr_unmanaged_flow_stat": {"en": "Unmanaged Flows",                         "zh_TW": "非受管流量"},
    "rpt_tr_unique_unmanaged_src": {"en": "Unique Unmanaged Src",                   "zh_TW": "不重複非受管來源"},
    "rpt_tr_unique_unmanaged_dst": {"en": "Unique Unmanaged Dst",                   "zh_TW": "不重複非受管目標"},
    "rpt_tr_managed_apps_unmanaged": {"en": "Managed Apps Receiving Unmanaged Traffic", "zh_TW": "接收非受管流量的受管應用"},
    "rpt_tr_exposed_ports_proto": {"en": "Exposed Ports / Protocols",               "zh_TW": "暴露通訊埠 / 協定"},
    "rpt_tr_unmanaged_src_port":  {"en": "Unmanaged Source × Port Detail",          "zh_TW": "非受管來源 × 通訊埠明細"},
    "rpt_tr_managed_targeted":    {"en": "Managed Hosts Targeted by Unmanaged Sources", "zh_TW": "被非受管來源存取的受管主機"},
    # Module 11 (Bandwidth)
    "rpt_tr_p95_bw":              {"en": "P95 Bandwidth",                           "zh_TW": "P95 頻寬"},
    # Module 13 (Enforcement Readiness)
    "rpt_tr_nav_readiness":       {"en": "13 Enforcement Readiness",                "zh_TW": "13 執行就緒度"},
    "rpt_tr_sec_readiness":       {"en": "13 · Enforcement Readiness",              "zh_TW": "13 · 執行就緒度"},
    "rpt_tr_readiness_score":     {"en": "Enforcement Readiness Score:",             "zh_TW": "執行就緒度分數："},
    "rpt_tr_score_breakdown":     {"en": "Score Breakdown by Factor",               "zh_TW": "各因素分數明細"},
    "rpt_tr_remediation_rec":     {"en": "Remediation Recommendations",             "zh_TW": "改善建議"},
    # Module 14 (Infrastructure Scoring)
    "rpt_tr_nav_infrastructure":  {"en": "14 Infrastructure Scoring",               "zh_TW": "14 基礎架構評分"},
    "rpt_tr_sec_infrastructure":  {"en": "14 · Infrastructure Scoring",             "zh_TW": "14 · 基礎架構評分"},
    "rpt_tr_apps_analysed":       {"en": "Applications analysed:",                   "zh_TW": "分析應用程式數："},
    "rpt_tr_comm_edges":          {"en": "Communication edges:",                     "zh_TW": "通訊連結數："},
    "rpt_tr_role_distribution":   {"en": "Role Distribution",                        "zh_TW": "角色分佈"},
    "rpt_tr_hub_apps":            {"en": "Hub Applications (High Blast Radius)",     "zh_TW": "樞紐應用程式（高爆炸半徑）"},
    "rpt_tr_top_apps_infra":      {"en": "Top Applications by Infrastructure Score", "zh_TW": "基礎架構評分最高應用程式"},
    "rpt_tr_top_comm_paths":      {"en": "Top Communication Paths (by Volume)",      "zh_TW": "最大通訊路徑（依流量）"},
    # Module 15 (Lateral Movement)
    "rpt_tr_nav_lateral":         {"en": "15 Lateral Movement",                      "zh_TW": "15 橫向移動"},
    "rpt_tr_sec_lateral":         {"en": "15 · Lateral Movement",                    "zh_TW": "15 · 橫向移動"},
    "rpt_tr_lateral_flows":       {"en": "Lateral movement port flows:",             "zh_TW": "橫向移動通訊埠流量："},
    "rpt_tr_lateral_pct":         {"en": "of all flows",                             "zh_TW": "佔總流量"},
    "rpt_tr_lateral_by_service":  {"en": "Lateral Port Activity by Service",         "zh_TW": "各服務橫向通訊埠活動"},
    "rpt_tr_fan_out":             {"en": "Fan-out Sources (Potential Scanner / Worm)", "zh_TW": "扇出來源（疑似掃描器/蠕蟲）"},
    "rpt_tr_allowed_lateral":     {"en": "Explicitly Allowed Lateral Flows (Highest Risk)", "zh_TW": "明確允許的橫向流量（最高風險）"},
    "rpt_tr_top_risk_sources":    {"en": "Top High-Risk Sources",                    "zh_TW": "最高風險來源"},
    "rpt_tr_app_chains":          {"en": "Lateral Movement App Chains (BFS Paths)",  "zh_TW": "橫向移動應用鏈（BFS 路徑）"},

    # ── Email template strings ────────────────────────────────────────────────
    "rpt_email_traffic_subject":  {"en": "Illumio Traffic Flow Report",              "zh_TW": "Illumio 流量分析報表"},
    "rpt_email_audit_subject":    {"en": "Illumio Audit & System Events Report",     "zh_TW": "Illumio 稽核與系統事件報表"},
    "rpt_email_ven_subject":         {"en": "Illumio VEN Status Report",                  "zh_TW": "Illumio VEN 狀態報表"},
    "rpt_email_policy_usage_subject": {"en": "Illumio Policy Usage Report",              "zh_TW": "Illumio 策略使用率報表"},
    "rpt_email_no_findings":      {"en": "No findings.",                             "zh_TW": "無發現項目。"},
    "rpt_email_footer":           {"en": "Full report attached as HTML file. · Illumio PCE Ops", "zh_TW": "完整報表已附加為 HTML 檔案。· Illumio PCE Ops"},
}


def make_i18n_js() -> str:
    """Return a self-contained <script> block with the full i18n logic."""
    strings_json = json.dumps(STRINGS, ensure_ascii=False, indent=2)
    return f"""<script>
(function(){{
  var _T = {strings_json};
  var _lang = localStorage.getItem('illumioReportLang') || 'zh_TW';
  function applyI18n() {{
    document.querySelectorAll('[data-i18n]').forEach(function(el) {{
      var k = el.getAttribute('data-i18n');
      if (_T[k] && _T[k][_lang]) el.textContent = _T[k][_lang];
    }});
    document.querySelectorAll('[data-i18n-html]').forEach(function(el) {{
      var k = el.getAttribute('data-i18n-html');
      if (_T[k] && _T[k][_lang]) el.innerHTML = _T[k][_lang];
    }});
    var btn = document.getElementById('_langBtn');
    if (btn) btn.textContent = _lang === 'zh_TW' ? 'EN' : '中文';
  }}
  window._toggleReportLang = function() {{
    _lang = _lang === 'zh_TW' ? 'en' : 'zh_TW';
    localStorage.setItem('illumioReportLang', _lang);
    applyI18n();
  }};
  document.addEventListener('DOMContentLoaded', applyI18n);
}})();
</script>"""


# ── Column name → i18n key mapping (shared by all HTML exporters) ────────────
# Auto-built from STRINGS: any key starting with "rpt_col_" maps its English
# value to the key.  E.g. "Port" → "rpt_col_port"
COL_I18N: dict[str, str] = {
    v.get("en", ""): k
    for k, v in STRINGS.items()
    if k.startswith("rpt_col_") and v.get("en")
}


def lang_btn_html() -> str:
    """Return the fixed-position language-toggle button HTML."""
    return (
        '<button id="_langBtn" onclick="_toggleReportLang()" '
        'style="position:fixed;top:10px;right:12px;z-index:999;padding:4px 10px;'
        'background:#2b6cb0;color:white;border:none;border-radius:4px;'
        'cursor:pointer;font-size:12px;">中文</button>'
    )
