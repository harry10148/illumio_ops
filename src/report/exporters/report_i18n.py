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
    "rpt_tr_footer":          {"en": "Illumio PCE Monitor — Traffic Flow Report",
                               "zh_TW": "Illumio PCE Monitor — 流量分析報表"},

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
    "rpt_au_total_health":  {"en": "Total Health Events:",               "zh_TW": "系統健康事件總數："},
    "rpt_au_summary_type":  {"en": "Summary by Event Type",              "zh_TW": "依事件類型摘要"},
    "rpt_au_recent":        {"en": "Recent Events (up to 50)",           "zh_TW": "最近事件（最多 50 筆）"},
    "rpt_au_total_user":    {"en": "Total User Events:",                 "zh_TW": "使用者事件總數："},
    "rpt_au_failed_logins": {"en": "Failed Logins:",                     "zh_TW": "登入失敗次數："},
    "rpt_au_total_policy":  {"en": "Total Policy Events:",               "zh_TW": "策略事件總數："},
    "rpt_au_footer":        {"en": "Illumio PCE Monitor — Audit Report", "zh_TW": "Illumio PCE Monitor — 稽核報表"},

    # ── VEN report ───────────────────────────────────────────────────────────
    "rpt_ven_title":          {"en": "Illumio VEN Status Inventory Report",
                               "zh_TW": "Illumio VEN 狀態盤點報表"},
    "rpt_ven_nav_summary":    {"en": "📊 Executive Summary",             "zh_TW": "📊 執行摘要"},
    "rpt_ven_nav_online":     {"en": "✅ Online VENs",                   "zh_TW": "✅ 在線 VEN"},
    "rpt_ven_nav_offline":    {"en": "❌ Offline VENs",                  "zh_TW": "❌ 離線 VEN"},
    "rpt_ven_nav_lost_today": {"en": "🔴 Lost Today (<24h)",             "zh_TW": "🔴 今日失聯 (<24h)"},
    "rpt_ven_nav_lost_yest":  {"en": "🟠 Lost Yesterday",                "zh_TW": "🟠 昨日失聯"},
    "rpt_ven_sec_online":     {"en": "✅ Online VENs",                   "zh_TW": "✅ 在線 VEN"},
    "rpt_ven_sec_offline":    {"en": "❌ Offline VENs",                  "zh_TW": "❌ 離線 VEN"},
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
        "en": "Illumio PCE Monitor — VEN Status Report",
        "zh_TW": "Illumio PCE Monitor — VEN 狀態報表",
    },
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


def lang_btn_html() -> str:
    """Return the fixed-position language-toggle button HTML."""
    return (
        '<button id="_langBtn" onclick="_toggleReportLang()" '
        'style="position:fixed;top:10px;right:12px;z-index:999;padding:4px 10px;'
        'background:#2b6cb0;color:white;border:none;border-radius:4px;'
        'cursor:pointer;font-size:12px;">中文</button>'
    )
