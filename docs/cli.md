# IE CLI (v0 skeleton)

Issue #18 — first installable `ie` command so a personal setup does **not** require manual template copying or `python -m runtime`.

## Install (once)

From a checkout of `identity-engineering/os`:

```bash
cd /path/to/os
pip install -e .
```

This registers the `ie` entry point (Typer) and pulls `typer` + `pyyaml`.

Later: `pip install` from a published package or `pip install git+https://github.com/identity-engineering/os.git` — same commands.

You only need the repo (or package) for **installing the tool**. Your Identity data lives in a **separate directory** created by `ie init`.

## Personal install (no manual copy)

```bash
# anywhere you want your Identity files to live
mkdir -p ~/ie && cd ~/ie
ie init . --handle jonas --name Jonas

ie status
```

`ie init` copies bundled `templates/personal/` into the target directory and sets `local_handle` / `preferred_name` in `HEADER.yaml`.

Optional:

```bash
ie init ~/ie --handle jonas --name Jonas
export IE_ROOT=~/ie   # so you can run ie commands from any cwd
```

## Commands (v0)

| Command | Purpose |
|---------|---------|
| `ie --version` | Package version |
| `ie init [path] --handle … [--name …]` | Create install from templates |
| `ie status` | Handle, registry peers, foreign-estimate senders |
| `ie registry list` | Peer handles in `registry/` |
| `ie registry get <handle>` | Print one registry entry |
| `ie signal apply [--payload file.json]` | Apply Interaction Signal → foreign-estimate zone + receipt |
| `ie catalogue` | Stub / path to catalogue |
| `ie reindex` | Stub |

### Apply a signal

```bash
cd ~/ie   # or IE_ROOT set

cat > /tmp/signal.json << 'EOF'
{
  "from": "peer-alice",
  "to": "jonas",
  "timestamp": "2026-07-29T10:00:00+00:00",
  "existence": true,
  "interaction_depth_delta": 0.12
}
EOF

ie signal apply --payload /tmp/signal.json
# consent fields in dogfood:
ie signal apply --payload /tmp/signal.json --open-consent
```

Receipt JSON is printed; writes go under `registry/_foreign_estimates/`.

## How the CLI finds your install

1. `IE_ROOT` env var, if set and contains `HEADER.yaml`
2. Else walk upward from cwd until `HEADER.yaml` is found
3. Else error: run `ie init` or set `IE_ROOT`

## Relation to Surface Runtime

`ie signal apply` calls the same `runtime.apply.apply_from_dict` as `python -m runtime apply`. One code path.

## Explicit non-goals (this slice)

- Global install without ever seeing the repo (publish to PyPI later)
- MCP / HTTP start via `ie serve` (HTTP handler exists; wire as `ie surface serve` later)
- Estimate request / inbox (#31)
- Cloud / Pro storage adapters

## See also

- `docs/surface-runtime-local.md`
- `docs/surface-runtime-worked-example.md`
- Issue #18
