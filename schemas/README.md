# Schemas

Language-neutral shape notes for IE contracts. They are documentation.

Canonical mutable state lives in the database (Local SQLite or managed SQL).
The runtime does not read these YAML files to decide what to persist.
See `docs/sqlite-schema-v1.md` and `docs/stem.md`.

Present contract files under this tree (v0):

- `header/` — public entry fields
- `interaction-signal/` — cross-membrane signal
- `estimate-request/` — inbound / outbound estimate ask
- `foreign-estimate-zone/` — observer-local estimate projection
- `geometry-receipt/` — Probe product after Interact / Mature
- `registry/` — observer alloys
- `dimension-catalogue/` — Metric Stem basis
- `surface-operations/` — Surface verbs
- `messaging/` — transport notes

Do not add a `particles`, `fibers`, or `preferences` schema as if it were a
store. Those are readings of `stem_state` / `stem_revisions` (`docs/stem.md`).
