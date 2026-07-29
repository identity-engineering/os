# Worked example: Surface Runtime local apply

Locked walkthrough so the operational meaning of Surface Runtime v0 stays concrete.

## Setup

- Observer Identity handle: `jonas`
- Registry root: `templates/personal/registry/` (or any local registry)
- Policy: default Free-tier (`open_consent=false`, no grants, no quarantine)

## Incoming Interaction Signal

Peer `peer-alice` sends:

```json
{
  "from": "peer-alice",
  "to": "jonas",
  "timestamp": "2026-07-29T06:10:00+00:00",
  "existence": true,
  "interaction_depth_delta": 0.18,
  "coarse_mass_estimate": 61,
  "mass_confidence": 0.75
}
```

## What the Runtime does

1. **Validate** required fields and ranges.
2. **Policy check**
   - `existence` → apply (always-passed)
   - `interaction_depth_delta` → apply (always-passed)
   - `coarse_mass_estimate` → reject (consent field, no grant)
   - `mass_confidence` → reject (consent field, no grant)
3. **Write** only into the foreign-estimate zone:
   `registry/_foreign_estimates/peer-alice.yaml`
4. **Return receipt** (always).

## Resulting foreign-estimate record (excerpt)

```yaml
sender_handle: peer-alice
first_signal_at: "2026-07-29T06:10:00+00:00"
last_signal_at: "2026-07-29T06:10:00+00:00"
signal_count: 1
accumulated_depth: 0.18
last_depth_delta: 0.18
existence_confirmed: true
coarse_mass_estimate: null
mass_confidence: null
quarantine: false
last_receipt_id: "<uuid>"
```

## Receipt returned to sender

```json
{
  "receipt_id": "<uuid>",
  "status": "partial",
  "timestamp": "<iso>",
  "from_handle": "peer-alice",
  "to_handle": "jonas",
  "applied_fields": ["existence", "interaction_depth_delta"],
  "rejected_fields": [
    {"field": "coarse_mass_estimate", "reason": "no grant for consent field"},
    {"field": "mass_confidence", "reason": "no grant for consent field"}
  ],
  "reason": "applied to foreign-estimate zone",
  "quarantine": false
}
```

## What this means geometrically

- Alice has confirmed existence of `jonas` in her frame and contributed interaction depth.
- Her Mass estimate of Jonas did **not** land, because Jonas has not granted that consent field.
- Jonas now has an audit trail (receipt) and a bounded write in the only region others may touch by default.
- Stem, Vision, Metric Stem weights and access policy remain untouched.

## Variants

| Policy / situation | Outcome |
|--------------------|---------|
| `--open-consent` or grant for mass fields | Status `applied`; mass fields written |
| Sender quarantined | Existence may still be recorded for audit; depth + consent refused; `quarantine: true` on receipt |
| `to` handle mismatch | Status `rejected`; nothing written |

## How to reproduce

```bash
python -m runtime apply \
  --registry templates/personal/registry \
  --to jonas \
  --payload /path/to/signal.json

# or via local HTTP surface
python -m runtime.http_handler --registry templates/personal/registry --to jonas --port 8787
curl -s -X POST http://127.0.0.1:8787/ie/v0/signals \
  -H 'Content-Type: application/json' \
  -d @signal.json
```

See also: `docs/surface-runtime-local.md`, `docs/foreign-estimate-zone.md`, `schemas/surface-operations/v0.yaml`.
