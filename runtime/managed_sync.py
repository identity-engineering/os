"""Optional Managed sync queue for the SQLite-first local Core."""

from __future__ import annotations

import json
import math
import re
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional, Protocol, Union
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import Request, urlopen
from uuid import uuid4

from .database import canonical_json, sha256_text, utcnow
from .models import InteractionSignal
from .sqlite_store import SQLiteStore, canonical_signal_payload


_TIMESTAMP_PATTERN = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,9})?(?:Z|[+-]\d{2}:\d{2})$"
)


class SyncQueueError(RuntimeError):
    """Base error for local sync queue operations."""


class SyncQueueConflict(SyncQueueError):
    """Raised when an event or idempotency key is reused with new content."""


@dataclass(frozen=True)
class ManagedSyncEnvelope:
    event_id: str
    stream: str
    entity_type: str
    entity_id: str
    idempotency_key: str
    previous_cursor: Optional[str]
    cursor: str
    occurred_at: str
    payload: dict[str, Any]
    payload_sha256: str

    def __post_init__(self) -> None:
        if not isinstance(self.event_id, str) or not 1 <= len(self.event_id) <= 128:
            raise ValueError("sync event_id is invalid")
        if not isinstance(self.entity_id, str) or not 1 <= len(self.entity_id) <= 128:
            raise ValueError("sync entity_id is invalid")
        if not isinstance(self.idempotency_key, str) or not 1 <= len(self.idempotency_key) <= 256:
            raise ValueError("sync idempotency_key is invalid")
        if self.previous_cursor is not None and (
            not isinstance(self.previous_cursor, str) or not self.previous_cursor
        ):
            raise ValueError("sync previous_cursor is invalid")
        if not isinstance(self.cursor, str) or not 1 <= len(self.cursor) <= 256:
            raise ValueError("sync cursor is invalid")
        _wire_timestamp(self.occurred_at, "sync occurred_at")
        if not isinstance(self.payload_sha256, str) or not re.fullmatch(
            r"[0-9a-f]{64}", self.payload_sha256
        ):
            raise ValueError("sync payload checksum is invalid")
        _validate_stream(self.stream)
        if not isinstance(self.payload, dict):
            raise ValueError("sync payload must be an object")
        if self.entity_type != "interaction.signal":
            raise ValueError("Managed sync currently supports interaction.signal only")
        if self.stream != f"identity:{self.entity_id}:interaction":
            raise ValueError("sync stream must match the identity")
        payload_json = canonical_json(self.payload)
        if sha256_text(payload_json) != self.payload_sha256:
            raise ValueError("sync payload checksum mismatch")
        try:
            signal = _validate_signal_payload(self.payload)
            errors = signal.validate_required()
        except (TypeError, ValueError) as exc:
            raise ValueError("invalid interaction.signal payload") from exc
        if errors:
            raise ValueError("invalid interaction.signal payload: " + "; ".join(errors))
        if _timestamp(self.occurred_at) != _timestamp(signal.timestamp):
            raise ValueError("occurred_at must match the signal timestamp")
        if not self.event_id or not self.idempotency_key or not self.cursor:
            raise ValueError("sync event_id, idempotency_key, and cursor are required")

    @classmethod
    def from_signal(
        cls,
        signal: InteractionSignal,
        *,
        identity_id: str,
        previous_cursor: Optional[str],
        cursor: str,
        event_id: Optional[str] = None,
        idempotency_key: Optional[str] = None,
    ) -> "ManagedSyncEnvelope":
        payload = canonical_signal_payload(signal)
        return cls(
            event_id=event_id or str(uuid4()),
            stream=f"identity:{identity_id}:interaction",
            entity_type="interaction.signal",
            entity_id=identity_id,
            idempotency_key=idempotency_key or str(uuid4()),
            previous_cursor=previous_cursor,
            cursor=cursor,
            occurred_at=signal.timestamp,
            payload=payload,
            payload_sha256=sha256_text(canonical_json(payload)),
        )

    def to_request(self) -> dict[str, Any]:
        return {
            "eventId": self.event_id,
            "stream": self.stream,
            "entityType": self.entity_type,
            "entityId": self.entity_id,
            "idempotencyKey": self.idempotency_key,
            "previousCursor": self.previous_cursor,
            "cursor": self.cursor,
            "occurredAt": self.occurred_at,
            "payload": self.payload,
            "payloadSha256": self.payload_sha256,
        }


@dataclass(frozen=True)
class QueuedSyncEvent:
    queue_id: str
    envelope: ManagedSyncEnvelope
    status: str
    attempts: int
    next_attempt_at: str
    last_error: Optional[str]
    server_cursor: Optional[str]
    accepted_at: Optional[str]
    created_at: str
    updated_at: str


@dataclass(frozen=True)
class SyncSendResult:
    status: int
    server_cursor: Optional[str] = None
    duplicate: bool = False
    retry_after_seconds: Optional[int] = None
    error: Optional[str] = None


@dataclass(frozen=True)
class SyncDrainResult:
    attempted: int
    accepted: int
    retried: int
    blocked: int


@dataclass(frozen=True)
class ManagedSyncPulledEvent:
    server_sequence: str
    event_id: str
    stream: str
    entity_type: str
    entity_id: str
    idempotency_key: str
    payload: dict[str, Any]
    payload_sha256: str
    occurred_at: str
    received_at: str


@dataclass(frozen=True)
class ManagedSyncPullResult:
    installation_id: str
    stream: str
    client_cursor: Optional[str]
    server_cursor: str
    next_cursor: str
    has_more: bool
    events: tuple[ManagedSyncPulledEvent, ...]


class SyncSender(Protocol):
    def __call__(self, envelope: ManagedSyncEnvelope) -> SyncSendResult:
        ...


def _timestamp(value: Optional[Union[str, datetime]] = None) -> str:
    if value is None:
        return utcnow()
    if isinstance(value, datetime):
        parsed = value
    else:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).isoformat()


def _after_seconds(value: str, seconds: int) -> str:
    parsed = datetime.fromisoformat(value)
    return (parsed + timedelta(seconds=seconds)).isoformat()


def _wire_timestamp(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not _TIMESTAMP_PATTERN.fullmatch(value):
        raise ValueError(f"{field_name} must be an ISO timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{field_name} must be an ISO timestamp") from exc
    if parsed.tzinfo is None:
        raise ValueError(f"{field_name} must include a timezone")
    return value


def _validate_stream(value: Any) -> str:
    if (
        not isinstance(value, str)
        or not 1 <= len(value) <= 256
        or not re.fullmatch(r"identity:.+:interaction", value)
    ):
        raise ValueError("sync stream is invalid")
    return value


def _validate_signal_payload(payload: dict[str, Any]) -> InteractionSignal:
    allowed = {
        "from",
        "to",
        "timestamp",
        "existence",
        "interaction_depth_delta",
        "sender_emergent_mass",
        "sender_last_mature_at",
        "coarse_mass_estimate",
        "mass_confidence",
        "dimensions_delta",
        "relation_pull",
        "schema_version",
        "transport",
        "in_reply_to_request_id",
    }
    if set(payload) - allowed:
        raise ValueError("sync payload contains unknown fields")

    def text(name: str, *, required: bool = False, max_length: int = 128) -> Optional[str]:
        value = payload.get(name)
        if value is None:
            if required:
                raise ValueError(f"sync payload field {name} is required")
            return None
        if not isinstance(value, str) or not value or len(value) > max_length:
            raise ValueError(f"sync payload field {name} is invalid")
        return value

    def number(name: str, *, minimum: float, maximum: float) -> Optional[float]:
        value = payload.get(name)
        if value is None:
            return None
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(f"sync payload field {name} is invalid")
        converted = float(value)
        if not math.isfinite(converted) or not minimum <= converted <= maximum:
            raise ValueError(f"sync payload field {name} is out of range")
        return converted

    from_handle = text("from", required=True)
    to_handle = text("to", required=True)
    timestamp = text("timestamp", required=True)
    _wire_timestamp(timestamp, "sync payload timestamp")
    if not isinstance(payload.get("existence"), bool):
        raise ValueError("sync payload field existence is invalid")
    interaction_depth_delta = number(
        "interaction_depth_delta",
        minimum=0.0,
        maximum=1.0,
    )
    sender_last_mature_at = text("sender_last_mature_at")
    if sender_last_mature_at is not None:
        _wire_timestamp(sender_last_mature_at, "sync payload sender_last_mature_at")
    dimensions_delta = payload.get("dimensions_delta")
    if dimensions_delta is not None:
        if not isinstance(dimensions_delta, list):
            raise ValueError("sync payload dimensions_delta is invalid")
        for dimension in dimensions_delta:
            if not isinstance(dimension, dict) or set(dimension) != {"name", "value", "confidence"}:
                raise ValueError("sync payload dimensions_delta is invalid")
            name = dimension["name"]
            value = dimension["value"]
            confidence = dimension["confidence"]
            if not isinstance(name, str) or not name or len(name) > 128:
                raise ValueError("sync payload dimension name is invalid")
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)):
                raise ValueError("sync payload dimension value is invalid")
            if (
                isinstance(confidence, bool)
                or not isinstance(confidence, (int, float))
                or not math.isfinite(float(confidence))
                or not 0.0 <= float(confidence) <= 1.0
            ):
                raise ValueError("sync payload dimension confidence is invalid")
    schema_version = payload.get("schema_version", "0")
    if schema_version != "0":
        raise ValueError("sync payload schema_version is unsupported")
    transport = text("transport", max_length=32) if "transport" in payload else "cli"
    if transport is None:
        raise ValueError("sync payload field transport is invalid")
    in_reply_to_request_id = text("in_reply_to_request_id")
    return InteractionSignal(
        from_handle=from_handle,
        to_handle=to_handle,
        timestamp=timestamp,
        existence=payload["existence"],
        interaction_depth_delta=interaction_depth_delta,
        sender_emergent_mass=number("sender_emergent_mass", minimum=0.0, maximum=100.0),
        sender_last_mature_at=sender_last_mature_at,
        coarse_mass_estimate=number("coarse_mass_estimate", minimum=0.0, maximum=100.0),
        mass_confidence=number("mass_confidence", minimum=0.0, maximum=1.0),
        dimensions_delta=dimensions_delta,
        relation_pull=number("relation_pull", minimum=0.0, maximum=1.0),
        schema_version=schema_version,
        transport=transport,
        in_reply_to_request_id=in_reply_to_request_id,
    )


def _row_to_event(row: Any) -> QueuedSyncEvent:
    payload = json.loads(row["payload_json"])
    envelope = ManagedSyncEnvelope(
        event_id=row["event_id"],
        stream=row["stream"],
        entity_type=row["entity_type"],
        entity_id=row["entity_id"],
        idempotency_key=row["idempotency_key"],
        previous_cursor=row["previous_cursor"],
        cursor=row["cursor"],
        occurred_at=row["occurred_at"],
        payload=payload,
        payload_sha256=row["payload_sha256"],
    )
    return QueuedSyncEvent(
        queue_id=row["queue_id"],
        envelope=envelope,
        status=row["status"],
        attempts=row["attempts"],
        next_attempt_at=row["next_attempt_at"],
        last_error=row["last_error"],
        server_cursor=row["server_cursor"],
        accepted_at=row["accepted_at"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


class ManagedSyncQueue:
    """Persist and drain optional Managed sync envelopes for one local install."""

    def __init__(
        self,
        install_root: Union[str, Path, SQLiteStore],
        *,
        base_delay_seconds: int = 5,
        max_delay_seconds: int = 3600,
        lease_seconds: int = 300,
    ) -> None:
        self.store = install_root if isinstance(install_root, SQLiteStore) else SQLiteStore(install_root)
        if (
            base_delay_seconds < 1
            or max_delay_seconds < base_delay_seconds
            or lease_seconds < 1
        ):
            raise ValueError("invalid sync retry delay bounds")
        self.base_delay_seconds = base_delay_seconds
        self.max_delay_seconds = max_delay_seconds
        self.lease_seconds = lease_seconds

    def enqueue(
        self,
        envelope: ManagedSyncEnvelope,
        *,
        now: Optional[Union[str, datetime]] = None,
    ) -> QueuedSyncEvent:
        timestamp = _timestamp(now)
        payload_json = canonical_json(envelope.payload)
        with self.store.open() as database:
            with database.transaction() as connection:
                existing = connection.execute(
                    """
                    SELECT * FROM managed_sync_queue
                    WHERE event_id = ? OR idempotency_key = ?
                    LIMIT 1
                    """,
                    (envelope.event_id, envelope.idempotency_key),
                ).fetchone()
                if existing is not None:
                    same = (
                        existing["event_id"] == envelope.event_id
                        and existing["stream"] == envelope.stream
                        and existing["entity_type"] == envelope.entity_type
                        and existing["entity_id"] == envelope.entity_id
                        and existing["idempotency_key"] == envelope.idempotency_key
                        and existing["previous_cursor"] == envelope.previous_cursor
                        and existing["cursor"] == envelope.cursor
                        and existing["occurred_at"] == envelope.occurred_at
                        and existing["payload_json"] == payload_json
                        and existing["payload_sha256"] == envelope.payload_sha256
                    )
                    if not same:
                        raise SyncQueueConflict("sync event or idempotency key conflict")
                    return _row_to_event(existing)

                queue_id = str(uuid4())
                connection.execute(
                    """
                    INSERT INTO managed_sync_queue(
                        queue_id, event_id, stream, entity_type, entity_id,
                        idempotency_key, payload_json, payload_sha256, occurred_at,
                        previous_cursor, cursor, status, attempts, next_attempt_at,
                        created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending', 0, ?, ?, ?)
                    """,
                    (
                        queue_id,
                        envelope.event_id,
                        envelope.stream,
                        envelope.entity_type,
                        envelope.entity_id,
                        envelope.idempotency_key,
                        payload_json,
                        envelope.payload_sha256,
                        envelope.occurred_at,
                        envelope.previous_cursor,
                        envelope.cursor,
                        timestamp,
                        timestamp,
                        timestamp,
                    ),
                )
                row = connection.execute(
                    "SELECT * FROM managed_sync_queue WHERE queue_id = ?",
                    (queue_id,),
                ).fetchone()
                if row is None:
                    raise SyncQueueError("queued sync event disappeared")
                return _row_to_event(row)

    def list_due(
        self,
        *,
        now: Optional[Union[str, datetime]] = None,
        limit: int = 20,
    ) -> list[QueuedSyncEvent]:
        if limit < 1 or limit > 100:
            raise ValueError("sync queue limit must be between 1 and 100")
        timestamp = _timestamp(now)
        with self.store.open() as database:
            rows = database.conn.execute(
                """
                SELECT queue.*
                FROM managed_sync_queue queue
                WHERE queue.status IN ('pending', 'retry')
                  AND queue.next_attempt_at <= ?
                                    AND NOT EXISTS (
                                            SELECT 1
                                            FROM managed_sync_leases active_lease
                                            WHERE active_lease.queue_id = queue.queue_id
                                                AND active_lease.lease_until > ?
                                    )
                  AND NOT EXISTS (
                      SELECT 1
                      FROM managed_sync_queue earlier
                      WHERE earlier.stream = queue.stream
                        AND earlier.status <> 'accepted'
                        AND (
                            earlier.created_at < queue.created_at
                            OR (
                                earlier.created_at = queue.created_at
                                AND earlier.queue_id < queue.queue_id
                            )
                        )
                  )
                ORDER BY queue.created_at ASC, queue.queue_id ASC
                LIMIT ?
                """,
                (timestamp, timestamp, limit),
            ).fetchall()
        return [_row_to_event(row) for row in rows]

    def get(self, queue_id: str) -> Optional[QueuedSyncEvent]:
        with self.store.open() as database:
            row = database.conn.execute(
                "SELECT * FROM managed_sync_queue WHERE queue_id = ?",
                (queue_id,),
            ).fetchone()
        return _row_to_event(row) if row is not None else None

    def list_events(self, *, status: Optional[str] = None) -> list[QueuedSyncEvent]:
        query = "SELECT * FROM managed_sync_queue"
        parameters: tuple[Any, ...] = ()
        if status is not None:
            query += " WHERE status = ?"
            parameters = (status,)
        query += " ORDER BY created_at ASC, queue_id ASC"
        with self.store.open() as database:
            rows = database.conn.execute(query, parameters).fetchall()
        return [_row_to_event(row) for row in rows]

    def stream_state(self, stream: str) -> dict[str, Optional[str]]:
        with self.store.open() as database:
            row = database.conn.execute(
                "SELECT client_cursor, server_cursor FROM managed_sync_state WHERE stream = ?",
                (stream,),
            ).fetchone()
        if row is None:
            return {"client_cursor": None, "server_cursor": None}
        return {
            "client_cursor": row["client_cursor"],
            "server_cursor": row["server_cursor"],
        }

    def record_server_cursor(
        self,
        stream: str,
        server_cursor: str,
        *,
        now: Optional[Union[str, datetime]] = None,
    ) -> None:
        if not server_cursor.isdigit():
            raise ValueError("server cursor must be a non-negative integer string")
        timestamp = _timestamp(now)
        with self.store.open() as database:
            with database.transaction() as connection:
                existing = connection.execute(
                    "SELECT server_cursor FROM managed_sync_state WHERE stream = ?",
                    (stream,),
                ).fetchone()
                current = existing["server_cursor"] if existing is not None else None
                if current is not None and int(current) > int(server_cursor):
                    server_cursor = current
                connection.execute(
                    """
                    INSERT INTO managed_sync_state(stream, client_cursor, server_cursor, updated_at)
                    VALUES (?, NULL, ?, ?)
                    ON CONFLICT(stream) DO UPDATE SET
                        server_cursor = excluded.server_cursor,
                        updated_at = excluded.updated_at
                    """,
                    (stream, server_cursor, timestamp),
                )

    def acknowledge_server_event(
        self,
        event_id: str,
        server_cursor: str,
        *,
        now: Optional[Union[str, datetime]] = None,
    ) -> bool:
        if not server_cursor.isdigit():
            raise ValueError("server cursor must be a non-negative integer string")
        timestamp = _timestamp(now)
        with self.store.open() as database:
            with database.transaction() as connection:
                event = connection.execute(
                    "SELECT * FROM managed_sync_queue WHERE event_id = ?",
                    (event_id,),
                ).fetchone()
                if event is None:
                    return False
                state = connection.execute(
                    "SELECT client_cursor, server_cursor FROM managed_sync_state WHERE stream = ?",
                    (event["stream"],),
                ).fetchone()
                current_server_cursor = state["server_cursor"] if state is not None else None
                current_client_cursor = state["client_cursor"] if state is not None else None
                effective_server_cursor = server_cursor
                if (
                    current_server_cursor is not None
                    and int(current_server_cursor) > int(server_cursor)
                ):
                    effective_server_cursor = current_server_cursor
                advance_client_cursor = (
                    current_server_cursor is None
                    or int(server_cursor) > int(current_server_cursor)
                    or current_client_cursor is None
                )
                connection.execute(
                    """
                    UPDATE managed_sync_queue
                    SET status = 'accepted',
                        server_cursor = ?,
                        accepted_at = COALESCE(accepted_at, ?),
                        last_error = NULL,
                        updated_at = ?
                    WHERE event_id = ?
                    """,
                    (effective_server_cursor, timestamp, timestamp, event_id),
                )
                connection.execute(
                    "DELETE FROM managed_sync_leases WHERE queue_id = ?",
                    (event["queue_id"],),
                )
                connection.execute(
                    """
                    INSERT INTO managed_sync_state(stream, client_cursor, server_cursor, updated_at)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(stream) DO UPDATE SET
                        client_cursor = CASE
                            WHEN ? THEN excluded.client_cursor
                            ELSE managed_sync_state.client_cursor
                        END,
                        server_cursor = CASE
                            WHEN managed_sync_state.server_cursor IS NULL
                              OR CAST(excluded.server_cursor AS INTEGER) > CAST(managed_sync_state.server_cursor AS INTEGER)
                            THEN excluded.server_cursor
                            ELSE managed_sync_state.server_cursor
                        END,
                        updated_at = excluded.updated_at
                    """,
                    (
                        event["stream"],
                        event["cursor"],
                        effective_server_cursor,
                        timestamp,
                        int(advance_client_cursor),
                    ),
                )
                return True

    def drain(
        self,
        sender: SyncSender,
        *,
        now: Optional[Union[str, datetime]] = None,
        limit: int = 20,
    ) -> SyncDrainResult:
        timestamp = _timestamp(now)
        due = self.list_due(now=timestamp, limit=limit)
        result = SyncDrainResult(attempted=0, accepted=0, retried=0, blocked=0)

        for event in due:
            claim = self._begin_attempt(event.queue_id, timestamp)
            if claim is None:
                continue
            attempted, lease_id = claim
            try:
                response = sender(attempted.envelope)
            except Exception as exc:  # noqa: BLE001 - transport failures are retryable
                response = SyncSendResult(
                    status=0,
                    error=f"{type(exc).__name__}: {exc}",
                )

            if response.status in {200, 201}:
                marked = self._mark_accepted(attempted, response, timestamp, lease_id)
                result = SyncDrainResult(
                    attempted=result.attempted + 1,
                    accepted=result.accepted + int(marked),
                    retried=result.retried,
                    blocked=result.blocked,
                )
                continue

            if response.status in {0, 408, 425, 429} or response.status >= 500:
                marked = self._mark_retry(attempted, response, timestamp, lease_id)
                result = SyncDrainResult(
                    attempted=result.attempted + 1,
                    accepted=result.accepted,
                    retried=result.retried + int(marked),
                    blocked=result.blocked,
                )
                continue

            marked = self._mark_blocked(attempted, response, timestamp, lease_id)
            result = SyncDrainResult(
                attempted=result.attempted + 1,
                accepted=result.accepted,
                retried=result.retried,
                blocked=result.blocked + int(marked),
            )
        return result

    def requeue_blocked(
        self,
        queue_id: str,
        *,
        now: Optional[Union[str, datetime]] = None,
        reset_attempts: bool = False,
    ) -> QueuedSyncEvent:
        timestamp = _timestamp(now)
        with self.store.open() as database:
            with database.transaction() as connection:
                row = connection.execute(
                    "SELECT status FROM managed_sync_queue WHERE queue_id = ?",
                    (queue_id,),
                ).fetchone()
                if row is None:
                    raise SyncQueueError("sync queue event not found")
                if row["status"] != "blocked":
                    raise SyncQueueError("only blocked sync events can be requeued")
                connection.execute(
                    """
                    UPDATE managed_sync_queue
                    SET status = 'pending',
                        attempts = CASE WHEN ? THEN 0 ELSE attempts END,
                        last_error = NULL,
                        updated_at = ?,
                        next_attempt_at = ?
                    WHERE queue_id = ? AND status = 'blocked'
                    """,
                    (int(reset_attempts), timestamp, timestamp, queue_id),
                )
                row = connection.execute(
                    "SELECT * FROM managed_sync_queue WHERE queue_id = ?",
                    (queue_id,),
                ).fetchone()
                if row is None:
                    raise SyncQueueError("sync queue event disappeared")
                return _row_to_event(row)

    def _begin_attempt(
        self,
        queue_id: str,
        timestamp: str,
    ) -> Optional[tuple[QueuedSyncEvent, str]]:
        lease_id = str(uuid4())
        lease_until = _after_seconds(timestamp, self.lease_seconds)
        with self.store.open() as database:
            with database.transaction() as connection:
                connection.execute(
                    "DELETE FROM managed_sync_leases WHERE queue_id = ? AND lease_until <= ?",
                    (queue_id, timestamp),
                )
                try:
                    connection.execute(
                        """
                        INSERT INTO managed_sync_leases(queue_id, lease_id, lease_until, claimed_at)
                        SELECT ?, ?, ?, ?
                        WHERE EXISTS (
                            SELECT 1 FROM managed_sync_queue
                            WHERE queue_id = ? AND status IN ('pending', 'retry')
                        )
                        """,
                        (queue_id, lease_id, lease_until, timestamp, queue_id),
                    )
                except sqlite3.IntegrityError:
                    return None
                if connection.execute("SELECT changes()").fetchone()[0] != 1:
                    return None
                connection.execute(
                    """
                    UPDATE managed_sync_queue
                    SET attempts = attempts + 1,
                        updated_at = ?,
                        next_attempt_at = ?
                    WHERE queue_id = ? AND status IN ('pending', 'retry')
                    """,
                    (timestamp, timestamp, queue_id),
                )
                row = connection.execute(
                    "SELECT * FROM managed_sync_queue WHERE queue_id = ?",
                    (queue_id,),
                ).fetchone()
                if row is None or row["status"] not in {"pending", "retry"}:
                    connection.execute(
                        "DELETE FROM managed_sync_leases WHERE lease_id = ?",
                        (lease_id,),
                    )
                    return None
                return _row_to_event(row), lease_id

    def _mark_accepted(
        self,
        event: QueuedSyncEvent,
        response: SyncSendResult,
        timestamp: str,
        lease_id: str,
    ) -> bool:
        with self.store.open() as database:
            with database.transaction() as connection:
                existing = connection.execute(
                    "SELECT server_cursor FROM managed_sync_state WHERE stream = ?",
                    (event.envelope.stream,),
                ).fetchone()
                server_cursor = response.server_cursor
                if (
                    existing is not None
                    and existing["server_cursor"] is not None
                    and server_cursor is not None
                    and int(existing["server_cursor"]) > int(server_cursor)
                ):
                    server_cursor = existing["server_cursor"]
                updated = connection.execute(
                    """
                    UPDATE managed_sync_queue
                    SET status = 'accepted',
                        server_cursor = ?,
                        accepted_at = ?,
                        last_error = NULL,
                        updated_at = ?
                    WHERE queue_id = ?
                      AND EXISTS (
                          SELECT 1 FROM managed_sync_leases
                          WHERE queue_id = ? AND lease_id = ?
                      )
                    """,
                    (server_cursor, timestamp, timestamp, event.queue_id, event.queue_id, lease_id),
                )
                if updated.rowcount != 1:
                    return False
                connection.execute(
                    "DELETE FROM managed_sync_leases WHERE queue_id = ? AND lease_id = ?",
                    (event.queue_id, lease_id),
                )
                connection.execute(
                    """
                    INSERT INTO managed_sync_state(stream, client_cursor, server_cursor, updated_at)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(stream) DO UPDATE SET
                        client_cursor = excluded.client_cursor,
                        server_cursor = COALESCE(excluded.server_cursor, managed_sync_state.server_cursor),
                        updated_at = excluded.updated_at
                    """,
                    (
                        event.envelope.stream,
                        event.envelope.cursor,
                        server_cursor,
                        timestamp,
                    ),
                )
                return True

    def _mark_retry(
        self,
        event: QueuedSyncEvent,
        response: SyncSendResult,
        timestamp: str,
        lease_id: str,
    ) -> bool:
        delay = response.retry_after_seconds
        if delay is None:
            exponent = min(max(event.attempts - 1, 0), 31)
            delay = min(self.max_delay_seconds, self.base_delay_seconds * (2 ** exponent))
        delay = max(0, min(delay, self.max_delay_seconds))
        next_attempt_at = _after_seconds(timestamp, delay)
        with self.store.open() as database:
            with database.transaction() as connection:
                updated = connection.execute(
                    """
                    UPDATE managed_sync_queue
                    SET status = 'retry',
                        next_attempt_at = ?,
                        last_error = ?,
                        updated_at = ?
                                        WHERE queue_id = ?
                                            AND EXISTS (
                                                    SELECT 1 FROM managed_sync_leases
                                                    WHERE queue_id = ? AND lease_id = ?
                                            )
                    """,
                    (
                        next_attempt_at,
                        (response.error or f"HTTP {response.status}")[:500],
                        timestamp,
                        event.queue_id,
                        event.queue_id,
                        lease_id,
                    ),
                )
                if updated.rowcount != 1:
                    return False
                connection.execute(
                    "DELETE FROM managed_sync_leases WHERE queue_id = ? AND lease_id = ?",
                    (event.queue_id, lease_id),
                )
                return True

    def _mark_blocked(
        self,
        event: QueuedSyncEvent,
        response: SyncSendResult,
        timestamp: str,
        lease_id: str,
    ) -> bool:
        with self.store.open() as database:
            with database.transaction() as connection:
                updated = connection.execute(
                    """
                    UPDATE managed_sync_queue
                    SET status = 'blocked',
                        last_error = ?,
                        updated_at = ?
                                        WHERE queue_id = ?
                                            AND EXISTS (
                                                    SELECT 1 FROM managed_sync_leases
                                                    WHERE queue_id = ? AND lease_id = ?
                                            )
                    """,
                    (
                        (response.error or f"HTTP {response.status}")[:500],
                        timestamp,
                        event.queue_id,
                        event.queue_id,
                        lease_id,
                    ),
                )
                if updated.rowcount != 1:
                    return False
                connection.execute(
                    "DELETE FROM managed_sync_leases WHERE queue_id = ? AND lease_id = ?",
                    (event.queue_id, lease_id),
                )
                return True


class ManagedSyncHttpTransport:
    """Stdlib HTTP sender for the optional Managed sync endpoint."""

    def __init__(
        self,
        base_url: str,
        installation_id: str,
        access_token: str,
        *,
        timeout_seconds: float = 15.0,
    ) -> None:
        self.url = (
            f"{base_url.rstrip('/')}/managed/v1/installations/"
            f"{quote(installation_id, safe='')}/sync/events"
        )
        self.access_token = access_token
        self.timeout_seconds = timeout_seconds

    def __call__(self, envelope: ManagedSyncEnvelope) -> SyncSendResult:
        request = Request(
            self.url,
            data=json.dumps(envelope.to_request(), ensure_ascii=False).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                return self._result(response.status, response.headers, response.read())
        except HTTPError as error:
            return self._result(error.code, error.headers, error.read())

    @staticmethod
    def _result(status: int, headers: Any, raw_body: bytes) -> SyncSendResult:
        try:
            body = json.loads(raw_body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            body = {}
        sync = body.get("sync") if isinstance(body, dict) else None
        error = body.get("error") if isinstance(body, dict) else None
        retry_after = None
        if headers is not None:
            try:
                retry_after = int(headers.get("retry-after")) if headers.get("retry-after") else None
            except (TypeError, ValueError):
                retry_after = None
        return SyncSendResult(
            status=status,
            server_cursor=(str(sync["serverCursor"]) if isinstance(sync, dict) and sync.get("serverCursor") is not None else None),
            duplicate=bool(sync.get("duplicate")) if isinstance(sync, dict) else False,
            retry_after_seconds=retry_after,
            error=(str(error.get("message")) if isinstance(error, dict) and error.get("message") else None),
        )


class ManagedSyncHttpClient:
    """Read Managed sync status and recover accepted events after lost responses."""

    def __init__(
        self,
        base_url: str,
        installation_id: str,
        access_token: str,
        *,
        timeout_seconds: float = 15.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.installation_id = installation_id
        self.access_token = access_token
        self.timeout_seconds = timeout_seconds

    def status(self, stream: str) -> dict[str, Optional[str]]:
        stream = _validate_stream(stream)
        body = self._get_json(
            "/managed/v1/installations/{}/sync/status".format(
                quote(self.installation_id, safe="")
            ),
            {"stream": stream},
        )
        sync = body.get("sync")
        if not isinstance(sync, dict):
            raise SyncQueueError("Managed sync status response is invalid")
        if (
            sync.get("installationId") != self.installation_id
            or sync.get("stream") != stream
        ):
            raise SyncQueueError("Managed sync status identity is invalid")
        server_cursor = sync.get("serverCursor")
        if not isinstance(server_cursor, str) or not server_cursor.isdigit():
            raise SyncQueueError("Managed sync status has an invalid server cursor")
        return {
            "installation_id": str(sync.get("installationId", self.installation_id)),
            "stream": str(sync.get("stream", stream)),
            "client_cursor": (
                str(sync["cursor"]) if sync.get("cursor") is not None else None
            ),
            "server_cursor": server_cursor,
        }

    def pull(
        self,
        stream: str,
        *,
        after: str = "0",
        limit: int = 100,
    ) -> ManagedSyncPullResult:
        stream = _validate_stream(stream)
        if not isinstance(after, str) or not after.isdigit():
            raise ValueError("server cursor must be a non-negative integer string")
        if limit < 1 or limit > 100:
            raise ValueError("sync pull limit must be between 1 and 100")
        body = self._get_json(
            "/managed/v1/installations/{}/sync/events".format(
                quote(self.installation_id, safe="")
            ),
            {"stream": stream, "after": after, "limit": str(limit)},
        )
        sync = body.get("sync")
        if not isinstance(sync, dict):
            raise SyncQueueError("Managed sync pull response is invalid")
        installation_id = sync.get("installationId")
        response_stream = sync.get("stream")
        if installation_id != self.installation_id or response_stream != stream:
            raise SyncQueueError("Managed sync pull identity is invalid")
        raw_events = sync.get("events")
        if not isinstance(raw_events, list):
            raise SyncQueueError("Managed sync pull events are invalid")
        events: list[ManagedSyncPulledEvent] = []
        seen_event_ids: set[str] = set()
        previous_sequence = int(after)
        for raw_event in raw_events:
            if not isinstance(raw_event, dict):
                raise SyncQueueError("Managed sync pull event is invalid")
            payload = raw_event.get("payload")
            if not isinstance(payload, dict):
                raise SyncQueueError("Managed sync pull payload is invalid")
            server_sequence = raw_event.get("serverSequence")
            if not isinstance(server_sequence, str) or not server_sequence.isdigit() or server_sequence == "0":
                raise SyncQueueError("Managed sync pull event has an invalid sequence")
            if int(server_sequence) <= previous_sequence:
                raise SyncQueueError("Managed sync pull events are out of order")
            previous_sequence = int(server_sequence)
            event_id = raw_event.get("eventId")
            event_stream = raw_event.get("stream")
            entity_type = raw_event.get("entityType")
            entity_id = raw_event.get("entityId")
            idempotency_key = raw_event.get("idempotencyKey")
            payload_sha256 = raw_event.get("payloadSha256")
            if (
                not isinstance(event_id, str)
                or not 1 <= len(event_id) <= 128
                or event_id in seen_event_ids
                or not isinstance(event_stream, str)
                or event_stream != stream
                or not isinstance(entity_type, str)
                or entity_type != "interaction.signal"
                or not isinstance(entity_id, str)
                or not 1 <= len(entity_id) <= 128
                or not isinstance(idempotency_key, str)
                or not 1 <= len(idempotency_key) <= 256
                or not isinstance(payload_sha256, str)
                or not re.fullmatch(r"[0-9a-f]{64}", payload_sha256)
                or sha256_text(canonical_json(payload)) != payload_sha256
            ):
                raise SyncQueueError("Managed sync pull event failed validation")
            seen_event_ids.add(event_id)
            try:
                _validate_signal_payload(payload)
                occurred_at = _wire_timestamp(raw_event.get("occurredAt"), "occurredAt")
                received_at = _wire_timestamp(raw_event.get("receivedAt"), "receivedAt")
            except (TypeError, ValueError) as exc:
                raise SyncQueueError("Managed sync pull event failed validation") from exc
            if _timestamp(occurred_at) != _timestamp(payload["timestamp"]):
                raise SyncQueueError("Managed sync pull event timestamp mismatch")
            events.append(
                ManagedSyncPulledEvent(
                    server_sequence=server_sequence,
                    event_id=event_id,
                    stream=event_stream,
                    entity_type=entity_type,
                    entity_id=entity_id,
                    idempotency_key=idempotency_key,
                    payload=payload,
                    payload_sha256=payload_sha256,
                    occurred_at=occurred_at,
                    received_at=received_at,
                )
            )
        server_cursor = sync.get("serverCursor")
        next_cursor = sync.get("nextCursor")
        has_more = sync.get("hasMore")
        if (
            not isinstance(server_cursor, str)
            or not server_cursor.isdigit()
            or not isinstance(next_cursor, str)
            or not next_cursor.isdigit()
            or int(next_cursor) < int(after)
            or int(next_cursor) > int(server_cursor)
            or (events and int(next_cursor) < int(events[-1].server_sequence))
            or not isinstance(has_more, bool)
            or (has_more and not events)
        ):
            raise SyncQueueError("Managed sync pull cursors are invalid")
        return ManagedSyncPullResult(
            installation_id=installation_id,
            stream=response_stream,
            client_cursor=(str(sync["cursor"]) if sync.get("cursor") is not None else None),
            server_cursor=server_cursor,
            next_cursor=next_cursor,
            has_more=has_more,
            events=tuple(events),
        )

    def recover(
        self,
        queue: ManagedSyncQueue,
        stream: str,
        *,
        limit: int = 100,
        now: Optional[Union[str, datetime]] = None,
    ) -> ManagedSyncPullResult:
        remote = self.status(stream)
        local_server_cursor = queue.stream_state(stream)["server_cursor"] or "0"
        if int(local_server_cursor) > int(remote["server_cursor"] or "0"):
            raise SyncQueueError("local server cursor is ahead of Managed")
        result = self.pull(stream, after=local_server_cursor, limit=limit)
        for event in result.events:
            queue.acknowledge_server_event(event.event_id, event.server_sequence, now=now)
        queue.record_server_cursor(stream, result.next_cursor, now=now)
        return result

    def _get_json(self, path: str, query: dict[str, str]) -> dict[str, Any]:
        from urllib.parse import urlencode

        request = Request(
            f"{self.base_url}{path}?{urlencode(query)}",
            headers={
                "Authorization": f"Bearer {self.access_token}",
                "Accept": "application/json",
            },
            method="GET",
        )
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                raw_body = response.read()
        except HTTPError as error:
            try:
                detail = json.loads(error.read().decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                detail = {}
            error_detail = detail.get("error") if isinstance(detail, dict) else None
            message = error_detail.get("message") if isinstance(error_detail, dict) else None
            suffix = f": {message}" if message else ""
            raise SyncQueueError(f"Managed sync HTTP {error.code}{suffix}") from error
        try:
            body = json.loads(raw_body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise SyncQueueError("Managed sync response is not JSON") from exc
        if not isinstance(body, dict):
            raise SyncQueueError("Managed sync response must be an object")
        return body