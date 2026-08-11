# IE CLI (local mini-Space V1)

Issue #18 — installable `ie` command.

The CLI operates a **local mini-Space** (`docs/space-model.md`): one install, one
Identity in V1, full Ownership, no account required for the geometry loop.
Mutable state is stored in SQLite under `.ie/ie.sqlite3` (store engine).

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
   - `1) No account` — local-only Free mini-Space (default)
   - `2) Login` — browser → account (stub in v0; optional continuity in IE-managed Space)
   - `3) Create account` — browser → account (stub in v0)
3. **Preferred name**
4. **local_handle** — default = preferred name lowercased (spaces → hyphens)

Non-interactive example:

```bash
ie init --path ~/ie --account no_account --name Jonas --handle jonas -y
```

`ie init` remembers the created install as the active local root (`$XDG_CONFIG_HOME/ie-os/active-root` or `~/.config/ie-os/active-root`).

V1 does not migrate existing `HEADER.yaml`, `STEM.yaml`, Registry, trajectory,
or other legacy YAML state. If a legacy install is detected, initialization
stops; back it up or export it manually before using `ie init --reset --yes`,
which removes the known legacy state and creates a new `.ie/ie.sqlite3`.

Account is **optional**. Geometry lives on the local Identity; an IE Account is
product auth/plan on the managed path only (`docs/account-identity-model.md`).

## Commands (local mini-Space V1)

| Command | Purpose |
|---------|---------|
| `ie init` | Interactive setup of a local mini-Space |
| `ie status` | Install summary (includes `geometry_feed`) |
| `ie registry list` / `get` | Local registry |
| `ie signal apply` | Interact: apply signal + Geometry Receipt + feed |
| `ie geometry feed` | Explicit Geometry Receipt → Registry feed |
| `ie request …` | Inbound estimate-request inbox |
| `ie policy …` | Persistent consent and sender quarantine |
| `ie mature` | Mature: atomic source-backed learning commit |
| `ie mass` | Emergent self-Mass readout |
| `ie db info` / `integrity-check` / `backup` / `rebuild-projections` | Database diagnostics and recovery |
| `ie jurisdiction probe` / `show` / `list` | Access & Jurisdiction owner probes |
| `ie jurisdiction grant list` / `transfer` / `revoke` | Audit ordinary Identity grants |
| `ie space list` | Persisted local and known Space membrane state |
| `ie space boundary export` / `verify` | Public Space membrane descriptor |

All mutable runtime state is in `<install-root>/.ie/ie.sqlite3`. `README.md` and
`IE.md` are orientation documents only; the YAML files under `schemas/` and
`templates/` are contracts/examples and are not runtime storage.

### Geometry feed

```bash
ie geometry feed                 # process pending receipts
ie geometry feed --all           # same, higher limit
ie geometry feed --receipt-id <id>
ie geometry feed --force         # re-feed already marked receipts
```

Hook path runs automatically after successful `ie signal apply`.

### TIM mapping (short)

- **Think** — no CLI. Phase label for inward, non-emitting work (plan-mode, private memory, prompts).
- **Interact** — `ie signal apply` + tools/MCP/APIs/scripts (cross-membrane).
- **Mature** — `ie mature` (source-backed atomic commit to Stem, Workspace,
  Registry, Trajectory, evidence, Geometry, and explicit reassessment requests).

```bash
ie mature --notes "what caused the Mass dip" \
  --source evidence/2026-08-05.txt \
  --state-delta "causal chain reconstructed" \
  --commitment "72h: ship Access probes draft" \
  --ownership-level 88 \
  --optionality 0.3 --optionality-notes "opens Ownership path"
```

For structured changes, pass a JSON object with `--changes`:

```json
{
  "substance": {"current_focus": "ownership probe"},
  "workspace_changes": [
    {"kind": "commitment", "title": "Run probe", "content": "Prepare evidence."}
  ],
  "registry_changes": [
    {"peer_handle": "alice", "my_mass_estimate": 62, "mass_confidence": 0.8}
  ],
  "reassessment_targets": ["alice"]
}
```

`--source` must point to at least one existing file inside the install root.
The source path and SHA-256 are retained; `--snapshot-sources` opts into a
UTF-8 content snapshot. All Mature writes commit or roll back together. Mature
never writes an owned numeric Self-Mass.

Persistent policy is explicit and auditable:

```bash
ie policy grant --from alice --field coarse_mass_estimate
ie policy revoke --from alice --field coarse_mass_estimate
ie policy quarantine --from alice --reason "boundary test"
ie policy release --from alice
ie policy show
```

Database recovery is explicit:

```bash
ie db info
ie db integrity-check
ie db backup --to ~/ie-backups/ie.sqlite3
ie db rebuild-projections --yes
```

Run `backup` first. `rebuild-projections` restores Foreign Estimates from
Interaction Events and owned projections from their revision snapshots; it
does not rewrite append-only audit history or policy history.

Grants and the public Space boundary are explicit too:

```bash
ie jurisdiction grant list --json
ie jurisdiction grant transfer --grant <grant-id> --to <identity-id> --note "delegate"
ie jurisdiction grant revoke --grant <grant-id> --note "retire access"

ie space boundary export --to ~/ie-boundary.json --space-id <space-id>
ie space boundary verify --from ~/ie-boundary.json --space-id <space-id>
ie space boundary verify --from ~/remote-boundary.json --path ~/ie --register
ie space list --path ~/ie --json
```

Transfer and revoke preserve audit rows and reject the residual emergency grant
through the ordinary path. Boundary export contains public host metadata and a
restrictive membrane policy, never the private Identity-space tables. Verify
classifies an accepted boundary as `known` with `addressable: false`. With
`--register --path`, that known state is persisted without creating membership.
The local Space and primary membership are persisted in Schema 9; MCP session
binding and per-tool checks enforce the local `surface`, `public_card`, and
`interaction_signal` gates. Governed membership administration, federation,
and complete HTTP/CLI endpoint gating remain later work.

## See also

- `docs/space-model.md`
- `docs/account-identity-model.md`
- `docs/local-operations-v1.md`
- `docs/storage-tiers.md`
- `docs/open-core.md`
- `docs/tim-cycle.md`
- `docs/living-form.md`
- `docs/distribution.md`
- `docs/surface-runtime-local.md`
- `docs/access-jurisdiction-probes.md`
- `docs/geometry-feed.md`
