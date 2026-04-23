from __future__ import annotations

from loguru import logger


_EMITTED = False


def emit_preview_warning(cm, *, context: str) -> None:
    """Emit a startup/runtime warning when SIEM forwarder is enabled.

    SIEM currently remains available for compatibility, but is explicitly
    positioned as preview until runtime pipeline gaps are closed.
    """
    global _EMITTED
    if _EMITTED:
        return

    try:
        cfg = getattr(cm, "config", {}) or {}
        siem_cfg = cfg.get("siem", {}) or {}
    except Exception:
        return

    if not bool(siem_cfg.get("enabled", False)):
        return

    destinations = siem_cfg.get("destinations", []) or []
    enabled_dest_names: list[str] = []
    for item in destinations:
        if not isinstance(item, dict):
            continue
        if not bool(item.get("enabled", True)):
            continue
        name = str(item.get("name", "")).strip()
        if name:
            enabled_dest_names.append(name)

    if enabled_dest_names:
        logger.warning(
            "SIEM forwarder is PREVIEW (context={}) and remains enabled for compatibility; "
            "known runtime gaps are still open. Enabled destinations: {}",
            context,
            ", ".join(enabled_dest_names),
        )
        _EMITTED = True
        return

    logger.warning(
        "SIEM forwarder is PREVIEW (context={}) and enabled without active destinations; "
        "known runtime gaps are still open.",
        context,
    )
    _EMITTED = True
