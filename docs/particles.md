# Particles as configuration at t

Status: **working operationalization of a proposal layer** (2026-08-29)
Not Core Concept law. Framework source: Space page + [Particles of Identity](https://identity-engineering.org/blog/particles-of-identity).
Product path: IE-managed first; same logical snapshot on Local Space.

Related: `docs/space-model.md`, `docs/mature.md`, `docs/probe-cycle.md`,
`schemas/particles/v0.yaml`, framework `/framework/space`, `/framework/time`.

## Why this exists

The Identity Stem is a temporal object. Before a line exists there is only an
arrangement: bound degrees of freedom at one moment. That arrangement is what
the framework calls **Particles**.

This contract operationalizes that slice and nothing after it. Fibers,
Preference, Scarcity sit later. They must not invent a Stem that Particles
have not yet made hold.

## Hierarchy (engineering order)

```text
Space        configuration arena; degrees of freedom are born
Particles    bound configuration at t — this document
Time         motion of that configuration; worldlines; Stem = bundle
Mass         densification around the already moving Stem
```

At a single moment the Stem is not a line. It is the Particle snapshot.
Time turns snapshots into a Stem. Rebuild of a database is not Time.

## Time axis (locked here)

| Step | What it is | What it is not |
|---|---|---|
| **Interact** | Observe the configuration. Write a Geometry Receipt. Do not rewrite Stem. | Not a Particle birth. |
| **Mature** | Owner-supplied commit of a new snapshot (`x(t)` → `x(t')`) plus Trajectory reading. Retrospective interpretation lives here. | Not an automatic inference engine. |
| **`ie db rebuild-projections`** | Storage recovery. Replay events into current tables after corruption or migration. | Not an identity-time step. Not Mature. Not a Fiber. |

If a reading of the past changes, that is Mature with sources. If the store is
rebuilt from the same events, the Identity did not move.

## Claim

A **Particle configuration** is the bound set of named aspects of one Identity
at time `t`. Strong Binding is why those aspects are one Identity rather than
a bag of free degrees of freedom.

This is the operational reading of framework `x(t)` (Time page: State as the
current cross-section of the Stem).

## What a Particle is not

- Not another Identity. Account ≠ Identity still holds; Particle ≠ Identity.
- Not a Metric Stem dimension (those classify *others*).
- Not a Fiber. A Fiber is the worldline of one aspect *through* snapshots.
- Not Mass. Binding can be tight with little stake, or loose with high stake.
- Not Preference. Ranking under Scarcity needs Time (a path) first.

## Strong Binding (operational minimum)

Framework: ultra-short-range coherence. You cannot pull the innermost aspects
apart without either failure or new disruptive pairs.

OS v0 does not compute a Strong-Force field. It records **whether the owner
treats an aspect as confined to this Identity**:

| Field | Meaning |
|---|---|
| `binding` | `confined` \| `loose` \| `unbound` |
| `extract_cost_note` | Qualitative: what breaks if this aspect is removed |

`confined` is the Strong-Binding claim. `unbound` is a free degree of freedom
in Space that has not yet entered the Particle. Mature may promote unbound →
loose → confined. Interact may only *observe* binding, never promote it.

Charge, Current, Fields stay out of v0. They are the electromagnetic layer of
the same essay. This contract stops at "why the dots hold."

## Snapshot (projection)

One current row per Identity: the Particle configuration *is* `stem_state`
read as `x(t)`, not a second geometry store.

```text
stem_state.substance_json.particles
  as_of                 # timestamp of this snapshot (Mature commit time)
  mature_id             # Mature event that authored it
  coherence             # already on stem_state; binding health of the set
  aspects[]
    aspect_id           # stable under rename
    label               # owned name (e.g. ie-front, somatic-base, craft)
    binding             # confined | loose | unbound
    extract_cost_note
    charge_note         # optional qualitative polarity; no numeric q in v0
    formed_from         # optional trajectory_entry_id / prior mature_id
```

`stem_revisions` already snapshot the whole `stem_state`. That *is* the history
of Particle configurations. No `particles_revisions` table.

Birth: an Identity may have zero named aspects. Then `x(t)` is only Differential
+ Vision Gradient text. Naming aspects is Mature authorship, not a side effect
of Interact or Spend.

## Loop

1. Session reads current `stem_state` as Particle snapshot + Vision Gradient.
2. Interact produces a Receipt. Optional observational block:
   `particle_observation` (which aspects felt confined / loose / unbound).
   No write to `substance_json.particles`.
3. Mature, with sources, may add / rebind / retire aspects and must write a
   new `as_of`. That commit *is* the new `x(t)`.
4. Trajectory entry points at that Mature event. The Stem grows as the sequence
   of snapshots, not as a rebuild.

## What comes after (not this contract)

```text
aspect at t                 Particle (this doc)
aspect through snapshots    Fiber / worldline          — later
bundle of worldlines        Identity Stem (Time)       — already named, not fully schema'd
ranking of fibers under cap Preference                 — parked until Fiber exists
finite envelope             Scarcity                   — separate Phase 0 PR
```

Do not put `path_id` on scarcity events until an aspect_id exists that Mature
has named. Until then `path_note` is an unbound label.

## Ownership

| Operation | Who |
|---|---|
| Name / rebind / retire an aspect | Owner via Mature |
| Observe binding in a Receipt | Any Act of this Identity |
| Read own snapshot | The Identity |
| Read another's aspects | Grant only |

Strong Binding is owner-authored. A peer Signal may *propose* an observation.
Foreign-Mature does not rewrite `particles`.

## Explicit non-goals (v0)

- Numeric Charge `q`, Current, radiation, Identity Chemistry
- Fiber table, Preference readout, Scarcity coupling
- Treating rebuild-projections as Mature
- Auto-clustering aspects from text
- Promoting Particles to Core Concept by this OS doc alone

## Exit criteria

- [ ] This contract reviewed
- [ ] `substance_json.particles` accepted as the snapshot shape
- [ ] Geometry Receipt optional `particle_observation`
- [ ] One Mature dogfood: name two aspects, one `confined`, one `loose`
- [ ] Rebuild of store does not create a third aspect or a new `as_of`
