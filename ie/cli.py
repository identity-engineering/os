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


def _database_root(path: Optional[Path]) -> Path:
    root = path.resolve() if path else require_ie_root()
    if not database_path(root).is_file():
        raise SystemExit(f"No .ie/ie.sqlite3 under {root}")
    return root


def _echo_data(data: dict, *, json_out: bool) -> None:
    if json_out:
        typer.echo(json.dumps(data, indent=2, ensure_ascii=False))
        return
    for key, value in data.items():
        if isinstance(value, (dict, list)):
            value = json.dumps(value, ensure_ascii=False, sort_keys=True)
        typer.echo(f"{key}: {value}")


@db_app.command("info")
def db_info(
    path: Optional[Path] = typer.Option(None, "--path", help="IE install root"),
    json_out: bool = typer.Option(
        True, "--json/--no-json", help="Output as JSON (default)"
    ),
) -> None:
    """Show SQLite path, schema, migration, and connection metadata."""
    from runtime.database import database_info

    _echo_data(database_info(_database_root(path)), json_out=json_out)


@db_app.command("integrity-check")
def db_integrity_check(
    path: Optional[Path] = typer.Option(None, "--path", help="IE install root"),
    json_out: bool = typer.Option(
        True, "--json/--no-json", help="Output as JSON (default)"
    ),
) -> None:
    """Run SQLite integrity and foreign-key checks."""
    from runtime.database import database_integrity_check

    result = database_integrity_check(_database_root(path))
    _echo_data(result, json_out=json_out)
    if not result["ok"]:
        raise typer.Exit(code=1)


@db_app.command("backup")
def db_backup(
    destination: Path = typer.Option(..., "--to", "--destination", help="Backup file path"),
    force: bool = typer.Option(False, "--force", help="Replace an existing backup"),
    path: Optional[Path] = typer.Option(None, "--path", help="IE install root"),
) -> None:
    """Create a consistent online backup of the local SQLite database."""
    from runtime.database import DatabaseError, backup_database

    try:
        result = backup_database(
            _database_root(path), destination, overwrite=force
        )
    except DatabaseError as exc:
        raise SystemExit(str(exc)) from exc
    typer.echo(json.dumps(result, indent=2, ensure_ascii=False))
