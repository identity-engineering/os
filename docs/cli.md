# IE CLI (v0 skeleton)

Issue #18 — installable `ie` command.

## Install the tool (once)

Free users must install **without GitHub auth**. See `docs/distribution.md`.

```bash
# target UX (macOS)
brew tap identity-engineering/tap && brew install ie-os

# universal Python fallback (once published)
pipx install ie-os
```

Dev until public packages exist: `pip install -e /path/to/os`.

## Personal setup — interactive

```bash
ie init
```

Prompt order:

1. **Install path** — default `~/ie` (created automatically)
2. **Account** — numbered choice:
   - `1) No account` — local-only Free (default)
   - `2) Login` — browser → account (stub in v0)
   - `3) Create account` — browser → account (stub in v0)
3. **Preferred name**
4. **local_handle** — default = preferred name lowercased (spaces → hyphens)

### Account model (product)

| Mode | Tier baseline | Capabilities |
|------|---------------|--------------|
| No account | Free | Local files only; no public registry metadata of others |
| Account (free entitlement) | Free | Basic account metadata; can read **public** registry metadata of others |
| Account (pro entitlement) | Pro | IE central identity hosting / managed surface |

Tier is determined by the **account**, not a separate “tier” prompt. Browser login/create returns an `account_id` to the CLI (v0: stub, local install still completes).

Non-interactive example:

```bash
ie init --path ~/ie --account no_account --name Jonas --handle jonas -y
```

## Commands (v0)

| Command | Purpose |
|---------|---------|
| `ie init` | Interactive setup |
| `ie status` | Install summary |
| `ie registry list` / `get` | Local registry |
| `ie signal apply` | Apply signal + receipt |
| `ie catalogue` / `ie reindex` | Stubs |

## See also

- `docs/distribution.md`
- `docs/surface-runtime-local.md`
