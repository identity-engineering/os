"""Geometry Receipt + minimal extractors + post-interaction hook (v0).

Questions as Probes operationalized: every Interaction can produce relative
geometry under the observer's frame. See docs/geometry-hook.md and
docs/probes-as-bridge.md.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional, Union
from uuid import uuid4

from .models import InteractionSignal, Receipt, ApplyStatus, _utcnow


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class GeometryReceipt:
    """Local Geometry Receipt (mirrors schemas/geometry-receipt/v0.yaml)."""

    receipt_id: str
    timestamp: str
    mode: str  # think | interact | mature
    observer: str
    target: str  # "self" or foreign handle
    source_signal_ref: Optional[str] = None

    # Sparse geometry deltas (only populated fields matter)
    relative_mass_proxy: Optional[dict[str, Any]] = None
    tension_components: list[dict[str, Any]] = field(default_factory=list)
    degrees_of_freedom: Optional[dict[str, Any]] = None
    jurisdiction_shift: Optional[dict[str, Any]] = None
    stem_differential: Optional[dict[str, Any]] = None
    ownership_move: Optional[dict[str, Any]] = None

    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def create(
        cls,
        *,
        mode: str,
        observer: str,
        target: str,
        source_signal_ref: Optional[str] = None,
    ) -> "GeometryReceipt":
        return cls(
            receipt_id=str(uuid4()),
            timestamp=_utcnow_iso(),
            mode=mode,
            observer=observer,
            target=target,
            source_signal_ref=source_signal_ref,
        )


# ---------------------------------------------------------------------------
# Extractors (pure, coarse, deterministic)
# ---------------------------------------------------------------------------


def extract_depth_mass(
    signal: InteractionSignal,
    apply_receipt: Receipt,
    context: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """DepthMassExtractor: relative mass proxy + interaction-density tension."""
    out: dict[str, Any] = {}
    context = context or {}

    depth = float(signal.interaction_depth_delta or 0.0)
    if depth <= 0.0 and "interaction_depth_delta" not in apply_receipt.applied_fields:
        return out

    # Coarse relative mass proxy: prefer sender's published emergent mass,
    # else the (possibly rejected) estimate they held of us is still a signal
    # about relation weight from their side — we only use it as a weak hint
    # when it was applied; otherwise we fall back to depth alone.
    proxy_value: Optional[float] = None
    confidence = 0.25

    if signal.sender_emergent_mass is not None:
        proxy_value = float(signal.sender_emergent_mass)
        confidence = 0.55
    elif (
        signal.coarse_mass_estimate is not None
        and "coarse_mass_estimate" in apply_receipt.applied_fields
    ):
        # Applied estimate of *us* is not our Mass; use only as weak relational weight.
        proxy_value = min(100.0, float(signal.coarse_mass_estimate) * 0.3 + depth * 40.0)
        confidence = 0.35
    else:
        # Depth-only placeholder on 0–100 scale (very low confidence).
        proxy_value = min(100.0, depth * 80.0)
        confidence = 0.2

    out["relative_mass_proxy"] = {
        "value": round(proxy_value, 2),
        "confidence": confidence,
        "notes": "v0 DepthMassExtractor — coarse, not Self-Mass",
    }
    out["tension_components"] = [
        {
            "name": "interaction_density",
            "delta": round(depth, 4),
            "confidence": 0.6 if depth > 0 else 0.2,
        }
    ]
    return out


def extract_consent_boundary(
    signal: InteractionSignal,
    apply_receipt: Receipt,
    context: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """ConsentBoundaryExtractor: jurisdiction / access observation from policy outcome."""
    out: dict[str, Any] = {}
    applied = set(apply_receipt.applied_fields or [])
    rejected = {r.get("field") for r in (apply_receipt.rejected_fields or []) if r.get("field")}

    consent_fields = {
        "coarse_mass_estimate",
        "mass_confidence",
        "dimensions_delta",
        "relation_pull",
    }
    applied_consent = applied & consent_fields
    rejected_consent = rejected & consent_fields

    if not applied_consent and not rejected_consent:
        # Only always-passed fields — neutral / no strong jurisdiction signal.
        return out

    # Crude signed shift: more applied consent → slight positive access reading;
    # more rejected → slight negative (boundary held).
    access_delta = 0.0
    if applied_consent:
        access_delta += 0.15 * len(applied_consent)
    if rejected_consent:
        access_delta -= 0.1 * len(rejected_consent)
    access_delta = max(-1.0, min(1.0, access_delta))

    notes_parts = []
    if applied_consent:
        notes_parts.append(f"applied consent: {sorted(applied_consent)}")
    if rejected_consent:
        notes_parts.append(f"rejected consent: {sorted(rejected_consent)}")

    out["jurisdiction_shift"] = {
        "access_delta": round(access_delta, 3),
        "jurisdiction_delta": 0.0,  # v0 does not infer Stem jurisdiction from signal alone
        "notes": "; ".join(notes_parts) or "consent boundary observed",
    }
    return out


def extract_existence_continuity(
    signal: InteractionSignal,
    apply_receipt: Receipt,
    context: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """ExistenceContinuityExtractor: simple relation-stability / continuity hint."""
    out: dict[str, Any] = {}
    context = context or {}

    if "existence" not in (apply_receipt.applied_fields or []) and not signal.existence:
        return out

    prior_count = int(context.get("prior_signal_count") or 0)
    prior_depth = float(context.get("prior_accumulated_depth") or 0.0)
    new_depth = prior_depth + float(signal.interaction_depth_delta or 0.0)

    if prior_count <= 0:
        summary = "first confirmed existence in observer frame"
        coherence = "new relation anchor"
    else:
        summary = f"re-confirmed existence (signal_count now ~{prior_count + 1})"
        coherence = "continuing relation" if new_depth > prior_depth else "existence only"

    out["stem_differential"] = {
        "state_delta_summary": summary,
        "vision_gradient_shift": "",
        "coherence_note": coherence,
    }
    # Mild tension component on continuity.
    out["tension_components"] = [
        {
            "name": "relation_continuity",
            "delta": 0.05 if prior_count > 0 else 0.1,
            "confidence": 0.45,
        }
    ]
    return out


DEFAULT_EXTRACTORS = (
    extract_depth_mass,
    extract_consent_boundary,
    extract_existence_continuity,
)


def _merge_extractor_outputs(base: GeometryReceipt, partials: list[dict[str, Any]]) -> None:
    """Merge sparse extractor outputs into the receipt (in place)."""
    for p in partials:
        if not p:
            continue
        if "relative_mass_proxy" in p and base.relative_mass_proxy is None:
            base.relative_mass_proxy = p["relative_mass_proxy"]
        if "jurisdiction_shift" in p and base.jurisdiction_shift is None:
            base.jurisdiction_shift = p["jurisdiction_shift"]
        if "stem_differential" in p and base.stem_differential is None:
            base.stem_differential = p["stem_differential"]
        if "degrees_of_freedom" in p and base.degrees_of_freedom is None:
            base.degrees_of_freedom = p["degrees_of_freedom"]
        if "ownership_move" in p and base.ownership_move is None:
            base.ownership_move = p["ownership_move"]
        for tc in p.get("tension_components") or []:
            base.tension_components.append(tc)


def run_geometry_hook(
    signal: InteractionSignal,
    apply_receipt: Receipt,
    *,
    observer: str,
    mode: str = "interact",
    context: Optional[dict[str, Any]] = None,
    extractors: Optional[tuple] = None,
) -> Optional[GeometryReceipt]:
    """Run Geometry Extraction after an Interaction.

    Returns a GeometryReceipt or None if apply was fully rejected.
    Never raises into the apply path; callers should treat as best-effort.
    """
    if apply_receipt.status == ApplyStatus.REJECTED:
        return None

    extractors = extractors or DEFAULT_EXTRACTORS
    target = signal.from_handle if mode == "interact" else "self"

    receipt = GeometryReceipt.create(
        mode=mode,
        observer=observer,
        target=target,
        source_signal_ref=apply_receipt.receipt_id,
    )

    partials: list[dict[str, Any]] = []
    for ext in extractors:
        try:
            partials.append(ext(signal, apply_receipt, context) or {})
        except Exception:
            # Best-effort: a single extractor failure must not kill the hook.
            continue

    _merge_extractor_outputs(receipt, partials)
    receipt.notes = "v0 geometry hook — coarse extractors only"
    return receipt


class GeometryReceiptStore:
    """Minimal file store for Geometry Receipts under registry/_geometry_receipts/."""

    def __init__(self, registry_root: Union[str, Path]):
        self.root = Path(registry_root) / "_geometry_receipts"
        self.root.mkdir(parents=True, exist_ok=True)

    def save(self, receipt: GeometryReceipt) -> Path:
        path = self.root / f"{receipt.receipt_id}.yaml"
        data = receipt.to_dict()
        try:
            import yaml  # type: ignore

            path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
        except Exception:
            import json

            path = path.with_suffix(".json")
            path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return path
