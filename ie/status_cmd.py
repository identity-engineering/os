"""ie status - summarize a local SQLite-first IE install."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from runtime.context import get_active_identity
from runtime.database import Database, database_path


def _json_object(raw: Any) -> dict[str, Any]:
    if not raw:
        return {}
    if isinstance(raw, dict):
        return raw
    try:
        value = json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def _text_field(obj: dict[str, Any], key: str) -> str:
    value = obj.get(key)
    if not isinstance(value, str):
        return ""
    return value.strip()


def _stem_readout(conn, identity_id: str) -> dict[str, Any]:
    row = conn.execute(
        "SELECT * FROM stem_state WHERE identity_id = ?",
        (identity_id,),
    ).fetchone()
    if row is None:
        return {
            "present": False,
            "formed": False,
            "revision": None,
            "revision_count": 0,
            "updated_at": None,
            "last_mature_id": None,
            "state_differential": {"latest_summary": ""},
            "vision_gradient": {"latest_shift": ""},
            "coherence": {"latest_note": ""},
        }

    state = _json_object(row["state_differential_json"])
    vision = _json_object(row["vision_gradient_json"])
    coherence = _json_object(row["coherence_json"])
    summary = _text_field(state, "latest_summary")
    shift = _text_field(vision, "latest_shift")
    note = _text_field(coherence, "latest_note")
    last_mature_id = row["last_mature_id"] or None
    revision_count = int(
        conn.execute(
            "SELECT COUNT(*) FROM stem_revisions WHERE identity_id = ?",
            (identity_id,),
        ).fetchone()[0]
    )
    formed = bool(last_mature_id) and bool(summary or shift or note)
    return {
        "present": True,
        "formed": formed,
        "revision": int(row["revision"]),
        "revision_count": revision_count,
        "updated_at": row["updated_at"],
        "last_mature_id": last_mature_id,
        "state_differential": {"latest_summary": summary},
        "vision_gradient": {"latest_shift": shift},
        "coherence": {"latest_note": note},
    }


def collect_status(root: Path) -> dict[str, Any]:
    root = root.expanduser().resolve()
    db_path = database_path(root)
    if not db_path.is_file():
        raise SystemExit(f"No IE database under {root} (.ie/ie.sqlite3)")

    try:
        identity = get_active_identity(root)
    except Exception as exc:
        raise SystemExit(f"IE database has no local identity: {db_path} ({exc})") from exc

    with Database(db_path) as database:
        conn = database.conn
        identity_id = identity["identity_id"]
        peers = [
            row[0]
            for row in conn.execute(
                "SELECT peer_handle FROM registry_entries WHERE identity_id = ? ORDER BY peer_handle",
                (identity_id,),
            ).fetchall()
        ]
        foreign = [
            row[0]
            for row in conn.execute(
                "SELECT sender_handle FROM foreign_estimates WHERE identity_id = ? ORDER BY sender_handle",
                (identity_id,),
            ).fetchall()
        ]
        dimension_count = int(
            conn.execute(
                "SELECT COUNT(*) FROM metric_dimensions WHERE identity_id = ?",
                (identity_id,),
            ).fetchone()[0]
        )
        schema_version = int(conn.execute("PRAGMA user_version").fetchone()[0])
        stem = _stem_readout(conn, identity_id)

    return {
        "root": str(root),
        "db_path": str(db_path),
        "database": True,
        "identity_id": identity_id,
        "handle": identity["local_handle"],
        "preferred_name": identity["preferred_name"],
        "substrate": identity["substrate"],
        "schema_version": schema_version,
        "last_signal_at": identity.get("last_signal_at"),
        "last_mature_at": identity.get("last_mature_at"),
        "registry_peers": peers,
        "foreign_estimate_senders": foreign,
        "metric_dimension_count": dimension_count,
        "has_stem": stem["present"],
        "has_catalogue": dimension_count > 0,
        "stem": stem,
    }


def format_status(info: dict[str, Any]) -> str:
    stem = info.get("stem") or {}
    if not stem.get("present"):
        stem_line = "missing"
    elif stem.get("formed"):
        stem_line = f"x(t) formed r{stem.get('revision')} ({stem.get('revision_count')} sample(s))"
    else:
        stem_line = f"x(t) present unformed r{stem.get('revision')} ({stem.get('revision_count')} sample(s))"

    lines = [
        f"IE install: {info['root']}",
        f"  database:  {info.get('db_path') or '—'}",
        f"  schema:    v{info.get('schema_version') or '—'}",
        f"  identity:  {info.get('handle') or '—'} ({(info.get('identity_id') or '')[:8]}…)",
        f"  name:      {info.get('preferred_name') or '—'}",
        f"  substrate: {info.get('substrate') or '—'}",
        f"  mature:    {info.get('last_mature_at') or 'not yet'}",
        f"  stem:      {stem_line}",
    ]
    if stem.get("present"):
        summary = (stem.get("state_differential") or {}).get("latest_summary") or "—"
        shift = (stem.get("vision_gradient") or {}).get("latest_shift") or "—"
        note = (stem.get("coherence") or {}).get("latest_note") or "—"
        lines.extend(
            [
                f"    differential: {summary}",
                f"    vision:       {shift}",
                f"    coherence:    {note}",
            ]
        )
    lines.extend(
        [
            f"  catalogue: {info.get('metric_dimension_count', 0)} dimension(s)",
            f"  registry:  {len(info.get('registry_peers') or [])} peer(s)",
        ]
    )
    for handle in info.get("registry_peers") or []:
        lines.append(f"    - {handle}")
    foreign = info.get("foreign_estimate_senders") or []
    lines.append(f"  foreign estimates: {len(foreign)} sender(s)")
    for handle in foreign:
        lines.append(f"    - {handle}")
    return "\n".join(lines)


def status_json(info: dict[str, Any]) -> str:
    return json.dumps(info, indent=2, ensure_ascii=False)
