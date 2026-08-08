"""Emergent self-Mass and volume readout from the foreign-estimate zone.

Self-Mass is never self-declared. It is a weighted mean of coarse_mass_estimate
values others applied into this Identity's foreign-estimate zone.

Weight M_i is the *sender's* emergent self-Mass (last seen on their signal /
public card), not the observer's private my_mass_estimate of the sender.

See docs/mass.md.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Optional, Union

from .sqlite_store import SQLiteStore

# Cold-start when sender never published sender_emergent_mass (0–100 scale).
M_UNKNOWN = 10.0
DEFAULT_CONFIDENCE = 0.5
DEPTH_EPS = 0.01


def depth_factor(accumulated_depth: float) -> float:
    """Diminishing returns on interaction depth: d / (1 + d)."""
    d = max(0.0, float(accumulated_depth))
    return d / (1.0 + d)


def weight_for(
    *,
    sender_mass: float,
    confidence: float,
    accumulated_depth: float,
) -> float:
    """w_i = (M_i/100) * c_i * max(depth_factor(d_i), ε)."""
    m = max(0.0, min(100.0, float(sender_mass)))
    c = max(0.0, min(1.0, float(confidence)))
    df = max(depth_factor(accumulated_depth), DEPTH_EPS)
    return (m / 100.0) * c * df


@dataclass
class Contributor:
    """One sender's contribution to the self-Mass aggregate."""

    sender_handle: str
    estimate: float
    confidence: float
    accumulated_depth: float
    sender_mass: float
    sender_mass_source: str  # "signal" | "cold_start"
    weight: float
    quarantined: bool = False
    included: bool = True
    skip_reason: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class MassReadout:
    """Derived volume + emergent self-Mass for one install."""

    emergent_self_mass: Optional[float]
    total_weight: float
    estimator_count: int
    volume_count: int
    volume_weighted: float
    contributors: list[Contributor] = field(default_factory=list)
    formula_version: str = "0"
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "emergent_self_mass": self.emergent_self_mass,
            "total_weight": self.total_weight,
            "estimator_count": self.estimator_count,
            "volume_count": self.volume_count,
            "volume_weighted": self.volume_weighted,
            "formula_version": self.formula_version,
            "notes": list(self.notes),
            "contributors": [c.to_dict() for c in self.contributors],
        }


def compute_mass_readout(registry_root: Union[str, Path]) -> MassReadout:
    """Compute volume + emergent self-Mass from the foreign-estimate zone.

    Pure function of SQLite foreign-estimate projections. No network. No Stem writes.
    M_i = last sender_emergent_mass stored from their signals (else M_UNKNOWN).
    """
    store = SQLiteStore.from_registry_root(registry_root)
    contributors: list[Contributor] = []
    weighted_sum = 0.0
    total_weight = 0.0
    volume_count = 0
    volume_weighted = 0.0
    notes: list[str] = []

    for handle in store.list_foreign_handles():
        rec = store.load_foreign(handle)
        if rec is None:
            continue

        if rec.quarantine:
            contributors.append(
                Contributor(
                    sender_handle=handle,
                    estimate=float(rec.coarse_mass_estimate)
                    if rec.coarse_mass_estimate is not None
                    else 0.0,
                    confidence=float(rec.mass_confidence)
                    if rec.mass_confidence is not None
                    else DEFAULT_CONFIDENCE,
                    accumulated_depth=float(rec.accumulated_depth),
                    sender_mass=float(rec.sender_emergent_mass)
                    if rec.sender_emergent_mass is not None
                    else 0.0,
                    sender_mass_source="signal",
                    weight=0.0,
                    quarantined=True,
                    included=False,
                    skip_reason="quarantined",
                )
            )
            continue

        if rec.existence_confirmed:
            volume_count += 1
            volume_weighted += depth_factor(rec.accumulated_depth)

        if rec.coarse_mass_estimate is None:
            contributors.append(
                Contributor(
                    sender_handle=handle,
                    estimate=0.0,
                    confidence=DEFAULT_CONFIDENCE,
                    accumulated_depth=float(rec.accumulated_depth),
                    sender_mass=float(rec.sender_emergent_mass)
                    if rec.sender_emergent_mass is not None
                    else M_UNKNOWN,
                    sender_mass_source=(
                        "signal" if rec.sender_emergent_mass is not None else "cold_start"
                    ),
                    weight=0.0,
                    included=False,
                    skip_reason="no_coarse_mass_estimate",
                )
            )
            continue

        if rec.sender_emergent_mass is not None:
            sender_mass = float(rec.sender_emergent_mass)
            mass_source = "signal"
        else:
            sender_mass = M_UNKNOWN
            mass_source = "cold_start"

        conf = (
            float(rec.mass_confidence)
            if rec.mass_confidence is not None
            else DEFAULT_CONFIDENCE
        )
        est = max(0.0, min(100.0, float(rec.coarse_mass_estimate)))

        w = weight_for(
            sender_mass=sender_mass,
            confidence=conf,
            accumulated_depth=float(rec.accumulated_depth),
        )

        contributors.append(
            Contributor(
                sender_handle=handle,
                estimate=est,
                confidence=conf,
                accumulated_depth=float(rec.accumulated_depth),
                sender_mass=sender_mass,
                sender_mass_source=mass_source,
                weight=w,
                included=True,
            )
        )
        weighted_sum += w * est
        total_weight += w

    if total_weight <= 0.0:
        self_mass: Optional[float] = None
        if volume_count == 0:
            notes.append("unobserved: no non-quarantined existence signals")
        else:
            notes.append(
                "volume present but no coarse_mass_estimate yet — self_Mass unobserved"
            )
    else:
        self_mass = weighted_sum / total_weight

    estimator_count = sum(1 for c in contributors if c.included)

    return MassReadout(
        emergent_self_mass=self_mass,
        total_weight=total_weight,
        estimator_count=estimator_count,
        volume_count=volume_count,
        volume_weighted=volume_weighted,
        contributors=contributors,
        formula_version="0",
        notes=notes,
    )


def build_public_card(
    *,
    local_handle: str,
    registry_root: Union[str, Path],
    preferred_name: Optional[str] = None,
    substrate: str = "human",
) -> dict[str, Any]:
    """Public card payload including live emergent self-Mass (always readable)."""
    readout = compute_mass_readout(registry_root)
    identity = SQLiteStore.from_registry_root(registry_root).identity()
    return {
        "local_handle": local_handle,
        "preferred_name": preferred_name,
        "substrate": substrate,
        "accepts_ie_signals": True,
        "schema_version": "0",
        "emergent_self_mass": readout.emergent_self_mass,
        "mass_unobserved": readout.emergent_self_mass is None,
        "volume_count": readout.volume_count,
        "estimator_count": readout.estimator_count,
        "mass_formula_version": readout.formula_version,
        "last_mature_at": identity["last_mature_at"],
    }
