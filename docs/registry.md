# Local Registry

The Registry is the observing Identity's local perception of space — the gravitational sensor of recognized Masses.

It answers:
- What Identities have I noticed?
- How do I identify them again across frames and sessions?
- What is my relative Mass estimate of each?
- How does this Mass sit and pull in *my* frame?
- What do I allow to be shared about this perception?

## Relativity core

- Everything is measured from the observer's frame.
- Mass only becomes visible in relation.
- Each newly recognized Mass creates a Spec inside the observer that feeds back into the Tension Tensor.
- The relation (the edge) is first-class, not only the other Identity.
- No global ID is required. Re-identification is solved locally (handle + shared history + confidence).

## Design decisions (v0)

- **Single file per Identity** under `templates/personal/registry/{local_handle}.yaml`
- `local_handle` is observer-owned and persistent inside this Registry
- All quantitative fields are relative (`my_mass_estimate`, `relation.pull`, …)
- Privacy defaults are structural and default to minimal sharing
- Multi-substrate from day 1 via the `substrate` field

## Key sections in each entry

| Section | Purpose |
|---------|---------|
| Core identity | handle, name, substrate, description |
| Interaction | depth, count, last_interaction |
| Mass (relative) | my_mass_estimate + confidence + dimensions |
| Relation | pull, resonance, frame_distance, asymmetry |
| Recognition | method, confidence, alternative handles |
| Effect on me | how this Spec currently contributes to my tension |
| Perceived ownership | freedom degrees and jurisdiction I attribute |
| Privacy | what may leave my frame |

## What comes next

1. Minimal interaction signal that can update an existing entry (or propose a new one)
2. How `interaction_depth`, `my_mass_estimate` and `relation.pull` are updated on interaction end
3. Stronger recognition strategies (shared history signatures, etc.)

See also: `schemas/registry/v0.yaml` and Issue #7.
