"""SQLite-backed estimate request inbox for the bidirectional sensor."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional, Union

from .models import EstimateRequest, RequestStatus, _utcnow
from .sqlite_store import SQLiteStore

# Soft local guard (not a time window). Symmetric spirit to signal rate limits.
DEFAULT_MAX_PENDING_PER_REQUESTER = 20


class RequestError(ValueError):
    """Raised for invalid request operations."""


def _request_from_row(row) -> EstimateRequest:
    requested_fields = json.loads(row["requested_fields_json"] or "[]")
    return EstimateRequest(
        request_id=row["request_id"],
        requester_handle=row["requester_handle"],
        target_handle=row["target_handle"],
        timestamp=row["timestamp"],
        status=RequestStatus(row["status"]),
        direction=row["direction"],
        requested_fields=list(requested_fields),
        note=row["note"],
        schema_version=row["schema_version"],
        transport=row["transport"],
        answered_at=row["answered_at"],
        reply_receipt_id=row["reply_receipt_id"],
        ignored_at=row["ignored_at"],
        quarantine=bool(row["quarantine"]),
    )


def create_inbound_request(
    *,
    registry_root: Union[str, Path],
    requester_handle: str,
    target_handle: str,
    requested_fields: Optional[list[str]] = None,
    note: Optional[str] = None,
    transport: str = "cli",
    request_id: Optional[str] = None,
    max_pending_per_requester: int = DEFAULT_MAX_PENDING_PER_REQUESTER,
) -> EstimateRequest:
    """Land an estimate request in *this* install's inbound inbox.

    Never auto-answers. Does not touch Stem / Vision / access policy.
    """
    if not requester_handle:
        raise RequestError("requester_handle required")
    if not target_handle:
        raise RequestError("target_handle required")

    req = EstimateRequest.create(
        requester_handle=requester_handle,
        target_handle=target_handle,
        requested_fields=requested_fields,
        note=note,
        transport=transport,
        request_id=request_id,
    )
    store = SQLiteStore.from_registry_root(registry_root)
    identity = store.identity()
    with store.open() as database:
        with database.transaction() as conn:
            pending = int(
                conn.execute(
                    """
                    SELECT COUNT(*) FROM estimate_requests
                    WHERE identity_id = ? AND direction = 'inbound'
                      AND requester_handle = ? AND status = 'pending'
                    """,
                    (identity["identity_id"], requester_handle),
                ).fetchone()[0]
            )
            if pending >= max_pending_per_requester:
                raise RequestError(
                    f"too many pending requests from {requester_handle!r} "
                    f"(limit {max_pending_per_requester})"
                )
            conn.execute(
                """
                INSERT INTO estimate_requests(
                    request_id, identity_id, direction, requester_handle, target_handle,
                    timestamp, status, requested_fields_json, note, schema_version,
                    transport, quarantine, created_at
                ) VALUES (?, ?, 'inbound', ?, ?, ?, ?, ?, ?, ?, ?, 0, ?)
                """,
                (
                    req.request_id,
                    identity["identity_id"],
                    req.requester_handle,
                    req.target_handle,
                    req.timestamp,
                    req.status.value,
                    json.dumps(req.requested_fields, ensure_ascii=False, sort_keys=True),
                    req.note,
                    req.schema_version,
                    req.transport,
                    _utcnow(),
                ),
            )
    return req


def list_inbound_requests(
    registry_root: Union[str, Path],
    *,
    status: Optional[RequestStatus] = None,
) -> list[EstimateRequest]:
    store = SQLiteStore.from_registry_root(registry_root)
    identity = store.identity()
    query = """
        SELECT * FROM estimate_requests
        WHERE identity_id = ? AND direction = 'inbound'
    """
    params: list[object] = [identity["identity_id"]]
    if status is not None:
        query += " AND status = ?"
        params.append(status.value)
    query += " ORDER BY timestamp, request_id"
    with store.open() as database:
        rows = database.conn.execute(query, params).fetchall()
    return [_request_from_row(row) for row in rows]


def get_inbound_request(
    registry_root: Union[str, Path],
    request_id: str,
) -> Optional[EstimateRequest]:
    store = SQLiteStore.from_registry_root(registry_root)
    identity = store.identity()
    with store.open() as database:
        row = database.conn.execute(
            """
            SELECT * FROM estimate_requests
            WHERE identity_id = ? AND request_id = ? AND direction = 'inbound'
            """,
            (identity["identity_id"], request_id),
        ).fetchone()
    return _request_from_row(row) if row is not None else None


def set_request_status(
    registry_root: Union[str, Path],
    request_id: str,
    status: RequestStatus,
) -> EstimateRequest:
    """Owner-side status change: ignore / quarantine (or re-open to pending)."""
    store = SQLiteStore.from_registry_root(registry_root)
    req = get_inbound_request(registry_root, request_id)
    if req is None:
        raise RequestError(f"no request {request_id!r}")

    if status == RequestStatus.ANSWERED:
        raise RequestError("use mark_request_answered after a reply signal apply")

    now = _utcnow()
    req.status = status
    if status == RequestStatus.IGNORED:
        req.ignored_at = now
        req.quarantine = False
    elif status == RequestStatus.QUARANTINED:
        req.quarantine = True
    elif status == RequestStatus.PENDING:
        req.ignored_at = None
        req.quarantine = False
        req.answered_at = None
        req.reply_receipt_id = None

    identity = store.identity()
    with store.open() as database:
        with database.transaction() as conn:
            conn.execute(
                """
                UPDATE estimate_requests
                SET status = ?, ignored_at = ?, quarantine = ?,
                    answered_at = ?, reply_receipt_id = ?
                WHERE identity_id = ? AND request_id = ? AND direction = 'inbound'
                """,
                (
                    req.status.value,
                    req.ignored_at,
                    int(req.quarantine),
                    req.answered_at,
                    req.reply_receipt_id,
                    identity["identity_id"],
                    request_id,
                ),
            )
    return req


def mark_request_answered(
    registry_root: Union[str, Path],
    request_id: str,
    reply_receipt_id: str,
) -> Optional[EstimateRequest]:
    """Link a successful reply signal to a pending/ignored request.

    Returns None if the request_id is unknown (signal still applies;
    linkage is best-effort audit).
    """
    store = SQLiteStore.from_registry_root(registry_root)
    req = get_inbound_request(registry_root, request_id)
    if req is None:
        return None

    req.status = RequestStatus.ANSWERED
    req.answered_at = _utcnow()
    req.reply_receipt_id = reply_receipt_id
    req.quarantine = False
    identity = store.identity()
    with store.open() as database:
        with database.transaction() as conn:
            conn.execute(
                """
                UPDATE estimate_requests
                SET status = 'answered', answered_at = ?, reply_receipt_id = ?, quarantine = 0
                WHERE identity_id = ? AND request_id = ? AND direction = 'inbound'
                """,
                (req.answered_at, reply_receipt_id, identity["identity_id"], request_id),
            )
    return req


def create_request_from_dict(
    payload: dict,
    *,
    registry_root: Union[str, Path],
    expected_target_handle: Optional[str] = None,
) -> EstimateRequest:
    """Dict → create_inbound_request (HTTP/CLI convenience)."""
    requester = str(payload.get("requester") or payload.get("from") or payload.get("requester_handle") or "")
    target = str(payload.get("target") or payload.get("to") or payload.get("target_handle") or "")
    if expected_target_handle and target and target != expected_target_handle:
        raise RequestError(
            f"target_handle mismatch: expected {expected_target_handle}, got {target}"
        )
    if expected_target_handle and not target:
        target = expected_target_handle

    fields = payload.get("requested_fields") or payload.get("scope") or []
    if isinstance(fields, str):
        fields = [f.strip() for f in fields.split(",") if f.strip()]

    return create_inbound_request(
        registry_root=registry_root,
        requester_handle=requester,
        target_handle=target,
        requested_fields=list(fields),
        note=payload.get("note"),
        transport=str(payload.get("transport", "cli")),
        request_id=payload.get("request_id"),
    )
