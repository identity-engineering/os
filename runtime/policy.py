"""Minimal access policy for Surface Runtime v0 local apply."""

from __future__ import annotations

from dataclasses import dataclass, field

from .models import InteractionSignal


@dataclass
class LocalPolicy:
    """Default Free-tier policy.

    Always-passed fields auto-apply for non-quarantined senders:
    - existence, interaction_depth_delta
    - sender_emergent_mass (public geometry of the sender)

    Consent fields (estimates *of me*) require grant or open_consent.
    """

    open_consent: bool = False
    quarantined_handles: set[str] = field(default_factory=set)
    grants: dict[str, set[str]] = field(default_factory=dict)
    max_signals_per_sender: int = 1000

    def is_quarantined(self, handle: str) -> bool:
        return handle in self.quarantined_handles

    def may_apply_consent_field(self, sender: str, field_name: str) -> bool:
        if self.open_consent:
            return True
        granted = self.grants.get(sender, set())
        return field_name in granted or "*" in granted

    def evaluate(self, signal: InteractionSignal) -> tuple[list[str], list[dict[str, str]], bool]:
        """Return (fields_to_apply, rejected_with_reason, quarantine_flag)."""
        applied: list[str] = []
        rejected: list[dict[str, str]] = []
        quarantine = self.is_quarantined(signal.from_handle)

        if quarantine:
            applied.append("existence")
            # Still record their published mass for audit, but no depth/consent weight.
            if signal.sender_emergent_mass is not None:
                applied.append("sender_emergent_mass")
            if signal.sender_last_mature_at is not None:
                applied.append("sender_last_mature_at")
            rejected.append(
                {"field": "interaction_depth_delta", "reason": "sender quarantined"}
            )
            for f in (
                "coarse_mass_estimate",
                "mass_confidence",
                "dimensions_delta",
                "relation_pull",
            ):
                if getattr(signal, f) is not None:
                    rejected.append({"field": f, "reason": "sender quarantined"})
            return applied, rejected, True

        # Always-passed
        if signal.existence:
            applied.append("existence")
        applied.append("interaction_depth_delta")
        if signal.sender_emergent_mass is not None:
            applied.append("sender_emergent_mass")
        if signal.sender_last_mature_at is not None:
            applied.append("sender_last_mature_at")

        # Consent-based (about *me*)
        consent_map = {
            "coarse_mass_estimate": signal.coarse_mass_estimate,
            "mass_confidence": signal.mass_confidence,
            "dimensions_delta": signal.dimensions_delta,
            "relation_pull": signal.relation_pull,
        }
        for name, value in consent_map.items():
            if value is None:
                continue
            if self.may_apply_consent_field(signal.from_handle, name):
                applied.append(name)
            else:
                rejected.append({"field": name, "reason": "no grant for consent field"})

        return applied, rejected, False
