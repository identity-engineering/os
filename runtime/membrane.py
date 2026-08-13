"""Space membrane policy: what may leave / enter a Space (OS #82)."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Optional

POLICY_VERSION = 1

# Table groups for export policy (logical, not DB engine).
EXPORT_TABLE_GROUPS: dict[str, tuple[str, ...]] = {
    "identity_core": (
        "install",
        "identity",
        "privacy_defaults",
        "stem_state",
        "stem_revisions",
    ),
    "metric": ("metric_dimensions", "metric_pairs"),
    "registry": (
        "registry_entries",
        "registry_entry_revisions",
        "registry_dimension_values",
        "registry_dimension_revisions",
    ),
    "interaction": (
        "interaction_events",
        "apply_receipts",
        "foreign_estimates",
        "estimate_requests",
    ),
    "workspace": ("workspace_items", "workspace_item_revisions", "evidence_sources"),
    "geometry": (
        "geometry_receipts",
        "geometry_receipt_sources",
        "mature_events",
        "trajectory_entries",
    ),
    "policy": ("consent_grants", "quarantines", "policy_events"),
}

ALL_EXPORT_TABLES: tuple[str, ...] = tuple(
    sorted({t for group in EXPORT_TABLE_GROUPS.values() for t in group})
)

# Inbound Interaction Signal fields the membrane may allow/deny.
INBOUND_SIGNAL_FIELDS: tuple[str, ...] = (
    "existence",
    "interaction_depth_delta",
    "sender_emergent_mass",
    "sender_last_mature_at",
    "coarse_mass_estimate",
    "mass_confidence",
    "dimensions_delta",
    "relation_pull",
)


def default_local_membrane_policy() -> dict[str, Any]:
    """Owner-sovereign local mini-Space defaults.

    Local Free is the owner's device: full export for backup/migration,
    inbound still gated by Surface LocalPolicy (consent/quarantine).
    Membrane layer is additive; it does not replace Identity-level grants.
    """
    return {
        "version": POLICY_VERSION,
        "export": {
            "mode": "owner_full",
            "allow_tables": None,
            "deny_tables": [],
        },
        "inbound": {
            "mode": "surface_default",
            "allow_fields": None,
            "deny_fields": [],
        },
    }


def parse_membrane_policy(raw: Any) -> dict[str, Any]:
    """Parse policy_json into a normalised policy dict.

    Empty / invalid / missing → local defaults (fail open for local owner path,
    never invent a parallel geometry model).
    """
    base = default_local_membrane_policy()
    if raw is None or raw == "" or raw == "{}":
        return base
    if isinstance(raw, str):
        try:
            data = json.loads(raw)
        except (TypeError, json.JSONDecodeError):
            return base
    elif isinstance(raw, dict):
        data = raw
    else:
        return base

    if not isinstance(data, dict):
        return base

    export = data.get("export") if isinstance(data.get("export"), dict) else {}
    inbound = data.get("inbound") if isinstance(data.get("inbound"), dict) else {}

    out = default_local_membrane_policy()
    if isinstance(data.get("version"), int) and data["version"] > 0:
        out["version"] = data["version"]

    mode = export.get("mode")
    if mode in {"owner_full", "allowlist", "denylist"}:
        out["export"]["mode"] = mode
    if isinstance(export.get("allow_tables"), list):
        out["export"]["allow_tables"] = [
            str(t) for t in export["allow_tables"] if isinstance(t, str)
        ]
    if isinstance(export.get("deny_tables"), list):
        out["export"]["deny_tables"] = [
            str(t) for t in export["deny_tables"] if isinstance(t, str)
        ]

    imode = inbound.get("mode")
    if imode in {"surface_default", "allowlist", "denylist"}:
        out["inbound"]["mode"] = imode
    if isinstance(inbound.get("allow_fields"), list):
        out["inbound"]["allow_fields"] = [
            str(f) for f in inbound["allow_fields"] if isinstance(f, str)
        ]
    if isinstance(inbound.get("deny_fields"), list):
        out["inbound"]["deny_fields"] = [
            str(f) for f in inbound["deny_fields"] if isinstance(f, str)
        ]

    return out


def expand_table_selectors(selectors: Optional[list[str]]) -> set[str]:
    """Expand group names and raw table names into concrete table set."""
    if not selectors:
        return set()
    tables: set[str] = set()
    for item in selectors:
        if item in EXPORT_TABLE_GROUPS:
            tables.update(EXPORT_TABLE_GROUPS[item])
        elif item in ALL_EXPORT_TABLES:
            tables.add(item)
    return tables


@dataclass(frozen=True)
class ExportMembraneResult:
    allowed_tables: tuple[str, ...]
    stripped_tables: tuple[str, ...]
    policy: dict[str, Any] = field(default_factory=default_local_membrane_policy)


def filter_export_tables(
    available_tables: list[str],
    policy: Optional[dict[str, Any]] = None,
) -> ExportMembraneResult:
    """Decide which export tables may leave the Space."""
    pol = parse_membrane_policy(policy)
    export = pol["export"]
    available = [t for t in available_tables if t in ALL_EXPORT_TABLES or t in available_tables]
    # Keep unknown tables only under owner_full (forward-compatible).
    mode = export["mode"]
    deny = expand_table_selectors(export.get("deny_tables") or [])

    if mode == "owner_full":
        allowed = [t for t in available if t not in deny]
    elif mode == "allowlist":
        allow = expand_table_selectors(export.get("allow_tables") or [])
        allowed = [t for t in available if t in allow and t not in deny]
    else:  # denylist
        allowed = [t for t in available if t not in deny]

    stripped = [t for t in available if t not in allowed]
    return ExportMembraneResult(
        allowed_tables=tuple(allowed),
        stripped_tables=tuple(stripped),
        policy=pol,
    )


@dataclass(frozen=True)
class InboundMembraneResult:
    allowed_fields: tuple[str, ...]
    stripped_fields: tuple[str, ...]
    policy: dict[str, Any] = field(default_factory=default_local_membrane_policy)


def filter_inbound_fields(
    candidate_fields: list[str],
    policy: Optional[dict[str, Any]] = None,
) -> InboundMembraneResult:
    """Intersect Surface-level candidates with Space membrane inbound rules."""
    pol = parse_membrane_policy(policy)
    inbound = pol["inbound"]
    candidates = [f for f in candidate_fields if f in INBOUND_SIGNAL_FIELDS]
    deny = set(inbound.get("deny_fields") or [])
    mode = inbound["mode"]

    if mode == "surface_default":
        allowed = [f for f in candidates if f not in deny]
    elif mode == "allowlist":
        allow = set(inbound.get("allow_fields") or [])
        allowed = [f for f in candidates if f in allow and f not in deny]
    else:  # denylist
        allowed = [f for f in candidates if f not in deny]

    stripped = [f for f in candidates if f not in allowed]
    return InboundMembraneResult(
        allowed_fields=tuple(allowed),
        stripped_fields=tuple(stripped),
        policy=pol,
    )


def load_space_policy_from_row(space_row: Any) -> dict[str, Any]:
    """Extract normalised membrane policy from a spaces row."""
    if space_row is None:
        return default_local_membrane_policy()
    try:
        raw = space_row["policy_json"]
    except (KeyError, IndexError, TypeError):
        raw = None
    return parse_membrane_policy(raw)
