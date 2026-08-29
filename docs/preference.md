# Preference as Stem direction in the Now

Status: **corrected reading** (2026-08-29)
Canonical lock: `docs/stem.md` on `feature/stem-as-xt-foundation` (PR #118).
Do not merge this economics branch ahead of that lock.

Not Market. Not Price. Not a ranking table. Not a `fibers[]` prerequisite.

## Claim

Preference is the Stem read as direction under finite sampling.

```text
stem_revisions[t-n … t]     samples of x(t)
slope                       revealed direction
vision_gradient             declared pull / extrapolation
Frequency                   sampling rate and tension of that slope
Preference                  which directions win when not all can be sampled
```

Same pattern as the living Tensor: persist samples, derive the reading.
There is no source-of-truth `preferences` table and no fiber ledger required
before a Stem exists.

## What changed from the earlier draft on this branch

- Dropped `path_id` fibers with `declared_weight` as a Stem projection.
- Revealed Preference is first the slope of recent Mature snapshots.
  Spend may later join that reading. Spend does not invent fibers.
- `path_note` is unbound language until Mature names an aspect.
- YAML documents shape. It is not the store.

## Locked decisions

1. Declared Preference = Vision Gradient plus any owner-named direction
   on the current `stem_state`. Mature only.
2. Revealed Preference = slope of recent `stem_revisions` (and later spend
   if an envelope exists).
3. Divergence is a Probe. It does not auto-rewrite Stem.
4. Metric Stem dimensions are not Preference axes.
5. Preference never writes Mass.
6. Scarcity is a cap, not Stem geometry. Envelope work on this branch may
   resume with `path_note` only after #118.

## Readout

```text
preference_readout
  identity_id, as_of, window
  declared                  # vision_gradient + named directions
  revealed                  # slope in the window
  divergence                # qualitative in v0
  sample_count              # flag if too few revisions
  tension                   # optional last Receipt tension_components
```

v0 honesty: the Stem is still three prose fields plus a bag. Do not fake
a numeric slope.

## Exit

Rebase or park this PR behind #118. Scarcity envelope tables can stay as a
later slice. Preference-as-fiber-weights cannot.
