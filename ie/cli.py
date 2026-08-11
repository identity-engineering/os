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
from ie.geometry_cmd import register as register_geometry
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
register_geometry(app)
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
    return {
        "account_mode": mode,
        "account_id": None,
        "tier": "free",
        "public_registry_access": False,
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
    force: bool = typer.Option(
        False, "--force", help="Allow replacing generated orientation documents"
    ),
    reset: bool = typer.Option(
        False,
        "--reset",
        help=(
            "Destructively replace existing DB/YAML state; V1 does not migrate "
            "legacy YAML automatically"
        ),
    ),
    yes: bool = typer.Option(
        False,
        "--yes",
        "-y",
        help="Skip confirmation when enough flags are provided",
    ),
) -> None:
    """Create a personal IE install (interactive by default)."""
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
        if reset:
            typer.echo("  reset:   DELETE existing local install state")
        if not typer.confirm("Continue?", default=True):
            raise SystemExit("aborted")
    if reset and not interactive and not yes:
        raise SystemExit("--reset is destructive; pass --yes to confirm in non-interactive mode")

    root = init_install(
        path,
        handle=handle,
        preferred_name=name,
        force=force,
        reset=reset,
        account_info=account_info,
        app_version=__version__,
    )
    remember_ie_root(root)
    typer.echo(f"\nIE install created at {root}")
    typer.echo(f"  name:    {name}")
    typer.echo(f"  handle:  {handle}")
    typer.echo(f"  account: {account_info['account_mode']}")
    typer.echo(f"  tier:    {account_info['tier']}")
    typer.echo("\nNext:")
    typer.echo("  ie status")


@app.command("status")
def status(
    path: Optional[Path] = typer.Option(
        None, "--path", help="IE install root (default: walk from cwd / IE_ROOT)"
    ),
    json_out: bool = typer.Option(False, "--json", help="Print machine-readable status"),
) -> None:
    """Show the SQLite-backed install and current local projections."""
    root = path.resolve() if path else require_ie_root()
    if path and not database_path(root).is_file():
        raise SystemExit(f"No .ie/ie.sqlite3 under {root}")
    info = collect_status(root)
    from runtime.geometry_feed import feed_capability

    info["geometry_feed"] = feed_capability(root)
    if json_out:
        typer.echo(status_json(info))
        return
    typer.echo(format_status(info))
    typer.echo(f"  geometry_feed: {info['geometry_feed']}")
    from runtime.mass import compute_mass_readout

    readout = compute_mass_readout(root)
    mass_s = (
        f"{readout.emergent_self_mass:.2f}"
        if readout.emergent_self_mass is not None
        else "unobserved"
    )
    typer.echo(
        f"  self-Mass:  {mass_s}  "
        f"(estimators={readout.estimator_count}, volume={readout.volume_count})"
    )


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


@db_app.command("export")
def db_export(
    destination: Path = typer.Option(..., "--to", "--destination", help="Export JSON path"),
    force: bool = typer.Option(False, "--force", help="Replace an existing export"),
    path: Optional[Path] = typer.Option(None, "--path", help="IE install root"),
) -> None:
    """Export the local identity space with a deterministic checksum."""
    from runtime.database import DatabaseError
    from runtime.export import write_identity_export

    try:
        result = write_identity_export(
            _database_root(path), destination, overwrite=force
        )
    except DatabaseError as exc:
        raise SystemExit(str(exc)) from exc
    typer.echo(json.dumps(result, indent=2, ensure_ascii=False))


@db_app.command("rebuild-projections")
def db_rebuild_projections(
    yes: bool = typer.Option(
        False,
        "--yes",
        help="Confirm rebuilding mutable projections from append-only history",
    ),
    path: Optional[Path] = typer.Option(None, "--path", help="IE install root"),
) -> None:
    """Rebuild current projections without rewriting audit history."""
    if not yes:
        raise SystemExit(
            "rebuild-projections rewrites current projections; pass --yes after a backup"
        )
    from runtime.database import DatabaseError
    from runtime.rebuild import rebuild_projections

    try:
        result = rebuild_projections(_database_root(path))
    except DatabaseError as exc:
        raise SystemExit(str(exc)) from exc
    typer.echo(json.dumps(result, indent=2, ensure_ascii=False))


def _policy_root(path: Optional[Path]) -> Path:
    return _database_root(path)


def _policy_result(result: dict) -> None:
    typer.echo(json.dumps(result, indent=2, ensure_ascii=False))


@policy_app.command("grant")
def policy_grant(
    sender_handle: str = typer.Option(..., "--from", "--sender", help="Sender handle"),
    field_name: str = typer.Option(..., "--field", help="Consent-gated signal field"),
    note: Optional[str] = typer.Option(None, "--note"),
    reason: Optional[str] = typer.Option(None, "--reason"),
    actor: Optional[str] = typer.Option(None, "--actor"),
    path: Optional[Path] = typer.Option(None, "--path", help="IE install root"),
) -> None:
    """Persist consent for one sender and signal field."""
    from runtime.policy_store import PolicyError, grant_consent

    try:
        result = grant_consent(
            _policy_root(path),
            sender_handle=sender_handle,
            field_name=field_name,
            note=note,
            reason=reason,
            actor=actor,
        )
    except PolicyError as exc:
        raise SystemExit(str(exc)) from exc
    _policy_result(result)


@policy_app.command("revoke")
def policy_revoke(
    sender_handle: str = typer.Option(..., "--from", "--sender", help="Sender handle"),
    field_name: str = typer.Option(..., "--field", help="Consent-gated signal field"),
    reason: Optional[str] = typer.Option(None, "--reason"),
    actor: Optional[str] = typer.Option(None, "--actor"),
    path: Optional[Path] = typer.Option(None, "--path", help="IE install root"),
) -> None:
    """Revoke consent while retaining its audit history."""
    from runtime.policy_store import PolicyError, revoke_consent

    try:
        result = revoke_consent(
            _policy_root(path),
            sender_handle=sender_handle,
            field_name=field_name,
            reason=reason,
            actor=actor,
        )
    except PolicyError as exc:
        raise SystemExit(str(exc)) from exc
    _policy_result(result)


@policy_app.command("quarantine")
def policy_quarantine(
    sender_handle: str = typer.Option(..., "--from", "--sender", help="Sender handle"),
    reason: str = typer.Option(..., "--reason", help="Why this sender is quarantined"),
    actor: Optional[str] = typer.Option(None, "--actor"),
    path: Optional[Path] = typer.Option(None, "--path", help="IE install root"),
) -> None:
    """Persistently quarantine a sender from depth and consent aggregation."""
    from runtime.policy_store import PolicyError, quarantine_sender

    try:
        result = quarantine_sender(
            _policy_root(path),
            sender_handle=sender_handle,
            reason=reason,
            actor=actor,
        )
    except PolicyError as exc:
        raise SystemExit(str(exc)) from exc
    _policy_result(result)


@policy_app.command("release")
def policy_release(
    sender_handle: str = typer.Option(..., "--from", "--sender", help="Sender handle"),
    reason: Optional[str] = typer.Option(None, "--reason"),
    actor: Optional[str] = typer.Option(None, "--actor"),
    path: Optional[Path] = typer.Option(None, "--path", help="IE install root"),
) -> None:
    """Release a sender from quarantine without deleting the history."""
    from runtime.policy_store import PolicyError, release_quarantine

    try:
        result = release_quarantine(
            _policy_root(path),
            sender_handle=sender_handle,
            reason=reason,
            actor=actor,
        )
    except PolicyError as exc:
        raise SystemExit(str(exc)) from exc
    _policy_result(result)


@policy_app.command("show")
def policy_show(
    path: Optional[Path] = typer.Option(None, "--path", help="IE install root"),
) -> None:
    """Show active persistent policy and audit count."""
    from runtime.policy_store import policy_snapshot

    _policy_result(policy_snapshot(_policy_root(path)))


@registry_app.command("list")
def registry_list(
    path: Optional[Path] = typer.Option(None, "--path"),
    json_out: bool = typer.Option(False, "--json", help="Print handles as JSON"),
) -> None:
    """List local Registry peer handles."""
    root = path.resolve() if path else require_ie_root()
    peers = list_peers(root)
    if json_out:
        typer.echo(json.dumps({"schema_version": "1", "peers": peers}, indent=2))
        return
    if not peers:
        typer.echo("(empty registry)")
        return
    for p in peers:
        typer.echo(p)


@registry_app.command("get")
def registry_get(
    handle: str = typer.Argument(..., help="Peer local_handle"),
    path: Optional[Path] = typer.Option(None, "--path"),
    json_out: bool = typer.Option(False, "--json", help="Print the entry as JSON"),
) -> None:
    """Print one Registry entry as YAML/JSON."""
    root = path.resolve() if path else require_ie_root()
    data = get_peer(root, handle)
    if data is None:
        raise SystemExit(f"No registry entry for {handle!r}")
    if json_out:
        typer.echo(json.dumps(data, indent=2, ensure_ascii=False))
        return
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
    if not database_path(root).is_file():
        raise SystemExit(f"No .ie/ie.sqlite3 under {root}")

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
    policy = (
        SQLiteStore.from_registry_root(root).load_policy(open_consent=True)
        if open_consent
        else None
    )
    receipt = apply_from_dict(
        data,
        registry_root=root,
        policy=policy,
        expected_to_handle=expected,
    )
    typer.echo(json.dumps(receipt.to_dict(), indent=2, ensure_ascii=False))
    if receipt.status == ApplyStatus.REJECTED:
        raise typer.Exit(code=1)


@request_app.command("create")
def request_create(
    requester: str = typer.Option(..., "--from", "--requester", help="Requester handle"),
    target: Optional[str] = typer.Option(
        None, "--to", "--target", help="Target handle (default: this install's handle)"
    ),
    scope: Optional[str] = typer.Option(
        None,
        "--scope",
        help="Comma-separated requested fields (e.g. coarse_mass_estimate,mass_confidence)",
    ),
    note: Optional[str] = typer.Option(None, "--note", help="Optional short note"),
    path: Optional[Path] = typer.Option(None, "--path", help="IE install root"),
) -> None:
    """Land an estimate request in this install's inbound inbox (local receive)."""
    root = path.resolve() if path else require_ie_root()
    if not database_path(root).is_file():
        raise SystemExit(f"No .ie/ie.sqlite3 under {root}")

    if target is None:
        st = collect_status(root)
        target = st.get("handle")
        if not target:
            raise SystemExit("Could not resolve target handle; pass --to")

    fields = [f.strip() for f in (scope or "").split(",") if f.strip()]

    from runtime.request import RequestError, create_inbound_request

    try:
        req = create_inbound_request(
            registry_root=root,
            requester_handle=requester,
            target_handle=target,
            requested_fields=fields,
            note=note,
            transport="cli",
        )
    except RequestError as e:
        raise SystemExit(str(e))

    typer.echo(json.dumps(req.to_dict(), indent=2, ensure_ascii=False))


@request_app.command("list")
def request_list(
    status: Optional[str] = typer.Option(
        None, "--status", help="Filter: pending|ignored|quarantined|answered|expired"
    ),
    path: Optional[Path] = typer.Option(None, "--path"),
    json_out: bool = typer.Option(False, "--json", help="Print requests as JSON"),
) -> None:
    """List inbound estimate requests."""
    root = path.resolve() if path else require_ie_root()
    if not database_path(root).is_file():
        raise SystemExit(f"No .ie/ie.sqlite3 under {root}")

    from runtime.models import RequestStatus
    from runtime.request import list_inbound_requests

    st_filter = None
    if status:
        try:
            st_filter = RequestStatus(status.strip().lower())
        except ValueError:
            raise SystemExit(
                "--status must be one of: pending|ignored|quarantined|answered|expired"
            )

    rows = list_inbound_requests(root, status=st_filter)
    if json_out:
        typer.echo(
            json.dumps(
                {"schema_version": "1", "requests": [row.to_dict() for row in rows]},
                indent=2,
                ensure_ascii=False,
            )
        )
        return
    if not rows:
        typer.echo("(no requests)")
        return
    for r in rows:
        fields = ",".join(r.requested_fields) if r.requested_fields else "-"
        typer.echo(
            f"{r.request_id}  {r.status.value:12}  from={r.requester_handle}  "
            f"scope={fields}  at={r.timestamp}"
        )


@request_app.command("show")
def request_show(
    request_id: str = typer.Argument(..., help="request_id"),
    path: Optional[Path] = typer.Option(None, "--path"),
) -> None:
    """Show one inbound request as JSON."""
    root = path.resolve() if path else require_ie_root()
    from runtime.request import get_inbound_request

    req = get_inbound_request(root, request_id)
    if req is None:
        raise SystemExit(f"No request {request_id!r}")
    typer.echo(json.dumps(req.to_dict(), indent=2, ensure_ascii=False))


@request_app.command("ignore")
def request_ignore(
    request_id: str = typer.Argument(..., help="request_id"),
    path: Optional[Path] = typer.Option(None, "--path"),
) -> None:
    """Mark an inbound request as ignored (no auto-answer; no quarantine)."""
    root = path.resolve() if path else require_ie_root()
    from runtime.models import RequestStatus
    from runtime.request import RequestError, set_request_status

    try:
        req = set_request_status(root, request_id, RequestStatus.IGNORED)
    except RequestError as e:
        raise SystemExit(str(e))
    typer.echo(json.dumps(req.to_dict(), indent=2, ensure_ascii=False))


@request_app.command("quarantine")
def request_quarantine(
    request_id: str = typer.Argument(..., help="request_id"),
    path: Optional[Path] = typer.Option(None, "--path"),
) -> None:
    """Quarantine the requester path for this request (symmetric to signal policy)."""
    root = path.resolve() if path else require_ie_root()
    from runtime.models import RequestStatus
    from runtime.request import RequestError, set_request_status

    try:
        req = set_request_status(
            root, request_id, RequestStatus.QUARANTINED
        )
    except RequestError as e:
        raise SystemExit(str(e))
    typer.echo(json.dumps(req.to_dict(), indent=2, ensure_ascii=False))


def _resolve_observer(root: Path, observer: Optional[str]) -> str:
    if observer:
        return observer.strip()
    st = collect_status(root)
    handle = st.get("handle")
    if not handle:
        raise SystemExit("Could not resolve observer handle; pass --observer")
    return handle


def _resolve_source_refs(root: Path, source_paths: list[str]) -> list[str]:
    """Resolve existing local Mature sources into root-relative references."""
    if not source_paths:
        raise SystemExit(
            "Mature requires at least one --source file under the install root"
        )

    root = root.resolve()
    resolved_refs: list[str] = []
    for raw_path in source_paths:
        raw_path = raw_path.strip()
        if not raw_path:
            raise SystemExit("--source must not be empty")

        candidate = Path(raw_path).expanduser()
        if not candidate.is_absolute():
            candidate = root / candidate
        candidate = candidate.resolve()
        try:
            relative = candidate.relative_to(root)
        except ValueError as exc:
            raise SystemExit("--source must stay inside the install root") from exc
        if not candidate.is_file():
            raise SystemExit(f"Mature source does not exist or is not a file: {raw_path}")

        ref = relative.as_posix()
        if ref not in resolved_refs:
            resolved_refs.append(ref)
    return resolved_refs


@app.command("mature")
def mature(
    notes: Optional[str] = typer.Option(
        None, "--notes", "-n", help="Causal integration / learning note"
    ),
    state_delta: Optional[str] = typer.Option(
        None, "--state-delta", help="stem_differential.state_delta_summary"
    ),
    vision_shift: Optional[str] = typer.Option(
        None, "--vision-shift", help="stem_differential.vision_gradient_shift"
    ),
    coherence: Optional[str] = typer.Option(
        None, "--coherence", help="stem_differential.coherence_note"
    ),
    commitment: Optional[str] = typer.Option(
        None,
        "--commitment",
        help="ownership_move.commitment (concrete next action, e.g. 72h)",
    ),
    ownership_level: Optional[float] = typer.Option(
        None,
        "--ownership-level",
        help="ownership_move.ownership_level_estimate (0–100)",
    ),
    optionality: Optional[float] = typer.Option(
        None,
        "--optionality",
        help="optionality_delta.value (signed local ΔO_τ)",
    ),
    optionality_confidence: Optional[float] = typer.Option(
        None,
        "--optionality-confidence",
        help="optionality_delta.confidence (0–1)",
    ),
    optionality_notes: Optional[str] = typer.Option(
        None, "--optionality-notes", help="optionality_delta.notes"
    ),
    changes: Optional[Path] = typer.Option(
        None,
        "--changes",
        help="JSON change-set with substance, workspace, registry, or reassessment changes",
    ),
    sources: list[str] = typer.Option(
        [],
        "--source",
        help="Existing evidence file under the install root (repeatable)",
    ),
    snapshot_sources: bool = typer.Option(
        False,
        "--snapshot-sources",
        help="Capture UTF-8 evidence snapshots in addition to path and hash",
    ),
    reassess: list[str] = typer.Option(
        [],
        "--reassess",
        help="Peer handle to ask for a fresh estimate after this Mature step (repeatable)",
    ),
    observer: Optional[str] = typer.Option(
        None, "--observer", help="Observer handle (default: this install)"
    ),
    path: Optional[Path] = typer.Option(None, "--path", help="IE install root"),
) -> None:
    """Mature: commit one directed, source-backed local learning step.

    Stem, Workspace, Registry, Trajectory, evidence, Geometry, and explicit
    reassessment requests are committed atomically. Emergent Self-Mass is never
    written by this command.

    Think is not a CLI: it is a phase label (inward, non-emitting) provided by
    substrate + prompts. Interact is tools/MCP/signals (see `ie signal apply`).
    """
    root = path.resolve() if path else require_ie_root()
    if not database_path(root).is_file():
        raise SystemExit(f"No .ie/ie.sqlite3 under {root}")

    change_set: dict = {}
    if changes:
        try:
            parsed = json.loads(changes.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise SystemExit(f"Could not read Mature change-set: {exc}") from exc
        if not isinstance(parsed, dict):
            raise SystemExit("Mature change-set must contain a JSON object")
        change_set = parsed

    change_sources = change_set.get("source_refs") or change_set.get("sources") or []
    if isinstance(change_sources, str):
        change_sources = [change_sources]
    if not isinstance(change_sources, list) or not all(
        isinstance(source_ref, str) for source_ref in change_sources
    ):
        raise SystemExit("Mature change-set source_refs must be a list of strings")
    source_refs = _resolve_source_refs(root, list(sources) + change_sources)
    obs = _resolve_observer(root, observer)
    stem = None
    if state_delta or vision_shift or coherence:
        stem = {
            "state_delta_summary": state_delta or "",
            "vision_gradient_shift": vision_shift or "",
            "coherence_note": coherence or "",
        }
    if isinstance(change_set.get("stem_differential"), dict):
        stem = {**(stem or {}), **change_set["stem_differential"]}
    elif isinstance(change_set.get("stem"), dict):
        stem = {**(stem or {}), **change_set["stem"]}

    ownership = None
    if commitment is not None or ownership_level is not None:
        ownership = {
            "commitment": commitment or "",
            "ownership_level_estimate": ownership_level,
        }
    if ownership is None and isinstance(change_set.get("ownership_move"), dict):
        ownership = change_set["ownership_move"]

    opt = None
    if optionality is not None:
        conf = (
            float(optionality_confidence)
            if optionality_confidence is not None
            else 0.5
        )
        if not (0.0 <= conf <= 1.0):
            raise SystemExit("--optionality-confidence must be in [0, 1]")
        opt = {
            "value": float(optionality),
            "confidence": conf,
            "notes": optionality_notes or "",
        }
    if opt is None and isinstance(change_set.get("optionality_delta"), dict):
        opt = change_set["optionality_delta"]

    notes_value = notes or str(change_set.get("notes") or "")
    workspace = change_set.get("workspace_changes", change_set.get("workspace", []))
    registry = change_set.get("registry_changes", change_set.get("registry", []))
    substance = change_set.get("substance")
    reassessment_targets = list(reassess)
    configured_targets = change_set.get("reassessment_targets") or []
    if isinstance(configured_targets, str):
        configured_targets = [configured_targets]
    if not isinstance(configured_targets, list) or not all(
        isinstance(target, str) for target in configured_targets
    ):
        raise SystemExit("Mature change-set reassessment_targets must be a list of strings")
    for target in configured_targets:
        if target not in reassessment_targets:
            reassessment_targets.append(target)

    from runtime.mature import MatureError, commit_mature

    try:
        result = commit_mature(
            root,
            source_refs=source_refs,
            notes=notes_value,
            actor=obs,
            stem_differential=stem,
            substance=substance,
            workspace_changes=workspace,
            registry_changes=registry,
            reassessment_targets=reassessment_targets,
            ownership_move=ownership,
            optionality_delta=opt,
            capture_snapshots=snapshot_sources
            or bool(change_set.get("capture_snapshots", False)),
        )
    except MatureError as exc:
        raise SystemExit(str(exc)) from exc
    typer.echo(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))


@app.command("mass")
def mass(
    path: Optional[Path] = typer.Option(None, "--path", help="IE install root"),
    json_out: bool = typer.Option(
        False, "--json", help="Print full MassReadout as JSON"
    ),
    detail: bool = typer.Option(
        False, "--detail", "-d", help="Per-contributor table (human output)"
    ),
) -> None:
    """Emergent self-Mass from foreign-estimate zone (never self-declared).

    Weighted mean of received coarse_mass_estimate values:
    weight = (sender_Mass/100) * confidence * depth_factor(accumulated_depth).
    See docs/mass.md.
    """
    root = path.resolve() if path else require_ie_root()
    if not database_path(root).is_file():
        raise SystemExit(f"No .ie/ie.sqlite3 under {root}")

    from runtime.mass import compute_mass_readout

    readout = compute_mass_readout(root)
    if json_out:
        typer.echo(json.dumps(readout.to_dict(), indent=2, ensure_ascii=False))
        return

    mass_s = (
        f"{readout.emergent_self_mass:.4f}"
        if readout.emergent_self_mass is not None
        else "unobserved"
    )
    typer.echo(f"emergent self-Mass: {mass_s}")
    typer.echo(f"  formula:           v{readout.formula_version}")
    typer.echo(f"  estimators:        {readout.estimator_count}")
    typer.echo(f"  total weight:      {readout.total_weight:.6f}")
    typer.echo(f"  volume count:      {readout.volume_count}")
    typer.echo(f"  volume weighted:   {readout.volume_weighted:.4f}")
    for n in readout.notes:
        typer.echo(f"  note: {n}")

    if detail:
        typer.echo("\ncontributors:")
        for c in readout.contributors:
            if not c.included:
                typer.echo(
                    f"  - {c.sender_handle}: skipped ({c.skip_reason or 'n/a'})"
                )
                continue
            typer.echo(
                f"  - {c.sender_handle}: E={c.estimate:.1f} c={c.confidence:.2f} "
                f"d={c.accumulated_depth:.3f} M={c.sender_mass:.1f}"
                f"({c.sender_mass_source}) w={c.weight:.6f}"
            )


@app.command("catalogue")
def catalogue(
    path: Optional[Path] = typer.Option(None, "--path"),
) -> None:
    """Show dimension catalogue path / stub summary."""
    root = path.resolve() if path else require_ie_root()
    from runtime.database import Database

    with Database(database_path(root)) as database:
        rows = database.conn.execute(
            """
            SELECT name, weight, active, discovered_via, revision
            FROM metric_dimensions
            ORDER BY name
            """
        ).fetchall()
    if not rows:
        typer.echo("(empty dimension catalogue)")
        return
    for row in rows:
        typer.echo(
            f"{row['name']}  weight={row['weight']:.3f}  "
            f"active={bool(row['active'])}  revision={row['revision']}"
        )


@app.command("reindex")
def reindex(
    path: Optional[Path] = typer.Option(None, "--path", help="IE install root"),
) -> None:
    """Recompute derived readouts (volume / emergent self-Mass). Live only in v0."""
    root = path.resolve() if path else require_ie_root()
    if not database_path(root).is_file():
        raise SystemExit(f"No .ie/ie.sqlite3 under {root}")

    from runtime.mass import compute_mass_readout

    readout = compute_mass_readout(root)
    mass_s = (
        f"{readout.emergent_self_mass:.4f}"
        if readout.emergent_self_mass is not None
        else "unobserved"
    )
    typer.echo("ie reindex: derived readouts recomputed (no persistent cache in v0)")
    typer.echo(f"  emergent self-Mass: {mass_s}")
    typer.echo(f"  estimators:         {readout.estimator_count}")
    typer.echo(f"  volume count:       {readout.volume_count}")


if __name__ == "__main__":
    app()
