# Header — always-on entry point

Locked direction 27.07.2026 (Issue #14 / feature/header-v0)

## Role

The Header is the **door** to a living Identity install.

1. At **session start**, every agent or tool reads the Header.
2. During the session, work happens against Registry, Metric Stem, and (later) Trajectory/Stem.
3. At **session end**, an Interaction Signal is written (see `docs/interaction-signal.md`).

The Header does **not** store alloys, full Mass vectors, or tension state. Those live in the Registry or are derived live.

## What must be present (v0)

| Block | Purpose |
|-------|---------|
| `identity` | Who this install is (`local_handle`, optional preferred name) |
| `substrate` | human / runtime / … (multi-substrate from day 1) |
| `paths` | Where Registry, Metric Stem, Trajectory, Stem files live |
| `state_differential` | Anchors for observed change (past → now) |
| `vision_gradient` | Anchors for intended direction (now → future) |
| `privacy` | Session-relevant defaults aligned with the Signal contract |
| `schema_version` | "0" |

## What is deliberately absent

- Open `dimensions[]` alloys → Registry
- Metric g_ij → Dimension Catalogue / Metric Stem
- Emergent self-Mass aggregation → derived from received signals
- Full tension tensor state → derived live
- Rich trajectory history → Trajectory-Log (later)

## Agent contract (minimal)

An IE-aware agent must:

1. **Read** `HEADER.yaml` (or equivalent) at start.
2. Respect `privacy.*` when emitting any Signal.
3. Use `paths.*` to find Registry and Metric Stem if it needs relative geometry.
4. At end, emit at least the **always-passed** Interaction Signal fields (`existence`, `interaction_depth_delta`, addressing).

It should **not** require the full geometric stack to start a useful session — only the Header.

## Relation to Stem

`paths.stem` may point at a placeholder `STEM.yaml` until Stem Schema v0.1 lands. The Header remains valid without a finished Stem.

## Files

- Schema: `schemas/header/v0.yaml`
- Template: `templates/personal/HEADER.yaml`
- Signal: `schemas/interaction-signal/v0.yaml`, `docs/interaction-signal.md`
- Registry: `schemas/registry/v0.yaml`, `docs/registry.md`
