# Particles as the current Stem snapshot

Status: **working reading of a proposal layer** (2026-08-29)
Not Core Concept law. Canonical lock: `docs/stem.md`.
Framework source: Space page + [Particles of Identity](https://identity-engineering.org/blog/particles-of-identity).

This document exists so Particles is not rebuilt as a parallel geometry.
It does not introduce a table, a CLI world, or a YAML store.

## Claim

Particles are `stem_state` read as framework `x(t)`.

At one moment the Stem is an arrangement of bound degrees of freedom.
That arrangement is already persisted. Naming it "Particles" does not
create a second object.

## Hierarchy (engineering order)

```text
Space        configuration arena; degrees of freedom are born
Particles    bound configuration at t = current stem_state
Time         motion of that configuration; stem_revisions; worldlines
Mass         densification around the already moving Stem
```

Rebuild of a store is not Time. Retrospective interpretation is Mature.

## Persist versus derive

| Need | Mechanism |
|---|---|
| What is bound now | Read `stem_state` |
| How binding moved | Read `stem_revisions` |
| Owner names an aspect and its binding | Optional Mature write into `substance_json` |
| Peer observes tightness | Receipt observation only |

No `particles` table. No `particles_revisions`. History is Stem history.

Optional authorship shape, only if the owner names aspects:

```text
stem_state.substance_json.aspects[]
  aspect_id           # stable under rename
  label               # owned name
  binding             # confined | loose | unbound
  extract_cost_note   # what breaks if removed
  formed_from         # optional trajectory_entry_id / prior mature_id
```

`confined` is the Strong-Binding claim. `unbound` is still Space, not yet
in the Particle. Mature may promote unbound → loose → confined. Interact
may only observe.

An Identity may have zero named aspects. Then `x(t)` is Differential +
Vision Gradient + substance bag. That is already a Particle snapshot.

## Time axis

| Step | Writes Particles? |
|---|---|
| Interact | No. Optional observation on the Receipt. |
| Mature | Yes, by writing `stem_state`. Aspects only if supplied. |
| `ie db rebuild-projections` | No. Replays the same snapshots. |

## What a Particle is not

- Not another Identity. Account ≠ Identity still holds.
- Not a Metric Stem dimension (those classify others).
- Not a Fiber. A Fiber is one aspect through snapshots, derived later.
- Not Mass. Binding can be tight with little stake.
- Not Preference. Ranking needs a curve, not only a slice.

Charge, Current, Fields, Identity Chemistry stay out.

## Exit criteria

- [ ] `docs/stem.md` accepted as the parent lock
- [ ] No separate Particles runtime module required for v0
- [ ] Status readout can present `stem_state` as `x(t)`
- [ ] Named aspects remain optional Mature authorship
