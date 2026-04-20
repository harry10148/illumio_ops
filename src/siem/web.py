from __future__ import annotations

from datetime import datetime, timezone, timedelta

from flask import Blueprint, jsonify, request
from flask_login import login_required
from loguru import logger

bp = Blueprint("siem", __name__, url_prefix="/api/siem")


def _get_siem_cfg():
    from src.config import ConfigManager
    return ConfigManager().models.siem


def _get_sf():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from src.config import ConfigManager
    from src.pce_cache.schema import init_schema
    cm = ConfigManager()
    cfg = cm.models.pce_cache
    engine = create_engine(f"sqlite:///{cfg.db_path}")
    init_schema(engine)
    return sessionmaker(engine)


@bp.route("/destinations", methods=["GET"])
@login_required
def list_destinations():
    try:
        cfg = _get_siem_cfg()
        dests = [d.model_dump() for d in cfg.destinations]
        return jsonify({"destinations": dests})
    except Exception as exc:
        logger.exception("siem list_destinations error: {}", exc)
        return jsonify({"error": str(exc)}), 500


@bp.route("/destinations", methods=["POST"])
@login_required
def add_destination():
    try:
        from src.config_models import SiemDestinationSettings
        data = request.get_json(force=True) or {}
        dest = SiemDestinationSettings(**data)
        warning = None
        if dest.transport == "udp":
            warning = "UDP transport does not guarantee delivery or ordering."
        return jsonify({"status": "ok", "name": dest.name, "warning": warning})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 400


@bp.route("/destinations/<name>", methods=["PUT"])
@login_required
def update_destination(name: str):
    try:
        from src.config_models import SiemDestinationSettings
        data = request.get_json(force=True) or {}
        data["name"] = name
        SiemDestinationSettings(**data)
        return jsonify({"status": "ok", "name": name})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 400


@bp.route("/destinations/<name>", methods=["DELETE"])
@login_required
def delete_destination(name: str):
    return jsonify({"status": "ok", "deleted": name})


@bp.route("/status", methods=["GET"])
@login_required
def dispatch_status():
    try:
        from sqlalchemy import func, select
        from src.pce_cache.models import DeadLetter, SiemDispatch
        sf = _get_sf()
        result = []
        with sf() as s:
            dests = s.execute(select(SiemDispatch.destination).distinct()).scalars().all()
            for dest in dests:
                counts = {}
                for st in ["pending", "sent", "failed"]:
                    cnt = s.execute(
                        select(func.count()).select_from(SiemDispatch)
                        .where(SiemDispatch.destination == dest)
                        .where(SiemDispatch.status == st)
                    ).scalar() or 0
                    counts[st] = cnt
                dlq_cnt = s.execute(
                    select(func.count()).select_from(DeadLetter)
                    .where(DeadLetter.destination == dest)
                ).scalar() or 0
                result.append({"destination": dest, **counts, "dlq": dlq_cnt})
        return jsonify({"status": result})
    except Exception as exc:
        logger.exception("siem dispatch_status error: {}", exc)
        return jsonify({"error": str(exc)}), 500


@bp.route("/dlq", methods=["GET"])
@login_required
def list_dlq():
    try:
        from src.siem.dlq import DeadLetterQueue
        dest = request.args.get("dest", "")
        limit = min(int(request.args.get("limit", 50)), 500)
        sf = _get_sf()
        dlq = DeadLetterQueue(sf)
        entries = dlq.list_entries(dest, limit=limit)
        return jsonify({
            "destination": dest,
            "entries": [
                {
                    "id": e.id,
                    "source_table": e.source_table,
                    "source_id": e.source_id,
                    "retries": e.retries,
                    "last_error": e.last_error,
                    "payload_preview": e.payload_preview,
                    "quarantined_at": e.quarantined_at.isoformat() if e.quarantined_at else None,
                }
                for e in entries
            ]
        })
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@bp.route("/dlq/replay", methods=["POST"])
@login_required
def replay_dlq():
    try:
        from src.siem.dlq import DeadLetterQueue
        data = request.get_json(force=True) or {}
        dest = data.get("dest", "")
        limit = min(int(data.get("limit", 100)), 1000)
        sf = _get_sf()
        dlq = DeadLetterQueue(sf)
        count = dlq.replay(dest, limit=limit)
        return jsonify({"status": "ok", "requeued": count})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@bp.route("/dlq/purge", methods=["POST"])
@login_required
def purge_dlq():
    try:
        from src.siem.dlq import DeadLetterQueue
        data = request.get_json(force=True) or {}
        dest = data.get("dest", "")
        older_than_days = int(data.get("older_than_days", 30))
        sf = _get_sf()
        dlq = DeadLetterQueue(sf)
        removed = dlq.purge(dest, older_than_days=older_than_days)
        return jsonify({"status": "ok", "removed": removed})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500
