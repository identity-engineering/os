# Stem as x(t)

Status: **operational foundation** (2026-08-29)
Canonical OS reading of the Identity Stem. Not a new Core Concept.
Framework source: Identity Stem (State Differential + Vision Gradient),
Time as worldlines, Frequency as sampling in the Now.
Particles / Space remain proposal layers on the public site.

Related: `docs/mature.md`, `docs/probe-cycle.md`, `docs/tensor.md`,
`docs/sqlite-schema-v1.md`, `runtime/mature.py` (`_apply_stem`),
`ie/status_cmd.py` (session readout of `stem_state` as `x(t)`).

## Claim

The Stem is the owned trajectory core of one Identity.

At one moment it is not a line. It is a configuration: the current
cross-section of that core. Framework language: `x(t)`. OS language:
`stem_state`.

Time turns successive configurations into a worldline. Rebuild of a
database is not Time.

## Persist versus derive

Follow the Tensor pattern already locked in `docs/tensor.md`:
there is no second source-of-truth file for a live geometric reading.

| Thing | Kind | Where |
|---|---|---|
| Current configuration `x(t)` | **Persisted projection** | `stem_state` (one row per Identity) |
| History of configurations | **Persisted snapshots** | `stem_revisions` |
| Causal learning step | **Persisted event** | `mature_events` + `trajectory_entries` |
| Particles | **Reading** of current `stem_state` | no `particles` table |
| Fiber / worldline | **Reading** of one named aspect through revisions | no fiber table in v0 |
| Preference | **Reading** of recent revisions in the Now (slope + pull) | no `preferences` table |
| Frequency | **Reading** of sampling / tension of that slope in the Now | no frequency table; `#73` later |
| Scarcity envelope | Later cap on allocation, not Stem geometry | parked until this lock holds |

YAML under `schemas/` is documentation of shape. The runtime does not
read YAML for mutable state. Managed SQL and Local SQLite carry the same
logical row. Skills stay storage-agnostic.

## What Mature actually writes today

`commit_mature` always calls `_apply_stem`. One transaction forms the Stem.

On `stem_state`:

- `state_differential_json.latest_summary` from `stem_differential.state_delta_summary`
- `vision_gradient_json.latest_shift` from `stem_differential.vision_gradient_shift`
- `coherence_json.latest_note` from `stem_differential.coherence_note`
- `substance_json` merged with any owner-supplied object
- `substance_json.last_mature` always written (`mature_id`, notes, source_ids,
  optional `ownership_move` / `optionality_delta`)
- `revision` incremented; `updated_at` / `last_mature_id` set

On history:

- full canonical snapshot into `stem_revisions`
- `mature_events` + `trajectory_entries` + Mature Geometry Receipt

The Stem is therefore already formed by Mature. What is thin is the
*structure* of that form: three prose fields plus an open substance bag.
That thinness is the next engineering problem. It is not a missing
Particles module.

Interact never writes `stem_state`. Rebuild-projections replays the same
events into the same projection. It does not create a new `as_of` in
identity-time.

## Particles (proposal-layer reading)

A Particle configuration is the bound set of degrees of freedom that
`stem_state` currently holds. Strong Binding is why those degrees belong
to one Identity rather than a bag in Space.

OS v0 does **not** compute a Strong-Force field and does **not** require
named aspects before the Stem is real. An Identity with only Differential +
Vision Gradient text already has an `x(t)`.

Named aspects (`aspect_id`, `binding: confined | loose | unbound`) are an
optional Mature authorship inside `substance_json`, not a second geometry
store. Interact may observe binding on a Receipt. Interact may not promote
it.

Particle ≠ Identity. Particle ≠ Fiber. Particle ≠ Mass. Particle ≠ Preference.

See `docs/particles.md`.

## Preference and Frequency (derived in the Now)

Preference is the Stem read as direction under finite sampling.

```text
stem_revisions[t-n … t]     discrete samples of x(t)
Δ / slope                  direction in the Now
Vision Gradient            declared pull / extrapolation
Frequency                  how often and how hard that direction is sampled
Preference                 ranking of that slope under scarce sampling time
```

Declared Preference is the Vision Gradient plus any owner-named direction
in the current snapshot. Revealed Preference is the slope of recent
Mature snapshots (and, later, scarce spend if an envelope exists).
Divergence between declared and revealed is a Probe, not an error, and
never auto-rewrites the Stem.

Do not invent `path_id` fibers before Mature has named aspects. Until
then a spend or Act may carry a `path_note`. That note is unbound language.

Frequency is the Core Concept for local sampling / tension in the Now.
Preference is not a new primitive. It is Frequency applied to the Stem
curve when not every direction can be sampled at once.

See `docs/preference.md`.

## When the information is needed

| Question | Answer from |
|---|---|
| What is this Identity made of right now? | `stem_state` (Particles reading) |
| How did that configuration move? | `stem_revisions` + `trajectory_entries` |
| Where is it pointing? | slope of recent revisions + `vision_gradient` |
| How tense / how sampled is that pointing? | Frequency reading; Receipt `tension_components` |
| What may still be allocated? | Scarcity envelope (later), not Stem |

Session start, `ie status`, Interact observation, and Mature authorship
all read the current snapshot. Allocation decisions read the curve.

`ie status` / `ie_status` expose `present` (row exists after init) and
`formed` (at least one Mature wrote a non-empty Differential, Vision, or
Coherence field). Default readout omits `substance_json`. No slope number
in v0.

## Ownership

| Operation | Who |
|---|---|
| Form / reshape `stem_state` | Owner via Mature |
| Observe configuration or slope | Any Act of this Identity (Receipt only) |
| Read own snapshot and curve | The Identity |
| Read another's Stem | Grant only |

Foreign-Mature may propose a reading in a Signal. It does not write Stem.

## Explicit non-goals

- A `particles` table, `fibers` table, or `preferences` table as source of truth
- YAML as mutable state
- Treating `ie db rebuild-projections` as Mature or as Time
- Numeric Charge, Identity Chemistry, auto-clustering of aspects
- Auto-updating Vision Gradient from spend or from slope
- Promoting Particles to a public Core Concept by this OS doc
- Marketplace, currency-identity, Price

## Exit criteria

- [x] This reading written against live `runtime/mature.py`
- [x] Contract reviewed
- [x] #117 / #116 rewritten onto this lock or closed as superseded
- [x] Status / session readout treats `stem_state` as `x(t)`
- [ ] Slope readout specified once enough revisions exist to beat noise
- [ ] Scarcity work resumes only after named aspects exist *or* explicitly
      accepts unbound `path_note` without `path_id`
