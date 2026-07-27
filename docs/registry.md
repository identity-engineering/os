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

## Geometry of Mass, Density and Volume (locked 27.07.2026)

- The space is the infinite-dimensional span of all discovered dimensions.
- Each Identity is an **alloy** (vector over that basis). Degree on each dimension = potential mass component.
- **Mass** = density of the alloy (relative, confidence- and interaction-depth-weighted).
- **Volume** candidate = number / weighted count of interacting Identities that estimate me (they sample my dimensions).
- Self-Mass is never self-declared. It emerges from the estimates returned by the surrounding Identities, weighted by their own Mass and interaction depth.
- I always hold my estimates of the densities around me; I also receive their estimates of me and (when shared) their own emergent Mass. This gives rich information for both self and other.
- Open: whether density still needs an explicit depth / intensity parameter in the dimension structure.
- Open: the exact balance between what I estimate of the surrounding vs. what I receive via signal (to be fixed in the interaction contract).

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
2. Live derivation rules for multi-dimensional distance, density aggregation and tension
3. Dimension-discovery and optional cross-Identity propagation mechanics
4. Clarification of density depth/intensity parameter (if needed)
5. The still-open physical analog for how dimensional alloys produce Curvature

See also: `schemas/registry/v0.yaml`, `docs/tensor.md` and Issue #7.
