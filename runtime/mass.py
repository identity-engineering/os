"""Emergent self-Mass and volume readout from the foreign-estimate zone.

Self-Mass is never self-declared. It is a weighted mean of coarse_mass_estimate
values others applied into this Identity's foreign-estimate zone.

See docs/mass.md for the locked v0 formula.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Optional, Union

from .models import ForeignEstimateRecord
from .storage import ForeignEstimateStore

try:
    import yaml  # type: ignore
except ImportError:  # pragma: no cover
    yaml = None

# Cold-start: Mass attributed to a sender with no Registry entry (0–100 scale).
M_UNKNOWN = 10.0
# Default confidence when sender omitted mass_confidence.
DEFAULT_CONFIDENCE = 0.5
# Floor on depth_factor so near-zero depth still yields a tiny weight.
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


def _load_registry_mass(registry_root: Path, handle: str) -> Optional[float]:
    """Read observer's my_mass_estimate of this sender from registry/{handle}."""
    for ext in (".yaml", ".yml", ".json"):
        path = Path(registry_root) / f"{handle}{ext}"
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        if path.suffix == ".json":
            data = json.loads(text)
        elif yaml is not None:
            data = yaml.safe_load(text) or {}
        else:
            return None
        if not isinstance(data, dict):
            return None
        raw = data.get("my_mass_estimate")
        if raw is None:
            return None
        try:
            return float(raw)
        except (TypeError, ValueError):
            return None
    return None


@dataclass
class Contributor:
    """One sender's contribution to the self-Mass aggregate."""

    sender_handle: str
    estimate: float
    confidence: float
    accumulated_depth: float
    sender_mass: float
    sender_mass_source: str  # "registry" | "cold_start"
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

    Pure function of files under registry/. No network. No Stem writes.
    """
    root = Path(registry_root)
    store = ForeignEstimateStore(root)
    contributors: list[Contributor] = []
    weighted_sum = 0.0
    total_weight = 0.0
    volume_count = 0
    volume_weighted = 0.0
    notes: list[str] = []

    for handle in store.list_senders():
        rec = store.load(handle)
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
                    sender_mass=0.0,
                    sender_mass_source="registry",
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
                    sender_mass=0.0,
                    sender_mass_source="registry",
                    weight=0.0,
                    included=False,
                    skip_reason="no_coarse_mass_estimate",
                )
            )
            continue

        reg_mass = _load_registry_mass(root, handle)
        if reg_mass is None:
            sender_mass = M_UNKNOWN
            mass_source = "cold_start"
        else:
            sender_mass = reg_mass
            mass_source = "registry"

        conf = (
            float(rec.mass_confidence)
            if rec.mass_confidence is not None
            else DEFAULT_CONFIDENCE
        )
        est = float(rec.coarse_mass_estimate)
        # Clamp estimate to the documented 0–100 scale
        est = max(0.0, min(100.0, est))

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
