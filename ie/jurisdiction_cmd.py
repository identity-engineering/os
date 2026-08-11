"""CLI commands for Access & Jurisdiction probes (issue #40)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import typer

from ie.paths import require_ie_root
from runtime.database import database_path


def register(app: typer.Typer) -> None:
    """Register jurisdiction subcommands on the root CLI app."""
    jurisdiction_app = typer.Typer(help="Access & Jurisdiction probes (owner-gated)")
    grant_app = typer.Typer(help="Identity grant lifecycle operations")
    space_app = typer.Typer(help="Space boundary operations")
    boundary_app = typer.Typer(help="Public Space membrane boundary")
    app.add_typer(jurisdiction_app, name="jurisdiction")
    jurisdiction_app.add_typer(grant_app, name="grant")
    app.add_typer(space_app, name="space")
    space_app.add_typer(boundary_app, name="boundary")

    def database_root(path: Optional[Path]) -> Path:
        root = path.resolve() if path else require_ie_root()
        if not database_path(root).is_file():
            raise SystemExit(f"No .ie/ie.sqlite3 under {root}")
        return root

    @jurisdiction_app.command("probe")
    def jurisdiction_probe(
        object_spec: str = typer.Option(
            ...,
            "--object",
            "-o",
            help="Target: self | peer:<handle> | stem:<aspect> | space:<id>",
        ),
        access: str = typer.Option(
            ...,
            "--access",
            help="JSON object for Access fields (reach/use/observe/affected_by)",
        ),
        jurisdiction: str = typer.Option(
            ...,
            "--jurisdiction",
            help="JSON object for Jurisdiction fields (decide_goals/constrain/transfer/destroy/redefine_boundary)",
        ),
        confidence: float = typer.Option(0.5, "--confidence", "-c", help="Overall confidence 0–1"),
        notes: Optional[str] = typer.Option(None, "--notes", "-n"),
        path: Optional[Path] = typer.Option(None, "--path", help="IE install root"),
    ) -> None:
        """Commit an owner-gated Access + Jurisdiction profile for an object."""
        root = database_root(path)
        try:
            access_obj = json.loads(access)
            juris_obj = json.loads(jurisdiction)
        except json.JSONDecodeError as exc:
            raise SystemExit(f"Invalid JSON: {exc}") from exc

        from runtime.jurisdiction import JurisdictionError, write_profile

        try:
            result = write_profile(
                root,
                object_spec=object_spec,
                access=access_obj,
                jurisdiction=juris_obj,
                confidence=confidence,
                notes=notes or "",
                source="cli",
            )
        except JurisdictionError as exc:
            raise SystemExit(str(exc)) from exc
        typer.echo(json.dumps(result, indent=2, ensure_ascii=False))

    @jurisdiction_app.command("show")
    def jurisdiction_show(
        object_spec: str = typer.Option(
            ...,
            "--object",
            "-o",
            help="Target: self | peer:<handle> | stem:<aspect> | space:<id>",
        ),
        path: Optional[Path] = typer.Option(None, "--path", help="IE install root"),
    ) -> None:
        """Show the latest Access/Jurisdiction profile for an object."""
        root = database_root(path)
        from runtime.jurisdiction import JurisdictionError, get_profile

        try:
            result = get_profile(root, object_spec=object_spec)
        except JurisdictionError as exc:
            raise SystemExit(str(exc)) from exc
        if result is None:
            raise SystemExit(f"No profile for {object_spec!r}")
        typer.echo(json.dumps(result, indent=2, ensure_ascii=False))

    @jurisdiction_app.command("list")
    def jurisdiction_list(
        path: Optional[Path] = typer.Option(None, "--path", help="IE install root"),
        json_out: bool = typer.Option(False, "--json", help="Print as JSON"),
    ) -> None:
        """List latest Access/Jurisdiction profiles for this Identity."""
        root = database_root(path)
        from runtime.jurisdiction import JurisdictionError, list_profiles

        try:
            rows = list_profiles(root)
        except JurisdictionError as exc:
            raise SystemExit(str(exc)) from exc
        if json_out:
            typer.echo(json.dumps({"profiles": rows}, indent=2, ensure_ascii=False))
            return
        if not rows:
            typer.echo("(no profiles)")
            return
        for r in rows:
            typer.echo(
                f"{r['object_kind']}:{r['object_ref']}  rev={r['revision']}  "
                f"c={r['confidence']:.2f}  at={r['observed_at']}"
            )

    @grant_app.command("list")
    def grant_list(
        object_identity_id: Optional[str] = typer.Option(
            None, "--object", help="Object Identity ID (default: local Identity)"
        ),
        actor_identity_id: Optional[str] = typer.Option(
            None, "--actor", help="Filter by acting Identity ID"
        ),
        include_revoked: bool = typer.Option(
            False, "--include-revoked", help="Include revoked grant history"
        ),
        path: Optional[Path] = typer.Option(None, "--path", help="IE install root"),
        json_out: bool = typer.Option(False, "--json", help="Print as JSON"),
    ) -> None:
        """List grants for the local object Identity."""
        from runtime.jurisdiction import JurisdictionError, list_grants

        try:
            rows = list_grants(
                database_root(path),
                object_identity_id=object_identity_id,
                actor_identity_id=actor_identity_id,
                include_revoked=include_revoked,
            )
        except JurisdictionError as exc:
            raise SystemExit(str(exc)) from exc
        if json_out:
            typer.echo(json.dumps({"grants": rows}, indent=2, ensure_ascii=False))
            return
        if not rows:
            typer.echo("(no grants)")
            return
        for grant in rows:
            status = "revoked" if grant["revoked_at"] else "active"
            typer.echo(
                f"{grant['grant_id']}  {grant['scope']}  {status}  "
                f"actor={grant['actor_identity_id']}  object={grant['object_identity_id']}"
            )

    @grant_app.command("transfer")
    def grant_transfer(
        grant_id: str = typer.Option(..., "--grant", "-g", help="Grant ID"),
        to_identity_id: str = typer.Option(
            ..., "--to", help="Target Identity ID"
        ),
        note: Optional[str] = typer.Option(None, "--note"),
        path: Optional[Path] = typer.Option(None, "--path", help="IE install root"),
    ) -> None:
        """Transfer an active ordinary grant to another local Identity."""
        from runtime.jurisdiction import JurisdictionError, transfer_grant

        try:
            result = transfer_grant(
                database_root(path),
                grant_id=grant_id,
                to_identity_id=to_identity_id,
                note=note or "",
            )
        except JurisdictionError as exc:
            raise SystemExit(str(exc)) from exc
        typer.echo(json.dumps(result, indent=2, ensure_ascii=False))

    @grant_app.command("revoke")
    def grant_revoke(
        grant_id: str = typer.Option(..., "--grant", "-g", help="Grant ID"),
        note: Optional[str] = typer.Option(None, "--note"),
        path: Optional[Path] = typer.Option(None, "--path", help="IE install root"),
    ) -> None:
        """Revoke an ordinary grant without deleting its audit history."""
        from runtime.jurisdiction import JurisdictionError, revoke_grant

        try:
            result = revoke_grant(
                database_root(path),
                grant_id=grant_id,
                note=note or "",
            )
        except JurisdictionError as exc:
            raise SystemExit(str(exc)) from exc
        typer.echo(json.dumps(result, indent=2, ensure_ascii=False))

    @boundary_app.command("export")
    def boundary_export(
        destination: Path = typer.Option(
            ..., "--to", "--destination", help="Boundary JSON path"
        ),
        space_id: Optional[str] = typer.Option(None, "--space-id"),
        force: bool = typer.Option(False, "--force", help="Replace an existing file"),
        path: Optional[Path] = typer.Option(None, "--path", help="IE install root"),
    ) -> None:
        """Write a public Space boundary without private Identity geometry."""
        from runtime.database import DatabaseError
        from runtime.membrane import MembraneError, write_space_boundary

        try:
            result = write_space_boundary(
                database_root(path),
                destination,
                space_id=space_id,
                overwrite=force,
            )
        except (DatabaseError, MembraneError) as exc:
            raise SystemExit(str(exc)) from exc
        typer.echo(json.dumps(result, indent=2, ensure_ascii=False))

    @boundary_app.command("verify")
    def boundary_verify(
        source: Path = typer.Option(
            ..., "--from", "--file", help="Boundary JSON path"
        ),
        expected_space_id: Optional[str] = typer.Option(
            None, "--space-id", help="Require this Space ID"
        ),
    ) -> None:
        """Verify and classify an inbound public Space boundary."""
        from runtime.membrane import MembraneError, accept_inbound_boundary

        try:
            document = json.loads(source.expanduser().resolve().read_text(encoding="utf-8"))
            result = accept_inbound_boundary(
                document,
                expected_space_id=expected_space_id,
            )
        except (OSError, json.JSONDecodeError, MembraneError) as exc:
            raise SystemExit(str(exc)) from exc
        result["verified"] = True
        result["source"] = str(source.expanduser().resolve())
        typer.echo(json.dumps(result, indent=2, ensure_ascii=False))
