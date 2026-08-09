"""ie — Identity Engineering OS CLI (SQLite-first V1)."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Optional

import typer

from ie import __version__
from ie.init_cmd import init_install
from ie.mcp_cmd import register as register_mcp
from ie.jurisdiction_cmd import register as register_jurisdiction
from ie.paths import remember_ie_root, require_ie_root
from ie.registry_cmd import get_peer, list_peers
from ie.status_cmd import collect_status, format_status, status_json
from runtime.database import database_path
from runtime.sqlite_store import SQLiteStore

app = typer.Typer(
    name="ie",
    help="Identity Engineering OS — local-first runtime CLI",
    no_args_is_help=True,
    add_completion=False,
)
registry_app = typer.Typer(help="Local Registry operations")
signal_app = typer.Typer(help="Interaction Signal operations")
request_app = typer.Typer(help="Inbound estimate-request inbox (bidirectional sensor)")
policy_app = typer.Typer(help="Persistent consent and sender policy")
db_app = typer.Typer(help="SQLite database diagnostics, recovery, and backup")
app.add_typer(registry_app, name="registry")
app.add_typer(signal_app, name="signal")
app.add_typer(request_app, name="request")
app.add_typer(policy_app, name="policy")
app.add_typer(db_app, name="db")
register_mcp(app)
register_jurisdiction(app)

DEFAULT_INIT_PATH = Path.home() / "ie"

ACCOUNT_NO = "no_account"
ACCOUNT_LOGIN = "login"
ACCOUNT_CREATE = "create"


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"ie-os {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: Optional[bool] = typer.Option(
        None, "--version", "-V", callback=_version_callback, is_eager=True
    ),
) -> None:
    """Identity Engineering OS CLI."""


def _handle_from_name(preferred_name: str) -> str:
    """Default local_handle: lowercased name, spaces → hyphens, safe chars only."""
    s = preferred_name.strip().lower()
    s = re.sub(r"\s+", "-", s)
    s = re.sub(r"[^a-z0-9._-]", "", s)
    s = re.sub(r"-+", "-", s).strip("-")
    return s or "identity"
