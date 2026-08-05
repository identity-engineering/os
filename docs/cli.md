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

Non-interactive example:

```bash
ie init --path ~/ie --account no_account --name Jonas --handle jonas -y
```

`ie init` remembers the created install as the active local root (`$XDG_CONFIG_HOME/ie-os/active-root` or `~/.config/ie-os/active-root`).

## Commands (v0)

| Command | Purpose |
|---------|---------|
| `ie init` | Interactive setup |
| `ie status` | Install summary |
| `ie registry list` / `get` | Local registry |
| `ie signal apply` | Interact: apply signal + Geometry Receipt |
| `ie request …` | Inbound estimate-request inbox |
| `ie mature` | Mature: source-backed self Geometry Receipt |
| `ie mass` | Emergent self-Mass readout |
| `ie catalogue` / `ie reindex` | Stubs |

### TIM mapping (short)

- **Think** — no CLI. Phase label for inward, non-emitting work (plan-mode, private memory, prompts).
- **Interact** — `ie signal apply` + tools/MCP/APIs/scripts (cross-membrane).
- **Mature** — `ie mature` (source-backed causal-integration record; optional ownership_move *record* only).

```bash
ie mature --notes "what caused the Mass dip" \
  --source trajectory/2026-08-05.yaml \
  --state-delta "causal chain reconstructed" \
  --commitment "72h: ship Access probes draft" \
  --ownership-level 88 \
  --optionality 0.3 --optionality-notes "opens Ownership path"
```

`--source` must point to at least one existing file inside the install root. The
state, vision, ownership, and optionality values are explicit v0 observations;
the command does not infer a trajectory or update live Stem/Vision/Policy.
Writes the source-backed record under `registry/_geometry_receipts/` and does not
apply `ownership_move` to Stem/Vision/Policy (#40).

## See also

- `docs/tim-cycle.md`
- `docs/living-form.md`
- `docs/distribution.md`
- `docs/surface-runtime-local.md`
- `docs/tim-cycle.md`
- `docs/living-form.md`
