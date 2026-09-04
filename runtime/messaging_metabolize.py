"""Metabolization of accepted messaging Envelopes (Biology Single).

After Recognition/delivery, an Identity may metabolize a message:
classify, optionally update geometry via Mature, emit a metabolization receipt.

This module is the bridge from messaging into Mature. It never forces a
Mature commit – callers opt in with commit_mature=True when a full IE
install (sqlite) is present.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

from .database import database_path
from .messaging import (
    MessagingError,
    _make_receipt,
    _new_uuid_v7,
    _persist_receipt,
    _utc_now,
    _write_json,
    ensure_layout,
    get_message,
    messaging_root,
)


def _metabolized_path(install_root: Path, message_id: str) -> Path:
    return messaging_root(install_root) / "metabolized" / f"{message_id}.json"


def get_metabolization(install_root: Path, message_id: str) -> Optional[dict]:
    path = _metabolized_path(install_root, message_id)
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def list_metabolizations(install_root: Path) -> list[dict]:
    ensure_layout(install_root)
    directory = messaging_root(install_root) / "metabolized"
    records: list[dict] = []
    for path in sorted(directory.glob("*.json"), reverse=True):
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(record, dict):
            records.append(record)
    return records


def metabolize_message(
    install_root: Path,
    message_id: str,
    *,
    notes: str = "",
    classification: Optional[str] = None,
    commit_mature: bool = False,
    emit_receipt: bool = True,
) -> dict[str, Any]:
    """Record metabolization of an inbox/outbox message.

    Steps (Biology Single Metabolism operationalization):
    1. Ingestion – message must already exist in local store
    2. Classification – optional free-text / signal-type based label
    3. Transformation / State update – optional Mature commit
    4. Emission – metabolization receipt to original sender
    """
    ensure_layout(install_root)
    (messaging_root(install_root) / "metabolized").mkdir(parents=True, exist_ok=True)

    msg = get_message(install_root, message_id)
    if msg is None:
        raise MessagingError(f"message not found: {message_id}")

    existing = get_metabolization(install_root, message_id)
    if existing is not None:
        return {"status": "already-metabolized", "record": existing}

    signal_type = (msg.get("signal") or {}).get("type", "unknown")
    class_label = classification or signal_type

    record: dict[str, Any] = {
        "metabolizationId": _new_uuid_v7(),
        "messageId": message_id,
        "from": msg.get("from"),
        "to": msg.get("to"),
        "signalType": signal_type,
        "classification": class_label,
        "notes": notes or "",
        "metabolizedAt": _utc_now(),
        "matureId": None,
    }

    mature_result = None
    if commit_mature:
        if not database_path(install_root).is_file():
            raise MessagingError(
                "commit_mature=True requires an IE sqlite install under the root"
            )
        mature_result = _commit_message_mature(
            install_root, msg, notes=notes or f"metabolized message {message_id}"
        )
        record["matureId"] = mature_result.get("mature_id")

    _write_json(_metabolized_path(install_root, message_id), record)

    receipt = None
    if emit_receipt and msg.get("from"):
        receipt = _make_receipt(
            msg,
            receipt_type="metabolized",
            from_id=str(msg.get("to") or "local"),
            reason=f"metabolized as {class_label}",
        )
        receipt["metabolizationId"] = record["metabolizationId"]
        if record["matureId"]:
            receipt["matureId"] = record["matureId"]
        _persist_receipt(install_root, receipt)

    return {
        "status": "metabolized",
        "record": record,
        "receipt": receipt,
        "mature": mature_result,
    }


def _commit_message_mature(
    install_root: Path,
    msg: dict,
    *,
    notes: str,
) -> dict:
    """Write a message snapshot under the install and commit a Mature step."""
    from .mature import MatureError, commit_mature

    evidence_dir = install_root / "trajectory" / "messaging"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    message_id = msg.get("messageId") or _new_uuid_v7()
    evidence_path = evidence_dir / f"{message_id}.json"
    evidence_path.write_text(
        json.dumps(msg, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    relative = f"trajectory/messaging/{message_id}.json"

    signal_type = (msg.get("signal") or {}).get("type", "message")
    try:
        result = commit_mature(
            install_root,
            source_refs=[relative],
            notes=notes,
            stem_differential={
                "state_delta_summary": (
                    f"Metabolized inbound message from {msg.get('from')} "
                    f"(signal={signal_type})"
                ),
            },
            substance={
                "last_messaging_metabolization": {
                    "messageId": message_id,
                    "from": msg.get("from"),
                    "signalType": signal_type,
                }
            },
            workspace_changes=[
                {
                    "kind": "observation",
                    "title": f"Message metabolized: {signal_type}",
                    "content": notes or f"Processed message {message_id}",
                    "source_ref": relative,
                    "tags": ["messaging", "metabolization"],
                }
            ],
            capture_snapshots=True,
        )
    except MatureError as exc:
        raise MessagingError(f"Mature commit failed: {exc}") from exc
    return result.to_dict() if hasattr(result, "to_dict") else dict(result)
