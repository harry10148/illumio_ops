from __future__ import annotations

import json
import re
import threading
from functools import lru_cache
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_EN_MESSAGES_PATH = _ROOT / "i18n_en.json"
_ZH_MESSAGES_PATH = _ROOT / "i18n_zh_TW.json"


class _I18nState:
    """Thread-safe singleton for the active language code."""

    _VALID = frozenset({"en", "zh_TW"})

    def __init__(self, initial: str = "en") -> None:
        self._lock = threading.Lock()
        self._lang = initial

    def get_language(self) -> str:
        with self._lock:
            return self._lang

    def set_language(self, lang: str) -> None:
        if lang in self._VALID:
            with self._lock:
                self._lang = lang


_I18N_STATE = _I18nState("en")


def set_language(lang: str) -> None:
    """Set the active UI language (thread-safe). Public API."""
    _I18N_STATE.set_language(lang)


def get_language() -> str:
    """Return the active UI language code (thread-safe). Public API."""
    return _I18N_STATE.get_language()

def _entry(en: str, zh_tw: str | None = None) -> tuple[str, str]:
    return en, zh_tw or en

def _load_en_messages() -> dict[str, str]:
    try:
        return json.loads(_EN_MESSAGES_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _load_zh_messages() -> dict[str, str]:
    try:
        return json.loads(_ZH_MESSAGES_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}

EN_MESSAGES = _load_en_messages()
ZH_MESSAGES = _load_zh_messages()
_PLACEHOLDER_VALUE_RE = re.compile(r"^(?:Rpt|GUI|Gui|Sched)\b")
_STRICT_PREFIXES = (
    "gui_", "sched_", "rs_", "wgs_", "login_", "cli_", "main_",
    "settings_", "rpt_", "menu_", "ven_", "pu_", "report_",
    "error_", "alert_", "daemon_", "line_", "mail_", "webhook_",
    "event_", "confirm_", "select_", "step_", "metric_", "pd_",
    "filter_", "ex_", "rule_", "trigger_", "pill_",
)


def _is_strict_surface_key(key: str) -> bool:
    # Event catalog labels/categories are generated from vendor event ids and
    # rely on humanized fallback when explicit dictionary keys are absent.
    if key.startswith("event_label_") or key.startswith("cat_"):
        return False
    return key.startswith(_STRICT_PREFIXES)


def _missing_marker(key: str) -> str:
    return f"[MISSING:{key}]"


def _load_json_data(filename: str) -> dict[str, str]:
    """Load a JSON-encoded dict from src/i18n/data/<filename>."""
    path = Path(__file__).parent / "data" / filename
    return json.loads(path.read_text(encoding="utf-8"))


_ZH_EXPLICIT: dict[str, str] = _load_json_data("zh_explicit.json")

_SKIP_TOKENS = {
    "gui", "cli", "lbl", "opt", "th", "nav", "wiz", "menu", "main",
    "msg", "col", "tab", "sec", "event",
}

_TOKEN_MAP_EN = {
    "rpt": "Report",
    "tr": "Traffic",
    "au": "Audit",
    "rs": "Ruleset",
    "pu": "Policy Usage",
    "ven": "VEN",
    "bw": "Bandwidth",
    "pd": "Policy Decision",
    "ws": "Workload",
    "ta": "Traffic Analysis",
    "ml": "Module Log",
    "smtp": "SMTP",
    "ssl": "SSL",
    "api": "API",
    "csv": "CSV",
    "url": "URL",
    "ip": "IP",
    "ips": "IPs",
    "id": "ID",
    "tcp": "TCP",
    "udp": "UDP",
    "pce": "PCE",
    "kpi": "KPI",
    "btn": "Button",
    "ev": "Event",
    "access": "Access",
    "agent": "Agent",
    "authentication": "Authentication",
    "authorization": "Authorization",
    "boundary": "Boundary",
    "bulk": "Bulk",
    "cluster": "Cluster",
    "clone": "Clone",
    "conditions": "Conditions",
    "connection": "Connection",
    "container": "Container",
    "containers": "Containers",
    "create": "Create",
    "delete": "Delete",
    "device": "Device",
    "domain": "Domain",
    "endpoint": "Endpoint",
    "enforcement": "Enforcement",
    "existing": "Existing",
    "firewall": "Firewall",
    "found": "Found",
    "generate": "Generate",
    "group": "Group",
    "heartbeat": "Heartbeat",
    "heartbeats": "Heartbeats",
    "href": "Href",
    "identifier": "Identifier",
    "interactive": "Interactive",
    "interface": "Interface",
    "interfaces": "Interfaces",
    "iptables": "IPTables",
    "lost": "Lost",
    "machine": "Machine",
    "map": "Map",
    "maintenance": "Maintenance",
    "network": "Network",
    "offline": "Offline",
    "operations": "Operations",
    "pending": "Pending",
    "policy": "Policy",
    "profile": "Profile",
    "principal": "Principal",
    "principals": "Principals",
    "proxy": "Proxy",
    "refresh": "Refresh",
    "release": "Release",
    "releases": "Releases",
    "remove": "Remove",
    "reguest": "Request",
    "report": "Report",
    "reports": "Reports",
    "restriction": "Restriction",
    "running": "Running",
    "request": "Request",
    "resource": "Resource",
    "restore": "Restore",
    "session": "Session",
    "security": "Security",
    "service": "Service",
    "services": "Services",
    "settings": "Settings",
    "software": "Software",
    "support": "Support",
    "suspend": "Suspend",
    "table": "Table",
    "tables": "Tables",
    "tampering": "Tampering",
    "tenants": "Tenants",
    "token": "Token",
    "unpair": "Unpair",
    "unsuspend": "Unsuspend",
    "update": "Update",
    "upgrade": "Upgrade",
    "upload": "Upload",
    "users": "Users",
    "version": "Version",
    "verify": "Verify",
    "binding": "Binding",
    "bindings": "Bindings",
    "account": "Account",
    "acks": "Acks",
    "applied": "Applied",
    "deploy": "Deploy",
    "key": "Key",
    "keys": "Keys",
    "workload": "Workload",
    "workloads": "Workloads",
    "rule": "Rule",
    "label": "Label",
    "labels": "Labels",
}

_TOKEN_MAP_ZH = {
    "rs": "Ruleset",
    "pu": "Policy 使用",
    "ven": "VEN",
    "bw": "頻寬",
    "pd": "Policy 判定",
    "ws": "Workload",
    "ta": "Traffic Analysis",
    "ml": "模組日誌",
    "smtp": "SMTP",
    "ssl": "SSL",
    "api": "API",
    "csv": "CSV",
    "url": "URL",
    "ip": "IP",
    "ips": "IP",
    "id": "ID",
    "tcp": "TCP",
    "udp": "UDP",
    "pce": "PCE",
    "access": "存取",
    "agent": "Agent",
    "authentication": "驗證",
    "authorization": "授權",
    "boundary": "邊界",
    "bulk": "批次",
    "cluster": "叢集",
    "clone": "複製",
    "conditions": "條件",
    "clear": "清除",
    "connection": "連線",
    "container": "容器",
    "containers": "容器",
    "create": "建立",
    "delete": "刪除",
    "device": "裝置",
    "domain": "網域",
    "endpoint": "端點",
    "enforcement": "Enforcement",  # glossary whitelist
    "existing": "既有",
    "firewall": "防火牆",
    "generate": "產生",
    "group": "群組",
    "found": "找回",
    "heartbeat": "心跳",
    "heartbeats": "心跳",
    "href": "連結",
    "identifier": "識別碼",
    "interactive": "互動",
    "interface": "介面",
    "interfaces": "介面",
    "iptables": "iptables",
    "lost": "遺失",
    "machine": "主機",
    "map": "對照",
    "maintenance": "維護",
    "offline": "離線",
    "operations": "操作",
    "pending": "待處理",
    "profile": "設定檔",
    "principal": "主體",
    "principals": "主體",
    "proxy": "代理",
    "refresh": "更新",
    "release": "版本",
    "releases": "版本",
    "remove": "移除",
    "reguest": "請求",
    "report": "報表",
    "reports": "報表",
    "restriction": "限制",
    "running": "執行中",
    "request": "請求",
    "resource": "資源",
    "restore": "還原",
    "session": "工作階段",
    "security": "安全",
    "service": "Service",  # glossary whitelist
    "services": "Services",  # glossary whitelist
    "settings": "設定",
    "software": "軟體",
    "support": "支援",
    "suspend": "暫停",
    "table": "表",
    "tables": "表",
    "tampering": "遭竄改",
    "tenants": "租戶",
    "token": "權杖",
    "unpair": "解除配對",
    "unsuspend": "解除暫停",
    "update": "更新",
    "upgrade": "升級",
    "upload": "上傳",
    "users": "使用者",
    "version": "版本",
    "verify": "驗證",
    "binding": "綁定",
    "bindings": "綁定",
    "account": "帳號",
    "acks": "確認",
    "applied": "已套用",
    "deploy": "部署",
    "key": "鍵值",
    "keys": "鍵值",
    "workload": "Workload",  # glossary whitelist
    "rule": "規則",
    "add": "新增",
    "action": "操作",
    "actions": "操作",
    "active": "啟用中",
    "actor": "操作者",
    "alert": "告警",
    "alerts": "告警",
    "all": "全部",
    "allowed": "Allowed",
    "any": "任一端",
    "apply": "套用",
    "audit": "稽核",
    "auth": "驗證",
    "back": "返回",
    "best": "Best",
    "practices": "Practices",
    "blocked": "Blocked",
    "browse": "瀏覽",
    "btn": "",
    "cancel": "取消",
    "category": "分類",
    "change": "變更",
    "check": "檢查",
    "clear": "清除",
    "completed": "完成",
    "condition": "條件",
    "confirm": "確認",
    "connections": "連線數",
    "cooldown": "Cooldown",
    "count": "數量",
    "coverage": "覆蓋率",
    "created": "建立",
    "current": "目前",
    "daily": "每日",
    "dashboard": "總覽",
    "date": "日期",
    "day": "天",
    "days": "天",
    "debug": "除錯",
    "decision": "判定",
    "delete": "刪除",
    "deleted": "已刪除",
    "density": "密度",
    "desc": "描述",
    "description": "描述",
    "dest": "目的端",
    "details": "詳細資訊",
    "disable": "停用",
    "disabled": "已停用",
    "download": "下載",
    "dst": "目的端",
    "edit": "編輯",
    "email": "Email",
    "empty": "空白",
    "enable": "啟用",
    "enabled": "已啟用",
    "end": "結束",
    "error": "錯誤",
    "event": "事件",
    "events": "事件",
    "ex": "排除",
    "exclude": "排除",
    "excludes": "排除條件",
    "failed": "失敗",
    "fetching": "取資料中",
    "file": "檔案",
    "filename": "檔名",
    "files": "檔案",
    "filter": "篩選",
    "filters": "篩選",
    "first": "首次",
    "flow": "Flow",
    "flows": "Flows",
    "format": "格式",
    "found": "找到",
    "freq": "頻率",
    "frequency": "頻率",
    "gen": "產生",
    "generate": "產生",
    "generated": "產出",
    "health": "健康",
    "help": "說明",
    "host": "主機",
    "hostname": "主機名稱",
    "hour": "小時",
    "html": "HTML",
    "invalid": "無效",
    "isolate": "隔離",
    "key": "鍵值",
    "label": "標籤",
    "labels": "標籤",
    "lang": "語言",
    "language": "語言",
    "last": "最後",
    "legend": "圖例",
    "light": "淺色",
    "line": "LINE",
    "list": "清單",
    "load": "載入",
    "loading": "載入中",
    "logs": "日誌",
    "lookback": "回看區間",
    "mail": "Mail",
    "managed": "managed",
    "management": "管理",
    "metric": "指標",
    "minute": "分鐘",
    "modal": "視窗",
    "module": "模組",
    "monthly": "每月",
    "name": "名稱",
    "network": "網路",
    "new": "新增",
    "next": "下一頁",
    "no": "無",
    "note": "說明",
    "offline": "Offline",
    "ok": "成功",
    "old": "舊",
    "online": "Online",
    "output": "輸出",
    "page": "頁",
    "param": "參數",
    "parsing": "解析中",
    "partial": "部分",
    "password": "密碼",
    "path": "路徑",
    "placeholder": "提示",
    "policy": "Policy",  # glossary whitelist
    "port": "Port",  # glossary whitelist
    "potential": "Potential",
    "potentially": "Potentially",
    "prev": "上一頁",
    "priority": "優先順序",
    "proto": "Protocol",
    "protocol": "Protocol",
    "query": "查詢",
    "querying": "查詢中",
    "quick": "快速",
    "rank": "排行",
    "range": "範圍",
    "recipients": "收件人",
    "refresh": "重新整理",
    "remaining": "剩餘",
    "report": "報表",
    "reports": "報表",
    "required": "必填",
    "resize": "調整欄寬",
    "retention": "保留",
    "review": "檢視",
    "risk": "風險",
    "run": "執行",
    "running": "執行中",
    "rule": "規則",
    "rules": "規則",
    "ruleset": "Ruleset",
    "save": "儲存",
    "saved": "已儲存",
    "sched": "排程",
    "schedule": "排程",
    "scheduled": "已排程",
    "scheduler": "排程",
    "search": "搜尋",
    "security": "安全",
    "select": "選擇",
    "selected": "已選",
    "sender": "寄件者",
    "service": "Service",  # glossary whitelist
    "settings": "設定",
    "severity": "Severity",
    "size": "大小",
    "snapshot": "快照",
    "source": "來源端",
    "src": "來源端",
    "start": "開始",
    "started": "已啟動",
    "state": "狀態",
    "status": "狀態",
    "step": "步驟",
    "stop": "停止",
    "success": "成功",
    "summary": "摘要",
    "system": "系統",
    "target": "目標",
    "test": "測試",
    "theme": "佈景",
    "threshold": "門檻",
    "time": "時間",
    "timezone": "時區",
    "title": "標題",
    "toggle": "切換",
    "top10": "Top 10",
    "total": "總數",
    "traffic": "流量",
    "type": "類型",
    "ui": "介面",
    "unmanaged": "unmanaged",
    "update": "更新",
    "updated": "已更新",
    "usage": "使用",
    "user": "使用者",
    "username": "帳號",
    "value": "值",
    "verify": "驗證",
    "view": "檢視",
    "vol": "流量",
    "volume": "流量",
    "warn": "警告",
    "warning": "警告",
    "web": "Web",
    "webhook": "Webhook",
    "weekly": "每週",
    "widget": "元件",
    "widgets": "元件",
    "window": "時間範圍",
    "workload": "Workload",  # glossary whitelist
    "workloads": "Workloads",  # glossary whitelist
    "pairing": "配對",
}

_PHRASE_OVERRIDES = {
    "No Reports": "尚無報表",
    "Generate your first report using the buttons above.": "請使用上方按鈕產生第一份報表。",
    "Delete Selected": "刪除已選項目",
    'Delete "{filename}"?': '確定要刪除「{filename}」嗎？',
    "Delete {count} reports?": "要刪除 {count} 份報表嗎？",
    "Deleted {count} items": "已刪除 {count} 個項目",
    "Some items failed to delete": "部分項目刪除失敗",
    "Bulk delete failed": "批次刪除失敗",
    "Bulk delete error: {error}": "批次刪除發生錯誤：{error}",
    "Name is required.": "名稱為必填。",
    "Loading rulesets...": "正在載入規則集...",
    "Loading rules...": "正在載入規則...",
    "Searching rules...": "正在搜尋規則...",
    "No results found.": "找不到結果。",
    "Request timed out": "請求逾時",
    "Request timed out (PCE may be unreachable)": "請求逾時（PCE 可能無法連線）",
    "Loading...": "載入中...",
    "Run": "立即執行",
    "Edit": "編輯",
    "Enable": "啟用",
    "Disable": "停用",
    "Schedule": "排程",
    "Edit Report Schedule": "編輯報表排程",
    "Add Report Schedule": "新增報表排程",
    "Schedule saved.": "排程已儲存。",
    "Schedule updated.": "排程已更新。",
    "Schedule deleted.": "排程已刪除。",
    "Schedule started.": "排程已啟動。",
    "Never run": "尚未執行",
    "Success": "成功",
    "Failed": "失敗",
    "No report schedules.": "目前沒有報表排程。",
}

def _humanize_key_en(key: str) -> str:
    if key.startswith("event_label_"):
        key = key[len("event_label_"):]
    elif key.startswith("cat_"):
        key = key[len("cat_"):]
    parts = [p for p in key.split("_") if p and p not in _SKIP_TOKENS and not p.isdigit()]
    if not parts:
        return key
    words = []
    for part in parts:
        words.append(_TOKEN_MAP_EN.get(part.lower(), part.replace("-", " ").title()))
    return " ".join(words).strip()

@lru_cache(maxsize=1)
def _normalized_en_messages() -> dict[str, str]:
    normalized: dict[str, str] = {}
    for key, value in dict(EN_MESSAGES).items():
        if not isinstance(value, str):
            normalized[key] = value
            continue
        stripped = value.strip()
        if not stripped:
            normalized[key] = _humanize_key_en(key)
            continue
        if _PLACEHOLDER_VALUE_RE.match(stripped):
            normalized[key] = _humanize_key_en(key)
            continue
        normalized[key] = value
    return normalized


@lru_cache(maxsize=1)
def _normalized_zh_messages() -> dict[str, str]:
    normalized: dict[str, str] = {}
    for key, value in dict(ZH_MESSAGES).items():
        if not isinstance(value, str):
            continue
        stripped = value.strip()
        if not stripped:
            continue
        normalized[key] = value
    return normalized

def _needs_space(prev: str, curr: str) -> bool:
    return (
        (prev.isascii() and (prev.isalnum() or prev in "/+%")) and
        (curr.isascii() and (curr.isalnum() or curr in "/+%"))
    )

def _smart_join_zh(parts: list[str]) -> str:
    result = ""
    for part in parts:
        if not part:
            continue
        if not result:
            result = part
            continue
        if _needs_space(result[-1], part[0]):
            result += " " + part
        else:
            result += part
    return result

def _humanize_key_zh(key: str) -> str:
    if key.startswith("event_label_"):
        key = key[len("event_label_"):]
    elif key.startswith("cat_"):
        key = key[len("cat_"):]
    parts = [p for p in key.split("_") if p and p not in _SKIP_TOKENS and not p.isdigit()]
    if not parts:
        return key
    words: list[str] = []
    for part in parts:
        word = _TOKEN_MAP_ZH.get(part.lower(), part.replace("-", " ").title())
        if words and words[-1] == word:
            continue
        words.append(word)
    return _smart_join_zh(words).strip() or key

def _translate_text(text: str) -> str:
    if not text:
        return text
    if text in _PHRASE_OVERRIDES:
        return _PHRASE_OVERRIDES[text]
    result = text
    for src, dst in sorted(_PHRASE_OVERRIDES.items(), key=lambda item: len(item[0]), reverse=True):
        result = result.replace(src, dst)

    replacements = [
        (r"\bTraffic Flow Report\b", "流量分析報表"),
        (r"\bAudit Log Report\b", "稽核報表"),
        (r"\bAudit & System Events Report\b", "稽核與系統事件報表"),
        (r"\bVEN Status Report\b", "VEN 狀態報表"),
        (r"\bPolicy Usage Report\b", "Policy 使用報表"),
        (r"\bReport Generation\b", "報表產生"),
        (r"\bRule Scheduler\b", "規則排程"),
        (r"\bSystem Settings\b", "系統設定"),
        (r"\bView System Logs\b", "查看系統日誌"),
        (r"\bLaunch Web GUI\b", "啟動 Web GUI"),
        (r"\bRule Management & Alerts\b", "規則管理與告警"),
        (r"\bGenerate\b", "產生"),
        (r"\bDelete\b", "刪除"),
        (r"\bDownload\b", "下載"),
        (r"\bView\b", "檢視"),
        (r"\bSave\b", "儲存"),
        (r"\bLoading\b", "載入中"),
        (r"\bSearch\b", "搜尋"),
        (r"\bRulesets\b", "規則集"),
        (r"\bRuleset\b", "Ruleset"),
        (r"\bRules\b", "規則"),
        (r"\bRule\b", "規則"),
        (r"\bSchedule\b", "排程"),
        (r"\bTraffic\b", "流量"),
        (r"\bAudit\b", "稽核"),
        (r"\bReport\b", "報表"),
        (r"\bStatus\b", "狀態"),
        (r"\bSettings\b", "設定"),
        (r"\bSystem\b", "系統"),
        (r"\bStart Date\b", "開始日期"),
        (r"\bEnd Date\b", "結束日期"),
        (r"\bTime Window\b", "時間視窗"),
        # Glossary whitelist: keep English — Port, Service(s), Workload(s),
        # Policy, Enforcement, Allow, Deny, Blocked, Potentially Blocked,
        # PCE, VEN are handled elsewhere in the chain but NO regex here
        # substitutes them with Chinese.
        (r"\bSource\b", "來源端"),
        (r"\bDestination\b", "目的端"),
        (r"\bProtocol\b", "Protocol"),
        (r"\bConnections\b", "連線數"),
        (r"\bDecision\b", "判定"),
        (r"\bEnabled\b", "啟用"),
        (r"\bDisabled\b", "停用"),
        (r"\bSuccess\b", "成功"),
        (r"\bFailed\b", "失敗"),
        (r"\bUpdated\b", "已更新"),
        (r"\bSaved\b", "已儲存"),
        (r"\bDeleted\b", "已刪除"),
        (r"\bNever run\b", "尚未執行"),
        (r"\bOnline\b", "Online"),
        (r"\bOffline\b", "Offline"),
        (r"\bmanaged\b", "managed"),
        (r"\bunmanaged\b", "unmanaged"),
        (r"\bYes\b", "是"),
        (r"\bNo\b", "否"),
    ]
    for pattern, repl in replacements:
        result = re.sub(pattern, repl, result)

    result = result.replace(" : ", "：").replace(": ", "：")
    result = result.replace(" ?", "？").replace(" .", "。")
    result = re.sub(r"\s{2,}", " ", result).strip()
    return result

@lru_cache(maxsize=1)
def _discover_keys() -> set[str]:
    patterns = [
        re.compile(r"""_?t\(\s*['"]([^'"]+)['"]"""),
        re.compile(r"""data-i18n=["']([A-Za-z0-9_&]+)["']"""),
        re.compile(r"""_translations\[['"]([A-Za-z0-9_&]+)['"]\]"""),
    ]
    keys: set[str] = set()
    for path in list(_ROOT.rglob("*.py")) + list(_ROOT.rglob("*.html")) + list(_ROOT.rglob("*.js")):
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for pattern in patterns:
            for key in pattern.findall(text):
                if re.fullmatch(r"[A-Za-z0-9_&]+", key):
                    keys.add(key)
    return keys

@lru_cache(maxsize=2)
def _build_messages(lang: str) -> dict[str, str]:
    en_messages = _normalized_en_messages()
    all_keys = set(en_messages) | _discover_keys()
    if lang == "en":
        base = dict(en_messages)
        for key in all_keys:
            if key in base and isinstance(base[key], str) and base[key].strip():
                continue
            if _is_strict_surface_key(key):
                base[key] = _missing_marker(key)
            else:
                base[key] = _humanize_key_en(key)
        return base

    zh_messages = _normalized_zh_messages()
    base: dict[str, str] = {}
    for key in all_keys:
        zh_text = zh_messages.get(key)
        if isinstance(zh_text, str) and zh_text.strip():
            base[key] = zh_text
            continue
        if _is_strict_surface_key(key):
            base[key] = _missing_marker(key)
            continue
        if key in _ZH_EXPLICIT:
            base[key] = _ZH_EXPLICIT[key]
            continue
        en_text = en_messages.get(key)
        if en_text:
            translated = _translate_text(en_text)
            if translated and translated != en_text:
                base[key] = translated
                continue
        base[key] = _humanize_key_zh(key)
    return base

def get_messages(lang: str | None = None) -> dict[str, str]:
    lang = lang or get_language()
    if lang not in {"en", "zh_TW"}:
        lang = "en"
    return dict(_build_messages(lang))

def t(key: str, **kwargs) -> str:
    default_val = kwargs.pop("default", None)
    _lang = get_language()
    text = get_messages(_lang).get(key)
    if text is None:
        text = _normalized_en_messages().get(key)
    if text is None and _is_strict_surface_key(key):
        text = _missing_marker(key)
    if text is None:
        if default_val is not None:
            text = default_val
        else:
            text = _humanize_key_zh(key) if _lang == "zh_TW" else _humanize_key_en(key)
    if kwargs:
        try:
            return text.format(**kwargs)
        except Exception:
            return text
    return text
