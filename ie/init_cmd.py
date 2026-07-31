"""ie init — create a personal IE install from bundled templates."""

from __future__ import annotations

import shutil
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

    tier = (account_info or {}).get("tier") or "free"
    readme = target / "README.md"
    if not readme.exists() or force:
        readme.write_text(
            f"# IE install — `{handle}`\n\n"
            f"Created by `ie init` (tier: {tier}).\n\n"
            f"- Header: `{HEADER_NAME}`\n"
            f"- Registry: `registry/`\n"
            f"- Foreign estimates: `registry/_foreign_estimates/`\n"
            f"- Inbound estimate requests: `registry/_inbound_requests/`\n\n"
            f"Commands: `ie status`, `ie signal apply`, `ie request list`, `ie registry list`\n",
            encoding="utf-8",
        )

    return target
