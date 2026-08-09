"""CLI commands for Geometry Receipt feed (OS #8)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import typer

from ie.paths import require_ie_root
from runtime.database import database_path


def register(app: typer.Typer) -> None:
    """Register geometry subcommands on the root CLI app."""
    geometry_app = typer.Typer(help="Geometry Receipt feed (Tension / Registry write-back)")
    app.add_typer(geometry_app, name="geometry")

    @geometry_app.command("feed")
    def geometry_feed(
        receipt_id: Optional[str] = typer.Option(
            None,
            "--receipt-id",
            help="Feed one specific Geometry Receipt",
        ),
        all_pending: bool = typer.Option(
            False,
            "--all",
            help="Feed all unfed receipts (oldest first)",
        ),
        limit: int = typer.Option(50, "--limit", help="Max receipts when using --all"),
        force: bool = typer.Option(
            False,
            "--force",
            help="Re-feed even if already marked fed",
        ),
        path: Optional[Path] = typer.Option(None, "--path", help="IE install root"),
    ) -> None:
        """Feed Geometry Receipts into Registry effect_on_me (explicit path)."""
        root = path.resolve() if path else require_ie_root()
        if not database_path(root).is_file():
            raise SystemExit(f"No .ie/ie.sqlite3 under {root}")

        from runtime.geometry_feed import GeometryFeedError, feed_pending, feed_receipt

        try:
            if receipt_id:
                result = feed_receipt(root, receipt_id, force=force)
            elif all_pending:
                result = feed_pending(root, limit=limit, force=force)
            else:
                # Default: process a small pending batch
                result = feed_pending(root, limit=limit, force=force)
        except GeometryFeedError as exc:
            raise SystemExit(str(exc)) from exc

        typer.echo(json.dumps(result, indent=2, ensure_ascii=False))
