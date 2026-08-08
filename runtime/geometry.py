"""Geometry Receipt + minimal extractors + post-interaction hook (v0).

Questions as Probes operationalized: every Interaction can produce relative
geometry under the observer's frame. See docs/geometry-hook.md and
docs/probes-as-bridge.md.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from math import isfinite
from pathlib import Path
from typing import Any, Callable, Optional, Union
from uuid import uuid4

from .models import InteractionSignal, Receipt, ApplyStatus


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
    source_refs: list[str] = field(default_factory=list)

    # Sparse geometry deltas (only populated fields matter)
    relative_mass_proxy: Optional[dict[str, Any]] = None
    tension_components: list[dict[str, Any]] = field(default_factory=list)
    degrees_of_freedom: Optional[dict[str, Any]] = None
    jurisdiction_shift: Optional[dict[str, Any]] = None
    stem_differential: Optional[dict[str, Any]] = None
    ownership_move: Optional[dict[str, Any]] = None
    optionality_delta: Optional[dict[str, Any]] = None

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
        source_refs: Optional[list[str]] = None,
    ) -> "GeometryReceipt":
        return cls(
            receipt_id=str(uuid4()),
            timestamp=_utcnow_iso(),
            mode=mode,
            observer=observer,
            target=target,
            source_signal_ref=source_signal_ref,
            source_refs=list(source_refs or []),
        )


# ---------------------------------------------------------------------------
# Extractors (pure, coarse, deterministic)
# ---------------------------------------------------------------------------

Extractor = Callable[
    [InteractionSignal, Receipt, Optional[dict[str, Any]]],
    dict[str, Any],
]


def extract_depth_mass(
    signal: InteractionSignal,
    apply_receipt: Receipt,
    context: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """DepthMassExtractor: sender's emergent Mass as relative_mass_proxy + density tension.

    relative_mass_proxy for target=sender is **their** emergent self-Mass
    (same normalized process as local Self-Mass — weighted inbound estimates of them).
    Sources the observer may treat as "real enough":
      1. signal.sender_emergent_mass (always-passed public geometry on the signal)
      2. context["sender_emergent_mass"] (last stored value in foreign-estimate zone)
      3. context["public_card_emergent_self_mass"] (live/cached public card read)

    Never uses coarse_mass_estimate: that is the sender's estimate *of the observer*,
    not the sender's own Mass.
    """
    out: dict[str, Any] = {}
    context = context or {}

    depth = float(signal.interaction_depth_delta or 0.0)
    depth_applied = "interaction_depth_delta" in (apply_receipt.applied_fields or [])

    proxy_value: Optional[float] = None
    confidence = 0.0
    source = ""

    if signal.sender_emergent_mass is not None:
        proxy_value = float(signal.sender_emergent_mass)
        confidence = 0.7
        source = "signal.sender_emergent_mass"
    elif context.get("sender_emergent_mass") is not None:
        proxy_value = float(context["sender_emergent_mass"])
        confidence = 0.55
        source = "stored foreign-estimate sender_emergent_mass"
    elif context.get("public_card_emergent_self_mass") is not None:
        proxy_value = float(context["public_card_emergent_self_mass"])
        confidence = 0.6
        source = "public_card.emergent_self_mass"

    if proxy_value is not None:
        out["relative_mass_proxy"] = {
            "value": round(proxy_value, 2),
            "confidence": confidence,
            "notes": (
                "sender emergent self-Mass (derived from their inbound estimates; "
                f"source={source}). Not Self-Mass of the observer."
            ),
        }
    elif depth_applied or depth > 0.0:
        # No published Mass yet: depth-only placeholder, explicitly not their Mass.
        out["relative_mass_proxy"] = {
            "value": round(min(100.0, depth * 80.0), 2),
            "confidence": 0.15,
            "notes": (
                "depth-only placeholder — sender has not published emergent Mass "
                "(no signal field, no stored value, no public card). Not Self-Mass."
            ),
        }

    if depth_applied or depth > 0.0:
        out["tension_components"] = [
            {
                "name": "interaction_density",
                "delta": round(depth, 4),
                "confidence": 0.6 if depth > 0 else 0.2,
            }
        ]
    return out


def extract_membrane_policy(
    signal: InteractionSignal,
    apply_receipt: Receipt,
    context: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """MembranePolicyExtractor (v0 stub): observe LocalPolicy consent outcomes.

    Records *what the membrane did* to consent-gated fields on this apply.
    Does **not** claim Access/Jurisdiction geometry — that needs a proper
    Ownership operationalization (OS #40). Signed access/jurisdiction deltas
    are intentionally omitted until the subject of Access is defined.
    """
    out: dict[str, Any] = {}
    applied = set(apply_receipt.applied_fields or [])
    rejected = {
        r.get("field") for r in (apply_receipt.rejected_fields or []) if r.get("field")
    }

    consent_fields = {
        "coarse_mass_estimate",
        "mass_confidence",
        "dimensions_delta",
        "relation_pull",
    }
    applied_consent = sorted(applied & consent_fields)
    rejected_consent = sorted(rejected & consent_fields)

    if not applied_consent and not rejected_consent:
        return out

    # Observational stub only: no signed Access/Jurisdiction claim.
    notes_parts = [
        "v0 membrane policy observation (not Ownership geometry; see OS #40)"
    ]
    if applied_consent:
        notes_parts.append(f"consent_applied={applied_consent}")
    if rejected_consent:
        notes_parts.append(f"consent_rejected={rejected_consent}")

    out["jurisdiction_shift"] = {
        # Explicit nulls in spirit: schema allows numbers; 0.0 + notes = "no claim".
        "access_delta": 0.0,
        "jurisdiction_delta": 0.0,
        "notes": "; ".join(notes_parts),
    }
    out["tension_components"] = [
        {
            "name": "membrane_consent_outcome",
            "delta": float(len(applied_consent) - len(rejected_consent)),
            "confidence": 0.35,
        }
    ]
    return out


# Back-compat alias (older docs/commits named this ConsentBoundaryExtractor)
extract_consent_boundary = extract_membrane_policy


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
    out["tension_components"] = [
        {
            "name": "relation_continuity",
            "delta": 0.05 if prior_count > 0 else 0.1,
            "confidence": 0.45,
        }
    ]
    return out


DEFAULT_EXTRACTORS: tuple[Extractor, ...] = (
    extract_depth_mass,
    extract_membrane_policy,
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
        if "optionality_delta" in p and base.optionality_delta is None:
            base.optionality_delta = p["optionality_delta"]
        for tc in p.get("tension_components") or []:
            base.tension_components.append(tc)


def run_geometry_hook(
    signal: InteractionSignal,
    apply_receipt: Receipt,
    *,
    observer: str,
    mode: str = "interact",
    context: Optional[dict[str, Any]] = None,
    extractors: Optional[tuple[Extractor, ...]] = None,
) -> Optional[GeometryReceipt]:
    """Run Geometry Extraction after an Interaction.

    Returns a GeometryReceipt or None if apply was fully rejected.
    Extractor failures are best-effort: recorded in notes, never raise into apply.
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
    extractor_errors: list[str] = []
    for ext in extractors:
        name = getattr(ext, "__name__", type(ext).__name__)
        try:
            partials.append(ext(signal, apply_receipt, context) or {})
        except Exception as exc:  # noqa: BLE001 — intentional best-effort boundary
            # Best-effort: a single extractor failure must not kill the hook.
            # Surface the failure in notes so dogfood is not silent.
            extractor_errors.append(f"{name}: {type(exc).__name__}: {exc}")
            continue

    _merge_extractor_outputs(receipt, partials)
    notes = ["v0 geometry hook — coarse extractors only"]
    if extractor_errors:
        notes.append("extractor_errors=" + " | ".join(extractor_errors))
    receipt.notes = "; ".join(notes)
    return receipt


def create_self_probe(
    *,
    mode: str,
    observer: str,
    notes: str = "",
    source_refs: Optional[list[str]] = None,
    stem_differential: Optional[dict[str, Any]] = None,
    ownership_move: Optional[dict[str, Any]] = None,
    optionality_delta: Optional[dict[str, Any]] = None,
    tension_components: Optional[list[dict[str, Any]]] = None,
) -> GeometryReceipt:
    """Create a Think or Mature Geometry Receipt with target=self.

    No Interaction Signal. No automatic write into Stem, Vision Gradient, or
    access policy. Mature requires at least one local source reference and one
    recorded geometry change; ownership_move is recorded on the receipt only.
    Applying it to persistent geometry requires Ownership design (#40).

    mode must be "think" or "mature".
    """
    mode = mode.strip().lower()
    if mode not in {"think", "mature"}:
        raise ValueError(f"mode must be think|mature, got {mode!r}")
    observer = observer.strip()
    if not observer:
        raise ValueError("observer must not be empty")

    if source_refs is not None and not isinstance(source_refs, (list, tuple)):
        raise ValueError("source_refs must be a list of strings")

    normalized_sources: list[str] = []
    for source_ref in source_refs or []:
        if not isinstance(source_ref, str) or not source_ref.strip():
            raise ValueError("source_refs must contain non-empty strings")
        source_ref = source_ref.strip()
        if source_ref not in normalized_sources:
            normalized_sources.append(source_ref)
    if mode == "mature" and not normalized_sources:
        raise ValueError(
            "mature self-probe requires at least one source_ref"
        )

    validated_stem: Optional[dict[str, str]] = None
    if stem_differential is not None:
        if not isinstance(stem_differential, dict):
            raise ValueError("stem_differential must be an object")
        validated_stem = {}
        for field_name in (
            "state_delta_summary",
            "vision_gradient_shift",
            "coherence_note",
        ):
            value = stem_differential.get(field_name, "")
            if not isinstance(value, str):
                raise ValueError(f"stem_differential.{field_name} must be a string")
            if value.strip():
                validated_stem[field_name] = value.strip()

    validated_ownership: Optional[dict[str, Any]] = None
    if ownership_move is not None:
        if mode != "mature":
            raise ValueError("ownership_move is only valid for mode=mature")
        if not isinstance(ownership_move, dict):
            raise ValueError("ownership_move must be an object")
        commitment = ownership_move.get("commitment")
        ownership_level = ownership_move.get("ownership_level_estimate")
        if not isinstance(commitment, str) or not commitment.strip():
            raise ValueError("ownership_move.commitment must not be empty")
        if (
            isinstance(ownership_level, bool)
            or not isinstance(ownership_level, (int, float))
            or not isfinite(float(ownership_level))
            or not 0.0 <= float(ownership_level) <= 100.0
        ):
            raise ValueError(
                "ownership_move.ownership_level_estimate must be in [0, 100]"
            )
        validated_ownership = {
            "commitment": commitment.strip(),
            "ownership_level_estimate": float(ownership_level),
        }

    validated_optionality: Optional[dict[str, Any]] = None
    if optionality_delta is not None:
        if not isinstance(optionality_delta, dict):
            raise ValueError("optionality_delta must be an object")
        value = optionality_delta.get("value")
        confidence = optionality_delta.get("confidence")
        justification = optionality_delta.get("notes")
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not isfinite(float(value))
        ):
            raise ValueError("optionality_delta.value must be a finite number")
        if (
            isinstance(confidence, bool)
            or not isinstance(confidence, (int, float))
            or not isfinite(float(confidence))
            or not 0.0 <= float(confidence) <= 1.0
        ):
            raise ValueError(
                "optionality_delta.confidence must be in [0, 1]"
            )
        if not isinstance(justification, str) or not justification.strip():
            raise ValueError("optionality_delta.notes must not be empty")
        validated_optionality = {
            "value": float(value),
            "confidence": float(confidence),
            "notes": justification.strip(),
        }

    if mode == "mature" and not any(
        (
            validated_stem,
            validated_ownership,
            validated_optionality,
            tension_components,
        )
    ):
        raise ValueError(
            "mature self-probe requires at least one geometry change"
        )

    receipt = GeometryReceipt.create(
        mode=mode,
        observer=observer,
        target="self",
        source_signal_ref=None,
        source_refs=normalized_sources,
    )

    if validated_stem:
        receipt.stem_differential = validated_stem
    if validated_ownership:
        receipt.ownership_move = validated_ownership
    if validated_optionality:
        receipt.optionality_delta = validated_optionality
    if tension_components:
        receipt.tension_components = list(tension_components)

    base_note = (
        f"v0 self-probe ({mode}) — local Geometry Receipt only; "
        "no Stem/Vision/Policy write without Ownership (#40)"
    )
    receipt.notes = f"{base_note}; {notes}".strip("; ") if notes else base_note
    return receipt


class GeometryReceiptStore:
    """SQLite store for local Geometry Receipts."""

    def __init__(self, registry_root: Union[str, Path]):
        from .sqlite_store import SQLiteStore

        self.store = SQLiteStore.from_registry_root(registry_root)

    def save(self, receipt: GeometryReceipt) -> Path:
        data = receipt.to_dict()
        from .database import canonical_json

        identity = self.store.identity()
        with self.store.open() as database:
            with database.transaction() as conn:
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
                        data.get("source_signal_ref"),
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
                for source_ref in data.get("source_refs") or []:
                    conn.execute(
                        """
                        INSERT INTO geometry_receipt_sources(receipt_id, source_kind, source_id)
                        VALUES (?, 'source_ref', ?)
                        """,
                        (data["receipt_id"], source_ref),
                    )
        return self.store.path

    def load(self, receipt_id: str) -> Optional[dict[str, Any]]:
        import json

        with self.store.open() as database:
            row = database.conn.execute(
                "SELECT * FROM geometry_receipts WHERE receipt_id = ?",
                (receipt_id,),
            ).fetchone()
            if row is None:
                return None
            sources = database.conn.execute(
                """
                SELECT source_id FROM geometry_receipt_sources
                WHERE receipt_id = ? AND source_kind = 'source_ref'
                ORDER BY source_id
                """,
                (receipt_id,),
            ).fetchall()

        def decode(column: str, default: Any = None) -> Any:
            raw = row[column]
            return default if raw is None else json.loads(raw)

        return {
            "receipt_id": row["receipt_id"],
            "timestamp": row["timestamp"],
            "mode": row["mode"],
            "observer": row["observer"],
            "target": row["target"],
            "source_signal_ref": row["source_apply_receipt_id"],
            "source_refs": [source[0] for source in sources],
            "relative_mass_proxy": decode("relative_mass_proxy_json"),
            "tension_components": decode("tension_components_json", []),
            "degrees_of_freedom": decode("degrees_of_freedom_json"),
            "jurisdiction_shift": decode("jurisdiction_shift_json"),
            "stem_differential": decode("stem_differential_json"),
            "ownership_move": decode("ownership_move_json"),
            "optionality_delta": decode("optionality_delta_json"),
            "notes": row["notes"],
        }

    def list_ids(self) -> list[str]:
        with self.store.open() as database:
            rows = database.conn.execute(
                "SELECT receipt_id FROM geometry_receipts ORDER BY receipt_id"
            ).fetchall()
        return [row[0] for row in rows]
