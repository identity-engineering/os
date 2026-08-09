"""CLI entry for local MCP Surface (Identity-scoped)."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer

from ie.paths import require_ie_root
from runtime.mcp_handler import main as mcp_main
from runtime.mcp_session import bind_local_session


def register(app: typer.Typer) -> None:
    surface_app = typer.Typer(help="Identity Surface bindings (MCP, …)")
    app.add_typer(surface_app, name="surface")

    @surface_app.command("mcp")
    def surface_mcp(
        path: Optional[Path] = typer.Option(
            None,
            "--path",
            "--install",
            help="IE install root (default: active root / IE_ROOT)",
        ),
        space_id: Optional[str] = typer.Option(
            None,
            "--space-id",
            help="Optional space_id stamp on actor envelope (membrane not enforced in V1)",
        ),
    ) -> None:
        """Run local stdio MCP Surface bound to the install Identity."""
        root = path if path is not None else require_ie_root()
        # Validate binding early so failures surface before the stdio loop.
        bind_local_session(root, space_id=space_id)
        argv = ["--install", str(root)]
        if space_id:
            argv.extend(["--space-id", space_id])
        raise SystemExit(mcp_main(argv))
