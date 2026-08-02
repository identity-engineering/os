"""Local deterministic apply path for Identity Surface Runtime v0."""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Union

from .models import (
    ApplyStatus,
    ForeignEstimateRecord,
    InteractionSignal,
    Receipt,
    _utcnow,
)
from .policy import LocalPolicy
from .storage import ForeignEstimateStore


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
    policy = policy or LocalPolicy()
    store = ForeignEstimateStore(Path(registry_root))

    errors = signal.validate_required()
    if errors:
        return Receipt.create(
            ApplyStatus.REJECTED,
            signal.from_handle,
            signal.to_handle,
            reason="; ".join(errors),
        )

    if expected_to_handle and signal.to_handle != expected_to_handle:
        return Receipt.create(
            ApplyStatus.REJECTED,
            signal.from_handle,
            signal.to_handle,
            reason=f"to_handle mismatch: expected {expected_to_handle}",
        )

    fields_to_apply, rejected, quarantine = policy.evaluate(signal)

    if not fields_to_apply and rejected:
        return Receipt.create(
            ApplyStatus.REJECTED,
            signal.from_handle,
            signal.to_handle,
            rejected=rejected,
            reason="policy refused all fields",
            quarantine=quarantine,
        )

    record = store.load(signal.from_handle)
    now = signal.timestamp or _utcnow()
    prior_signal_count = int(record.signal_count) if record is not None else 0
    prior_accumulated_depth = float(record.accumulated_depth) if record is not None else 0.0

    if record is None:
        record = ForeignEstimateRecord(
            sender_handle=signal.from_handle,
            first_signal_at=now,
            last_signal_at=now,
            signal_count=0,
            existence_confirmed=False,
        )

    applied: list[str] = []

    if "existence" in fields_to_apply:
        record.existence_confirmed = True
        applied.append("existence")

    if "interaction_depth_delta" in fields_to_apply:
        delta = float(signal.interaction_depth_delta)
        record.last_depth_delta = delta
        record.accumulated_depth = float(record.accumulated_depth) + delta
        applied.append("interaction_depth_delta")

    if "sender_emergent_mass" in fields_to_apply and signal.sender_emergent_mass is not None:
        record.sender_emergent_mass = float(signal.sender_emergent_mass)
        record.sender_emergent_mass_at = now
        applied.append("sender_emergent_mass")

    if "coarse_mass_estimate" in fields_to_apply and signal.coarse_mass_estimate is not None:
        record.coarse_mass_estimate = float(signal.coarse_mass_estimate)
        record.mass_estimate_at = now
        applied.append("coarse_mass_estimate")

    if "mass_confidence" in fields_to_apply and signal.mass_confidence is not None:
        record.mass_confidence = float(signal.mass_confidence)
        applied.append("mass_confidence")

    if "dimensions_delta" in fields_to_apply and signal.dimensions_delta is not None:
        record.dimensions_delta = signal.dimensions_delta
        applied.append("dimensions_delta")

    if "relation_pull" in fields_to_apply and signal.relation_pull is not None:
        record.relation_pull = float(signal.relation_pull)
        applied.append("relation_pull")

    record.last_signal_at = now
    record.signal_count = int(record.signal_count) + 1
    record.quarantine = quarantine

    receipt = Receipt.create(
        ApplyStatus.APPLIED if not rejected else ApplyStatus.PARTIAL,
        signal.from_handle,
        signal.to_handle,
        applied=applied,
        rejected=rejected,
        reason="applied to foreign-estimate zone" if applied else "no fields applied",
        quarantine=quarantine,
    )
    record.last_receipt_id = receipt.receipt_id
    store.save(record)

    if signal.in_reply_to_request_id and receipt.status in (
        ApplyStatus.APPLIED,
        ApplyStatus.PARTIAL,
    ):
        try:
            from .request import mark_request_answered

            mark_request_answered(
                registry_root,
                signal.in_reply_to_request_id,
                receipt.receipt_id,
            )
        except Exception:
            pass

    # Geometry Hook (Probes-as-Bridge). Default on. Best-effort; never fails apply.
    # Failures are recorded in receipt.reason when possible (not fully silent).
    if emit_geometry_receipt and receipt.status != ApplyStatus.REJECTED:
        try:
            from .geometry import GeometryReceiptStore, run_geometry_hook

            observer = observer_handle or signal.to_handle or expected_to_handle or "local"
            # Prefer Mass published on this signal; else last stored value for sender.
            stored_sender_mass = None
            if record.sender_emergent_mass is not None:
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
                    # Callers / future Surface adapters may inject a card read:
                    # "public_card_emergent_self_mass": <float>
                },
            )
            if geo is not None:
                GeometryReceiptStore(registry_root).save(geo)
                extra = f"geometry_receipt={geo.receipt_id}"
                if geo.notes and "extractor_errors=" in geo.notes:
                    extra += " (geometry extractor errors; see receipt notes)"
                receipt.reason = ((receipt.reason or "") + f"; {extra}").strip("; ")
        except Exception as exc:  # noqa: BLE001 — apply must not fail on geometry
            receipt.reason = (
                (receipt.reason or "")
                + f"; geometry_hook_error={type(exc).__name__}"
            ).strip("; ")

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
