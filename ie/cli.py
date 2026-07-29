"""ie — Identity Engineering OS CLI (v0 skeleton)."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Optional

import typer

from ie import __version__
from ie.init_cmd import init_install
from ie.paths import find_ie_root, require_ie_root
from ie.registry_cmd import get_peer, list_peers
from ie.status_cmd import collect_status, format_status

app = typer.Typer(
    name="ie",
    help="Identity Engineering OS — local-first runtime CLI",
    no_args_is_help=True,
    add_completion=False,
)
registry_app = typer.Typer(help="Local Registry operations")
signal_app = typer.Typer(help="Interaction Signal operations")
app.add_typer(registry_app, name="registry")
app.add_typer(signal_app, name="signal")


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


@app.command("init")
def init(
    path: Path = typer.Argument(
        Path("."),
        help="Directory for the new IE install (created if missing)",
    ),
    handle: str = typer.Option(..., "--handle", "-h", help="local_handle for this Identity"),
    name: Optional[str] = typer.Option(None, "--name", "-n", help="preferred_name"),
    force: bool = typer.Option(False, "--force", help="Overwrite existing template files"),
) -> None:
    """Create a personal IE install from bundled templates."""
    root = init_install(path, handle=handle, preferred_name=name, force=force)
    typer.echo(f"IE install created at {root}")
    typer.echo(f"  handle: {handle}")
    if name:
        typer.echo(f"  name:   {name}")
    typer.echo("Next: cd into the directory and run `ie status`")


@app.command("status")
def status(
    path: Optional[Path] = typer.Option(
        None, "--path", help="IE install root (default: walk from cwd / IE_ROOT)"
    ),
) -> None:
    """Show handle, registry peers, foreign-estimate senders."""
    root = path.resolve() if path else require_ie_root()
    if path and not (root / "HEADER.yaml").is_file():
        raise SystemExit(f"No HEADER.yaml under {root}")
    typer.echo(format_status(collect_status(root)))


@registry_app.command("list")
def registry_list(
    path: Optional[Path] = typer.Option(None, "--path"),
) -> None:
    """List local Registry peer handles."""
    root = path.resolve() if path else require_ie_root()
    peers = list_peers(root)
    if not peers:
        typer.echo("(empty registry)")
        return
    for p in peers:
        typer.echo(p)


@registry_app.command("get")
def registry_get(
    handle: str = typer.Argument(..., help="Peer local_handle"),
    path: Optional[Path] = typer.Option(None, "--path"),
) -> None:
    """Print one Registry entry as YAML/JSON."""
    root = path.resolve() if path else require_ie_root()
    data = get_peer(root, handle)
    if data is None:
        raise SystemExit(f"No registry entry for {handle!r}")
    try:
        import yaml  # type: ignore

        typer.echo(yaml.safe_dump(data, sort_keys=False, allow_unicode=True))
    except Exception:
        typer.echo(json.dumps(data, indent=2, ensure_ascii=False))


@signal_app.command("apply")
def signal_apply(
    payload: Optional[Path] = typer.Option(
        None, "--payload", "-p", help="JSON file (default: stdin)"
    ),
    path: Optional[Path] = typer.Option(None, "--path", help="IE install root"),
    open_consent: bool = typer.Option(
        False, "--open-consent", help="Apply consent fields without grants (dogfood)"
    ),
    to_handle: Optional[str] = typer.Option(
        None, "--to", help="Override expected to_handle (default: from HEADER)"
    ),
) -> None:
    """Apply an Interaction Signal into this install's foreign-estimate zone."""
    root = path.resolve() if path else require_ie_root()
    registry = root / "registry"
    if not registry.is_dir():
        raise SystemExit(f"No registry/ under {root}")

    if payload:
        raw = payload.read_text(encoding="utf-8")
    else:
        raw = sys.stdin.read()
    data = json.loads(raw)

    # Default to_handle from HEADER
    expected = to_handle
    if expected is None:
        st = collect_status(root)
        expected = st.get("handle")

    from runtime.apply import apply_from_dict
    from runtime.models import ApplyStatus
    from runtime.policy import LocalPolicy

    policy = LocalPolicy(open_consent=open_consent)
    receipt = apply_from_dict(
        data,
        registry_root=registry,
        policy=policy,
        expected_to_handle=expected,
    )
    typer.echo(json.dumps(receipt.to_dict(), indent=2, ensure_ascii=False))
    if receipt.status == ApplyStatus.REJECTED:
        raise typer.Exit(code=1)


@app.command("catalogue")
def catalogue(
    path: Optional[Path] = typer.Option(None, "--path"),
) -> None:
    """Show dimension catalogue path / stub summary."""
    root = path.resolve() if path else require_ie_root()
    cat = root / "dimension-catalogue.yaml"
    if not cat.is_file():
        typer.echo("No dimension-catalogue.yaml in this install.")
        raise typer.Exit(code=1)
    typer.echo(f"catalogue: {cat}")
    typer.echo("(full catalogue inspection comes in a later slice)")


@app.command("reindex")
def reindex() -> None:
    """Stub: rebuild derived indexes (volume / self-Mass caches)."""
    typer.echo("ie reindex: not implemented yet (no derived caches in v0).")
    raise typer.Exit(code=0)


if __name__ == "__main__":
    app()
