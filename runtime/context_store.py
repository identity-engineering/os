"""ContextStore: Identity-scoped skill/context text backends.

Geometry stays in SQLite. This layer only supplies workspace-facing text
(skills, optional context notes) for humans and agents.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional, Protocol, runtime_checkable


class ContextStoreError(Exception):
    """Adapter or resolution failure."""


@dataclass(frozen=True)
class SkillRef:
    name: str
    source: str  # local_fs | notion | …
    path: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "source": self.source, "path": self.path}


@dataclass(frozen=True)
class SkillDocument:
    name: str
    body: str
    source: str
    path: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "body": self.body,
            "source": self.source,
            "path": self.path,
        }


@runtime_checkable
class ContextStore(Protocol):
    """Identity-scoped context/skill text store."""

    @property
    def kind(self) -> str:
        """Adapter id: local_fs | notion | …"""

    def list_skills(self) -> list[SkillRef]:
        ...

    def read_skill(self, name: str) -> SkillDocument:
        ...

    def write_skill(self, name: str, body: str) -> SkillDocument:
        ...


def skills_dir(install_root: Path) -> Path:
    return Path(install_root).expanduser().resolve() / "skills"


def adapter_config_path(install_root: Path) -> Path:
    return Path(install_root).expanduser().resolve() / ".ie" / "context_store.json"


def load_adapter_config(install_root: Path) -> dict[str, Any]:
    path = adapter_config_path(install_root)
    if not path.is_file():
        return {"adapter": "local_fs"}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ContextStoreError(f"Invalid context store config: {exc}") from exc
    if not isinstance(data, dict):
        raise ContextStoreError("context_store.json must be a JSON object")
    data.setdefault("adapter", "local_fs")
    return data


def write_adapter_config(install_root: Path, config: dict[str, Any]) -> Path:
    path = adapter_config_path(install_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(config, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return path


class LocalFsContextStore:
    """Reference ContextStore: <install>/skills/<name>/SKILL.md."""

    def __init__(self, install_root: Path, *, identity_id: Optional[str] = None):
        self.install_root = Path(install_root).expanduser().resolve()
        self.identity_id = identity_id
        self._root = skills_dir(self.install_root)

    @property
    def kind(self) -> str:
        return "local_fs"

    def list_skills(self) -> list[SkillRef]:
        if not self._root.is_dir():
            return []
        refs: list[SkillRef] = []
        for child in sorted(self._root.iterdir()):
            skill_file = child / "SKILL.md"
            if child.is_dir() and skill_file.is_file():
                refs.append(
                    SkillRef(
                        name=child.name,
                        source=self.kind,
                        path=str(skill_file.relative_to(self.install_root)),
                    )
                )
        return refs

    def read_skill(self, name: str) -> SkillDocument:
        name = name.strip()
        if not name or "/" in name or name in {".", ".."}:
            raise ContextStoreError(f"Invalid skill name: {name!r}")
        path = self._root / name / "SKILL.md"
        if not path.is_file():
            raise ContextStoreError(f"Skill not found: {name}")
        return SkillDocument(
            name=name,
            body=path.read_text(encoding="utf-8"),
            source=self.kind,
            path=str(path.relative_to(self.install_root)),
        )

    def write_skill(self, name: str, body: str) -> SkillDocument:
        name = name.strip()
        if not name or "/" in name or name in {".", ".."}:
            raise ContextStoreError(f"Invalid skill name: {name!r}")
        dest_dir = self._root / name
        dest_dir.mkdir(parents=True, exist_ok=True)
        path = dest_dir / "SKILL.md"
        path.write_text(body, encoding="utf-8")
        return SkillDocument(
            name=name,
            body=body,
            source=self.kind,
            path=str(path.relative_to(self.install_root)),
        )


def open_context_store(
    install_root: Path,
    *,
    identity_id: Optional[str] = None,
    config: Optional[dict[str, Any]] = None,
) -> ContextStore:
    """Resolve the active ContextStore for an install."""
    cfg = config if config is not None else load_adapter_config(install_root)
    adapter = str(cfg.get("adapter") or "local_fs").strip().lower()
    if adapter in {"local_fs", "local", "fs", "file"}:
        return LocalFsContextStore(install_root, identity_id=identity_id)
    if adapter == "notion":
        from runtime.notion_context_store import NotionContextStore

        return NotionContextStore.from_config(
            install_root, cfg, identity_id=identity_id
        )
    raise ContextStoreError(f"Unknown context store adapter: {adapter!r}")


def adapter_status(install_root: Path) -> dict[str, Any]:
    """Describe configured + effective context store."""
    cfg = load_adapter_config(install_root)
    try:
        store = open_context_store(install_root, config=cfg)
        skills = [r.to_dict() for r in store.list_skills()]
        effective = store.kind
        error = None
    except ContextStoreError as exc:
        skills = []
        effective = None
        error = str(exc)
    return {
        "configured_adapter": cfg.get("adapter", "local_fs"),
        "effective_adapter": effective,
        "config": {k: v for k, v in cfg.items() if k != "token"},
        "skill_count": len(skills),
        "skills": skills,
        "error": error,
    }
