# Surface Runtime – Local deterministic apply (v0)

First implementation slice of issue #29 / `docs/realization-surface-runtime.md`.

## What is shipped

A pure local apply path with **no network**:

```
payload → validate → policy check → write foreign-estimate zone → receipt
```

Location of code: `runtime/`

| Module | Role |
|--------|------|
| `models.py` | InteractionSignal, Receipt, ForeignEstimateRecord |
| `policy.py` | LocalPolicy (always-passed vs consent, quarantine) |
| `storage.py` | File store under `registry/_foreign_estimates/` |
| `apply.py` | `apply_interaction_signal` / `apply_from_dict` |
| `__main__.py` | Minimal CLI: `python -m runtime apply ...` |

## Usage (dev)

```bash
# From repo root, with a personal template registry
python -m runtime apply \
  --registry templates/personal/registry \
  --to my-handle \
  --open-consent \
  --payload /tmp/signal.json
```

Example payload (always-passed only):

```json
{
  "from": "peer-alice",
  "to": "my-handle",
  "timestamp": "2026-07-28T12:00:00+00:00",
  "existence": true,
  "interaction_depth_delta": 0.15
}
```

With consent fields (requires `--open-consent` or a grant):

```json
{
  "from": "peer-alice",
  "to": "my-handle",
  "timestamp": "2026-07-28T12:00:00+00:00",
  "existence": true,
  "interaction_depth_delta": 0.15,
  "coarse_mass_estimate": 42,
  "mass_confidence": 0.7
}
```

Receipt is always printed as JSON (status: applied | partial | rejected).

## Storage layout

```
registry/
  _foreign_estimates/
    peer-alice.yaml   # or .json if PyYAML missing
    ...
```

See `schemas/foreign-estimate-zone/v0.yaml` for the record shape.

## Policy defaults (v0)

- Always-passed (`existence`, `interaction_depth_delta`) → auto-apply for non-quarantined senders.
- Consent fields → refused unless `LocalPolicy.open_consent=True` or an explicit grant exists.
- Quarantined senders → existence still recorded for audit; depth + consent refused; receipt carries `quarantine: true`.
- No path from this apply function into Stem, Vision, Metric Stem weights, or access-policy mutation.

## Explicit non-goals of this slice

- HTTP / MCP bindings (next steps on the same branch or follow-up)
- Full Typer CLI packaging (`ie signal apply`) – see issue #18
- Managed Pro / Supabase
- Emergent self-Mass aggregation formula (issue #15)
- Rate-limit window implementation beyond a simple max-count guard

## Next on this branch

1. Minimal tests (stdlib unittest) for apply / quarantine / consent refusal
2. Optional: thin HTTP handler that re-uses the same `apply_interaction_signal`
3. Receipt persistence (audit log) if needed for dogfood
