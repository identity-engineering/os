"""ie — Identity Engineering OS CLI (v0 skeleton)."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Optional

import typer

from ie import __version__
from ie.init_cmd import init_install
from ie.paths import require_ie_root
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


def _prompt_account(account: Optional[str]) -> str:
    if account:
        key = account.strip().lower().replace("-", "_")
        aliases = {
            "no": ACCOUNT_NO,
            "none": ACCOUNT_NO,
            "no_account": ACCOUNT_NO,
            "local": ACCOUNT_NO,
            "login": ACCOUNT_LOGIN,
            "signin": ACCOUNT_LOGIN,
            "sign_in": ACCOUNT_LOGIN,
            "create": ACCOUNT_CREATE,
            "register": ACCOUNT_CREATE,
            "signup": ACCOUNT_CREATE,
            "sign_up": ACCOUNT_CREATE,
        }
        if key not in aliases:
            raise SystemExit(
                "--account must be one of: no_account | login | create"
            )
        return aliases[key]

    typer.echo("Account")
    typer.echo("  1) No account     — local-only Free (default)")
    typer.echo("  2) Login          — existing IE account (browser)")
    typer.echo("  3) Create account — new IE account (browser)")
    choice = typer.prompt("Choice", default="1")
    mapping = {
        "1": ACCOUNT_NO,
        "2": ACCOUNT_LOGIN,
        "3": ACCOUNT_CREATE,
        "no": ACCOUNT_NO,
        "login": ACCOUNT_LOGIN,
        "create": ACCOUNT_CREATE,
    }
    key = choice.strip().lower()
    if key not in mapping:
        raise SystemExit("Invalid account choice")
    return mapping[key]


def _resolve_account_flow(mode: str) -> dict:
    """Browser login/create is stubbed in v0; local install always proceeds."""
    if mode == ACCOUNT_NO:
        return {
            "account_mode": ACCOUNT_NO,
            "account_id": None,
            "tier": "free",
            "public_registry_access": False,
        }

    typer.echo(
        "\nBrowser account flow is not wired yet (v0 stub).\n"
        "When live: CLI opens a browser → login/create → redirect back with account_id.\n"
        "Proceeding with a local Free install; you can link an account later.\n"
    )
    # Reserved for: webbrowser.open(auth_url); poll/callback with account_id
    return {
        "account_mode": mode,
        "account_id": None,  # set when OAuth/callback exists
        "tier": "free",  # account may still be free; pro comes from account entitlements
        "public_registry_access": False,  # True once account_id is real
        "account_link_pending": True,
    }


def _prompt_init(
    path: Optional[Path],
    handle: Optional[str],
    name: Optional[str],
    account: Optional[str],
) -> tuple[Path, str, str, dict]:
    typer.echo("Identity Engineering — setup")
    typer.echo("(Enter keeps the default in brackets.)\n")

    if path is None:
        raw = typer.prompt("Install path", default=str(DEFAULT_INIT_PATH))
        path = Path(raw).expanduser()
    else:
        path = path.expanduser()

    account_mode = _prompt_account(account)
    account_info = _resolve_account_flow(account_mode)

    if not name:
        name = typer.prompt("Preferred name").strip()
        if not name:
            raise SystemExit("preferred name is required")

    if not handle:
        default_handle = _handle_from_name(name)
        handle = typer.prompt("local_handle", default=default_handle).strip()
        if not handle:
            raise SystemExit("local_handle is required")

    return path, handle, name, account_info


@app.command("init")
def init(
    path: Optional[Path] = typer.Option(
        None,
        "--path",
        help=f"Install directory (default in dialog: {DEFAULT_INIT_PATH})",
    ),
    account: Optional[str] = typer.Option(
        None,
        "--account",
        help="no_account | login | create (prompted if omitted)",
    ),
    name: Optional[str] = typer.Option(
        None, "--name", "-n", help="preferred_name (prompted if omitted)"
    ),
    handle: Optional[str] = typer.Option(
        None,
        "--handle",
        "-h",
        help="local_handle (default: lowercased preferred name)",
    ),
    force: bool = typer.Option(False, "--force", help="Overwrite existing template files"),
    yes: bool = typer.Option(
        False,
        "--yes",
        "-y",
        help="Skip confirmation when enough flags are provided",
    ),
) -> None:
    """Create a personal IE install (interactive by default).

    Prompt order: path → account → preferred name → local_handle.

    Examples:
      ie init
      ie init --name Jonas
      ie init --path ~/ie --account no_account --name Jonas --handle jonas -y
    """
    interactive = sys.stdin.isatty()

    if not interactive and not (name and (handle or name)):
        raise SystemExit(
            "Non-interactive init requires --name "
            "(and optionally --handle, --path, --account)."
        )

    if interactive and (
        path is None or name is None or handle is None or account is None
    ):
        path, handle, name, account_info = _prompt_init(path, handle, name, account)
    else:
        path = (path or DEFAULT_INIT_PATH).expanduser()
        if not name:
            raise SystemExit("--name is required in non-interactive mode")
        handle = handle or _handle_from_name(name)
        account_mode = _prompt_account(account or ACCOUNT_NO)
        account_info = _resolve_account_flow(account_mode)

    assert path is not None and handle is not None and name is not None

    if not yes and interactive:
        typer.echo("\nAbout to create:")
        typer.echo(f"  path:    {path}")
        typer.echo(f"  name:    {name}")
        typer.echo(f"  handle:  {handle}")
        typer.echo(f"  account: {account_info['account_mode']}")
        typer.echo(f"  tier:    {account_info['tier']}")
        if not typer.confirm("Continue?", default=True):
            raise SystemExit("aborted")

    root = init_install(
        path,
        handle=handle,
        preferred_name=name,
        force=force,
        account_info=account_info,
    )
    typer.echo(f"\nIE install created at {root}")
    typer.echo(f"  name:    {name}")
    typer.echo(f"  handle:  {handle}")
    typer.echo(f"  account: {account_info['account_mode']}")
    typer.echo(f"  tier:    {account_info['tier']}")
    typer.echo("\nNext:")
    typer.echo(f"  export IE_ROOT={root}   # optional")
    typer.echo("  ie status")


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
