"""Identity-Native Messaging – local runtime.

File-backed store under <install>/.ie/messaging/.
Does not replace Interaction Signals; sits alongside them.
"""

from __future__ import annotations

import json
import re
import sqlite3
import time
import uuid
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

UUID_V7_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-7[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$",
    re.IGNORECASE,
)

IMPACT_CLASSES = ("mass-altering", "stem-altering")
REGULATION_MODES = ("fan-out", "specialist", "central")


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
    time_hi = (ts_ms >> 16) & 0xFFFFFFFF
    time_mid = ts_ms & 0xFFFF
    rand = uuid.uuid4().int
    version_and_rand = 0x7000 | ((rand >> 62) & 0x0FFF)
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
    for sub in (
        "cards",
        "inbox",
        "outbox",
        "receipts",
        "consents",
        "consent_audit",
        "damping",
        "metabolized",
    ):
        (root / sub).mkdir(parents=True, exist_ok=True)
    return root


def _card_path(install_root: Path, identity_id: str) -> Path:
    return messaging_root(install_root) / "cards" / f"{identity_id}.json"


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _is_local_identity_id(install_root: Path, identity_id: str) -> bool:
    db_path = install_root.resolve() / ".ie" / "ie.sqlite3"
    if not db_path.is_file():
        return False
    try:
        with sqlite3.connect(db_path) as connection:
            row = connection.execute(
                "SELECT 1 FROM identity WHERE identity_id = ? LIMIT 1",
                (identity_id,),
            ).fetchone()
    except sqlite3.Error:
        return False
    return row is not None


# ---------------------------------------------------------------------------
# Identity Cards
# ---------------------------------------------------------------------------


def register_card(install_root: Path, card: dict) -> dict:
    """Validate minimal required fields and persist a Card."""
    ensure_layout(install_root)
    identity_id = card.get("identityId")
    if not identity_id or not isinstance(identity_id, str):
        raise MessagingError("card.identityId is required")
    if not UUID_V7_RE.match(identity_id) and not _is_local_identity_id(
        install_root, identity_id
    ):
        raise MessagingError(
            "card.identityId must be UUID v7 format or an existing local Identity ID"
        )
    for key in ("name", "type", "version", "endpoints"):
        if key not in card:
            raise MessagingError(f"card.{key} is required")
    if not isinstance(card.get("endpoints"), dict) or "messaging" not in card["endpoints"]:
        raise MessagingError("card.endpoints.messaging is required")
    if card.get("version") != "0.1":
        raise MessagingError("card.version must be '0.1' for this skeleton")

    # Soft-validate regulation block when present
    reg = card.get("regulation")
    if reg is not None:
        if not isinstance(reg, dict):
            raise MessagingError("card.regulation must be an object")
        routing = reg.get("routing")
        if routing is not None and routing not in REGULATION_MODES:
            raise MessagingError(
                f"card.regulation.routing must be one of {REGULATION_MODES}"
            )

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
    if default == "accept-known":
        return False, "default accept-known – sender not on allowlist"
    return False, f"unknown recognition default: {default}"


def consent_required(envelope: dict) -> bool:
    hints = envelope.get("impactHints") or []
    return any(h in IMPACT_CLASSES for h in hints)


# ---------------------------------------------------------------------------
# Consent grants (mass-/stem-altering)
# ---------------------------------------------------------------------------


def _consent_key(target_id: str, sender_id: str) -> str:
    return f"{target_id}__{sender_id}"


def _consent_path(install_root: Path, target_id: str, sender_id: str) -> Path:
    return messaging_root(install_root) / "consents" / f"{_consent_key(target_id, sender_id)}.json"


def _consent_audit_dir(install_root: Path) -> Path:
    return messaging_root(install_root) / "consent_audit"


def grant_consent(
    install_root: Path,
    *,
    target_id: str,
    sender_id: str,
    impact_classes: list[str],
    granted_by: Optional[str] = None,
) -> dict:
    """Record that target allows sender for the given impact classes."""
    ensure_layout(install_root)
    classes = sorted({c for c in impact_classes if c in IMPACT_CLASSES})
    if not classes:
        raise MessagingError("impact_classes must include mass-altering and/or stem-altering")

    path = _consent_path(install_root, target_id, sender_id)
    existing: dict = {}
    if path.is_file():
        try:
            existing = _read_json(path)
        except (OSError, json.JSONDecodeError):
            existing = {}

    previous_classes = sorted(set(existing.get("impactClasses") or []))
    merged = sorted(set(previous_classes) | set(classes))
    added_classes = sorted(set(merged) - set(previous_classes))
    now = _utc_now()
    record = {
        "targetId": target_id,
        "senderId": sender_id,
        "impactClasses": merged,
        "grantedBy": granted_by or target_id,
        "updatedAt": now,
        "createdAt": existing.get("createdAt") or now,
    }
    _write_json(path, record)
    audit = {
        "auditId": _new_uuid_v7(),
        "eventType": "consent-granted",
        "targetId": target_id,
        "senderId": sender_id,
        "requestedImpactClasses": classes,
        "addedImpactClasses": added_classes,
        "impactClasses": merged,
        "grantedBy": record["grantedBy"],
        "changed": bool(added_classes),
        "createdAt": now,
    }
    _write_json(_consent_audit_dir(install_root) / f"{audit['auditId']}.json", audit)
    return record


def has_consent(
    install_root: Path,
    *,
    target_id: str,
    sender_id: str,
    impact_classes: list[str],
) -> bool:
    path = _consent_path(install_root, target_id, sender_id)
    if not path.is_file():
        return False
    try:
        record = _read_json(path)
    except (OSError, json.JSONDecodeError):
        return False
    granted = set(record.get("impactClasses") or [])
    needed = {c for c in impact_classes if c in IMPACT_CLASSES}
    return bool(needed) and needed.issubset(granted)


def _apply_consent_grant_if_present(install_root: Path, env: dict, message_to: str) -> None:
    """If this is a consent-grant signal, persist the grant after delivery.

    Granter = env['from'] (becomes target_id of the grant).
    Grantee = message_to   (becomes sender_id of the grant).
    """
    signal = env.get("signal") or {}
    if signal.get("type") != "consent-grant":
        return
    payload = env.get("payload") or {}
    classes: list[str] = []
    inline = payload.get("inline")
    if isinstance(inline, str):
        try:
            body = json.loads(inline)
            if isinstance(body, dict):
                raw = body.get("impactClasses") or body.get("impactHints") or []
                if isinstance(raw, list):
                    classes = [str(c) for c in raw]
        except json.JSONDecodeError:
            pass
    if not classes:
        classes = list(IMPACT_CLASSES)
    grant_consent(
        install_root,
        target_id=env["from"],
        sender_id=message_to,
        impact_classes=classes,
        granted_by=env["from"],
    )


# ---------------------------------------------------------------------------
# Collective Regulation + Damping
# ---------------------------------------------------------------------------


def resolve_regulation_targets(
    install_root: Path, collective_card: dict
) -> tuple[list[str], str]:
    """Decide delivery targets for a collective Identity.

    Returns (target_identity_ids, routing_mode).
    Modes:
      central    – only the collective itself
      specialist – first registered specialist (fallback: collective)
      fan-out    – all registered specialists + collective inbox
    """
    collective_id = collective_card["identityId"]
    reg = collective_card.get("regulation") or {}
    routing = reg.get("routing") or "central"
    specialists = [s for s in (reg.get("specialists") or []) if isinstance(s, str)]

    if routing == "central" or collective_card.get("type") != "collective":
        return [collective_id], "central"

    registered = [s for s in specialists if get_card(install_root, s) is not None]

    if routing == "specialist":
        if registered:
            return [registered[0]], "specialist"
        return [collective_id], "specialist-fallback-central"

    if routing == "fan-out":
        # Collective keeps a copy; each registered specialist gets a routed copy.
        targets = [collective_id] + registered
        # de-dupe preserving order
        seen: set[str] = set()
        ordered: list[str] = []
        for t in targets:
            if t not in seen:
                seen.add(t)
                ordered.append(t)
        return ordered, "fan-out"

    return [collective_id], f"unknown-routing:{routing}"


def _damping_path(install_root: Path, collective_id: str) -> Path:
    return messaging_root(install_root) / "damping" / f"{collective_id}.json"


def damping_allows(install_root: Path, collective_card: dict) -> tuple[bool, str]:
    """Enforce regulation.damping.maxMessagesPerWindow if configured."""
    reg = collective_card.get("regulation") or {}
    damping = reg.get("damping") or {}
    max_n = damping.get("maxMessagesPerWindow")
    window_s = damping.get("windowSeconds")
    if not max_n or not window_s:
        return True, "no damping"
    try:
        max_n = int(max_n)
        window_s = int(window_s)
    except (TypeError, ValueError):
        return True, "invalid damping config ignored"

    collective_id = collective_card["identityId"]
    path = _damping_path(install_root, collective_id)
    now = time.time()
    timestamps: list[float] = []
    if path.is_file():
        try:
            data = _read_json(path)
            timestamps = [float(t) for t in (data.get("timestamps") or [])]
        except (OSError, json.JSONDecodeError, TypeError, ValueError):
            timestamps = []

    cutoff = now - window_s
    timestamps = [t for t in timestamps if t >= cutoff]
    if len(timestamps) >= max_n:
        return False, (
            f"damping: max {max_n} messages per {window_s}s "
            f"(have {len(timestamps)})"
        )

    timestamps.append(now)
    ensure_layout(install_root)
    _write_json(path, {"timestamps": timestamps, "updatedAt": _utc_now()})
    return True, "ok"


# ---------------------------------------------------------------------------
# Send / Inbox / Receipts
# ---------------------------------------------------------------------------


@dataclass
class SendResult:
    envelope: dict
    receipt: dict
    status: str  # delivered | rejected | partial
    deliveries: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        out = {
            "status": self.status,
            "envelope": self.envelope,
            "receipt": self.receipt,
        }
        if self.deliveries:
            out["deliveries"] = self.deliveries
        return out


def _target_id(to_field: Any) -> str:
    if isinstance(to_field, str):
        return to_field
    if isinstance(to_field, dict) and "collectiveId" in to_field:
        return to_field["collectiveId"]
    raise MessagingError("envelope.to must be identityId string or {collectiveId}")


def _deliver_to(
    install_root: Path,
    env: dict,
    delivery_target: str,
    *,
    via_collective: Optional[str] = None,
    routing: Optional[str] = None,
) -> dict:
    """Write one inbox copy (and optional routed metadata). Returns delivery record."""
    copy = dict(env)
    if via_collective and delivery_target != via_collective:
        # Distinct messageId for specialist copies so inbox entries don't collide.
        copy["messageId"] = _new_uuid_v7()
        copy["routedFrom"] = via_collective
        copy["originalMessageId"] = env["messageId"]
        if routing:
            copy["regulationRouting"] = routing

    member_card = get_card(install_root, delivery_target)
    if member_card is None:
        return {
            "target": delivery_target,
            "status": "skipped",
            "reason": "no local card",
        }

    # Member may still refuse via own Recognition (except the collective itself
    # which already passed Recognition).
    if via_collective and delivery_target != via_collective:
        allowed, reason = recognition_allows(
            member_card, env["from"], (env.get("signal") or {}).get("type", "")
        )
        if not allowed:
            return {
                "target": delivery_target,
                "status": "rejected",
                "reason": f"member recognition: {reason}",
            }

    _write_json(
        messaging_root(install_root) / "inbox" / f"{copy['messageId']}.json", copy
    )
    _apply_consent_grant_if_present(install_root, copy, delivery_target)
    return {
        "target": delivery_target,
        "status": "delivered",
        "messageId": copy["messageId"],
    }


def send_envelope(install_root: Path, envelope: dict) -> SendResult:
    """Validate, recognition-check, consent-gate, regulate, persist, emit receipt."""
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
        hints = [h for h in (env.get("impactHints") or []) if h in IMPACT_CLASSES]
        if not has_consent(
            install_root,
            target_id=target,
            sender_id=env["from"],
            impact_classes=hints,
        ):
            receipt = _make_receipt(
                env,
                receipt_type="rejected",
                from_id=target,
                reason=(
                    "impactHints require explicit consent "
                    "(granter must send consent-grant first; missing grant for "
                    + ",".join(hints)
                    + ")"
                ),
            )
            _persist_receipt(install_root, receipt)
            _write_json(
                messaging_root(install_root) / "outbox" / f"{env['messageId']}.json", env
            )
            return SendResult(envelope=env, receipt=receipt, status="rejected")

    # Damping only for collective targets
    if card.get("type") == "collective":
        ok, damp_reason = damping_allows(install_root, card)
        if not ok:
            receipt = _make_receipt(
                env, receipt_type="rejected", from_id=target, reason=damp_reason
            )
            _persist_receipt(install_root, receipt)
            _write_json(
                messaging_root(install_root) / "outbox" / f"{env['messageId']}.json", env
            )
            return SendResult(envelope=env, receipt=receipt, status="rejected")

    delivery_targets, routing = resolve_regulation_targets(install_root, card)
    _write_json(
        messaging_root(install_root) / "outbox" / f"{env['messageId']}.json", env
    )

    deliveries: list[dict] = []
    via = target if card.get("type") == "collective" else None
    for tid in delivery_targets:
        deliveries.append(
            _deliver_to(
                install_root,
                env,
                tid,
                via_collective=via,
                routing=routing if via else None,
            )
        )

    delivered_n = sum(1 for d in deliveries if d.get("status") == "delivered")
    if delivered_n == 0:
        status = "rejected"
        receipt_type = "rejected"
        reason = "regulation produced no successful deliveries"
    elif delivered_n < len(deliveries):
        status = "partial"
        receipt_type = "delivered"
        reason = f"regulation={routing}; {delivered_n}/{len(deliveries)} delivered"
    else:
        status = "delivered"
        receipt_type = "delivered"
        reason = f"local delivery (regulation={routing})" if via else "local delivery"

    receipt = _make_receipt(
        env, receipt_type=receipt_type, from_id=target, reason=reason
    )
    if deliveries:
        receipt["deliveries"] = deliveries
    _persist_receipt(install_root, receipt)
    return SendResult(
        envelope=env, receipt=receipt, status=status, deliveries=deliveries
    )


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


def _list_json_records(directory: Path, *, reverse: bool = False) -> list[dict]:
    records: list[dict] = []
    for path in sorted(directory.glob("*.json"), reverse=reverse):
        try:
            record = _read_json(path)
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(record, dict):
            records.append(record)
    return records


def list_outbox(install_root: Path) -> list[dict]:
    ensure_layout(install_root)
    return _list_json_records(messaging_root(install_root) / "outbox", reverse=True)


def list_receipts(install_root: Path) -> list[dict]:
    ensure_layout(install_root)
    return _list_json_records(messaging_root(install_root) / "receipts", reverse=True)


def list_consents(install_root: Path) -> list[dict]:
    ensure_layout(install_root)
    return _list_json_records(messaging_root(install_root) / "consents")


def list_consent_audit(install_root: Path) -> list[dict]:
    ensure_layout(install_root)
    return _list_json_records(
        messaging_root(install_root) / "consent_audit", reverse=True
    )


def list_damping(install_root: Path) -> list[dict]:
    ensure_layout(install_root)
    states: dict[str, dict[str, Any]] = {}

    for card in list_cards(install_root):
        identity_id = card.get("identityId")
        regulation = card.get("regulation") or {}
        damping = regulation.get("damping") if isinstance(regulation, dict) else None
        if not isinstance(identity_id, str) or not isinstance(damping, dict):
            continue
        states[identity_id] = {
            "identityId": identity_id,
            "configured": True,
            "maxMessagesPerWindow": damping.get("maxMessagesPerWindow"),
            "windowSeconds": damping.get("windowSeconds"),
            "timestamps": [],
            "currentCount": 0,
            "updatedAt": None,
        }

    damping_dir = messaging_root(install_root) / "damping"
    for path in sorted(damping_dir.glob("*.json")):
        identity_id = path.stem
        try:
            state = _read_json(path)
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(state, dict):
            continue
        item = states.setdefault(
            identity_id,
            {
                "identityId": identity_id,
                "configured": False,
                "maxMessagesPerWindow": None,
                "windowSeconds": None,
                "timestamps": [],
                "currentCount": 0,
                "updatedAt": None,
            },
        )
        item["timestamps"] = state.get("timestamps") or []
        item["updatedAt"] = state.get("updatedAt")

    now = time.time()
    for item in states.values():
        timestamps: list[float] = []
        for timestamp in item.get("timestamps") or []:
            try:
                timestamps.append(float(timestamp))
            except (TypeError, ValueError):
                continue
        try:
            window_seconds = int(item.get("windowSeconds"))
        except (TypeError, ValueError):
            window_seconds = 0
        active = [timestamp for timestamp in timestamps if not window_seconds or timestamp >= now - window_seconds]
        item["timestamps"] = active
        item["currentCount"] = len(active)

    return [states[key] for key in sorted(states)]


def collect_messaging_status(install_root: Path) -> dict[str, Any]:
    root = install_root.expanduser().resolve()
    ensure_layout(root)
    cards = list_cards(root)
    inbox = list_inbox(root)
    outbox = list_outbox(root)
    receipts = list_receipts(root)
    consents = list_consents(root)
    consent_audit = list_consent_audit(root)
    damping = list_damping(root)
    from .messaging_metabolize import list_metabolizations

    metabolizations = list_metabolizations(root)
    rejected = [
        {
            "receiptId": receipt.get("messageId"),
            "messageId": receipt.get("inReplyTo"),
            "from": receipt.get("from"),
            "createdAt": receipt.get("createdAt"),
            "reason": receipt.get("reason") or "unspecified rejection",
        }
        for receipt in receipts
        if receipt.get("receiptType") == "rejected"
    ]
    receipt_types = Counter(str(receipt.get("receiptType") or "unknown") for receipt in receipts)
    return {
        "root": str(root),
        "cards": {
            "count": len(cards),
            "identity_ids": [card.get("identityId") for card in cards],
        },
        "inbox": {"count": len(inbox)},
        "outbox": {"count": len(outbox)},
        "receipts": {
            "count": len(receipts),
            "by_type": dict(sorted(receipt_types.items())),
            "items": receipts,
        },
        "consents": {
            "count": len(consents),
            "items": consents,
        },
        "consent_audit": {
            "count": len(consent_audit),
            "items": consent_audit,
        },
        "metabolizations": {
            "count": len(metabolizations),
            "by_status": {"metabolized": len(metabolizations)},
            "items": metabolizations,
        },
        "damping": {
            "count": len(damping),
            "items": damping,
        },
        "rejections": rejected,
    }
