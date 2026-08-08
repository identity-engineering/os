"""Local deterministic apply path for Identity Surface Runtime v0."""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Union

from .models import (
    ApplyStatus,
    InteractionSignal,
    Receipt,
    _utcnow,
)
from .policy import LocalPolicy
from .sqlite_store import SQLiteStore


def apply_interaction_signal(
    signal: InteractionSignal,
    *,
    registry_root: Union[str, Path],
    policy: Optional[LocalPolicy] = None,
    expected_to_handle: Optional[str] = None,
    emit_geometry_receipt: bool = True,
    observer_handle: Optional[str] = None,
) -> Receipt:
    """Apply an Interaction Signal into the local foreign-estimate zone.

    Geometry Hook runs by default after a non-rejected apply (Probes-as-Bridge).
    Extraction is best-effort and never fails the Interaction apply itself.
    Pass emit_geometry_receipt=False only for tests or explicit opt-out.
    """
    store = SQLiteStore.from_registry_root(registry_root)
    policy = policy or store.load_policy()

    errors = signal.validate_required()
    if errors:
        return Receipt.create(
            ApplyStatus.REJECTED,
            signal.from_handle,
            signal.to_handle,
            reason="; ".join(errors),
        )

    event_id = str(__import__("uuid").uuid4())

    if expected_to_handle and signal.to_handle != expected_to_handle:
        receipt = Receipt.create(
            ApplyStatus.REJECTED,
            signal.from_handle,
            signal.to_handle,
            event_id=event_id,
            reason=f"to_handle mismatch: expected {expected_to_handle}",
        )
        store.persist_signal(
            signal,
            receipt,
            fields_to_apply=[],
            quarantine=False,
            geometry=None,
            prior_record=None,
        )
        return receipt

    fields_to_apply, rejected, quarantine = policy.evaluate(signal)

    if not fields_to_apply and rejected:
        receipt = Receipt.create(
            ApplyStatus.REJECTED,
            signal.from_handle,
            signal.to_handle,
            event_id=event_id,
            rejected=rejected,
            reason="policy refused all fields",
            quarantine=quarantine,
        )
        store.persist_signal(
            signal,
            receipt,
            fields_to_apply=[],
            quarantine=quarantine,
            geometry=None,
            prior_record=None,
        )
        return receipt

    record = store.load_foreign(signal.from_handle)
    now = signal.timestamp or _utcnow()
    prior_signal_count = int(record.signal_count) if record is not None else 0
    prior_accumulated_depth = float(record.accumulated_depth) if record is not None else 0.0

    applied: list[str] = []

    if "existence" in fields_to_apply:
        applied.append("existence")

    if "interaction_depth_delta" in fields_to_apply:
        applied.append("interaction_depth_delta")

    if "sender_emergent_mass" in fields_to_apply and signal.sender_emergent_mass is not None:
        applied.append("sender_emergent_mass")

    if "sender_last_mature_at" in fields_to_apply and signal.sender_last_mature_at is not None:
        applied.append("sender_last_mature_at")

    if "coarse_mass_estimate" in fields_to_apply and signal.coarse_mass_estimate is not None:
        applied.append("coarse_mass_estimate")

    if "mass_confidence" in fields_to_apply and signal.mass_confidence is not None:
        applied.append("mass_confidence")

    if "dimensions_delta" in fields_to_apply and signal.dimensions_delta is not None:
        applied.append("dimensions_delta")

    if "relation_pull" in fields_to_apply and signal.relation_pull is not None:
        applied.append("relation_pull")

    receipt = Receipt.create(
        ApplyStatus.APPLIED if not rejected else ApplyStatus.PARTIAL,
        signal.from_handle,
        signal.to_handle,
        event_id=event_id,
        applied=applied,
        rejected=rejected,
        reason="applied to foreign-estimate zone" if applied else "no fields applied",
        quarantine=quarantine,
    )

    # Geometry Hook (Probes-as-Bridge). Default on. Best-effort; never fails apply.
    # Failures are recorded in receipt.reason when possible (not fully silent).
    if emit_geometry_receipt and receipt.status != ApplyStatus.REJECTED:
        try:
            from .geometry import GeometryReceiptStore, run_geometry_hook

            observer = observer_handle or signal.to_handle or expected_to_handle or "local"
            # Prefer Mass published on this signal; else last stored value for sender.
            stored_sender_mass = None
            if record is not None and record.sender_emergent_mass is not None:
                stored_sender_mass = float(record.sender_emergent_mass)
            geo = run_geometry_hook(
                signal,
                receipt,
                observer=observer,
                mode="interact",
                context={
                    "prior_signal_count": prior_signal_count,
                    "prior_accumulated_depth": prior_accumulated_depth,
                    "sender_emergent_mass": (
                        float(signal.sender_emergent_mass)
                        if signal.sender_emergent_mass is not None
                        else stored_sender_mass
                    ),
                    "sender_last_mature_at": (
                        signal.sender_last_mature_at
                        if signal.sender_last_mature_at is not None
                        else (record.sender_last_mature_at if record is not None else None)
                    ),
                    # Callers / future Surface adapters may inject a card read:
                    # "public_card_emergent_self_mass": <float>
                },
            )
            if geo is not None:
                extra = f"geometry_receipt={geo.receipt_id}"
                if geo.notes and "extractor_errors=" in geo.notes:
                    extra += " (geometry extractor errors; see receipt notes)"
                receipt.reason = ((receipt.reason or "") + f"; {extra}").strip("; ")
        except Exception as exc:  # noqa: BLE001 — apply must not fail on geometry
            receipt.reason = (
                (receipt.reason or "")
                + f"; geometry_hook_error={type(exc).__name__}"
            ).strip("; ")

    store.persist_signal(
        signal,
        receipt,
        fields_to_apply=applied,
        quarantine=quarantine,
        geometry=geo if "geo" in locals() else None,
        prior_record=record,
    )

    return receipt


def apply_from_dict(
    payload: dict,
    *,
    registry_root: Union[str, Path],
    policy: Optional[LocalPolicy] = None,
    expected_to_handle: Optional[str] = None,
    emit_geometry_receipt: bool = True,
    observer_handle: Optional[str] = None,
) -> Receipt:
    """Convenience wrapper: dict payload → InteractionSignal → apply."""
    sem = payload.get("sender_emergent_mass")
    if sem is None:
        sem = payload.get("from_emergent_mass")

    signal = InteractionSignal(
        from_handle=str(payload.get("from") or payload.get("from_handle") or ""),
        to_handle=str(payload.get("to") or payload.get("to_handle") or ""),
        timestamp=str(payload.get("timestamp") or _utcnow()),
        existence=bool(payload.get("existence", True)),
        interaction_depth_delta=float(payload.get("interaction_depth_delta", 0.0)),
        sender_emergent_mass=float(sem) if sem is not None else None,
        sender_last_mature_at=(
            str(payload["sender_last_mature_at"])
            if payload.get("sender_last_mature_at")
            else None
        ),
        coarse_mass_estimate=payload.get("coarse_mass_estimate"),
        mass_confidence=payload.get("mass_confidence"),
        dimensions_delta=payload.get("dimensions_delta"),
        relation_pull=payload.get("relation_pull"),
        schema_version=str(payload.get("schema_version", "0")),
        transport=str(payload.get("transport", "cli")),
        in_reply_to_request_id=(
            str(payload["in_reply_to_request_id"])
            if payload.get("in_reply_to_request_id")
            else None
        ),
    )
    return apply_interaction_signal(
        signal,
        registry_root=registry_root,
        policy=policy,
        expected_to_handle=expected_to_handle,
        emit_geometry_receipt=emit_geometry_receipt,
        observer_handle=observer_handle,
    )
