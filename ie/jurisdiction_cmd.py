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
    app.add_typer(jurisdiction_app, name="jurisdiction")

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
        root = path.resolve() if path else require_ie_root()
        if not database_path(root).is_file():
            raise SystemExit(f"No .ie/ie.sqlite3 under {root}")
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
        root = path.resolve() if path else require_ie_root()
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
        root = path.resolve() if path else require_ie_root()
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

    from ie.grant_cmd import register as register_grant
    from ie.identity_cmd import register as register_identity

    register_grant(app)
    register_identity(app)
