"""Public Space boundary descriptors and safe inbound validation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional, Union

from .database import Database, DatabaseError, canonical_json, database_path, sha256_text

MEMBRANE_FORMAT = "identity-engineering.space-boundary"
MEMBRANE_FORMAT_VERSION = 1


class MembraneError(ValueError):
    """Raised when a Space boundary cannot be exported or accepted."""


def export_space_boundary(
    install_root: Union[str, Path],
    *,
    space_id: Optional[str] = None,
) -> dict[str, Any]:
    """Build a public descriptor without exporting private Identity geometry."""
    root = Path(install_root).expanduser().resolve()
    db_path = database_path(root)
    if not db_path.is_file():
        raise MembraneError(f"No IE database under {root}")

    with Database(db_path) as database:
        install = database.conn.execute("SELECT * FROM install LIMIT 1").fetchone()
        identity = database.conn.execute("SELECT * FROM identity LIMIT 1").fetchone()
        if install is None or identity is None:
            raise MembraneError("database has no local install and identity")
        effective_space_id = space_id or str(identity["identity_id"])
        _validate_identifier(effective_space_id, "space_id")
        payload = {
            "space": {
                "space_id": effective_space_id,
                "kind": "local",
                "hosting": "local_device",
                "identity_id": str(identity["identity_id"]),
                "local_handle": str(identity["local_handle"]),
                "preferred_name": identity["preferred_name"],
                "substrate": str(identity["substrate"]),
            },
            "membrane": {
                "known": True,
                "addressable": False,
                "export_policy": {
                    "public_card": True,
                    "full_private_geometry": False,
                },
                "inbound_policy": {
                    "interaction_signals": "grant_and_membrane",
                    "private_geometry": "deny",
                },
            },
        }

    checksum = sha256_text(canonical_json(payload))
    return {
        "format": MEMBRANE_FORMAT,
        "format_version": MEMBRANE_FORMAT_VERSION,
        "boundary_id": checksum,
        "payload_sha256": checksum,
        "payload": payload,
    }


def verify_space_boundary(document: Any) -> dict[str, Any]:
    """Validate a boundary descriptor without granting access to its Space."""
    if not isinstance(document, dict):
        raise MembraneError("Space boundary must be an object")
    required = {"format", "format_version", "boundary_id", "payload_sha256", "payload"}
    if set(document) != required:
        raise MembraneError("Space boundary envelope has unsupported fields")
    if document.get("format") != MEMBRANE_FORMAT:
        raise MembraneError("unsupported Space boundary format")
    if document.get("format_version") != MEMBRANE_FORMAT_VERSION:
        raise MembraneError("unsupported Space boundary version")
    payload = document.get("payload")
    if not isinstance(payload, dict) or set(payload) != {"space", "membrane"}:
        raise MembraneError("Space boundary payload is invalid")
    expected = sha256_text(canonical_json(payload))
    if document.get("payload_sha256") != expected or document.get("boundary_id") != expected:
        raise MembraneError("Space boundary checksum mismatch")

    space = payload["space"]
    membrane = payload["membrane"]
    if not isinstance(space, dict) or set(space) != {
        "space_id",
        "kind",
        "hosting",
        "identity_id",
        "local_handle",
        "preferred_name",
        "substrate",
    }:
        raise MembraneError("Space boundary identity descriptor is invalid")
    for field in ("space_id", "identity_id", "local_handle", "substrate"):
        _validate_identifier(space.get(field), f"space.{field}")
    if space.get("preferred_name") is not None and not isinstance(space["preferred_name"], str):
        raise MembraneError("space.preferred_name must be text or null")
    if space.get("kind") != "local" or space.get("hosting") != "local_device":
        raise MembraneError("unsupported Space boundary hosting")
    if not isinstance(membrane, dict) or set(membrane) != {
        "known",
        "addressable",
        "export_policy",
        "inbound_policy",
    }:
        raise MembraneError("Space membrane policy is invalid")
    if not isinstance(membrane["known"], bool) or not isinstance(membrane["addressable"], bool):
        raise MembraneError("Space membrane visibility flags are invalid")
    if membrane["export_policy"] != {
        "public_card": True,
        "full_private_geometry": False,
    }:
        raise MembraneError("Space export policy is not membrane-safe")
    if membrane["inbound_policy"] != {
        "interaction_signals": "grant_and_membrane",
        "private_geometry": "deny",
    }:
        raise MembraneError("Space inbound policy is not membrane-safe")
    return document


def accept_inbound_boundary(
    document: Any,
    *,
    expected_space_id: Optional[str] = None,
) -> dict[str, Any]:
    """Classify a verified remote Space as known, never as implicitly addressable."""
    verified = verify_space_boundary(document)
    space = verified["payload"]["space"]
    if expected_space_id is not None and space["space_id"] != expected_space_id:
        raise MembraneError("Space boundary does not match the expected Space")
    return {
        "status": "known",
        "space_id": space["space_id"],
        "identity_id": space["identity_id"],
        "local_handle": space["local_handle"],
        "addressable": False,
        "private_geometry_accepted": False,
        "boundary_id": verified["boundary_id"],
    }


def write_space_boundary(
    install_root: Union[str, Path],
    destination: Union[str, Path],
    *,
    space_id: Optional[str] = None,
    overwrite: bool = False,
) -> dict[str, Any]:
    """Write a public boundary descriptor as JSON."""
    destination_path = Path(destination).expanduser().resolve()
    if destination_path.exists() and not overwrite:
        raise DatabaseError(f"Space boundary destination already exists: {destination_path}")
    document = export_space_boundary(install_root, space_id=space_id)
    destination_path.parent.mkdir(parents=True, exist_ok=True)
    destination_path.write_text(
        json.dumps(document, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return {
        "destination": str(destination_path),
        "boundary_id": document["boundary_id"],
        "space_id": document["payload"]["space"]["space_id"],
        "private_geometry_exported": False,
    }


def _validate_identifier(value: Any, label: str) -> None:
    if not isinstance(value, str) or not 1 <= len(value) <= 128 or not value.strip():
        raise MembraneError(f"{label} is invalid")