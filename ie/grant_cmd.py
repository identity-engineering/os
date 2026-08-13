"""CLI commands for identity grants (list / revoke / transfer)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import typer

from ie.paths import require_ie_root
from runtime.database import database_path


def register(app: typer.Typer) -> None:
    """Register grant subcommands on the root CLI app."""
    grant_app = typer.Typer(help="Identity jurisdiction grants (list / revoke / transfer)")
    app.add_typer(grant_app, name="grant")

    @grant_app.command("list")
    def grant_list(
        path: Optional[Path] = typer.Option(None, "--path", help="IE install root"),
        all_grants: bool = typer.Option(
            False, "--all", help="Include revoked grants"
        ),
        json_out: bool = typer.Option(False, "--json", help="Print as JSON"),
    ) -> None:
        """List grants on the local Identity (creation package + later changes)."""
        root = path.resolve() if path else require_ie_root()
        if not database_path(root).is_file():
            raise SystemExit(f"No .ie/ie.sqlite3 under {root}")

        from runtime.grants import GrantError, list_grants

        try:
            rows = list_grants(root, active_only=not all_grants)
        except GrantError as exc:
            raise SystemExit(str(exc)) from exc

        if json_out:
            typer.echo(json.dumps({"grants": rows}, indent=2, ensure_ascii=False))
            return
        if not rows:
            typer.echo("(no grants)")
            return
        for r in rows:
            flags = []
            if r["residual"]:
                flags.append("residual")
            if not r["transferable"]:
                flags.append("non-transferable")
            if r["revoked_at"]:
                flags.append(f"revoked@{r['revoked_at']}")
            flag_s = f"  [{', '.join(flags)}]" if flags else ""
            typer.echo(
                f"{r['scope']:22}  actor={r['actor_identity_id'][:8]}…  "
                f"id={r['grant_id'][:8]}…{flag_s}"
            )

    @grant_app.command("revoke")
    def grant_revoke(
        grant_id: Optional[str] = typer.Option(
            None, "--grant-id", help="Specific grant_id"
        ),
        scope: Optional[str] = typer.Option(
            None, "--scope", help="Scope of the active grant to revoke"
        ),
        reason: Optional[str] = typer.Option(None, "--reason"),
        path: Optional[Path] = typer.Option(None, "--path", help="IE install root"),
    ) -> None:
        """Revoke an ordinary grant (residual emergency cannot be revoked here)."""
        root = path.resolve() if path else require_ie_root()
        if not database_path(root).is_file():
            raise SystemExit(f"No .ie/ie.sqlite3 under {root}")

        from runtime.grants import GrantError, revoke_grant

        try:
            result = revoke_grant(
                root, grant_id=grant_id, scope=scope, reason=reason or ""
            )
        except GrantError as exc:
            raise SystemExit(str(exc)) from exc
        typer.echo(json.dumps(result, indent=2, ensure_ascii=False))

    @grant_app.command("transfer")
    def grant_transfer(
        to_actor: str = typer.Option(
            ...,
            "--to-actor",
            help="Target actor identity_id (must exist locally)",
        ),
        grant_id: Optional[str] = typer.Option(
            None, "--grant-id", help="Specific grant_id"
        ),
        scope: Optional[str] = typer.Option(
            None, "--scope", help="Scope of the active grant to transfer"
        ),
        reason: Optional[str] = typer.Option(None, "--reason"),
        path: Optional[Path] = typer.Option(None, "--path", help="IE install root"),
    ) -> None:
        """Transfer a transferable grant to another local Identity actor."""
        root = path.resolve() if path else require_ie_root()
        if not database_path(root).is_file():
            raise SystemExit(f"No .ie/ie.sqlite3 under {root}")

        from runtime.grants import GrantError, transfer_grant

        try:
            result = transfer_grant(
                root,
                to_actor_identity_id=to_actor,
                grant_id=grant_id,
                scope=scope,
                reason=reason or "",
            )
        except GrantError as exc:
            raise SystemExit(str(exc)) from exc
        typer.echo(json.dumps(result, indent=2, ensure_ascii=False))
