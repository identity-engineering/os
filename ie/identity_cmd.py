"""CLI: identity list/create/use + space list/show (OS #77)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import typer

from ie.paths import require_ie_root
from runtime.database import Database, database_path


def register(app: typer.Typer) -> None:
    identity_app = typer.Typer(help="Local Identities in this install")
    space_app = typer.Typer(help="Local Space (mini-Space host)")
    app.add_typer(identity_app, name="identity")
    app.add_typer(space_app, name="space")

    @identity_app.command("list")
    def identity_list(
        path: Optional[Path] = typer.Option(None, "--path"),
        json_out: bool = typer.Option(False, "--json"),
    ) -> None:
        root = path.resolve() if path else require_ie_root()
        from runtime.context import ContextError, get_active_identity, list_identities

        try:
            rows = list_identities(root)
            active = get_active_identity(root)
        except ContextError as exc:
            raise SystemExit(str(exc)) from exc
        if json_out:
            typer.echo(
                json.dumps(
                    {"active_identity_id": active["identity_id"], "identities": rows},
                    indent=2,
                    ensure_ascii=False,
                )
            )
            return
        if not rows:
            typer.echo("(no identities)")
            return
        for r in rows:
            mark = "*" if r["identity_id"] == active["identity_id"] else " "
            typer.echo(
                f"{mark} {r['local_handle']:16}  {r['identity_id'][:8]}…  "
                f"substrate={r['substrate']}"
            )

    @identity_app.command("use")
    def identity_use(
        handle: str = typer.Argument(..., help="local_handle to activate"),
        path: Optional[Path] = typer.Option(None, "--path"),
    ) -> None:
        root = path.resolve() if path else require_ie_root()
        from runtime.context import ContextError, set_active_identity

        try:
            row = set_active_identity(root, handle=handle)
        except ContextError as exc:
            raise SystemExit(str(exc)) from exc
        typer.echo(json.dumps({"active": row["local_handle"], "identity_id": row["identity_id"]}, indent=2))

    @identity_app.command("create")
    def identity_create(
        name: str = typer.Option(..., "--name", "-n", help="preferred_name"),
        handle: Optional[str] = typer.Option(None, "--handle", "-h"),
        substrate: str = typer.Option("human", "--substrate"),
        path: Optional[Path] = typer.Option(None, "--path"),
        activate: bool = typer.Option(False, "--activate", help="Switch active Identity to the new one"),
    ) -> None:
        """Create an additional Identity in this install (same local Space)."""
        root = path.resolve() if path else require_ie_root()
        if not database_path(root).is_file():
            raise SystemExit(f"No .ie/ie.sqlite3 under {root}")

        import re

        from runtime.context import set_active_identity
        from runtime.space_bootstrap import create_additional_identity

        h = handle or re.sub(r"[^a-z0-9._-]", "", name.strip().lower().replace(" ", "-")) or "identity"
        with Database(database_path(root)) as database:
            with database.transaction() as conn:
                install = conn.execute("SELECT install_id FROM install LIMIT 1").fetchone()
                if install is None:
                    raise SystemExit("no install row")
                try:
                    result = create_additional_identity(
                        conn,
                        install_id=install["install_id"],
                        handle=h,
                        preferred_name=name,
                        substrate=substrate,
                    )
                except Exception as exc:
                    raise SystemExit(str(exc)) from exc
        if activate:
            set_active_identity(root, identity_id=result["identity_id"])
        typer.echo(json.dumps(result, indent=2, ensure_ascii=False))

    @space_app.command("list")
    def space_list(
        path: Optional[Path] = typer.Option(None, "--path"),
        json_out: bool = typer.Option(False, "--json"),
    ) -> None:
        root = path.resolve() if path else require_ie_root()
        from runtime.context import ContextError, list_spaces

        try:
            rows = list_spaces(root)
        except ContextError as exc:
            raise SystemExit(str(exc)) from exc
        if json_out:
            typer.echo(json.dumps({"spaces": rows}, indent=2, ensure_ascii=False))
            return
        if not rows:
            typer.echo("(no spaces — run migration / ie init)")
            return
        for r in rows:
            typer.echo(
                f"{r['space_id'][:8]}…  kind={r['kind']}  hosting={r['hosting']}"
            )

    @space_app.command("show")
    def space_show(
        path: Optional[Path] = typer.Option(None, "--path"),
    ) -> None:
        root = path.resolve() if path else require_ie_root()
        from runtime.context import ContextError, get_active_identity, get_primary_space_for_identity

        try:
            active = get_active_identity(root)
            space = get_primary_space_for_identity(root, active["identity_id"])
        except ContextError as exc:
            raise SystemExit(str(exc)) from exc
        payload = {
            "active_identity": {
                "identity_id": active["identity_id"],
                "local_handle": active["local_handle"],
            },
            "primary_space": space,
        }
        typer.echo(json.dumps(payload, indent=2, ensure_ascii=False))
