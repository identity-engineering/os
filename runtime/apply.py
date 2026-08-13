"""Local deterministic apply path for Identity Surface Runtime v0."""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Union
from uuid import uuid4

from .models import (
    ApplyStatus,
    InteractionSignal,
    Receipt,
    _utcnow,
)
from .policy import LocalPolicy
from .sqlite_store import SQLiteStore


def _membrane_policy_for_install(registry_root: Union[str, Path]) -> Optional[dict]:
    """Load primary Space membrane policy when Space rows exist."""
    try:
        from .context import get_active_identity, get_primary_space_for_identity
        from .membrane import load_space_policy_from_row

        identity = get_active_identity(registry_root)
        space = get_primary_space_for_identity(registry_root, identity["identity_id"])
        if space is None:
            return None
        return load_space_policy_from_row(space)
    except Exception:  # noqa: BLE001 — membrane is additive; never fail apply bootstrap
        return None


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
    Extraction + feed are best-effort and never fail the Interaction apply itself.
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

    event_id = str(uuid4())

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

    # Space membrane inbound filter (additive to Surface LocalPolicy).
    membrane_stripped: list[str] = []
    membrane_policy = _membrane_policy_for_install(registry_root)
    if membrane_policy is not None and fields_to_apply:
        from .membrane import filter_inbound_fields

        membrane = filter_inbound_fields(fields_to_apply, membrane_policy)
        membrane_stripped = list(membrane.stripped_fields)
        if membrane_stripped:
            allowed_set = set(membrane.allowed_fields)
            fields_to_apply = [f for f in fields_to_apply if f in allowed_set]
            for name in membrane_stripped:
                rejected.append(
                    {"field": name, "reason": "space membrane inbound deny"}
                )

    if not fields_to_apply and rejected:
        reason = "policy refused all fields"
        if membrane_stripped:
            reason += f"; membrane_stripped={','.join(membrane_stripped)}"
        receipt = Receipt.create(
            ApplyStatus.REJECTED,
            signal.from_handle,
            signal.to_handle,
            event_id=event_id,
            rejected=rejected,
            reason=reason,
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

    reason = "applied to foreign-estimate zone" if applied else "no fields applied"
    if membrane_stripped:
        reason += f"; membrane_stripped={','.join(membrane_stripped)}"

    receipt = Receipt.create(
        ApplyStatus.APPLIED if not rejected else ApplyStatus.PARTIAL,
        signal.from_handle,
        signal.to_handle,
        event_id=event_id,
        applied=applied,
        rejected=rejected,
        reason=reason,
        quarantine=quarantine,
    )

    # Geometry Hook (Probes-as-Bridge). Default on. Best-effort; never fails apply.
    geo = None
    if emit_geometry_receipt and receipt.status != ApplyStatus.REJECTED:
        try:
            from .geometry import run_geometry_hook

            observer = observer_handle or signal.to_handle or expected_to_handle or "local"
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
        geometry=geo,
        prior_record=record,
    )

    # Geometry feed (OS #8): write Receipt into Registry effect_on_me. Best-effort.
    if geo is not None:
        try:
            from .geometry_feed import feed_receipt

            fed = feed_receipt(registry_root, geo.receipt_id)
            if fed.get("status") == "fed":
                receipt.reason = (
                    (receipt.reason or "") + f"; geometry_fed={geo.receipt_id}"
                ).strip("; ")
        except Exception as exc:  # noqa: BLE001 — feed must not fail apply
            receipt.reason = (
                (receipt.reason or "")
                + f"; geometry_feed_error={type(exc).__name__}"
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
