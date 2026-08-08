"""ie init - create a personal DB-only IE install."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any, Optional

from runtime.database import DatabaseError, initialize_database

from .paths import HEADER_NAME


LEGACY_STATE_NAMES = (
    HEADER_NAME,
    "STEM.yaml",
    "dimension-catalogue.yaml",
    "registry",
    "trajectory",
)


def _legacy_state_paths(root: Path) -> list[Path]:
    return [root / name for name in LEGACY_STATE_NAMES if (root / name).exists()]


def _remove_legacy_state(root: Path) -> None:
    for path in _legacy_state_paths(root):
        if path.is_dir():
            shutil.rmtree(path)
        else:
            path.unlink()


def init_install(
    target: Path,
    *,
    handle: str,
    preferred_name: Optional[str] = None,
    force: bool = False,
    reset: bool = False,
    account_info: Optional[dict[str, Any]] = None,
    app_version: str = "",
) -> Path:
    """Create a fresh DB-only install without copying mutable YAML state."""
    target = target.expanduser().resolve()
    db_path = target / ".ie" / "ie.sqlite3"
    legacy_paths = _legacy_state_paths(target)

    if db_path.exists() and not reset:
        raise SystemExit(
            f"IE database already exists at {db_path}. "
            "Use --reset with explicit confirmation to replace it."
        )
    if legacy_paths and not reset:
        names = ", ".join(path.name for path in legacy_paths)
        raise SystemExit(
            f"Legacy YAML install detected at {target} ({names}). "
            "V1 does not migrate YAML state automatically; back it up or export "
            "it manually, then use --reset with explicit confirmation to remove it."
        )

    if reset:
        if db_path.parent.exists():
            shutil.rmtree(db_path.parent)
        _remove_legacy_state(target)

    target.mkdir(parents=True, exist_ok=True)
    try:
        initialize_database(
            target,
            handle=handle,
            preferred_name=preferred_name,
            account_info=account_info,
            app_version=app_version,
        )
    except DatabaseError as exc:
        raise SystemExit(str(exc)) from exc

    tier = (account_info or {}).get("tier") or "free"
    readme = target / "README.md"
    if not readme.exists() or force or reset:
        readme.write_text(
            f"# IE install - `{handle}`\n\n"
            f"Created by `ie init` (tier: {tier}).\n\n"
            "Canonical mutable state lives in `.ie/ie.sqlite3`.\n\n"
            "Commands: `ie status`, `ie db info`, `ie signal apply`, "
            "`ie request list`, `ie registry list`, `ie mass`\n",
            encoding="utf-8",
        )

    agent_doc = target / "IE.md"
    if not agent_doc.exists() or force or reset:
        agent_doc.write_text(
            f"# Local IE Surface: `{handle}`\n\n"
            "This install is DB-only. Read mutable state from `.ie/ie.sqlite3` "
            "through the `ie` CLI or runtime API.\n\n"
            "- Discovery: `.ie/ie.sqlite3`\n"
            "- Public metadata: `ie status --json` and the local card surface\n"
            "- Writes: use CLI/runtime operations; do not edit the database directly\n"
            "- Evidence: use root-relative paths and hashes\n",
            encoding="utf-8",
        )

    return target
