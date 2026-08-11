"""Geometry Receipt → live geometry feed (OS #8).

Turns stored Geometry Receipts into ownership-gated Registry / Tension updates.
Best-effort: never fails the Interaction apply path.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional, Union
from uuid import uuid4

from .database import Database, DatabaseError, canonical_json, database_path, utcnow


class GeometryFeedError(RuntimeError):
    """Raised when a Geometry Receipt cannot be fed."""


def _load_receipt(conn, receipt_id: str) -> Optional[dict[str, Any]]:
    row = conn.execute(
        "SELECT * FROM geometry_receipts WHERE receipt_id = ?",
        (receipt_id,),
    ).fetchone()
    if row is None:
        return None

    def decode(column: str, default: Any = None) -> Any:
        raw = row[column]
        return default if raw is None else json.loads(raw)

    return {
        "receipt_id": row["receipt_id"],
        "timestamp": row["timestamp"],
        "mode": row["mode"],
        "observer": row["observer"],
        "target": row["target"],
        "source_apply_receipt_id": row["source_apply_receipt_id"],
        "relative_mass_proxy": decode("relative_mass_proxy_json"),
        "tension_components": decode("tension_components_json", []),
        "degrees_of_freedom": decode("degrees_of_freedom_json"),
        "jurisdiction_shift": decode("jurisdiction_shift_json"),
        "stem_differential": decode("stem_differential_json"),
        "ownership_move": decode("ownership_move_json"),
        "optionality_delta": decode("optionality_delta_json"),
        "notes": row["notes"] or "",
        "fed_at": row["fed_at"] if "fed_at" in row.keys() else None,
    }


def _tension_sum(components: list[dict[str, Any]]) -> float:
    total = 0.0
    for item in components or []:
        try:
            total += float(item.get("delta") or 0.0)
        except (TypeError, ValueError):
            continue
    return round(total, 6)


def feed_receipt(
    install_root: Union[str, Path],
    receipt_id: str,
    *,
    force: bool = False,
) -> dict[str, Any]:
    """Feed one Geometry Receipt into Registry effect_on_me (idempotent).

    v0 scope:
    - mode=interact + target=peer only
    - writes effect_on_me_json on the peer registry entry
    - marks geometry_receipts.fed_at
    - never writes Stem, Self-Mass, or Access/Jurisdiction claims
    """
    root = Path(install_root).expanduser().resolve()
    db_path = database_path(root)
    if not db_path.is_file():
        raise GeometryFeedError(f"No IE database under {root}")

    now = utcnow()
    with Database(db_path) as database:
        with database.transaction() as conn:
            receipt = _load_receipt(conn, receipt_id)
            if receipt is None:
                raise GeometryFeedError(f"No geometry receipt {receipt_id!r}")

            if receipt.get("fed_at") and not force:
                return {
                    "receipt_id": receipt_id,
                    "status": "already_fed",
                    "fed_at": receipt["fed_at"],
                    "target": receipt["target"],
                    "mode": receipt["mode"],
                }

            if receipt["mode"] != "interact" or receipt["target"] in {"self", ""}:
                # Mark fed so explicit --all does not retry forever on self probes.
                conn.execute(
                    "UPDATE geometry_receipts SET fed_at = ? WHERE receipt_id = ?",
                    (now, receipt_id),
                )
                return {
                    "receipt_id": receipt_id,
                    "status": "skipped_non_peer_interact",
                    "fed_at": now,
                    "target": receipt["target"],
                    "mode": receipt["mode"],
                }

            identity = conn.execute("SELECT * FROM identity LIMIT 1").fetchone()
            if identity is None:
                raise GeometryFeedError("no local identity in database")

            peer_handle = receipt["target"]
            entry = conn.execute(
                """
                SELECT * FROM registry_entries
                WHERE identity_id = ? AND peer_handle = ?
                """,
                (identity["identity_id"], peer_handle),
            ).fetchone()

            if entry is None:
                # Continuity projection may lag; still mark fed to avoid loops.
                conn.execute(
                    "UPDATE geometry_receipts SET fed_at = ? WHERE receipt_id = ?",
                    (now, receipt_id),
                )
                return {
                    "receipt_id": receipt_id,
                    "status": "skipped_no_registry_entry",
                    "fed_at": now,
                    "target": peer_handle,
                    "mode": receipt["mode"],
                }

            components = receipt.get("tension_components") or []
            effect = {
                "last_geometry_receipt_id": receipt_id,
                "last_fed_at": now,
                "source_mode": receipt["mode"],
                "relative_mass_proxy": receipt.get("relative_mass_proxy"),
                "tension_components": components,
                "tension_sum": _tension_sum(components),
                "notes": "v0 geometry feed — observational effect_on_me only",
            }

            new_revision = int(entry["revision"]) + 1
            conn.execute(
                """
                UPDATE registry_entries
                SET effect_on_me_json = ?, revision = ?, updated_at = ?, source = 'geometry_feed'
                WHERE entry_id = ?
                """,
                (canonical_json(effect), new_revision, now, entry["entry_id"]),
            )

            snapshot = dict(
                conn.execute(
                    "SELECT * FROM registry_entries WHERE entry_id = ?",
                    (entry["entry_id"],),
                ).fetchone()
            )
            snapshot["dimensions"] = []
            conn.execute(
                """
                INSERT INTO registry_entry_revisions(
                    revision_id, entry_id, revision, actor, event_id, mature_id,
                    snapshot_json, created_at
                ) VALUES (?, ?, ?, 'geometry_feed', NULL, NULL, ?, ?)
                """,
                (
                    str(uuid4()),
                    entry["entry_id"],
                    new_revision,
                    canonical_json(snapshot),
                    now,
                ),
            )

            conn.execute(
                "UPDATE geometry_receipts SET fed_at = ? WHERE receipt_id = ?",
                (now, receipt_id),
            )

    return {
        "receipt_id": receipt_id,
        "status": "fed",
        "fed_at": now,
        "target": peer_handle,
        "mode": receipt["mode"],
        "registry_revision": new_revision,
        "tension_sum": effect["tension_sum"],
    }


def feed_pending(
    install_root: Union[str, Path],
    *,
    limit: int = 50,
    force: bool = False,
) -> dict[str, Any]:
    """Feed unfed Geometry Receipts (oldest first)."""
    root = Path(install_root).expanduser().resolve()
    db_path = database_path(root)
    if not db_path.is_file():
        raise GeometryFeedError(f"No IE database under {root}")

    with Database(db_path) as database:
        if force:
            rows = database.conn.execute(
                """
                SELECT receipt_id FROM geometry_receipts
                ORDER BY timestamp ASC
                LIMIT ?
                """,
                (int(limit),),
            ).fetchall()
        else:
            rows = database.conn.execute(
                """
                SELECT receipt_id FROM geometry_receipts
                WHERE fed_at IS NULL
                ORDER BY timestamp ASC
                LIMIT ?
                """,
                (int(limit),),
            ).fetchall()

    results = []
    for row in rows:
        try:
            results.append(feed_receipt(root, row[0], force=force))
        except GeometryFeedError as exc:
            results.append(
                {"receipt_id": row[0], "status": "error", "error": str(exc)}
            )

    fed = sum(1 for r in results if r.get("status") == "fed")
    skipped = sum(1 for r in results if str(r.get("status", "")).startswith("skipped") or r.get("status") == "already_fed")
    errors = sum(1 for r in results if r.get("status") == "error")
    return {
        "processed": len(results),
        "fed": fed,
        "skipped": skipped,
        "errors": errors,
        "results": results,
    }


def feed_capability(install_root: Union[str, Path]) -> str:
    """Return declared feed mode for status surfaces."""
    # v0 always supports hook + explicit once this module is present.
    return "hook"
