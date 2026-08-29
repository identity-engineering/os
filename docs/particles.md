# Particles as the current Stem snapshot

Status: **superseded as a standalone contract** (2026-08-29)
Canonical lock: `docs/stem.md` on `feature/stem-as-xt-foundation` (PR #118).
Not Core Concept law.

Do not merge this branch ahead of #118. The snapshot bag below treated
Particles as a shape that still wanted its own schema and exit criteria.
The lock is: Particles are `stem_state` read as `x(t)`. No second store.

## Claim

Particles are the current Stem configuration. Mature already persists that
row. Named aspects are optional authorship inside `substance_json`, not a
prerequisite for having a Particle snapshot.

An Identity with only Differential + Vision Gradient text already has `x(t)`.

## Persist versus derive

| Need | Mechanism |
|---|---|
| What is bound now | Read `stem_state` |
| How binding moved | Read `stem_revisions` |
| Owner names an aspect | Optional Mature `substance` write |
| Peer observes tightness | Receipt only |

No `particles` table. YAML is not mutable state.

Optional authorship, only if the owner names aspects:

```text
stem_state.substance_json.aspects[]
  aspect_id, label
  binding             # confined | loose | unbound
  extract_cost_note
  formed_from
```

Interact never writes this. Rebuild is not Time.

## What a Particle is not

Not an Identity, not a Fiber, not Mass, not Preference, not a Metric Stem
dimension.

## Exit

Close or rebase this PR after #118. Remaining work is a status readout of
`stem_state` as `x(t)`, not a Particles runtime module.
