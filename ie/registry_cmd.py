"""ie registry list|get"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

try:
    import yaml  # type: ignore
except ImportError:  # pragma: no cover
    yaml = None


def list_peers(root: Path) -> list[str]:
    registry = root / "registry"
    if not registry.is_dir():
        return []
    names: list[str] = []
    for p in registry.iterdir():
        if not p.is_file():
            continue
        if p.name.startswith("_"):
            continue
        if p.suffix in {".yaml", ".yml", ".json"}:
            names.append(p.stem)
    return sorted(set(names))


def get_peer(root: Path, handle: str) -> Optional[dict[str, Any]]:
    registry = root / "registry"
    for ext in (".yaml", ".yml", ".json"):
        path = registry / f"{handle}{ext}"
        if path.is_file():
            text = path.read_text(encoding="utf-8")
            if path.suffix == ".json":
                import json

                return json.loads(text)
            if yaml is not None:
                return yaml.safe_load(text) or {}
            return {"_raw": text}
    return None
