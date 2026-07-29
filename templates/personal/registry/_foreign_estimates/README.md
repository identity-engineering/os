# Foreign-estimate zone (local files)

This directory holds the **only** region that inbound `receive_interaction_signal` writes into by default.

- One file per sender: `{sender_handle}.yaml` (or `.json`)
- Created and updated by the Surface Runtime local apply path (`runtime/`)
- Feeds volume candidate and emergent self-Mass (derived, never self-declared)

See:

- `schemas/foreign-estimate-zone/v0.yaml`
- `docs/foreign-estimate-zone.md`
- `docs/surface-runtime-local.md`

Do not hand-edit production records unless you know the invariants. Use `python -m runtime apply` for writes.
