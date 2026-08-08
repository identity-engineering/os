"""Persistent consent and quarantine operations for the local policy membrane."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional, Union
from uuid import uuid4

from .database import utcnow
from .sqlite_store import SQLiteStore


class PolicyError(ValueError):
    """Raised when a policy mutation is invalid."""


def _identity(store: SQLiteStore):
    row = store.identity()
    return row["identity_id"], row["local_handle"]


def _event(
    conn,
    *,
    identity_id: str,
    event_type: str,
    subject_handle: Optional[str],
    field_name: Optional[str],
    previous: Any,
    current: Any,
    actor: str,
    reason: Optional[str],
    created_at: str,
) -> None:
    import json

    conn.execute(
        """
        INSERT INTO policy_events(
            policy_event_id, identity_id, event_type, subject_handle, field_name,
            previous_value_json, new_value_json, actor, reason, details_json, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, '{}', ?)
        """,
        (
            str(uuid4()),
            identity_id,
            event_type,
            subject_handle,
            field_name,
            json.dumps(previous, ensure_ascii=False, sort_keys=True),
            json.dumps(current, ensure_ascii=False, sort_keys=True),
            actor,
            reason,
            created_at,
        ),
    )


def grant_consent(
    install_root: Union[str, Path],
    *,
    sender_handle: str,
    field_name: str,
    actor: Optional[str] = None,
    reason: Optional[str] = None,
    source: str = "cli",
    note: Optional[str] = None,
) -> dict[str, Any]:
    """Grant one consent-gated signal field and append a policy audit event."""
    sender_handle = sender_handle.strip()
    field_name = field_name.strip()
    if not sender_handle or not field_name:
        raise PolicyError("sender_handle and field_name are required")
    store = SQLiteStore(install_root)
    identity_id, local_handle = _identity(store)
    actor = (actor or local_handle).strip()
    now = utcnow()
    with store.open() as database:
        with database.transaction() as conn:
            active = conn.execute(
                """
                SELECT grant_id FROM consent_grants
                WHERE identity_id = ? AND sender_handle = ? AND field_name = ?
                  AND revoked_at IS NULL
                ORDER BY granted_at DESC LIMIT 1
                """,
                (identity_id, sender_handle, field_name),
            ).fetchone()
            if active is not None:
                return {
                    "changed": False,
                    "grant_id": active[0],
                    "sender_handle": sender_handle,
                    "field_name": field_name,
                }
            grant_id = str(uuid4())
            conn.execute(
                """
                INSERT INTO consent_grants(
                    grant_id, identity_id, sender_handle, field_name,
                    granted_at, revoked_at, source, note
                ) VALUES (?, ?, ?, ?, ?, NULL, ?, ?)
                """,
                (grant_id, identity_id, sender_handle, field_name, now, source, note),
            )
            _event(
                conn,
                identity_id=identity_id,
                event_type="consent_granted",
                subject_handle=sender_handle,
                field_name=field_name,
                previous=False,
                current=True,
                actor=actor,
                reason=reason,
                created_at=now,
            )
    return {
        "changed": True,
        "grant_id": grant_id,
        "sender_handle": sender_handle,
        "field_name": field_name,
    }


def revoke_consent(
    install_root: Union[str, Path],
    *,
    sender_handle: str,
    field_name: str,
    actor: Optional[str] = None,
    reason: Optional[str] = None,
) -> dict[str, Any]:
    """Revoke all active grants for one sender/field without deleting history."""
    sender_handle = sender_handle.strip()
    field_name = field_name.strip()
    if not sender_handle or not field_name:
        raise PolicyError("sender_handle and field_name are required")
    store = SQLiteStore(install_root)
    identity_id, local_handle = _identity(store)
    actor = (actor or local_handle).strip()
    now = utcnow()
    with store.open() as database:
        with database.transaction() as conn:
            cursor = conn.execute(
                """
                UPDATE consent_grants
                SET revoked_at = ?
                WHERE identity_id = ? AND sender_handle = ? AND field_name = ?
                  AND revoked_at IS NULL
                """,
                (now, identity_id, sender_handle, field_name),
            )
            changed = cursor.rowcount > 0
            if changed:
                _event(
                    conn,
                    identity_id=identity_id,
                    event_type="consent_revoked",
                    subject_handle=sender_handle,
                    field_name=field_name,
                    previous=True,
                    current=False,
                    actor=actor,
                    reason=reason,
                    created_at=now,
                )
    return {
        "changed": changed,
        "sender_handle": sender_handle,
        "field_name": field_name,
    }


def quarantine_sender(
    install_root: Union[str, Path],
    *,
    sender_handle: str,
    reason: str,
    actor: Optional[str] = None,
    source: str = "cli",
) -> dict[str, Any]:
    """Activate quarantine for a sender and preserve the previous policy state."""
    sender_handle = sender_handle.strip()
    reason = reason.strip()
    if not sender_handle or not reason:
        raise PolicyError("sender_handle and reason are required")
    store = SQLiteStore(install_root)
    identity_id, local_handle = _identity(store)
    actor = (actor or local_handle).strip()
    now = utcnow()
    with store.open() as database:
        with database.transaction() as conn:
            active = conn.execute(
                """
                SELECT quarantine_id FROM quarantines
                WHERE identity_id = ? AND sender_handle = ? AND active = 1
                  AND revoked_at IS NULL
                ORDER BY created_at DESC LIMIT 1
                """,
                (identity_id, sender_handle),
            ).fetchone()
            if active is not None:
                return {
                    "changed": False,
                    "quarantine_id": active[0],
                    "sender_handle": sender_handle,
                    "active": True,
                }
            quarantine_id = str(uuid4())
            conn.execute(
                """
                INSERT INTO quarantines(
                    quarantine_id, identity_id, sender_handle, active, reason,
                    created_at, revoked_at, source
                ) VALUES (?, ?, ?, 1, ?, ?, NULL, ?)
                """,
                (quarantine_id, identity_id, sender_handle, reason, now, source),
            )
            _event(
                conn,
                identity_id=identity_id,
                event_type="sender_quarantined",
                subject_handle=sender_handle,
                field_name=None,
                previous=False,
                current=True,
                actor=actor,
                reason=reason,
                created_at=now,
            )
    return {
        "changed": True,
        "quarantine_id": quarantine_id,
        "sender_handle": sender_handle,
        "active": True,
    }


def release_quarantine(
    install_root: Union[str, Path],
    *,
    sender_handle: str,
    actor: Optional[str] = None,
    reason: Optional[str] = None,
) -> dict[str, Any]:
    """Deactivate current quarantine rows while retaining their history."""
    sender_handle = sender_handle.strip()
    if not sender_handle:
        raise PolicyError("sender_handle is required")
    store = SQLiteStore(install_root)
    identity_id, local_handle = _identity(store)
    actor = (actor or local_handle).strip()
    now = utcnow()
    with store.open() as database:
        with database.transaction() as conn:
            cursor = conn.execute(
                """
                UPDATE quarantines
                SET active = 0, revoked_at = ?
                WHERE identity_id = ? AND sender_handle = ? AND active = 1
                  AND revoked_at IS NULL
                """,
                (now, identity_id, sender_handle),
            )
            changed = cursor.rowcount > 0
            if changed:
                _event(
                    conn,
                    identity_id=identity_id,
                    event_type="sender_quarantine_released",
                    subject_handle=sender_handle,
                    field_name=None,
                    previous=True,
                    current=False,
                    actor=actor,
                    reason=reason,
                    created_at=now,
                )
    return {"changed": changed, "sender_handle": sender_handle, "active": False}


def policy_snapshot(install_root: Union[str, Path]) -> dict[str, Any]:
    """Return current persistent policy state and its audit count."""
    store = SQLiteStore(install_root)
    identity_id, _ = _identity(store)
    with store.open() as database:
        grants = [
            dict(row)
            for row in database.conn.execute(
                """
                SELECT sender_handle, field_name, granted_at, source, note
                FROM consent_grants
                WHERE identity_id = ? AND revoked_at IS NULL
                ORDER BY sender_handle, field_name
                """,
                (identity_id,),
            ).fetchall()
        ]
        quarantines = [
            dict(row)
            for row in database.conn.execute(
                """
                SELECT sender_handle, reason, created_at, source
                FROM quarantines
                WHERE identity_id = ? AND active = 1 AND revoked_at IS NULL
                ORDER BY sender_handle
                """,
                (identity_id,),
            ).fetchall()
        ]
        event_count = int(
            database.conn.execute(
                "SELECT COUNT(*) FROM policy_events WHERE identity_id = ?",
                (identity_id,),
            ).fetchone()[0]
        )
    return {
        "grants": grants,
        "quarantines": quarantines,
        "policy_event_count": event_count,
    }