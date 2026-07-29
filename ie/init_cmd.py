"""ie init — create a personal IE install from bundled templates."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Optional

from .paths import HEADER_NAME, bundled_templates_dir

try:
    import yaml  # type: ignore
except ImportError:  # pragma: no cover
    yaml = None


def _patch_header(
    header_path: Path,
    handle: str,
    preferred_name: Optional[str],
    tier: str = "free",
) -> None:
    text = header_path.read_text(encoding="utf-8")
    if yaml is not None:
        data = yaml.safe_load(text) or {}
        identity = data.setdefault("identity", {})
        identity["local_handle"] = handle
        if preferred_name:
            identity["preferred_name"] = preferred_name
        data["tier"] = tier
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
    lines.append(f'tier: "{tier}"\n')
    header_path.write_text("".join(lines), encoding="utf-8")


def init_install(
    target: Path,
    *,
    handle: str,
    preferred_name: Optional[str] = None,
    force: bool = False,
    tier: str = "free",
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

    _patch_header(
        target / HEADER_NAME,
        handle=handle,
        preferred_name=preferred_name,
        tier=tier,
    )

    readme = target / "README.md"
    if not readme.exists() or force:
        readme.write_text(
            f"# IE install — `{handle}`\n\n"
            f"Created by `ie init` (tier: {tier}).\n\n"
            f"- Header: `{HEADER_NAME}`\n"
            f"- Registry: `registry/`\n"
            f"- Foreign estimates: `registry/_foreign_estimates/`\n\n"
            f"Commands: `ie status`, `ie signal apply`, `ie registry list`\n",
            encoding="utf-8",
        )

    return target
