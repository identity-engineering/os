"""ie messaging – Identity-Native Messaging CLI."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Optional

import typer

from ie.paths import require_ie_root
from runtime.database import database_path
from runtime.messaging import (
    MessagingError,
    get_card,
    get_message,
    list_cards,
    list_inbox,
    register_card,
    send_envelope,
)

messaging_app = typer.Typer(help="Identity-Native Messaging")
card_app = typer.Typer(help="Identity Card operations")
a2a_app = typer.Typer(help="A2A Agent Card import/export")
messaging_app.add_typer(card_app, name="card")
messaging_app.add_typer(a2a_app, name="a2a")


def _root(path: Optional[Path]) -> Path:
    root = path.resolve() if path else require_ie_root()
    if not database_path(root).is_file():
        raise SystemExit(f"No .ie/ie.sqlite3 under {root}")
    return root


def _load_json(file: Optional[Path]) -> dict:
    if file:
        raw = file.read_text(encoding="utf-8")
    else:
        raw = sys.stdin.read()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise SystemExit("Expected a JSON object")
    return data


@card_app.command("register")
def card_register(
    file: Optional[Path] = typer.Option(
        None, "--file", "-f", help="Card JSON file (default: stdin)"
    ),
    path: Optional[Path] = typer.Option(None, "--path", help="IE install root"),
) -> None:
    """Register or update an Identity Card in the local messaging store."""
    root = _root(path)
    card = _load_json(file)
    try:
        stored = register_card(root, card)
    except MessagingError as exc:
        raise SystemExit(str(exc)) from exc
    typer.echo(json.dumps(stored, indent=2, ensure_ascii=False))


@card_app.command("list")
def card_list(
    path: Optional[Path] = typer.Option(None, "--path"),
    json_out: bool = typer.Option(False, "--json"),
) -> None:
    """List registered Identity Cards."""
    root = _root(path)
    cards = list_cards(root)
    if json_out:
        typer.echo(json.dumps({"cards": cards}, indent=2, ensure_ascii=False))
        return
    if not cards:
        typer.echo("(no cards)")
        return
    for c in cards:
        typer.echo(
            f"{c.get('identityId', '?')}  {c.get('type', '?')}  {c.get('name', '?')}"
        )


@card_app.command("show")
def card_show(
    identity_id: str = typer.Argument(..., help="identityId"),
    path: Optional[Path] = typer.Option(None, "--path"),
) -> None:
    """Show one Identity Card."""
    root = _root(path)
    card = get_card(root, identity_id)
    if card is None:
        raise SystemExit(f"No card for {identity_id!r}")
    typer.echo(json.dumps(card, indent=2, ensure_ascii=False))


@a2a_app.command("export")
def a2a_export(
    identity_id: str = typer.Argument(..., help="identityId"),
    path: Optional[Path] = typer.Option(None, "--path"),
) -> None:
    """Export an Identity Card as an A2A Agent Card (JSON)."""
    root = _root(path)
    card = get_card(root, identity_id)
    if card is None:
        raise SystemExit(f"No card for {identity_id!r}")
    from runtime.a2a_adapter import identity_card_to_agent_card

    try:
        agent = identity_card_to_agent_card(card)
    except MessagingError as exc:
        raise SystemExit(str(exc)) from exc
    typer.echo(json.dumps(agent, indent=2, ensure_ascii=False))


@a2a_app.command("import-card")
def a2a_import_card(
    file: Optional[Path] = typer.Option(
        None, "--file", "-f", help="A2A Agent Card JSON (default: stdin)"
    ),
    path: Optional[Path] = typer.Option(None, "--path"),
) -> None:
    """Import an A2A Agent Card into the local Identity Card store."""
    root = _root(path)
    agent = _load_json(file)
    from runtime.a2a_adapter import agent_card_to_identity_card

    try:
        card = agent_card_to_identity_card(agent)
        stored = register_card(root, card)
    except MessagingError as exc:
        raise SystemExit(str(exc)) from exc
    typer.echo(json.dumps(stored, indent=2, ensure_ascii=False))


@messaging_app.command("send")
def messaging_send(
    file: Optional[Path] = typer.Option(
        None, "--file", "-f", help="Envelope JSON file (default: stdin)"
    ),
    path: Optional[Path] = typer.Option(None, "--path"),
) -> None:
    """Send an Envelope (local delivery + receipt)."""
    root = _root(path)
    envelope = _load_json(file)
    try:
        result = send_envelope(root, envelope)
    except MessagingError as exc:
        raise SystemExit(str(exc)) from exc
    typer.echo(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))
    if result.status == "rejected":
        raise typer.Exit(code=1)


@messaging_app.command("inbox")
def messaging_inbox(
    path: Optional[Path] = typer.Option(None, "--path"),
    json_out: bool = typer.Option(False, "--json"),
) -> None:
    """List messages in the local inbox."""
    root = _root(path)
    messages = list_inbox(root)
    if json_out:
        typer.echo(json.dumps({"messages": messages}, indent=2, ensure_ascii=False))
        return
    if not messages:
        typer.echo("(empty inbox)")
        return
    for m in messages:
        sig = (m.get("signal") or {}).get("type", "?")
        typer.echo(
            f"{m.get('messageId', '?')}  from={m.get('from', '?')}  "
            f"signal={sig}  at={m.get('createdAt', '?')}"
        )


@messaging_app.command("show")
def messaging_show(
    message_id: str = typer.Argument(..., help="messageId"),
    path: Optional[Path] = typer.Option(None, "--path"),
) -> None:
    """Show one message from inbox or outbox."""
    root = _root(path)
    msg = get_message(root, message_id)
    if msg is None:
        raise SystemExit(f"No message {message_id!r}")
    typer.echo(json.dumps(msg, indent=2, ensure_ascii=False))


@messaging_app.command("serve")
def messaging_serve(
    path: Optional[Path] = typer.Option(None, "--path", help="IE install root"),
    host: str = typer.Option("127.0.0.1", "--host"),
    port: int = typer.Option(7420, "--port"),
    identity: Optional[str] = typer.Option(
        None, "--identity", help="Primary identityId for /.well-known/agent-card.json"
    ),
) -> None:
    """Start the local messaging HTTP surface (stdlib)."""
    root = _root(path)
    from runtime.messaging_http import serve

    serve(root, host=host, port=port, primary_identity_id=identity)


def register(app: typer.Typer) -> None:
    app.add_typer(messaging_app, name="messaging")
