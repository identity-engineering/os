"""Resolve package templates and live IE install roots."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

HEADER_NAME = "HEADER.yaml"


def package_root() -> Path:
    """Root of the installed/editable ie-os source tree (repo root in dev)."""
    return Path(__file__).resolve().parent.parent


def bundled_templates_dir() -> Path:
    """Personal templates shipped with the package/repo."""
    # Prefer repo layout (editable install / git checkout)
    repo_templates = package_root() / "templates" / "personal"
    if repo_templates.is_dir():
        return repo_templates
    # Fallback: package-adjacent copy if we ever vendor templates under ie/
    alt = Path(__file__).resolve().parent / "templates" / "personal"
    if alt.is_dir():
        return alt
    raise FileNotFoundError(
        "Could not find templates/personal. Reinstall ie-os from the os repository."
    )


def find_ie_root(start: Optional[Path] = None) -> Optional[Path]:
    """Walk upward from start (default cwd) looking for HEADER.yaml."""
    env = os.environ.get("IE_ROOT")
    if env:
        p = Path(env).expanduser().resolve()
        if (p / HEADER_NAME).is_file():
            return p
    cur = (start or Path.cwd()).resolve()
    for candidate in [cur, *cur.parents]:
        if (candidate / HEADER_NAME).is_file():
            return candidate
    return None


def require_ie_root(start: Optional[Path] = None) -> Path:
    root = find_ie_root(start)
    if root is None:
        raise SystemExit(
            "No IE install found (HEADER.yaml). Run `ie init` in a directory, "
            "or set IE_ROOT, or cd into an existing install."
        )
    return root
