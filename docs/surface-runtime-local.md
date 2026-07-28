# Surface Runtime – Local deterministic apply (v0)

First implementation slice of issue #29 / `docs/realization-surface-runtime.md`.

## What is shipped

A pure local apply path with **no external network dependency required for the core**:

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
| `http_handler.py` | Thin stdlib HTTP surface re-using the same apply path |

Tests: `tests/test_apply.py` (stdlib unittest).

## Usage – CLI apply

```bash
# From repo root
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

## Usage – local HTTP surface

```bash
python -m runtime.http_handler \
  --registry templates/personal/registry \
  --to my-handle \
  --open-consent \
  --port 8787
```

Routes (aligned with `schemas/surface-operations/v0.yaml`):

| Method | Path | Op |
|--------|------|----|
| POST | `/ie/v0/signals` | `receive_interaction_signal` |
| GET | `/ie/v0/card` | `get_public_card` |
| GET | `/ie/v0/health` | liveness |

Example:

```bash
curl -s -X POST http://127.0.0.1:8787/ie/v0/signals \
  -H 'Content-Type: application/json' \
  -d '{"from":"peer-alice","to":"my-handle","timestamp":"2026-07-28T12:00:00+00:00","existence":true,"interaction_depth_delta":0.1}'
```

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

## Tests

```bash
python -m unittest tests.test_apply -v
```

Covers: always-passed apply, consent refusal, open-consent apply, quarantine, to-handle mismatch, invalid depth, depth accumulation.

## Explicit non-goals of this slice

- MCP binding (next)
- Full Typer CLI packaging (`ie signal apply`) – see issue #18
- Auth beyond local trust / expected_to_handle check
- Managed Pro / Supabase
- Emergent self-Mass aggregation formula (issue #15)
- Rate-limit time windows (only a soft max-count guard in policy)

## Next on this branch / follow-ups

1. MCP tool wrappers around the same handlers
2. Receipt / audit log persistence if dogfood needs it
3. Wire into future `ie` CLI (#18)
