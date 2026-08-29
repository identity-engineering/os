# Scarcity envelope + Preference as Stem

Status: **Phase 0 contract** (2026-08-29)
Product path: **IE-managed Space first**. Same logical schema on Local Space.
Not a marketplace. Not a currency-identity. Not billing.

Related: framework Economics lens (Scarcity, Preference),
`docs/preference.md` (Preference operationalization),
`docs/storage-tiers.md`, `docs/account-identity-model.md`,
`docs/sqlite-schema-v1.md` (audit pattern), `schemas/scarcity-envelope/v0.yaml`,
`schemas/preference/v0.yaml`, `schemas/geometry-receipt/v0.yaml`.

## Why this exists

Every Identity allocates under a finite envelope. That envelope is measurable.
Preference is not a separate ranking table. It is the Stem read in the Now:
the direction of Stem fibers shaped by past trajectory, reacting to Vision
Gradient. Scarcity makes that direction allocatable.

Full Preference contract: `docs/preference.md`.

## Locked decisions

1. Scarcity is Identity-bound. Account is not the envelope holder.
2. Envelope units start as `tokens`, `energy_wh`, `attention_h`.
   `fiat_budget` is an owner-set counter only. No onramp, token, or chain.
3. Cap is owner-granted or substrate-given. Identity cannot declare Mass
   by inflating its envelope.
4. Preference is Stem-inherent. Declared fibers live on `stem_state`.
   Revealed Preference is spend on a fiber. See `docs/preference.md`.
5. Logging is the existing append-only event / revision / receipt journal.
   Correction is a later compensating event. History is never rewritten.
6. Backend is Space-kind: IE-managed SQL is the product host; Local Space
   mirrors the same tables in SQLite. Skills stay storage-agnostic.
7. Every mutation carries `actor_identity_id`. Add `space_id` when membrane
   applies.

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
| `remaining` | `cap - spent` (never below 0 without an explicit overdraft policy; v0 forbids overdraft) |
| `source` | `owner_grant` \| `substrate` \| `provider_limit` |
| `grant_id` | Optional jurisdiction grant that set or last changed the cap |
| `period_started_at` / `period_ends_at` | Open period bounds |
| `revision` | Monotonic |
| `updated_at` | Last projection write |

Empty envelope is allowed at birth. A runtime Identity that infers or talks
without any unit is incomplete for Economics Phase 0 once the owner enables
the lens. Default v0: no silent spend if no envelope exists for that unit.

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
| `path_id` | Optional fiber this event committed to |
| `path_note` | Short owned label; resolve to `path_id` when the fiber exists |
| `details_json` | Canonical extras (provider meter, energy Wh, token count) |
| `created_at` | UTC RFC3339 |

Invariants:

- Spend without envelope for that unit is rejected (no implicit create).
- Spend that would make `remaining < 0` is rejected in v0.
- `compensate` references the original `event_id` in `details_json`.
- Rebuild of `spent` / `remaining` is the ordered sum of events in the period.
- Spend does not create fibers. Fiber creation is Mature / Stem write.

## Preference

See `docs/preference.md` and `schemas/preference/v0.yaml`.

Declared = active fiber weights on `stem_state`.
Revealed = spend grouped by `path_id` in the open period.
Divergence = revealed minus declared. Cacheable readout only.

## Geometry Receipt additions

Optional block on `geometry_receipts` JSON (see schema):

```text
scarcity_spent:
  unit, delta, remaining_after, envelope_id, event_id, path_id, path_note

opportunity_forgone:
  path_id, path_note, note    # qualitative in v0; not a second ledger
```

A high-cost Act writes Receipt + scarcity event in one transaction.
Failed extractor must not roll back a valid spend once the event committed.
Prefer: one transaction for event + projection + receipt link.

## Loop (Phase 0)

1. Session reads Stem fibers + Vision Gradient + current envelopes.
2. Proposed Act names unit + estimated delta + `path_id` / `path_note`.
3. If envelope missing or remaining insufficient: reject or ask owner grant.
4. Commit scarcity event + envelope projection + Geometry Receipt.
5. Revealed Preference updates by derivation. Declared fibers move only via Mature.

Make-or-buy (later): compare own `opportunity_forgone` to a foreign offer.
No Price table in Phase 0.

## Ownership and gates

| Operation | Who |
|---|---|
| Set / raise cap | Owner or `grant_admin` over the Identity |
| Spend | The Identity itself under its Surface, within cap |
| Compensate | Owner or `residual_emergency` / `grant_admin` |
| Create / reweight fibers | Owner via Mature |
| Read own envelope / readout | The Identity |
| Read another's envelope or fibers | Explicit grant only |

Envelope is not Mass. Cap size never writes `emergent_self_mass`.
Fiber weights never write Mass.

## Product vs Open Core

| Surface | Host |
|---|---|
| IE-managed Space (main path) | Hosted SQL, Identity-scoped RLS |
| Local Space | Same logical tables in SQLite |
| Skills / CLI / MCP | Storage-agnostic; adapter selects backend |

Managed implementation lives in `identity-engineering/os-managed` once this
contract is accepted. Open Core may ship Local Space tables without waiting
for billing.

## Explicit non-goals (Phase 0)

- Currency-Identity, IE-token, fiat onramp, chain
- Market, Competition, Specialization product surfaces
- Attention auction UI
- Self-declared Price as Mass
- Rewriting history for rollback
- Treating `fiat_budget` as legal money movement
- Auto-updating declared fiber weights from spend

## Exit criteria for Phase 0

- [ ] This contract reviewed
- [ ] Logical tables accepted (managed + Local Space mirror)
- [ ] Geometry Receipt optional blocks in schema
- [ ] Preference fibers + readout (`docs/preference.md`)
- [ ] One dogfood path: owner sets token cap; one Act spends on a fiber; receipt + event visible
- [ ] Rebuild of envelope from events demonstrated
- [ ] No Mass write from cap, spend, or fiber weights
