"""ie init — create a personal IE install from bundled templates."""

from __future__ import annotations

import shutil
import json
from pathlib import Path
from typing import Any, Optional

from .paths import HEADER_NAME, bundled_templates_dir

try:
    import yaml  # type: ignore
except ImportError:  # pragma: no cover
    yaml = None


def _patch_header(
    header_path: Path,
    handle: str,
    preferred_name: Optional[str],
    account_info: Optional[dict[str, Any]] = None,
) -> None:
    account_info = account_info or {
        "account_mode": "no_account",
        "account_id": None,
        "tier": "free",
        "public_registry_access": False,
    }
    text = header_path.read_text(encoding="utf-8")
    if yaml is not None:
        data = yaml.safe_load(text) or {}
        identity = data.setdefault("identity", {})
        identity["local_handle"] = handle
        if preferred_name:
            identity["preferred_name"] = preferred_name
        data["account"] = {
            "mode": account_info.get("account_mode"),
            "account_id": account_info.get("account_id"),
            "link_pending": bool(account_info.get("account_link_pending")),
            "public_registry_access": bool(
                account_info.get("public_registry_access")
            ),
        }
        data["tier"] = account_info.get("tier") or "free"
        header_path.write_text(
            yaml.safe_dump(data, sort_keys=False, allow_unicode=True),
            encoding="utf-8",
        )
        return

    lines = []
    for line in text.splitlines(keepends=True):
        if "local_handle:" in line:
            lines.append(f'  local_handle: "{handle}"\n')
        elif preferred_name and "preferred_name:" in line:
            lines.append(f'  preferred_name: "{preferred_name}"\n')
        else:
            lines.append(line)
    if not text.endswith("\n"):
        lines.append("\n")
    lines.append(f'tier: "{account_info.get("tier") or "free"}"\n')
    lines.append("account:\n")
    lines.append(f'  mode: "{account_info.get("account_mode")}"\n')
    lines.append("  account_id: null\n")
    lines.append(
        f'  public_registry_access: {str(bool(account_info.get("public_registry_access"))).lower()}\n'
    )
    header_path.write_text("".join(lines), encoding="utf-8")


def _patch_catalogue(catalogue_path: Path, observer: str) -> None:
    if not catalogue_path.is_file():
        return

    text = catalogue_path.read_text(encoding="utf-8")
    if yaml is not None:
        data = yaml.safe_load(text) or {}
        data["observer"] = observer
        catalogue_path.write_text(
            yaml.safe_dump(data, sort_keys=False, allow_unicode=True),
            encoding="utf-8",
        )
        return

    lines = []
    for line in text.splitlines(keepends=True):
        if line.startswith("observer:"):
            lines.append(f'observer: "{observer}"\n')
        else:
            lines.append(line)
    catalogue_path.write_text("".join(lines), encoding="utf-8")


def init_install(
    target: Path,
    *,
    handle: str,
    preferred_name: Optional[str] = None,
    force: bool = False,
    account_info: Optional[dict[str, Any]] = None,
) -> Path:
    """Create install directory (mkdir -p) and copy templates."""
    target = target.expanduser().resolve()
    header = target / HEADER_NAME

    if header.exists() and not force:
        raise SystemExit(
            f"IE install already exists at {target} (found {HEADER_NAME}). "
            f"Use --force to overwrite templates (destructive)."
        )

    src = bundled_templates_dir()
    target.mkdir(parents=True, exist_ok=True)
    readme = target / "README.md"
    readme_existed = readme.exists()

    for item in src.iterdir():
        dest = target / item.name
        if item.is_dir():
            if dest.exists() and force:
                shutil.rmtree(dest)
            if not dest.exists():
                shutil.copytree(item, dest)
        else:
            if dest.exists() and not force:
                continue
            shutil.copy2(item, dest)

    fe = target / "registry" / "_foreign_estimates"
    fe.mkdir(parents=True, exist_ok=True)

    inbox = target / "registry" / "_inbound_requests"
    inbox.mkdir(parents=True, exist_ok=True)

    _patch_header(
        target / HEADER_NAME,
        handle=handle,
        preferred_name=preferred_name,
        account_info=account_info,
    )
    _patch_catalogue(target / "dimension-catalogue.yaml", observer=handle)

    tier = (account_info or {}).get("tier") or "free"
    if not readme_existed or force:
        demo_signal = json.dumps(
            {
                "from": "example-peer",
                "to": handle,
                "timestamp": "2026-08-08T12:00:00+00:00",
                "existence": True,
                "interaction_depth_delta": 0.1,
                "sender_emergent_mass": 70,
                "coarse_mass_estimate": 55,
                "mass_confidence": 0.8,
            },
            separators=(",", ":"),
        )
        readme.write_text(
            f"# IE install - `{handle}`\n\n"
            f"Created by `ie init` (tier: {tier}).\n\n"
            "## First local loop\n\n"
            "This synthetic signal stays on this machine and demonstrates the "
            "local geometry path. Replace it with a real peer signal later.\n\n"
            "```bash\n"
            "ie status\n"
            f"printf '%s\\n' '{demo_signal}' | ie signal apply --open-consent\n"
            "ie mass --detail\n"
            "ie mature --source HEADER.yaml \\\n+  --notes \"What did the interaction make visible?\" \\\n+  --state-delta \"First local interaction recorded\"\n"
            "```\n\n"
            "The signal creates a local Geometry Receipt. Self-Mass remains "
            "relative: it is derived from received estimates, never declared "
            "by this install. Mature records a source-backed self-review and "
            "does not rewrite Stem, Vision, or Policy in v0.\n\n"
            f"Files: `{HEADER_NAME}`, `STEM.yaml`, `dimension-catalogue.yaml`, "
            "`registry/`, `registry/_foreign_estimates/`, and "
            "`registry/_inbound_requests/`.\n",
            encoding="utf-8",
        )

    return target
