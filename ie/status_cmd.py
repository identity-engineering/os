"""ie status - summarize a local SQLite-first IE install."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from runtime.context import get_active_identity
from runtime.database import Database, database_path


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
        peers = [
            row[0]
            for row in conn.execute(
                "SELECT peer_handle FROM registry_entries WHERE identity_id = ? ORDER BY peer_handle",
                (identity["identity_id"],),
            ).fetchall()
        ]
        foreign = [
            row[0]
            for row in conn.execute(
                "SELECT sender_handle FROM foreign_estimates WHERE identity_id = ? ORDER BY sender_handle",
                (identity["identity_id"],),
            ).fetchall()
        ]
        dimension_count = int(
            conn.execute(
                "SELECT COUNT(*) FROM metric_dimensions WHERE identity_id = ?",
                (identity["identity_id"],),
            ).fetchone()[0]
        )
        schema_version = int(conn.execute("PRAGMA user_version").fetchone()[0])

    return {
        "root": str(root),
        "db_path": str(db_path),
        "database": True,
        "identity_id": identity["identity_id"],
        "handle": identity["local_handle"],
        "preferred_name": identity["preferred_name"],
        "substrate": identity["substrate"],
        "schema_version": schema_version,
        "last_signal_at": identity.get("last_signal_at"),
        "last_mature_at": identity.get("last_mature_at"),
        "registry_peers": peers,
        "foreign_estimate_senders": foreign,
        "metric_dimension_count": dimension_count,
        "has_stem": True,
        "has_catalogue": dimension_count > 0,
    }


def format_status(info: dict[str, Any]) -> str:
    lines = [
        f"IE install: {info['root']}",
        f"  database:  {info.get('db_path') or '—'}",
        f"  schema:    v{info.get('schema_version') or '—'}",
        f"  identity:  {info.get('handle') or '—'} ({(info.get('identity_id') or '')[:8]}…)",
        f"  name:      {info.get('preferred_name') or '—'}",
        f"  substrate: {info.get('substrate') or '—'}",
        f"  mature:    {info.get('last_mature_at') or 'not yet'}",
        f"  stem:      {'yes' if info.get('has_stem') else 'no'}",
        f"  catalogue: {info.get('metric_dimension_count', 0)} dimension(s)",
        f"  registry:  {len(info.get('registry_peers') or [])} peer(s)",
    ]
    for handle in info.get("registry_peers") or []:
        lines.append(f"    - {handle}")
    foreign = info.get("foreign_estimate_senders") or []
    lines.append(f"  foreign estimates: {len(foreign)} sender(s)")
    for handle in foreign:
        lines.append(f"    - {handle}")
    return "\n".join(lines)


def status_json(info: dict[str, Any]) -> str:
    return json.dumps(info, indent=2, ensure_ascii=False)
