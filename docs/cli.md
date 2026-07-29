# IE CLI (v0 skeleton)

Issue #18 — installable `ie` command. Personal setup does **not** require manual template copying.

## Install the tool (once) — distribution

Free CLI for everyone must be installable **without a GitHub account or token**.
That is a **distribution** requirement, separate from Free vs Pro product tiers.

See `docs/distribution.md`.

Until a public package exists, dev install from a checkout:

```bash
pip install -e /path/to/os
# or later:
# brew tap identity-engineering/tap && brew install ie-os
# pip install ie-os   # once published to PyPI
```

## Personal install — interactive

```bash
ie init
```

Dialog (Enter = default):

```
Install path [~/ie]:
local_handle (required):
preferred_name [same as handle]:
Tier [free]:
```

- Creates `~/ie` (or chosen path) including `mkdir -p` — no prior `mkdir` needed
- `free` = local files only, no account
- `pro` = stub in v0 (local install still; cloud link later)

Non-interactive:

```bash
ie init --path ~/ie --handle jonas --name Jonas --tier free -y
```

Then:

```bash
export IE_ROOT=~/ie   # optional
ie status
ie signal apply --payload /tmp/signal.json
```

## Commands (v0)

| Command | Purpose |
|---------|---------|
| `ie --version` | Package version |
| `ie init` | Interactive (or flagged) personal install |
| `ie status` | Handle, registry, foreign estimates |
| `ie registry list` / `get` | Registry |
| `ie signal apply` | Apply signal → foreign-estimate zone + receipt |
| `ie catalogue` / `ie reindex` | Stubs |

## How the CLI finds your install

1. `IE_ROOT` if set and contains `HEADER.yaml`
2. Else walk upward from cwd
3. Else: run `ie init` or set `IE_ROOT`

## See also

- `docs/distribution.md` — why private git ≠ product auth
- `docs/surface-runtime-local.md`
- Issue #18
