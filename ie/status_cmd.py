"""ie status — summarize a local IE install."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from .paths import HEADER_NAME

try:
    import yaml  # type: ignore
except ImportError:  # pragma: no cover
    yaml = None


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    text = path.read_text(encoding="utf-8")
    if yaml is None:
        return {"_raw": text[:200]}
    return yaml.safe_load(text) or {}


def collect_status(root: Path) -> dict[str, Any]:
    header = _load_yaml(root / HEADER_NAME)
    identity = header.get("identity") or {}
    registry_dir = root / "registry"
    fe_dir = registry_dir / "_foreign_estimates"

    peers = []
    if registry_dir.is_dir():
        for p in sorted(registry_dir.glob("*.yaml")):
            if p.name.startswith("_"):
                continue
            peers.append(p.stem)
        for p in sorted(registry_dir.glob("*.json")):
            if p.name.startswith("_"):
                continue
            peers.append(p.stem)

    foreign = []
    if fe_dir.is_dir():
        for p in sorted(fe_dir.glob("*.*")):
            if p.name.startswith("_"):
                continue
            foreign.append(p.stem)

    return {
        "root": str(root),
        "handle": identity.get("local_handle"),
        "preferred_name": identity.get("preferred_name"),
        "substrate": header.get("substrate"),
        "schema_version": header.get("schema_version"),
        "registry_peers": sorted(set(peers)),
        "foreign_estimate_senders": sorted(set(foreign)),
        "has_stem": (root / "STEM.yaml").is_file(),
        "has_catalogue": (root / "dimension-catalogue.yaml").is_file(),
    }


def format_status(info: dict[str, Any]) -> str:
    lines = [
        f"IE install: {info['root']}",
        f"  handle:     {info.get('handle') or '—'}",
        f"  name:       {info.get('preferred_name') or '—'}",
        f"  substrate:  {info.get('substrate') or '—'}",
        f"  stem:       {'yes' if info.get('has_stem') else 'no'}",
        f"  catalogue:  {'yes' if info.get('has_catalogue') else 'no'}",
        f"  registry:   {len(info.get('registry_peers') or [])} peer(s)",
    ]
    for h in info.get("registry_peers") or []:
        lines.append(f"    - {h}")
    fe = info.get("foreign_estimate_senders") or []
    lines.append(f"  foreign estimates: {len(fe)} sender(s)")
    for h in fe:
        lines.append(f"    - {h}")
    return "\n".join(lines)
