"""Effective Freedom — derived readout (not primary storage).

    effective_freedom  ≈  unbound_DoF  /  (1 + constraint_intensity)

See docs/effective-freedom.md. Inputs come from Geometry Receipts, Registry
effect_on_me (geometry feed), policy quarantines, identity grants, and optional
Access/Jurisdiction profiles. Never writes Stem or self-declared Mass.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Optional, Union

from .context import ContextError, resolve_active_identity_row
from .database import Database, database_path

FORMULA_VERSION = "0"
RECEIPT_WINDOW = 20
BASELINE_UNBOUND = 0.5


@dataclass
class FreedomReadout:
    """Derived Effective Freedom for one local install."""

    effective_freedom: float
    unbound_dof: float
    constraint_intensity: float
    formula_version: str = FORMULA_VERSION
    confidence: float = 0.0
    sources: dict[str, Any] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _mean(values: list[float]) -> Optional[float]:
    if not values:
        return None
    return sum(values) / len(values)


def _decode_json(raw: Any, default: Any = None) -> Any:
    if raw is None:
        return default
    if isinstance(raw, (dict, list)):
        return raw
    try:
        return json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        return default


def compute_freedom_readout(install_root: Union[str, Path]) -> FreedomReadout:
    """Compute Effective Freedom live from local SQLite projections.

    Pure derived signal. Safe to call often; does not mutate state.
    Uses the active Identity when multiple Identities exist in the install.
    """
    root = Path(install_root).expanduser().resolve()
    db_path = database_path(root)
    notes: list[str] = []
    sources: dict[str, Any] = {}

    if not db_path.is_file():
        return FreedomReadout(
            effective_freedom=BASELINE_UNBOUND,
            unbound_dof=BASELINE_UNBOUND,
            constraint_intensity=0.0,
            confidence=0.0,
            sources={"database": False},
            notes=["no IE database — baseline only"],
        )

    unbound_samples: list[float] = []
    constraint_labels = 0
    receipt_count = 0
    fed_count = 0

    with Database(db_path) as database:
        conn = database.conn
        try:
            identity = resolve_active_identity_row(conn)
        except ContextError:
            return FreedomReadout(
                effective_freedom=BASELINE_UNBOUND,
                unbound_dof=BASELINE_UNBOUND,
                constraint_intensity=0.0,
                confidence=0.0,
                sources={"identity": False},
                notes=["no local identity"],
            )
        identity_id = identity["identity_id"]

        # --- Geometry Receipts (recent window) ---
        rows = conn.execute(
            """
            SELECT degrees_of_freedom_json, fed_at, mode
            FROM geometry_receipts
            ORDER BY timestamp DESC
            LIMIT ?
            """,
            (RECEIPT_WINDOW,),
        ).fetchall()
        receipt_count = len(rows)
        for row in rows:
            if row["fed_at"]:
                fed_count += 1
            dof = _decode_json(row["degrees_of_freedom_json"], {}) or {}
            if isinstance(dof, dict):
                raw_unbound = dof.get("unbound_estimate")
                if isinstance(raw_unbound, (int, float)):
                    unbound_samples.append(max(0.0, float(raw_unbound)))
                noted = dof.get("constraints_noted") or []
                if isinstance(noted, list):
                    constraint_labels += len(noted)
                intensity_field = dof.get("constraint_intensity")
                if isinstance(intensity_field, (int, float)):
                    constraint_labels += max(0, int(round(float(intensity_field))))

        sources["receipts_window"] = receipt_count
        sources["receipts_fed"] = fed_count
        sources["unbound_from_receipts"] = len(unbound_samples)

        # --- Self Access/Jurisdiction probe (optional numerator + intensity) ---
        self_profile = conn.execute(
            """
            SELECT access_json, jurisdiction_json, confidence
            FROM access_jurisdiction_profiles
            WHERE observer_identity_id = ?
              AND object_kind = 'self'
              AND object_ref = 'self'
            ORDER BY revision DESC LIMIT 1
            """,
            (identity_id,),
        ).fetchone()

        access_mean: Optional[float] = None
        juris_constraint: float = 0.0
        if self_profile is not None:
            access = _decode_json(self_profile["access_json"], {}) or {}
            juris = _decode_json(self_profile["jurisdiction_json"], {}) or {}
            access_scores = [
                float(access[k])
                for k in ("reach", "use", "observe", "affected_by")
                if isinstance(access.get(k), (int, float))
            ]
            access_mean = _mean(access_scores)
            bind_keys = ("constrain", "destroy", "redefine_boundary")
            bind_scores = [
                float(juris[k])
                for k in bind_keys
                if isinstance(juris.get(k), (int, float))
            ]
            juris_constraint = _mean(bind_scores) or 0.0
            sources["self_probe"] = {
                "access_mean": access_mean,
                "jurisdiction_bind_mean": juris_constraint,
                "confidence": float(self_profile["confidence"] or 0.0),
            }
        else:
            sources["self_probe"] = None
            notes.append("no self Access/Jurisdiction probe yet")

        # --- Registry effect_on_me tension (geometry feed) ---
        tension_abs: list[float] = []
        effect_rows = conn.execute(
            """
            SELECT effect_on_me_json FROM registry_entries
            WHERE identity_id = ?
            """,
            (identity_id,),
        ).fetchall()
        for row in effect_rows:
            effect = _decode_json(row["effect_on_me_json"], {}) or {}
            if not isinstance(effect, dict):
                continue
            ts = effect.get("tension_sum")
            if isinstance(ts, (int, float)):
                tension_abs.append(abs(float(ts)))
        mean_tension = _mean(tension_abs) or 0.0
        sources["registry_peers_with_effect"] = len(tension_abs)
        sources["mean_abs_tension_sum"] = mean_tension

        # --- Quarantines ---
        quarantine_count = int(
            conn.execute(
                """
                SELECT COUNT(*) FROM quarantines
                WHERE identity_id = ? AND active = 1
                """,
                (identity_id,),
            ).fetchone()[0]
        )
        sources["active_quarantines"] = quarantine_count

        # --- Residual / emergency grants (intensity levers) ---
        residual_count = 0
        try:
            residual_count = int(
                conn.execute(
                    """
                    SELECT COUNT(*) FROM identity_grants
                    WHERE object_identity_id = ?
                      AND residual = 1
                      AND revoked_at IS NULL
                    """,
                    (identity_id,),
                ).fetchone()[0]
            )
        except Exception:
            residual_count = 0
        sources["residual_grants"] = residual_count

    # --- Aggregate unbound ---
    receipt_unbound = _mean(unbound_samples)
    candidates = [BASELINE_UNBOUND]
    if receipt_unbound is not None:
        candidates.append(receipt_unbound)
    if access_mean is not None:
        candidates.append(access_mean * 2.0)
    unbound = max(candidates)
    sources["unbound_components"] = {
        "baseline": BASELINE_UNBOUND,
        "receipt_mean": receipt_unbound,
        "self_access_scaled": (access_mean * 2.0) if access_mean is not None else None,
        "chosen": unbound,
    }

    # --- Aggregate constraint intensity ---
    intensity = 0.0
    intensity += min(2.0, quarantine_count * 0.5)
    intensity += min(2.0, constraint_labels * 0.15)
    intensity += min(2.0, mean_tension * 0.25)
    intensity += min(1.5, residual_count * 0.25)
    intensity += min(1.0, juris_constraint * 0.75)
    sources["constraint_components"] = {
        "quarantine_term": min(2.0, quarantine_count * 0.5),
        "receipt_constraints_term": min(2.0, constraint_labels * 0.15),
        "tension_term": min(2.0, mean_tension * 0.25),
        "residual_grant_term": min(1.5, residual_count * 0.25),
        "self_jurisdiction_bind_term": min(1.0, juris_constraint * 0.75),
    }

    effective = unbound / (1.0 + intensity)

    confidence = 0.15
    if receipt_count > 0:
        confidence += min(0.35, receipt_count * 0.03)
    if fed_count > 0:
        confidence += min(0.2, fed_count * 0.02)
    if access_mean is not None:
        confidence += 0.2
    if unbound_samples:
        confidence += 0.1
    confidence = min(1.0, confidence)

    if receipt_count == 0 and access_mean is None:
        notes.append(
            "cold baseline: no recent Geometry Receipt unbound_estimate and no self probe"
        )
    if fed_count == 0 and receipt_count > 0:
        notes.append("receipts present but none fed yet — tension from feed may lag")

    return FreedomReadout(
        effective_freedom=round(effective, 6),
        unbound_dof=round(unbound, 6),
        constraint_intensity=round(intensity, 6),
        formula_version=FORMULA_VERSION,
        confidence=round(confidence, 4),
        sources=sources,
        notes=notes,
    )
