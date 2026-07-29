"""File-based foreign-estimate zone storage (Free tier)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from .models import ForeignEstimateRecord

try:
    import yaml  # type: ignore
except ImportError:  # pragma: no cover
    yaml = None


def _safe_handle(handle: str) -> str:
    """Filesystem-safe filename from handle."""
    return "".join(c if c.isalnum() or c in "-_." else "_" for c in handle)


class ForeignEstimateStore:
    """YAML (preferred) or JSON store under registry/_foreign_estimates/."""

    def __init__(self, registry_root: Path):
        self.root = Path(registry_root) / "_foreign_estimates"
        self.root.mkdir(parents=True, exist_ok=True)

    def _path_for(self, sender_handle: str) -> Path:
        base = _safe_handle(sender_handle)
        yml = self.root / f"{base}.yaml"
        if yml.exists() or yaml is not None:
            return yml
        return self.root / f"{base}.json"

    def load(self, sender_handle: str) -> Optional[ForeignEstimateRecord]:
        path = self._path_for(sender_handle)
        if not path.exists():
            # try the other extension
            alt = path.with_suffix(".json" if path.suffix == ".yaml" else ".yaml")
            if alt.exists():
                path = alt
            else:
                return None
        text = path.read_text(encoding="utf-8")
        if path.suffix == ".yaml" and yaml is not None:
            data = yaml.safe_load(text) or {}
        else:
            data = json.loads(text)
        return ForeignEstimateRecord.from_dict(data)

    def save(self, record: ForeignEstimateRecord) -> Path:
        path = self._path_for(record.sender_handle)
        data = record.to_dict()
        if path.suffix == ".yaml" and yaml is not None:
            path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")
        else:
            path = path.with_suffix(".json")
            path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        return path

    def list_senders(self) -> list[str]:
        handles = []
        for p in self.root.glob("*.*"):
            if p.stem.startswith("_"):
                continue
            handles.append(p.stem)
        return sorted(set(handles))
