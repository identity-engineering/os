"""SQLite-backed projections for the local Surface Runtime."""

from __future__ import annotations

import json
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator, Optional, Union
from uuid import uuid4

from .database import Database, DatabaseError, canonical_json, database_path, sha256_text, utcnow
from .geometry import GeometryReceipt
from .models import ForeignEstimateRecord, InteractionSignal, Receipt
from .policy import LocalPolicy


def install_root_from_registry(registry_root: Union[str, Path]) -> Path:
    path = Path(registry_root).expanduser().resolve()
    return path.parent if path.name == "registry" else path


def canonical_signal_payload(signal: InteractionSignal) -> dict[str, Any]:
    """Return only validated contract fields, without a raw transport envelope."""
    return {
        "from": signal.from_handle,
        "to": signal.to_handle,
        "timestamp": signal.timestamp,
        "existence": signal.existence,
        "interaction_depth_delta": signal.interaction_depth_delta,
        "sender_emergent_mass": signal.sender_emergent_mass,
        "sender_last_mature_at": signal.sender_last_mature_at,
        "coarse_mass_estimate": signal.coarse_mass_estimate,
        "mass_confidence": signal.mass_confidence,
        "dimensions_delta": signal.dimensions_delta,
        "relation_pull": signal.relation_pull,
        "schema_version": signal.schema_version,
        "transport": signal.transport,
        "in_reply_to_request_id": signal.in_reply_to_request_id,
    }


def _timestamp_key(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _is_at_least_as_new(candidate: Optional[str], current: Optional[str]) -> bool:
    if not current:
        return bool(candidate)
    if not candidate:
        return False
    candidate_key = _timestamp_key(candidate)
    current_key = _timestamp_key(current)
    if candidate_key is not None and current_key is not None:
        return candidate_key >= current_key
    return str(candidate) >= str(current)


def _persist_registry_projection(
    conn,
    *,
    identity_id: str,
    signal: InteractionSignal,
    fields_to_apply: list[str],
    event_id: str,
    received_at: str,
) -> None:
    """Project accepted signal continuity and public freshness into the Registry."""
    row = conn.execute(
        """
        SELECT * FROM registry_entries
        WHERE identity_id = ? AND peer_handle = ?
        """,
        (identity_id, signal.from_handle),
    ).fetchone()
    if row is None:
        entry: dict[str, Any] = {
            "entry_id": str(uuid4()),
            "identity_id": identity_id,
            "peer_handle": signal.from_handle,
            "preferred_name": None,
            "substrate": None,
            "description": "",
            "first_noticed": signal.timestamp,
            "last_interaction": signal.timestamp,
            "interaction_count": 1,
            "interaction_depth": (
                float(signal.interaction_depth_delta)
                if "interaction_depth_delta" in fields_to_apply
                else 0.0
            ),
            "my_mass_estimate": None,
            "mass_confidence": None,
            "estimate_updated_at": None,
            "estimate_as_of_peer_mature_at": None,
            "peer_last_mature_at": (
                signal.sender_last_mature_at
                if "sender_last_mature_at" in fields_to_apply
                else None
            ),
            "peer_last_mature_seen_at": (
                received_at
                if "sender_last_mature_at" in fields_to_apply
                else None
            ),
            "recognition_json": "{}",
            "relation_json": "{}",
            "effect_on_me_json": "{}",
            "perceived_ownership_json": "{}",
            "privacy_json": "{}",
            "tags_json": "[]",
            "notes": "",
            "source": "signal",
            "revision": 1,
            "created_at": received_at,
            "updated_at": received_at,
        }
        fields = [
            "entry_id",
            "identity_id",
            "peer_handle",
            "preferred_name",
            "substrate",
            "description",
            "first_noticed",
            "last_interaction",
            "interaction_count",
            "interaction_depth",
            "my_mass_estimate",
            "mass_confidence",
            "estimate_updated_at",
            "estimate_as_of_peer_mature_at",
            "peer_last_mature_at",
            "peer_last_mature_seen_at",
            "recognition_json",
            "relation_json",
            "effect_on_me_json",
            "perceived_ownership_json",
            "privacy_json",
            "tags_json",
            "notes",
            "source",
            "revision",
            "created_at",
            "updated_at",
        ]
        conn.execute(
            f"INSERT INTO registry_entries({', '.join(fields)}) "
            f"VALUES ({', '.join('?' for _ in fields)})",
            tuple(entry[field] for field in fields),
        )
    else:
        entry = dict(row)
        entry["last_interaction"] = (
            signal.timestamp
            if _is_at_least_as_new(signal.timestamp, entry["last_interaction"])
            else entry["last_interaction"]
        )
        entry["interaction_count"] = int(entry["interaction_count"]) + 1
        if "interaction_depth_delta" in fields_to_apply:
            entry["interaction_depth"] = min(
                1.0,
                float(entry["interaction_depth"])
                + float(signal.interaction_depth_delta),
            )
        if "sender_last_mature_at" in fields_to_apply:
            if _is_at_least_as_new(
                signal.sender_last_mature_at, entry["peer_last_mature_at"]
            ):
                entry["peer_last_mature_at"] = signal.sender_last_mature_at
            entry["peer_last_mature_seen_at"] = received_at
        entry["revision"] = int(entry["revision"]) + 1
        entry["updated_at"] = received_at
        fields = [
            field
            for field in entry
            if field not in {"entry_id", "identity_id", "peer_handle", "created_at"}
        ]
        conn.execute(
            f"UPDATE registry_entries SET {', '.join(f'{field} = ?' for field in fields)} "
            "WHERE entry_id = ?",
            tuple(entry[field] for field in fields) + (entry["entry_id"],),
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
        ) VALUES (?, ?, ?, 'signal', ?, NULL, ?, ?)
        """,
        (
            str(uuid4()),
            entry["entry_id"],
            entry["revision"],
            event_id,
            canonical_json(snapshot),
            received_at,
        ),
    )


class SQLiteStore:
    """Open the canonical database for one local install."""

    def __init__(self, install_root: Union[str, Path]):
        self.root = Path(install_root).expanduser().resolve()
        self.path = database_path(self.root)
        if not self.path.is_file():
            raise DatabaseError(f"No IE database under {self.root} (.ie/ie.sqlite3)")

    @classmethod
    def from_registry_root(cls, registry_root: Union[str, Path]) -> "SQLiteStore":
        return cls(install_root_from_registry(registry_root))

    @contextmanager
    def open(self) -> Iterator[Database]:
        with Database(self.path) as database:
            yield database

    def identity(self) -> Any:
        with self.open() as database:
            row = database.conn.execute(
                "SELECT * FROM identity LIMIT 1"
            ).fetchone()
        if row is None:
            raise DatabaseError(f"IE database has no local identity: {self.path}")
        return row

    def load_foreign(self, sender_handle: str) -> Optional[ForeignEstimateRecord]:
        identity = self.identity()
        with self.open() as database:
            row = database.conn.execute(
                "SELECT * FROM foreign_estimates WHERE identity_id = ? AND sender_handle = ?",
                (identity["identity_id"], sender_handle),
            ).fetchone()
        if row is None:
            return None
        return ForeignEstimateRecord(
            sender_handle=row["sender_handle"],
            sender_substrate=row["sender_substrate"],
            first_signal_at=row["first_signal_at"],
            last_signal_at=row["last_signal_at"],
            signal_count=row["signal_count"],
            accumulated_depth=row["accumulated_depth"],
            last_depth_delta=row["last_depth_delta"],
            existence_confirmed=bool(row["existence_confirmed"]),
            coarse_mass_estimate=row["coarse_mass_estimate"],
            mass_confidence=row["mass_confidence"],
            mass_estimate_at=row["mass_estimate_at"],
            dimensions_delta=json.loads(row["dimensions_delta_json"])
            if row["dimensions_delta_json"]
            else None,
            relation_pull=row["relation_pull"],
            sender_emergent_mass=row["sender_emergent_mass"],
            sender_emergent_mass_at=row["sender_emergent_mass_at"],
            sender_last_mature_at=row["sender_last_mature_at"],
            sender_last_mature_seen_at=row["sender_last_mature_seen_at"],
            last_receipt_id=row["last_receipt_id"],
            quarantine=bool(row["quarantine"]),
            notes=row["notes"],
        )

    def list_foreign_handles(self) -> list[str]:
        identity = self.identity()
        with self.open() as database:
            rows = database.conn.execute(
                "SELECT sender_handle FROM foreign_estimates WHERE identity_id = ? ORDER BY sender_handle",
                (identity["identity_id"],),
            ).fetchall()
        return [row[0] for row in rows]

    def save_foreign(self, record: ForeignEstimateRecord) -> None:
        identity = self.identity()
        with self.open() as database:
            with database.transaction() as conn:
                conn.execute(
                    """
                    INSERT INTO foreign_estimates(
                        identity_id, sender_handle, sender_substrate, first_signal_at,
                        last_signal_at, signal_count, accumulated_depth, last_depth_delta,
                        existence_confirmed, coarse_mass_estimate, mass_confidence,
                        mass_estimate_at, dimensions_delta_json, relation_pull,
                        sender_emergent_mass, sender_emergent_mass_at,
                        sender_last_mature_at, sender_last_mature_seen_at,
                        last_receipt_id, quarantine, notes
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(identity_id, sender_handle) DO UPDATE SET
                        sender_substrate = excluded.sender_substrate,
                        first_signal_at = excluded.first_signal_at,
                        last_signal_at = excluded.last_signal_at,
                        signal_count = excluded.signal_count,
                        accumulated_depth = excluded.accumulated_depth,
                        last_depth_delta = excluded.last_depth_delta,
                        existence_confirmed = excluded.existence_confirmed,
                        coarse_mass_estimate = excluded.coarse_mass_estimate,
                        mass_confidence = excluded.mass_confidence,
                        mass_estimate_at = excluded.mass_estimate_at,
                        dimensions_delta_json = excluded.dimensions_delta_json,
                        relation_pull = excluded.relation_pull,
                        sender_emergent_mass = excluded.sender_emergent_mass,
                        sender_emergent_mass_at = excluded.sender_emergent_mass_at,
                        sender_last_mature_at = excluded.sender_last_mature_at,
                        sender_last_mature_seen_at = excluded.sender_last_mature_seen_at,
                        last_receipt_id = excluded.last_receipt_id,
                        quarantine = excluded.quarantine,
                        notes = excluded.notes
                    """,
                    (
                        identity["identity_id"],
                        record.sender_handle,
                        record.sender_substrate,
                        record.first_signal_at,
                        record.last_signal_at,
                        record.signal_count,
                        record.accumulated_depth,
                        record.last_depth_delta,
                        int(record.existence_confirmed),
                        record.coarse_mass_estimate,
                        record.mass_confidence,
                        record.mass_estimate_at,
                        canonical_json(record.dimensions_delta)
                        if record.dimensions_delta is not None
                        else None,
                        record.relation_pull,
                        record.sender_emergent_mass,
                        record.sender_emergent_mass_at,
                        record.sender_last_mature_at,
                        record.sender_last_mature_seen_at,
                        record.last_receipt_id,
                        int(record.quarantine),
                        record.notes,
                    ),
                )

    def load_policy(self, *, open_consent: bool = False) -> LocalPolicy:
        identity = self.identity()
        with self.open() as database:
            conn = database.conn
            grants: dict[str, set[str]] = {}
            for row in conn.execute(
                """
                SELECT sender_handle, field_name
                FROM consent_grants
                WHERE identity_id = ? AND revoked_at IS NULL
                ORDER BY granted_at DESC
                """,
                (identity["identity_id"],),
            ).fetchall():
                grants.setdefault(row["sender_handle"], set()).add(row["field_name"])
            quarantined = {
                row["sender_handle"]
                for row in conn.execute(
                    """
                    SELECT sender_handle FROM quarantines
                    WHERE identity_id = ? AND active = 1 AND revoked_at IS NULL
                    """,
                    (identity["identity_id"],),
                ).fetchall()
            }
        return LocalPolicy(
            open_consent=open_consent,
            grants=grants,
            quarantined_handles=quarantined,
        )

    def persist_signal(
        self,
        signal: InteractionSignal,
        receipt: Receipt,
        *,
        fields_to_apply: list[str],
        quarantine: bool,
        geometry: Optional[GeometryReceipt],
        prior_record: Optional[ForeignEstimateRecord],
    ) -> None:
        identity = self.identity()
        payload = canonical_signal_payload(signal)
        payload_json = canonical_json(payload)
        received_at = utcnow()
        now = signal.timestamp or received_at
        event_id = receipt.event_id
        if not event_id:
            raise DatabaseError("apply receipt is missing its event_id")

        with self.open() as database:
            with database.transaction() as conn:
                conn.execute(
                    """
                    INSERT INTO interaction_events(
                        event_id, install_id, from_handle, to_handle, signal_timestamp,
                        received_at, schema_version, transport, canonical_payload_json,
                        payload_sha256, in_reply_to_request_id
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        event_id,
                        identity["install_id"],
                        signal.from_handle,
                        signal.to_handle,
                        signal.timestamp,
                        received_at,
                        signal.schema_version,
                        signal.transport,
                        payload_json,
                        sha256_text(payload_json),
                        signal.in_reply_to_request_id,
                    ),
                )
                conn.execute(
                    """
                    INSERT INTO apply_receipts(
                        receipt_id, event_id, status, timestamp, from_handle, to_handle,
                        applied_fields_json, rejected_fields_json, reason, quarantine
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        receipt.receipt_id,
                        event_id,
                        receipt.status.value,
                        receipt.timestamp,
                        receipt.from_handle,
                        receipt.to_handle,
                        canonical_json(receipt.applied_fields),
                        canonical_json(receipt.rejected_fields),
                        receipt.reason,
                        int(receipt.quarantine),
                    ),
                )

                if fields_to_apply:
                    previous = prior_record
                    if previous is None:
                        conn.execute(
                            """
                            INSERT INTO foreign_estimates(
                                identity_id, sender_handle, first_signal_at, last_signal_at,
                                signal_count, accumulated_depth, last_depth_delta,
                                existence_confirmed, quarantine
                            ) VALUES (?, ?, ?, ?, 0, 0.0, 0.0, 0, ?)
                            """,
                            (identity["identity_id"], signal.from_handle, now, now, int(quarantine)),
                        )

                    updates: dict[str, Any] = {
                        "last_signal_at": now,
                        "signal_count": (previous.signal_count if previous else 0) + 1,
                        "quarantine": int(quarantine),
                    }
                    if "existence" in fields_to_apply:
                        updates["existence_confirmed"] = 1
                    if "interaction_depth_delta" in fields_to_apply:
                        updates["last_depth_delta"] = float(signal.interaction_depth_delta)
                        updates["accumulated_depth"] = (
                            float(previous.accumulated_depth) if previous else 0.0
                        ) + float(signal.interaction_depth_delta)
                    if "sender_emergent_mass" in fields_to_apply:
                        updates["sender_emergent_mass"] = signal.sender_emergent_mass
                        updates["sender_emergent_mass_at"] = now
                    if "sender_last_mature_at" in fields_to_apply:
                        updates["sender_last_mature_at"] = signal.sender_last_mature_at
                        updates["sender_last_mature_seen_at"] = received_at
                    if "coarse_mass_estimate" in fields_to_apply:
                        updates["coarse_mass_estimate"] = signal.coarse_mass_estimate
                        updates["mass_estimate_at"] = now
                    if "mass_confidence" in fields_to_apply:
                        updates["mass_confidence"] = signal.mass_confidence
                    if "dimensions_delta" in fields_to_apply:
                        updates["dimensions_delta_json"] = canonical_json(signal.dimensions_delta)
                    if "relation_pull" in fields_to_apply:
                        updates["relation_pull"] = signal.relation_pull
                    updates["last_receipt_id"] = receipt.receipt_id

                    assignments = ", ".join(f"{column} = ?" for column in updates)
                    conn.execute(
                        f"UPDATE foreign_estimates SET {assignments} "
                        "WHERE identity_id = ? AND sender_handle = ?",
                        (*updates.values(), identity["identity_id"], signal.from_handle),
                    )
                    conn.execute(
                        "UPDATE identity SET last_signal_at = ?, updated_at = ? WHERE identity_id = ?",
                        (received_at, received_at, identity["identity_id"]),
                    )
                    _persist_registry_projection(
                        conn,
                        identity_id=identity["identity_id"],
                        signal=signal,
                        fields_to_apply=fields_to_apply,
                        event_id=event_id,
                        received_at=received_at,
                    )

                if signal.in_reply_to_request_id and receipt.status.value in {"applied", "partial", "accepted"}:
                    conn.execute(
                        """
                        UPDATE estimate_requests
                        SET status = 'answered', answered_at = ?, reply_receipt_id = ?, quarantine = 0
                        WHERE request_id = ? AND identity_id = ?
                        """,
                        (received_at, receipt.receipt_id, signal.in_reply_to_request_id, identity["identity_id"]),
                    )

                if geometry is not None:
                    data = geometry.to_dict()
                    conn.execute(
                        """
                        INSERT INTO geometry_receipts(
                            receipt_id, install_id, timestamp, mode, observer, target,
                            source_apply_receipt_id, relative_mass_proxy_json,
                            tension_components_json, degrees_of_freedom_json,
                            jurisdiction_shift_json, stem_differential_json,
                            ownership_move_json, optionality_delta_json, notes
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            data["receipt_id"],
                            identity["install_id"],
                            data["timestamp"],
                            data["mode"],
                            data["observer"],
                            data["target"],
                            receipt.receipt_id,
                            canonical_json(data["relative_mass_proxy"])
                            if data.get("relative_mass_proxy") is not None
                            else None,
                            canonical_json(data.get("tension_components") or []),
                            canonical_json(data["degrees_of_freedom"])
                            if data.get("degrees_of_freedom") is not None
                            else None,
                            canonical_json(data["jurisdiction_shift"])
                            if data.get("jurisdiction_shift") is not None
                            else None,
                            canonical_json(data["stem_differential"])
                            if data.get("stem_differential") is not None
                            else None,
                            canonical_json(data["ownership_move"])
                            if data.get("ownership_move") is not None
                            else None,
                            canonical_json(data["optionality_delta"])
                            if data.get("optionality_delta") is not None
                            else None,
                            data.get("notes") or "",
                        ),
                    )
                    conn.execute(
                        "INSERT INTO geometry_receipt_sources(receipt_id, source_kind, source_id) VALUES (?, 'apply_receipt', ?)",
                        (data["receipt_id"], receipt.receipt_id),
                    )
