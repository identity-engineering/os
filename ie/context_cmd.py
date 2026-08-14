"""ie context / adapters — ContextStore surface."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import typer

from ie.paths import require_ie_root
from runtime.context_store import (
    ContextStoreError,
    adapter_status,
    open_context_store,
    write_adapter_config,
    load_adapter_config,
)
from runtime.database import database_path


def register(app: typer.Typer) -> None:
    context_app = typer.Typer(help="Context Layer skills via ContextStore adapters")
    adapters_app = typer.Typer(help="Context store adapter status and config")
    app.add_typer(context_app, name="context")
    app.add_typer(adapters_app, name="adapters")

    def _root(path: Optional[Path]) -> Path:
        root = path.resolve() if path else require_ie_root()
        if not database_path(root).is_file():
            raise SystemExit(f"No .ie/ie.sqlite3 under {root}")
        return root

    @context_app.command("skills")
    def skills_list(
        path: Optional[Path] = typer.Option(None, "--path", help="IE install root"),
        json_out: bool = typer.Option(False, "--json", help="Machine-readable list"),
    ) -> None:
        """List skills from the active ContextStore."""
        root = _root(path)
        try:
            store = open_context_store(root)
            refs = store.list_skills()
        except ContextStoreError as exc:
            raise SystemExit(str(exc)) from exc
        if json_out:
            typer.echo(
                json.dumps(
                    {
                        "adapter": store.kind,
                        "skills": [r.to_dict() for r in refs],
                    },
                    indent=2,
                    ensure_ascii=False,
                )
            )
            return
        if not refs:
            typer.echo("(no skills)")
            return
        typer.echo(f"adapter: {store.kind}")
        for ref in refs:
            loc = f"  {ref.path}" if ref.path else ""
            typer.echo(f"{ref.name}{loc}")

    @context_app.command("skill")
    def skill_get(
        name: str = typer.Argument(..., help="Skill name, e.g. mature"),
        path: Optional[Path] = typer.Option(None, "--path", help="IE install root"),
        json_out: bool = typer.Option(False, "--json", help="Include metadata JSON"),
    ) -> None:
        """Read one skill document from the active ContextStore."""
        root = _root(path)
        try:
            store = open_context_store(root)
            doc = store.read_skill(name)
        except ContextStoreError as exc:
            raise SystemExit(str(exc)) from exc
        if json_out:
            typer.echo(json.dumps(doc.to_dict(), indent=2, ensure_ascii=False))
            return
        typer.echo(doc.body, nl=False)
        if not doc.body.endswith("\n"):
            typer.echo("")

    @adapters_app.command("status")
    def adapters_status_cmd(
        path: Optional[Path] = typer.Option(None, "--path", help="IE install root"),
        json_out: bool = typer.Option(True, "--json/--no-json", help="JSON (default)"),
    ) -> None:
        """Show configured and effective ContextStore adapter."""
        root = _root(path)
        info = adapter_status(root)
        if json_out:
            typer.echo(json.dumps(info, indent=2, ensure_ascii=False))
            return
        typer.echo(f"configured: {info.get('configured_adapter')}")
        typer.echo(f"effective:  {info.get('effective_adapter')}")
        typer.echo(f"skills:     {info.get('skill_count')}")
        if info.get("error"):
            typer.echo(f"error:      {info['error']}")

    @adapters_app.command("set")
    def adapters_set(
        adapter: str = typer.Argument(..., help="local_fs | notion"),
        root_page_id: Optional[str] = typer.Option(
            None, "--root-page-id", help="Notion root page id (notion only)"
        ),
        skills_parent_id: Optional[str] = typer.Option(
            None, "--skills-parent-id", help="Notion Skills parent page id"
        ),
        path: Optional[Path] = typer.Option(None, "--path", help="IE install root"),
    ) -> None:
        """Select ContextStore adapter for this install (writes .ie/context_store.json)."""
        root = _root(path)
        key = adapter.strip().lower()
        if key in {"local", "fs", "file"}:
            key = "local_fs"
        if key not in {"local_fs", "notion"}:
            raise SystemExit("adapter must be local_fs or notion")
        cfg = load_adapter_config(root)
        cfg["adapter"] = key
        if key == "notion":
            if root_page_id:
                cfg["root_page_id"] = root_page_id
            if skills_parent_id:
                cfg["skills_parent_id"] = skills_parent_id
            if not cfg.get("root_page_id"):
                raise SystemExit("notion requires --root-page-id (or existing config)")
        out = write_adapter_config(root, cfg)
        typer.echo(json.dumps({"ok": True, "path": str(out), "config": cfg}, indent=2))
