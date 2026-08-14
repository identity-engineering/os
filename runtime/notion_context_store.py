"""Notion ContextStore adapter (read-first skills).

Config (install .ie/context_store.json):
{
  "adapter": "notion",
  "root_page_id": "<notion page id>",
  "skills_child_title": "Skills"   // optional folder page title
}

Token: environment IE_NOTION_TOKEN or NOTION_TOKEN (never stored in repo).

Mapping: child pages of the Skills parent, title = skill name, markdown body.
Write path is implemented for tests/dogfood but read is the v0 priority.
"""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Callable, Optional

from runtime.context_store import (
    ContextStoreError,
    SkillDocument,
    SkillRef,
)

NOTION_VERSION = "2022-06-28"
NOTION_API = "https://api.notion.com/v1"


def _normalize_page_id(raw: str) -> str:
    s = raw.strip().replace("-", "")
    if len(s) == 32 and re.fullmatch(r"[0-9a-fA-F]+", s):
        return f"{s[0:8]}-{s[8:12]}-{s[12:16]}-{s[16:20]}-{s[20:32]}"
    return raw.strip()


def _rich_text_to_plain(rich: list[dict[str, Any]]) -> str:
    parts: list[str] = []
    for item in rich or []:
        if isinstance(item, dict):
            parts.append(str(item.get("plain_text") or ""))
    return "".join(parts)


def _blocks_to_markdown(blocks: list[dict[str, Any]]) -> str:
    lines: list[str] = []
    for block in blocks:
        btype = block.get("type")
        payload = block.get(btype) if isinstance(btype, str) else None
        if not isinstance(payload, dict):
            continue
        text = _rich_text_to_plain(payload.get("rich_text") or [])
        if btype == "heading_1":
            lines.append(f"# {text}")
        elif btype == "heading_2":
            lines.append(f"## {text}")
        elif btype == "heading_3":
            lines.append(f"### {text}")
        elif btype == "bulleted_list_item":
            lines.append(f"- {text}")
        elif btype == "numbered_list_item":
            lines.append(f"1. {text}")
        elif btype == "code":
            lang = payload.get("language") or ""
            lines.append(f"```{lang}\n{text}\n```")
        elif btype in {"paragraph", "quote", "callout"}:
            lines.append(text)
        else:
            if text:
                lines.append(text)
    return "\n".join(lines).strip() + ("\n" if blocks else "")


class NotionClient:
    """Minimal Notion REST client (stdlib only)."""

    def __init__(self, token: str, *, opener: Optional[Callable[..., Any]] = None):
        self.token = token
        self._opener = opener or urllib.request.urlopen

    def request(self, method: str, path: str, body: Optional[dict] = None) -> dict[str, Any]:
        url = f"{NOTION_API}{path}"
        data = None
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Notion-Version": NOTION_VERSION,
            "Content-Type": "application/json",
        }
        if body is not None:
            data = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with self._opener(req, timeout=30) as resp:
                raw = resp.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise ContextStoreError(f"Notion HTTP {exc.code}: {detail}") from exc
        except urllib.error.URLError as exc:
            raise ContextStoreError(f"Notion network error: {exc}") from exc
        if not raw:
            return {}
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ContextStoreError(f"Notion invalid JSON: {exc}") from exc
        if not isinstance(parsed, dict):
            raise ContextStoreError("Notion response must be an object")
        return parsed

    def list_children(self, page_id: str) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        cursor = None
        while True:
            q = f"/blocks/{page_id}/children?page_size=100"
            if cursor:
                q += f"&start_cursor={cursor}"
            payload = self.request("GET", q)
            batch = payload.get("results") or []
            if isinstance(batch, list):
                results.extend([b for b in batch if isinstance(b, dict)])
            if not payload.get("has_more"):
                break
            cursor = payload.get("next_cursor")
            if not cursor:
                break
        return results

    def page_title(self, page: dict[str, Any]) -> str:
        props = page.get("properties") or {}
        if isinstance(props, dict):
            for value in props.values():
                if isinstance(value, dict) and value.get("type") == "title":
                    return _rich_text_to_plain(value.get("title") or []).strip()
        # block child_page
        if page.get("type") == "child_page":
            return str((page.get("child_page") or {}).get("title") or "").strip()
        return ""


class NotionContextStore:
    """Read (and optional write) skills from a Notion page tree."""

    def __init__(
        self,
        *,
        install_root: Path,
        client: NotionClient,
        root_page_id: str,
        skills_parent_id: Optional[str] = None,
        skills_child_title: str = "Skills",
        identity_id: Optional[str] = None,
    ):
        self.install_root = Path(install_root).expanduser().resolve()
        self.client = client
        self.root_page_id = _normalize_page_id(root_page_id)
        self.skills_parent_id = (
            _normalize_page_id(skills_parent_id) if skills_parent_id else None
        )
        self.skills_child_title = skills_child_title
        self.identity_id = identity_id
        self._skills_id_cache: Optional[str] = None

    @classmethod
    def from_config(
        cls,
        install_root: Path,
        config: dict[str, Any],
        *,
        identity_id: Optional[str] = None,
        client: Optional[NotionClient] = None,
    ) -> "NotionContextStore":
        token = (
            config.get("token")
            or os.environ.get("IE_NOTION_TOKEN")
            or os.environ.get("NOTION_TOKEN")
        )
        if not token and client is None:
            raise ContextStoreError(
                "Notion adapter requires IE_NOTION_TOKEN or NOTION_TOKEN"
            )
        root = config.get("root_page_id") or config.get("page_id")
        if not root:
            raise ContextStoreError("Notion adapter requires root_page_id in config")
        return cls(
            install_root=install_root,
            client=client or NotionClient(str(token)),
            root_page_id=str(root),
            skills_parent_id=(
                str(config["skills_parent_id"])
                if config.get("skills_parent_id")
                else None
            ),
            skills_child_title=str(config.get("skills_child_title") or "Skills"),
            identity_id=identity_id,
        )

    @property
    def kind(self) -> str:
        return "notion"

    def _skills_parent(self) -> str:
        if self.skills_parent_id:
            return self.skills_parent_id
        if self._skills_id_cache:
            return self._skills_id_cache
        children = self.client.list_children(self.root_page_id)
        for block in children:
            if block.get("type") == "child_page":
                title = self.client.page_title(block)
                if title.lower() == self.skills_child_title.lower():
                    self._skills_id_cache = str(block.get("id"))
                    return self._skills_id_cache
        # Fallback: treat root as skills parent
        self._skills_id_cache = self.root_page_id
        return self.root_page_id

    def _iter_skill_pages(self) -> list[tuple[str, str]]:
        parent = self._skills_parent()
        out: list[tuple[str, str]] = []
        for block in self.client.list_children(parent):
            if block.get("type") != "child_page":
                continue
            title = self.client.page_title(block)
            if not title:
                continue
            out.append((title, str(block.get("id"))))
        return sorted(out, key=lambda t: t[0].lower())

    def list_skills(self) -> list[SkillRef]:
        return [
            SkillRef(name=name, source=self.kind, path=f"notion:{page_id}")
            for name, page_id in self._iter_skill_pages()
        ]

    def read_skill(self, name: str) -> SkillDocument:
        name = name.strip()
        for title, page_id in self._iter_skill_pages():
            if title == name:
                blocks = self.client.list_children(page_id)
                body = _blocks_to_markdown(blocks)
                return SkillDocument(
                    name=name,
                    body=body,
                    source=self.kind,
                    path=f"notion:{page_id}",
                )
        raise ContextStoreError(f"Skill not found in Notion: {name}")

    def write_skill(self, name: str, body: str) -> SkillDocument:
        raise ContextStoreError(
            "Notion write_skill is not enabled in v0 (read-first); "
            "use local_fs or update the Notion page manually"
        )
