"""src/settings — backwards-compatibility re-export shim.

Wizard functions live in src/cli/menus/; catalog data in src/events/catalog.
This shim exists so the six importers of 'from src.settings import X' keep
working without changes.

The `os` and `get_last_input_action` module-level names are kept for any
external code that accesses them via the settings module reference.
"""
from __future__ import annotations

import os  # noqa: F401
from src.utils import get_last_input_action  # noqa: F401

from src.events.catalog import (  # noqa: F401
    FULL_EVENT_CATALOG,
    ACTION_EVENTS,
    SEVERITY_FILTER_EVENTS,
    DISCOVERY_EVENTS,
    EVENT_DESCRIPTION_KEYS,
    EVENT_TIPS_KEYS,
    _event_category,
)
from src.cli.menus.event import add_event_menu  # noqa: F401
from src.cli.menus.system_health import add_system_health_menu  # noqa: F401
from src.cli.menus.traffic import add_traffic_menu  # noqa: F401
from src.cli.menus.bandwidth import add_bandwidth_volume_menu  # noqa: F401
from src.cli.menus.manage_rules import (  # noqa: F401
    manage_rules_menu,
    _parse_manage_rules_command,
)
from src.cli.menus.alert import alert_settings_menu  # noqa: F401
from src.cli.menus.web_gui import (  # noqa: F401
    web_gui_security_menu,
    _web_gui_tls_menu,
)
from src.cli.menus.report_schedule import manage_report_schedules_menu  # noqa: F401
from src.cli.menus._root import settings_menu  # noqa: F401
from src.cli.menus._helpers import (  # noqa: F401
    _wizard_step,
    _wizard_confirm,
    _menu_hints,
    _tz_offset_info,
    _utc_to_local_hour,
    _local_to_utc_hour,
    _empty_uses_default,
)
