# Local Registry

The Registry is the observing Identity's local perception of space.

It answers:
- What Identities have I noticed?
- How do I identify them again?
- What is my relative Mass estimate of each?
- What do I allow to be shared about this perception?

## Design decisions (v0)

- **Single file per Identity** under `templates/personal/registry/{local_handle}.yaml`
- `local_handle` is observer-owned and persistent inside this Registry
- No global ID is required or forced
- Mass is always relative (my estimate)
- Privacy defaults are structural and default to minimal sharing
- Multi-substrate from day 1 via the `substrate` field

## What comes next

After the Registry structure is solid:
1. Minimal interaction signal that can update an existing entry (or propose a new one)
2. How interaction_depth and my_mass_estimate are updated on interaction end
3. Recognition strategies beyond pure local_handle (shared history signatures, etc.)

See also: `schemas/registry/v0.yaml` and Issue #7.
