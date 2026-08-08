# IE CLI (SQLite-first V1)

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

Non-interactive example:

```bash
ie init --path ~/ie --account no_account --name Jonas --handle jonas -y
```

`ie init` remembers the created install as the active local root (`$XDG_CONFIG_HOME/ie-os/active-root` or `~/.config/ie-os/active-root`).

V1 is a DB-only cutover. `ie init` does not migrate existing `HEADER.yaml`,
`STEM.yaml`, Registry, trajectory, or other legacy YAML state. If a legacy
install is detected, initialization stops; back it up or export it manually
before using `ie init --reset --yes`, which removes the known legacy state and
creates a new `.ie/ie.sqlite3`.

## Commands (SQLite-first V1)

| Command | Purpose |
|---------|---------|
| `ie init` | Interactive setup |
| `ie status` | Install summary |
| `ie registry list` / `get` | Local registry |
| `ie signal apply` | Interact: apply signal + Geometry Receipt |
| `ie request …` | Inbound estimate-request inbox |
| `ie policy …` | Persistent consent and sender quarantine |
| `ie mature` | Mature: atomic source-backed learning commit |
| `ie mass` | Emergent self-Mass readout |
| `ie db info` / `integrity-check` / `backup` / `rebuild-projections` | Database diagnostics and recovery |

All mutable runtime state is in `<install-root>/.ie/ie.sqlite3`. `README.md` and
`IE.md` are orientation documents only; the YAML files under `schemas/` and
`templates/` are contracts/examples and are not runtime storage.

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

## See also

- `docs/tim-cycle.md`
- `docs/living-form.md`
- `docs/distribution.md`
- `docs/surface-runtime-local.md`
- `docs/tim-cycle.md`
- `docs/living-form.md`
