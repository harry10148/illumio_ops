import os
import sys
import datetime
import re
from src.events.catalog import KNOWN_EVENT_TYPES
from src.utils import Colors, safe_input, draw_panel, draw_table, get_last_input_action
from src.config import ConfigManager
from src.i18n import t, set_language, get_language
from src import __version__

# Catalog constants and helpers have moved to src/events/catalog.
# Imported here so _legacy.py callers keep working during the H6 refactor.
from src.events.catalog import (
    FULL_EVENT_CATALOG,
    ACTION_EVENTS,
    SEVERITY_FILTER_EVENTS,
    DISCOVERY_EVENTS,
    EVENT_DESCRIPTION_KEYS,
    EVENT_TIPS_KEYS,
    _event_category,
    _humanize_event_id,
    _event_translation_key,
    _build_full_event_catalog,
    _LEGACY_STUB,
    _LEGACY_EVENT_CATALOG,
    _EVENT_CATEGORY_OVERRIDES,
    _EVENT_DESCRIPTION_OVERRIDES,
    _CATEGORY_ORDER,
    _HIDDEN_EVENT_TYPES,
    _STATUS_FILTER_EVENT_TYPES,
    _SEVERITY_FILTER_EVENT_TYPES,
)

from src.cli.menus._helpers import (
    _tz_offset_info,
    _utc_to_local_hour,
    _local_to_utc_hour,
    _menu_hints,
    _wizard_step,
    _wizard_confirm,
    _empty_uses_default,
)

from src.cli.menus.event import add_event_menu  # noqa: F401
from src.cli.menus.system_health import add_system_health_menu  # noqa: F401
from src.cli.menus.traffic import add_traffic_menu  # noqa: F401
from src.cli.menus.bandwidth import add_bandwidth_volume_menu  # noqa: F401
from src.cli.menus.manage_rules import manage_rules_menu, _parse_manage_rules_command  # noqa: F401
from src.cli.menus.alert import alert_settings_menu  # noqa: F401
from src.cli.menus.web_gui import web_gui_security_menu, _web_gui_tls_menu, _clear_screen  # noqa: F401
from src.cli.menus.report_schedule import manage_report_schedules_menu  # noqa: F401
from src.cli.menus._root import settings_menu  # noqa: F401

