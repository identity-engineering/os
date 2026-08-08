"""ie status - summarize a local SQLite-first IE install."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from runtime.database import Database, database_path


def collect_status(root: Path) -> dict[str, Any]:
    root = root.expanduser().resolve()
    db_path = database_path(root)
    if not db_path.is_file():
        raise SystemExit(f"No IE database under {root} (.ie/ie.sqlite3)")

    with Database(db_path) as database:
        conn = database.conn
        identity = conn.execute(
            """
            SELECT identity_id, local_handle, preferred_name, substrate,
                   last_signal_at, last_mature_at
            FROM identity
            LIMIT 1
            """
        ).fetchone()
        if identity is None:
            raise SystemExit(f"IE database has no local identity: {db_path}")

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
        "handle": identity["local_handle"],
        "preferred_name": identity["preferred_name"],
        "substrate": identity["substrate"],
        "schema_version": schema_version,
        "last_signal_at": identity["last_signal_at"],
        "last_mature_at": identity["last_mature_at"],
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
        f"  handle:    {info.get('handle') or '—'}",
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
