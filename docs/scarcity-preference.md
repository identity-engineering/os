# Scarcity envelope

Status: **parked behind Stem lock #118** (2026-08-29)
Product path: IE-managed Space first. Same logical schema on Local Space.
Not a marketplace. Not a currency-identity. Not billing.

Parent: `docs/stem.md` (PR #118). Preference reading: `docs/preference.md`.
Related: `docs/storage-tiers.md`, `docs/account-identity-model.md`,
`docs/sqlite-schema-v1.md`, `schemas/scarcity-envelope/v0.yaml`.

## Why this exists

Every Identity allocates under a finite envelope. That envelope is measurable.
It is not Stem geometry. Preference is the Stem curve in the Now (slope of
`stem_revisions` + Vision Gradient under Frequency). Scarcity is a later cap
on sampling / spend. It must not invent fibers so that spend has a foreign key.

## Locked decisions

1. Scarcity is Identity-bound. Account is not the envelope holder.
2. Envelope units start as `tokens`, `energy_wh`, `attention_h`.
   `fiat_budget` is an owner-set counter only. No onramp, token, or chain.
3. Cap is owner-granted or substrate-given. Identity cannot declare Mass
   by inflating its envelope.
4. Preference is Stem-inherent and derived. See `docs/preference.md` and #118.
   Revealed Preference is first slope, later optionally spend.
5. Logging is the existing append-only event / revision / receipt journal.
   Correction is a later compensating event. History is never rewritten.
6. Backend is Space-kind: IE-managed SQL is the product host; Local Space
   mirrors the same tables in SQLite. Skills stay storage-agnostic.
   YAML is documentation, not mutable state.
7. Every mutation carries `actor_identity_id`. Add `space_id` when membrane
   applies.
8. Events may carry `path_note`. `path_id` only after Mature has named an
   aspect. Spend does not create aspects.

## Scarcity envelope (projection)

One current row per `(identity_id, unit, period)`.

| Field | Meaning |
|---|---|
| `envelope_id` | UUID |
| `identity_id` | Envelope subject |
| `unit` | `tokens` \| `energy_wh` \| `attention_h` \| `fiat_budget` |
| `period` | `session` \| `month` \| `lifetime` |
| `cap` | Granted or substrate ceiling |
| `spent` | Sum of spend events in the open period |
| `remaining` | `cap - spent` (v0 forbids overdraft) |
| `source` | `owner_grant` \| `substrate` \| `provider_limit` |
| `grant_id` | Optional jurisdiction grant that set or last changed the cap |
| `period_started_at` / `period_ends_at` | Open period bounds |
| `revision` | Monotonic |
| `updated_at` | Last projection write |

Empty envelope is allowed at birth. Default v0: no silent spend if no envelope
exists for that unit.

## Scarcity events (append-only journal)

| Field | Meaning |
|---|---|
| `event_id` | UUID |
| `identity_id` | Whose envelope moved |
| `envelope_id` | Projection row |
| `unit` | Same as envelope |
| `kind` | `spend` \| `grant` \| `refill` \| `period_reset` \| `compensate` |
| `delta` | Signed. Spend is negative. Grant/refill/compensate are positive |
| `cap_after` / `remaining_after` | Projection snapshot after apply |
| `actor_identity_id` | Who authorized the move |
| `space_id` | When membrane applies |
| `receipt_id` | Geometry Receipt or Apply Receipt |
| `grant_id` | Optional |
| `path_note` | Unbound owned label |
| `path_id` | Only if an aspect_id already exists |
| `details_json` | Canonical extras |
| `created_at` | UTC RFC3339 |

Invariants:

- Spend without envelope for that unit is rejected (no implicit create).
- Spend that would make `remaining < 0` is rejected in v0.
- `compensate` references the original `event_id` in `details_json`.
- Rebuild of `spent` / `remaining` is the ordered sum of events in the period.
- Spend does not create aspects, fibers, or Stem direction.

## Preference

See `docs/preference.md`. Declared = Vision Gradient on `stem_state`.
Revealed = slope of `stem_revisions`, later plus spend.
Do not wait for a fiber table.

## Geometry Receipt additions

Optional block on `geometry_receipts` JSON:

```text
scarcity_spent:
  unit, delta, remaining_after, envelope_id, event_id, path_note

opportunity_forgone:
  path_note, note    # qualitative in v0; not a second ledger
```

## Ownership and gates

| Operation | Who |
|---|---|
| Set / raise cap | Owner or `grant_admin` over the Identity |
| Spend | The Identity itself under its Surface, within cap |
| Compensate | Owner or `residual_emergency` / `grant_admin` |
| Change declared Stem direction | Owner via Mature |
| Read own envelope / readout | The Identity |
| Read another's envelope | Explicit grant only |

Envelope is not Mass. Cap size never writes `emergent_self_mass`.

## Explicit non-goals (Phase 0)

- Currency-Identity, IE-token, fiat onramp, chain
- Market, Competition, Specialization product surfaces
- Attention auction UI
- Self-declared Price as Mass
- Rewriting history for rollback
- Treating `fiat_budget` as legal money movement
- Auto-updating Vision Gradient from spend or slope
- A fibers[] projection as a prerequisite

## Exit criteria

- [ ] #118 Stem lock merged or accepted
- [ ] This envelope contract reviewed as a later slice
- [ ] `path_note` only until aspects exist
- [ ] Rebuild of envelope from events demonstrated
- [ ] No Mass write from cap or spend
