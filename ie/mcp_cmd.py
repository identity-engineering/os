"""CLI entry for local MCP Surface (Identity-scoped)."""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path
from typing import Optional

import typer

from ie.paths import require_ie_root
from runtime.mcp_handler import main as mcp_main
from runtime.mcp_session import bind_local_session


def _resolve_ie_command() -> list[str]:
    """Best-effort command vector to launch the local MCP server."""
    which = shutil.which("ie")
    if which:
        return [which, "surface", "mcp"]
    return [sys.executable, "-m", "runtime.mcp_handler"]


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
            help="Optional space_id stamp on actor envelope",
        ),
        identity_id: Optional[str] = typer.Option(
            None,
            "--identity-id",
            help="Bind this local identity_id (default: install active)",
        ),
        handle: Optional[str] = typer.Option(
            None,
            "--handle",
            help="Bind this local_handle (default: install active)",
        ),
    ) -> None:
        """Run local stdio MCP Surface bound to one Identity in the install."""
        root = path if path is not None else require_ie_root()
        bind_local_session(
            root, space_id=space_id, identity_id=identity_id, handle=handle
        )
        argv = ["--install", str(root)]
        if space_id:
            argv.extend(["--space-id", space_id])
        if identity_id:
            argv.extend(["--identity-id", identity_id])
        if handle:
            argv.extend(["--handle", handle])
        raise SystemExit(mcp_main(argv))

    @surface_app.command("mcp-config")
    def surface_mcp_config(
        path: Optional[Path] = typer.Option(
            None,
            "--path",
            "--install",
            help="IE install root (default: active root / IE_ROOT)",
        ),
        format: str = typer.Option(
            "claude",
            "--format",
            help="claude | cursor | generic",
        ),
        name: str = typer.Option(
            "ie-os",
            "--name",
            help="Server key / display name in the client config",
        ),
        identity_id: Optional[str] = typer.Option(
            None,
            "--identity-id",
            help="Pin MCP session to this local identity_id",
        ),
        handle: Optional[str] = typer.Option(
            None,
            "--handle",
            help="Pin MCP session to this local_handle",
        ),
    ) -> None:
        """Print a ready-to-paste MCP client config for the local install."""
        root = (path if path is not None else require_ie_root()).expanduser().resolve()
        session = bind_local_session(
            root, identity_id=identity_id, handle=handle
        )

        cmd = _resolve_ie_command()
        if cmd[-2:] == ["surface", "mcp"]:
            args = ["surface", "mcp", "--path", str(root)]
            command = cmd[0]
        else:
            command = cmd[0]
            args = cmd[1:] + ["--install", str(root)]

        if identity_id:
            args.extend(["--identity-id", identity_id])
        elif handle:
            args.extend(["--handle", handle])

        fmt = format.strip().lower()
        if fmt not in {"claude", "cursor", "generic"}:
            raise SystemExit("--format must be one of: claude | cursor | generic")

        notes = (
            f"Session binds to identity_id={session.identity_id} "
            f"handle={session.local_handle}."
        )

        if fmt in {"claude", "cursor"}:
            payload = {
                "mcpServers": {
                    name: {
                        "command": command,
                        "args": args,
                    }
                }
            }
        else:
            payload = {
                "name": name,
                "command": command,
                "args": args,
                "transport": "stdio",
                "notes": notes,
            }

        typer.echo(json.dumps(payload, indent=2, ensure_ascii=False))
