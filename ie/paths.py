"""Resolve package templates and live IE install roots."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

HEADER_NAME = "HEADER.yaml"
CONFIG_DIR_NAME = "ie-os"
ACTIVE_ROOT_NAME = "active-root"


def active_root_config_path() -> Path:
    """Return the user config file that stores the active IE install root."""
    config_home = os.environ.get("XDG_CONFIG_HOME")
    if config_home:
        base = Path(config_home).expanduser()
    else:
        base = Path.home() / ".config"
    return base / CONFIG_DIR_NAME / ACTIVE_ROOT_NAME


def remember_ie_root(root: Path) -> None:
    """Persist a valid install root for commands run outside that directory."""
    root = root.expanduser().resolve()
    if not (root / HEADER_NAME).is_file():
        raise ValueError(f"Cannot remember IE root without {HEADER_NAME}: {root}")

    config_path = active_root_config_path()
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(f"{root}\n", encoding="utf-8")


def remembered_ie_root() -> Optional[Path]:
    """Load the remembered root, ignoring missing or stale configuration."""
    config_path = active_root_config_path()
    try:
        raw = config_path.read_text(encoding="utf-8").strip()
    except OSError:
        return None
    if not raw:
        return None

    root = Path(raw).expanduser().resolve()
    return root if (root / HEADER_NAME).is_file() else None


def package_root() -> Path:
    """Root of the installed/editable ie-os source tree (repo root in dev)."""
    return Path(__file__).resolve().parent.parent


def bundled_templates_dir() -> Path:
    """Personal templates shipped with the package/repo.

    Search order:
    1. Repo layout: <repo>/templates/personal (editable install)
    2. Bundled in package: ie/templates/personal (wheel/sdist install)
    """
    here = Path(__file__).resolve().parent
    candidates = [
        package_root() / "templates" / "personal",
        here / "templates" / "personal",
    ]
    for path in candidates:
        if path.is_dir():
            return path
    raise FileNotFoundError(
        "Could not find templates/personal. Reinstall ie-os "
        "(wheel must include ie/templates/personal; see docs/release.md)."
    )


def find_ie_root(start: Optional[Path] = None) -> Optional[Path]:
    """Find an IE root from the environment, cwd, or remembered config."""
    env = os.environ.get("IE_ROOT")
    if env:
        p = Path(env).expanduser().resolve()
        if (p / HEADER_NAME).is_file():
            return p
    cur = (start or Path.cwd()).resolve()
    for candidate in [cur, *cur.parents]:
        if (candidate / HEADER_NAME).is_file():
            return candidate
    remembered = remembered_ie_root()
    if remembered is not None:
        return remembered

    default_root = (Path.home() / "ie").resolve()
    if (default_root / HEADER_NAME).is_file():
        return default_root
    return None


def require_ie_root(start: Optional[Path] = None) -> Path:
    root = find_ie_root(start)
    if root is None:
        raise SystemExit(
            "No IE install found (HEADER.yaml). Run `ie init` in a directory, "
            "or set IE_ROOT, or cd into an existing install."
        )
    return root
