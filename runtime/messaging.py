"""Identity-Native Messaging – local skeleton (Phase 3).

File-backed store under <install>/.ie/messaging/.
Does not replace Interaction Signals; sits alongside them.
"""

from __future__ import annotations

import json
import re
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

UUID_V7_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-7[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$",
    re.IGNORECASE,
)


class MessagingError(Exception):
    """User-facing messaging error."""


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _new_uuid_v7() -> str:
    """Best-effort UUID v7: time-ordered prefix + random suffix.

    Python <3.13 has no stdlib uuid7; we synthesize a compatible string
    so schemas and docs stay consistent. Not cryptographically identical
    to RFC 9562, but unique and time-sortable for local use.
    """
    ts_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    # 48-bit timestamp
    time_hi = (ts_ms >> 16) & 0xFFFFFFFF
    time_mid = ts_ms & 0xFFFF
    rand = uuid.uuid4().int
    # version 7 nibble
    version_and_rand = 0x7000 | ((rand >> 62) & 0x0FFF)
    # variant 10xx
    variant_and_rand = 0x8000 | ((rand >> 48) & 0x3FFF)
    node = rand & 0xFFFFFFFFFFFF
    return (
        f"{time_hi:08x}-{time_mid:04x}-{version_and_rand:04x}-"
        f"{variant_and_rand:04x}-{node:012x}"
    )


def messaging_root(install_root: Path) -> Path:
    return install_root.resolve() / ".ie" / "messaging"


def ensure_layout(install_root: Path) -> Path:
    root = messaging_root(install_root)
    for sub in ("cards", "inbox", "outbox", "receipts"):
        (root / sub).mkdir(parents=True, exist_ok=True)
    return root


def _card_path(install_root: Path, identity_id: str) -> Path:
    return messaging_root(install_root) / "cards" / f"{identity_id}.json"


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Identity Cards
# ---------------------------------------------------------------------------


def register_card(install_root: Path, card: dict) -> dict:
    """Validate minimal required fields and persist a Card."""
    ensure_layout(install_root)
    identity_id = card.get("identityId")
    if not identity_id or not isinstance(identity_id, str):
        raise MessagingError("card.identityId is required")
    if not UUID_V7_RE.match(identity_id):
        raise MessagingError("card.identityId must be UUID v7 format")
    for key in ("name", "type", "version", "endpoints"):
        if key not in card:
            raise MessagingError(f"card.{key} is required")
    if not isinstance(card.get("endpoints"), dict) or "messaging" not in card["endpoints"]:
        raise MessagingError("card.endpoints.messaging is required")
    if card.get("version") != "0.1":
        raise MessagingError("card.version must be '0.1' for this skeleton")

    card = dict(card)
    card.setdefault("updatedAt", _utc_now())
    path = _card_path(install_root, identity_id)
    _write_json(path, card)
    return card


def list_cards(install_root: Path) -> list[dict]:
    ensure_layout(install_root)
    cards_dir = messaging_root(install_root) / "cards"
    out: list[dict] = []
    for path in sorted(cards_dir.glob("*.json")):
        try:
            out.append(_read_json(path))
        except (OSError, json.JSONDecodeError):
            continue
    return out


def get_card(install_root: Path, identity_id: str) -> Optional[dict]:
    path = _card_path(install_root, identity_id)
    if not path.is_file():
        return None
    return _read_json(path)


# ---------------------------------------------------------------------------
# Recognition
# ---------------------------------------------------------------------------


def recognition_allows(card: dict, sender_id: str, signal_type: str) -> tuple[bool, str]:
    """Evaluate the public recognitionPolicy on a Card.

    Returns (allowed, reason).
    Full private policy stays outside this skeleton.
    """
    policy = card.get("recognitionPolicy") or {}
    default = policy.get("default", "accept-known")
    allowlist = set(policy.get("allowlist") or [])
    blocklist = set(policy.get("blocklist") or [])

    if sender_id in blocklist:
        return False, "sender on blocklist"
    if sender_id in allowlist:
        return True, "sender on allowlist"

    if default == "accept-all":
        return True, "default accept-all"
    if default == "reject-unknown":
        return False, "default reject-unknown"
    if default == "manual":
        return False, "default manual – requires explicit consent"
    # accept-known: only allowlist (already checked) or same owner scope later
    if default == "accept-known":
        return False, "default accept-known – sender not on allowlist"
    return False, f"unknown recognition default: {default}"


def consent_required(envelope: dict) -> bool:
    hints = envelope.get("impactHints") or []
    return any(h in ("mass-altering", "stem-altering") for h in hints)


# ---------------------------------------------------------------------------
# Send / Inbox / Receipts
# ---------------------------------------------------------------------------


@dataclass
class SendResult:
    envelope: dict
    receipt: dict
    status: str  # delivered | rejected

    def to_dict(self) -> dict:
        return {
            "status": self.status,
            "envelope": self.envelope,
            "receipt": self.receipt,
        }


def _target_id(to_field: Any) -> str:
    if isinstance(to_field, str):
        return to_field
    if isinstance(to_field, dict) and "collectiveId" in to_field:
        return to_field["collectiveId"]
    raise MessagingError("envelope.to must be identityId string or {collectiveId}")


def send_envelope(install_root: Path, envelope: dict) -> SendResult:
    """Validate, recognition-check, persist to outbox + target inbox, emit receipt."""
    ensure_layout(install_root)
    env = dict(envelope)

    if "messageId" not in env:
        env["messageId"] = _new_uuid_v7()
    if "createdAt" not in env:
        env["createdAt"] = _utc_now()

    for key in ("from", "to", "signal", "payload"):
        if key not in env:
            raise MessagingError(f"envelope.{key} is required")

    signal = env["signal"]
    if not isinstance(signal, dict) or "type" not in signal:
        raise MessagingError("envelope.signal.type is required")

    target = _target_id(env["to"])
    card = get_card(install_root, target)
    if card is None:
        receipt = _make_receipt(
            env,
            receipt_type="rejected",
            from_id=target,
            reason="target Identity Card not found in local store",
        )
        _persist_receipt(install_root, receipt)
        _write_json(
            messaging_root(install_root) / "outbox" / f"{env['messageId']}.json", env
        )
        return SendResult(envelope=env, receipt=receipt, status="rejected")

    allowed, reason = recognition_allows(card, env["from"], signal["type"])
    if not allowed:
        receipt = _make_receipt(
            env, receipt_type="rejected", from_id=target, reason=f"recognition: {reason}"
        )
        _persist_receipt(install_root, receipt)
        _write_json(
            messaging_root(install_root) / "outbox" / f"{env['messageId']}.json", env
        )
        return SendResult(envelope=env, receipt=receipt, status="rejected")

    if consent_required(env):
        # Skeleton: mass-/stem-altering always needs a prior consent-grant message.
        # We reject with a clear reason so the sender can request consent.
        receipt = _make_receipt(
            env,
            receipt_type="rejected",
            from_id=target,
            reason="impactHints require explicit consent (mass-altering or stem-altering)",
        )
        _persist_receipt(install_root, receipt)
        _write_json(
            messaging_root(install_root) / "outbox" / f"{env['messageId']}.json", env
        )
        return SendResult(envelope=env, receipt=receipt, status="rejected")

    # Deliver locally: same Space store acts as both outbox and inbox
    _write_json(
        messaging_root(install_root) / "outbox" / f"{env['messageId']}.json", env
    )
    _write_json(
        messaging_root(install_root) / "inbox" / f"{env['messageId']}.json", env
    )
    receipt = _make_receipt(
        env, receipt_type="delivered", from_id=target, reason="local delivery"
    )
    _persist_receipt(install_root, receipt)
    return SendResult(envelope=env, receipt=receipt, status="delivered")


def _make_receipt(
    envelope: dict, *,
    receipt_type: str,
    from_id: str,
    reason: str,
) -> dict:
    return {
        "messageId": _new_uuid_v7(),
        "receiptType": receipt_type,
        "from": from_id,
        "to": envelope["from"],
        "createdAt": _utc_now(),
        "reason": reason,
        "inReplyTo": envelope["messageId"],
        "signal": {"type": "receipt"},
        "payload": {
            "contentType": "application/json",
            "inline": json.dumps({"receiptType": receipt_type, "reason": reason}),
        },
    }


def _persist_receipt(install_root: Path, receipt: dict) -> None:
    path = messaging_root(install_root) / "receipts" / f"{receipt['messageId']}.json"
    _write_json(path, receipt)


def list_inbox(install_root: Path) -> list[dict]:
    ensure_layout(install_root)
    inbox = messaging_root(install_root) / "inbox"
    out: list[dict] = []
    for path in sorted(inbox.glob("*.json"), reverse=True):
        try:
            out.append(_read_json(path))
        except (OSError, json.JSONDecodeError):
            continue
    return out


def get_message(install_root: Path, message_id: str) -> Optional[dict]:
    ensure_layout(install_root)
    root = messaging_root(install_root)
    for folder in ("inbox", "outbox"):
        path = root / folder / f"{message_id}.json"
        if path.is_file():
            return _read_json(path)
    return None
