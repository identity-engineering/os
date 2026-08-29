# Preference as Stem

Status: **Phase 0 contract** (2026-08-29)
Product path: **IE-managed Space first**. Same logical readout on Local Space.
Not a ranking table. Not Market. Not Price.

Related: `docs/scarcity-preference.md`, `docs/mature.md`, `docs/metric-stem.md`,
`schemas/preference/v0.yaml`, `schemas/geometry-receipt/v0.yaml`,
framework Economics Preference + Physics Frequency / Stem.

## Claim

Preference is the Stem read in the Now.

The Stem is a bundle of fibers. Past trajectory shapes those fibers
(State Differential, narrative frequency, σ_past). In the Now each fiber has
a direction. Vision Gradient pulls on the bundle (σ_future). Which fibers
hold, yield, or commit under that pull *is* Preference.

Economics does not invent a second faculty. Under Scarcity the same fibers
must be ranked because the envelope cannot fund all of them at once.
Declared Preference without spend is Vision copy. Revealed Preference is
spend on a named fiber.

## Locked decisions

1. No source-of-truth `preferences` table. Source is Stem + Trajectory +
   Scarcity events.
2. Fibers are named paths owned by the Identity (`path_id` + `label`).
   Labels are observer-owned language, not a global ontology.
3. Declared Preference is an owned weighting of fibers on `stem_state`.
   It changes only through Mature (or an explicit owner Stem write).
4. Revealed Preference is derived from `scarcity_events.kind=spend`
   grouped by `path_id` in the open period.
5. Divergence (declared vs revealed) is a readout, not an error. A Receipt
   may name it. It does not auto-rewrite the Stem.
6. Vision Gradient is the pull, not the Preference. Preference is the
   bundle's response to that pull under Scarcity.
7. Metric Stem dimensions are classification axes for *other* Identities.
   Fiber labels are allocation axes for *this* Identity. Do not collapse them.
8. Preference never writes Mass.

## Fibers

A fiber is one allocatable Stem path.

| Field | Meaning |
|---|---|
| `path_id` | UUID, stable under rename |
| `identity_id` | Owner of the bundle |
| `label` | Short owned name (e.g. `ie-framework`, `local-inference`, `rest`) |
| `declared_weight` | 0–1 relative claim on the bundle in the Now |
| `active` | Soft-retired fibers stay in history, drop out of declared ranking |
| `formed_from` | Optional `stem_revision_id` or `trajectory_entry_id` |
| `last_sharpened_at` | Last Mature that touched this fiber |
| `note` | Optional owned gloss |

Weights of active fibers should sum to 1 when any declared ranking exists.
If they do not, the readout normalizes and flags `weights_unnormalized`.

Birth: an Identity may have zero fibers. Then there is no declared Preference.
Spend still requires a `path_note`; the first spend may *propose* a fiber,
but creating it is a Stem/Mature write, not a silent side effect of spend.

## Where it lives (existing surfaces)

| Layer | Role |
|---|---|
| `stem_state.substance_json.fibers[]` | Current declared bundle (projection) |
| `stem_revisions` | How the bundle changed |
| `trajectory_entries` | When a fiber formed or turned |
| Header / Surface vision gradient | Current pull (σ_future), not the ranking |
| Geometry Receipt `stem_differential` | Observed reaction in this Act |
| Scarcity event `path_id` / `path_note` | Revealed commitment |
| Receipt `opportunity_forgone.path_note` | Named fiber not funded |

`path_note` on events should resolve to `path_id` when the fiber exists.
Unresolved notes are allowed in v0 and listed as `unbound_path_notes`.

## Readout (derived, not stored as truth)

```text
declared[path]  = fiber.declared_weight          # active fibers, Now
revealed[path]  = |spend_delta| / sum(|spend|)   # open period, same unit
divergence[path] = revealed[path] - declared[path]
```

A Preference readout payload (CLI/MCP, storage-agnostic):

```text
preference_readout
  identity_id
  as_of
  period
  unit                    # unit used for revealed; omit if no spend
  fibers[]                # path_id, label, declared_weight, revealed_weight, divergence
  weights_unnormalized    # bool
  unbound_path_notes[]    # spend notes that did not resolve
  vision_gradient         # current pull text / last_sharpened
```

Rebuild declared from latest `stem_state`. Rebuild revealed from events.
Do not persist the readout except as a cache with `as_of`.

## Loop

1. Session loads Stem fibers + Vision Gradient + envelopes.
2. Proposed Act names `path_id` (or `path_note`) + scarcity unit/delta.
3. Receipt records `stem_differential` (did this Act follow or fight the pull)
   and optional `opportunity_forgone` (which fiber was not funded).
4. Spend commits against that path. Revealed weights move. Declared weights
   do not move unless Mature says so.
5. Mature may reshape fibers: new label, reweight, retire, attach
   `formed_from` to a trajectory entry. That is Preference authorship.

Reaction to Vision Gradient is visible when `stem_differential` and the
chosen `path_id` agree or disagree with `vision_gradient.direction`.
Agreement is not required. Chronic divergence is a probe, not a lock.

## Ownership

| Operation | Who |
|---|---|
| Create / reweight / retire fiber | Owner via Mature or explicit Stem write |
| Spend against a fiber | The Identity, within envelope |
| Read own readout | The Identity |
| Read another's declared fibers | No, unless grant. Revealed spend of another is never public by default |

Foreign-Mature may *propose* a fiber interpretation in a Signal. The receiver
integrates or declines. No silent write into `stem_state.fibers`.

## Relation to Frequency / Tensor

- Fiber bundle ≈ local tension modes that can take allocation.
- Vision Gradient ≈ σ_future.
- Trajectory / narrative ≈ σ_past shaping which fibers exist.
- Divergence under spend ≈ elevated internal friction (destructive resonance
  with one's own declared direction).

This is a reading, not a new primitive.

## Explicit non-goals

- Global preference ontology
- Auto-updating declared weights from spend
- Treating Metric Stem dimensions as fibers
- Publishing Preference on the Public Card by default
- Price or Market ranking
- Preference as a substitute for Mass

## Exit criteria (Preference slice)

- [ ] Fibers live in `stem_state` (managed + Local Space mirror)
- [ ] Spend can carry `path_id`
- [ ] `ie preference` or MCP readout: declared / revealed / divergence
- [ ] Mature can add or reweight a fiber with a trajectory source
- [ ] No Mass write from weights or spend
- [ ] Dogfood: two fibers, one spend, readout shows divergence if the other was declared heavier
