# Preference as Stem direction in the Now

Status: **working reading** (2026-08-29)
Canonical lock: `docs/stem.md`.
Not Market. Not Price. Not a ranking table.

Parent physics: Frequency (sampling / tension in the Now).
Economics lens supplies Scarcity as a later cap, not the geometry.

## Claim

Preference is the Stem read as direction under finite sampling.

```text
stem_revisions[t-n … t]     samples of x(t)
slope                       revealed direction
vision_gradient             declared pull / extrapolation
Frequency                   sampling rate and tension of that slope
Preference                  which directions win when not all can be sampled
```

This is the same pattern as the living Tensor: a live reading of persisted
samples. There is no source-of-truth `preferences` table.

## Locked decisions

1. Declared Preference lives on the current snapshot: Vision Gradient
   text plus any owner-named direction in `substance_json`.
   It changes only through Mature.
2. Revealed Preference is derived from the slope of recent
   `stem_revisions` (and, later, scarce spend if an envelope exists).
3. Divergence is a readout and a Probe. It does not auto-rewrite Stem.
4. Vision Gradient is the pull, not the Preference. Preference is the
   bundle's response to that pull when sampling time is finite.
5. Metric Stem dimensions classify *other* Identities. They are not
   Preference axes.
6. Preference never writes Mass.
7. No `path_id` until Mature has named an aspect. Until then `path_note`
   is unbound language.
8. YAML documents the readout shape if needed. It is not the store.

## Fibers

A Fiber is the worldline of one named aspect through `stem_revisions`.
It is reconstructed, not stored as a second ledger.

Do not birth a fiber table so that spend has somewhere to point.
Spend may later point at an `aspect_id` that Mature already named.

## Readout (derived, not stored as truth)

```text
preference_readout
  identity_id
  as_of
  window                    # last n Mature snapshots, or time bound
  declared                  # vision_gradient + named directions
  revealed                  # slope / dominant movement in the window
  divergence                # qualitative in v0; numeric only when comparable
  sample_count              # revisions in the window; flag if too few
  tension                   # optional: last Receipt tension_components
```

Rebuild declared from `stem_state`. Rebuild revealed from revisions.
Cache only with `as_of`. Never treat the cache as law.

v0 honesty: with three prose fields on the Stem, slope is mostly
narrative continuity (which summaries keep being rewritten, which
vision shifts recur). A numeric slope waits on named aspects or on a
denser substance. Do not fake precision.

## Frequency

Frequency is the Core Concept. Preference is Frequency applied to the
Stem curve under scarcity of sampling time.

| Frequency question | Preference reading |
|---|---|
| How often is this direction sampled? | revealed weight of that movement |
| How hard does it pull in the Now? | tension on the last Receipts |
| What cannot be sampled at once? | Scarcity cap (later) |

`#73` (Frequency after denser Tensor) remains the product track for a
numeric sampler. This document does not jump that queue with a new primitive.

## Scarcity

Scarcity is an envelope on tokens / energy / attention / an owner-set
fiat counter. It is not Stem geometry. It may later make revealed
Preference include spend. It must not invent fibers in order to exist.

Economics Phase 0 stays parked until this lock is accepted. Envelope
work may resume with `path_note` only.

## Ownership

| Operation | Who |
|---|---|
| Change declared direction | Owner via Mature |
| Read own curve | The Identity |
| Read another's declared or revealed Preference | Grant only |

Foreign-Mature may propose a reading. No silent Stem write.

## Explicit non-goals

- Global preference ontology
- Auto-updating Vision Gradient from slope or spend
- Metric Stem dimensions as fibers
- Publishing Preference on the Public Card by default
- Price or Market ranking
- Preference as a substitute for Mass
- A fibers[] projection as a prerequisite for having a Stem

## Exit criteria

- [ ] Parent lock `docs/stem.md` accepted
- [ ] Readout specified against real `stem_revisions` (even if qualitative)
- [ ] No Preference table shipped
- [ ] Scarcity work, if resumed, uses `path_note` until aspects exist
- [ ] No Mass write from slope, tension, or spend
