# Local Registry

The Registry is the observing Identity's local perception of space — both gravitational sensor and carrier of its high-dimensional classification space.

It answers:
- What Identities have I noticed?
- How do I identify them again across frames and sessions?
- What is my relative Mass estimate of each?
- Along which contentful dimensions do I locate them, and with what confidence?
- How does this Mass sit and pull in *my* frame?
- What do I allow to be shared about this perception?

## Relativity & living Tensor core

- Everything is measured from the observer's frame.
- Mass only becomes visible in relation.
- The open `dimensions[]` array *is* the living high-dimensional Tensor.
- These dimensions describe the material substance and character of Mass (the "material science" of Mass), not the abstract framework primitives.
- Dimensions are discovered through interaction and Questions as Probes; they are not a fixed ontology.
- When a new dimension is discovered, the observer may evaluate its relevance for already known Identities → the world-view expands and old entries can be re-framed.
- Each dimensional assessment carries its own confidence.
- Multi-dimensional distance (to self and between Identities) and overall tension are **derived dynamically** from the whole Registry. They are not stored as primary persistent state.
- Curvature of the possibility space will later be derived from the Mass distribution + this dimensional metric. The precise physical analog (how material differences produce curvature) remains an open requirement of the IE tension experience.

## Design decisions (v0)

- **Single file per Identity** under `templates/personal/registry/{local_handle}.yaml`
- `local_handle` is observer-owned and persistent inside this Registry
- All quantitative fields are relative (`my_mass_estimate`, dimensional values, …)
- Privacy defaults are structural and default to minimal sharing
- Multi-substrate from day 1 via the `substrate` field
- No separate persistent Tensor file

## Key sections in each entry

| Section | Purpose |
|---------|---------|
| Core identity | handle, name, substrate, description |
| Interaction | depth, count, last_interaction |
| Mass (relative) | my_mass_estimate + overall confidence |
| Dimensions (living Tensor) | open, contentful axes with per-dimension confidence |
| Relation | pull, resonance, frame_distance, asymmetry |
| Recognition | method, confidence, alternative handles |
| Effect on me | how this Spec currently contributes to my tension |
| Perceived ownership | freedom degrees and jurisdiction I attribute |
| Privacy | what may leave my frame |

## What comes next

1. Minimal interaction signal that can update an existing entry (or propose a new one) and potentially discover / propose new dimensions
2. Live derivation rules for multi-dimensional distance and tension aggregation
3. Dimension-discovery and optional cross-Identity propagation mechanics
4. The still-open physical analog: how dimensional / material differences produce Curvature of the possibility space

See also: `schemas/registry/v0.yaml` and Issue #7.
