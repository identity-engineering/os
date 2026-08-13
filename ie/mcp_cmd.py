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
    # Fall back to the running interpreter + module path.
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
    ) -> None:
        """Run local stdio MCP Surface bound to the install Identity."""
        root = path if path is not None else require_ie_root()
        # Validate binding early so failures surface before the stdio loop.
        bind_local_session(root, space_id=space_id)
        argv = ["--install", str(root)]
        if space_id:
            argv.extend(["--space-id", space_id])
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
    ) -> None:
        """Print a ready-to-paste MCP client config for the local install."""
        root = (path if path is not None else require_ie_root()).expanduser().resolve()
        # Validate that the install can bind (fails fast with a clear error).
        bind_local_session(root)

        cmd = _resolve_ie_command()
        # Prefer explicit path so clients do not depend on active-root discovery.
        if cmd[-2:] == ["surface", "mcp"]:
            args = ["surface", "mcp", "--path", str(root)]
            command = cmd[0]
        else:
            # python -m runtime.mcp_handler --install <root>
            command = cmd[0]
            args = cmd[1:] + ["--install", str(root)]

        fmt = format.strip().lower()
        if fmt not in {"claude", "cursor", "generic"}:
            raise SystemExit("--format must be one of: claude | cursor | generic")

        if fmt == "claude":
            # Claude Desktop: ~/Library/Application Support/Claude/claude_desktop_config.json
            payload = {
                "mcpServers": {
                    name: {
                        "command": command,
                        "args": args,
                    }
                }
            }
        elif fmt == "cursor":
            # Cursor mcp.json style
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
                "notes": (
                    "Wire this stdio process into any MCP-capable client. "
                    "Session binds to the install's active Identity."
                ),
            }

        typer.echo(json.dumps(payload, indent=2, ensure_ascii=False))
