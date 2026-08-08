# Surface Runtime – Local deterministic apply (SQLite-first V1)

First implementation slice of issue #29 / `docs/realization-surface-runtime.md`.

## What is shipped

A pure local apply path with **no external network dependency required for the core**:

```
payload → validate → canonical event → policy check → SQLite projections → receipt
```

Plus the inbound **estimate request** path (issue #31):

```
request → validate → soft rate limit → write `estimate_requests` → pending
```

Location of code: `runtime/`

| Module | Role |
|--------|------|
| `models.py` | InteractionSignal, Receipt, ForeignEstimateRecord, EstimateRequest |
| `policy.py` | LocalPolicy (always-passed vs consent, quarantine) |
| `database.py` | SQLite lifecycle, schema, migrations, integrity, backup |
| `sqlite_store.py` | Foreign Estimate, policy, signal, Registry and receipt persistence |
| `apply.py` | `apply_interaction_signal` / `apply_from_dict` (+ reply linkage) |
| `request.py` | create / list / status / mark_answered for estimate requests |
| `__main__.py` | Minimal CLI: `python -m runtime apply ...` |
| `http_handler.py` | Thin stdlib HTTP surface re-using the same apply path |

Tests: `tests/test_apply.py`, `tests/test_request.py` (stdlib unittest).

## Usage – CLI apply

```bash
# From repo root
python -m runtime apply \
  --install /path/to/ie-install \
  --to my-handle \
  --open-consent \
  --payload /tmp/signal.json
```

Or via packaged CLI:

```bash
ie signal apply --open-consent --payload /tmp/signal.json
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

Reply linkage (marks a pending inbound request answered):

```json
{
  "from": "me",
  "to": "peer-alice",
  "timestamp": "2026-07-31T10:00:00+00:00",
  "existence": true,
  "interaction_depth_delta": 0.1,
  "coarse_mass_estimate": 60,
  "in_reply_to_request_id": "<request_id>"
}
```

Receipt is always printed as JSON (status: applied | partial | rejected).

## Usage – estimate request inbox

```bash
ie request create --from alice --to me --scope coarse_mass_estimate
ie request list --status pending
ie request show <request_id>
ie request ignore <request_id>
ie request quarantine <request_id>
```

See `docs/estimate-request.md`.

## Usage – local HTTP surface

```bash
python -m runtime.http_handler \
  --install /path/to/ie-install \
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

(HTTP binding for `request_estimate` is sketched in the schema; local CLI is the v0 path.)

Example:

```bash
curl -s -X POST http://127.0.0.1:8787/ie/v0/signals \
  -H 'Content-Type: application/json' \
  -d '{"from":"peer-alice","to":"my-handle","timestamp":"2026-07-28T12:00:00+00:00","existence":true,"interaction_depth_delta":0.1}'
```

## Storage layout

```
<install-root>/
  .ie/
    ie.sqlite3
  README.md        # orientation only
  IE.md             # agent discovery only
```

See `docs/sqlite-schema-v1.md`. The YAML files under `schemas/` remain wire
contracts and are not read as mutable runtime storage.

## Policy defaults (v0)

- Always-passed (`existence`, `interaction_depth_delta`) → auto-apply for non-quarantined senders.
- Consent fields → refused unless `LocalPolicy.open_consent=True` or an explicit grant exists.
- Quarantined senders → existence still recorded for audit; depth + consent refused; receipt carries `quarantine: true`.
- Estimate requests → never auto-answered; soft pending-count limit per requester.
- No path from apply or request into Stem, Vision, Metric Stem weights, or access-policy mutation.

## Tests

```bash
python -m unittest tests.test_apply tests.test_request -v
```

## Explicit non-goals of this slice

- MCP binding (next)
- Full network delivery of requests between separate installs
- Managed Pro / Supabase
- Emergent self-Mass aggregation formula (issue #15)
- Rate-limit time windows (only soft max-count guards)

## Next on this path

1. MCP tool wrappers around the same handlers (including request_estimate)
2. Thin HTTP routes for `/ie/v0/requests`
3. Opt-in post-interaction outbound request hooks
