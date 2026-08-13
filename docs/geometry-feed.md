# Geometry Receipt → Tension / Tensor / Registry feed

Status: **v0 implemented** (hook + explicit) · OS #8

Related: `docs/tensor.md`, `docs/geometry-hook.md`, `docs/probes-as-bridge.md`,
`docs/effective-freedom.md`, `docs/geometry-feed-delivery.md` (#44),
issue #8, issue #44 (delivery modes)

## Core claim

Geometry Receipts are already written after Interact (and later Think/Mature).
They are local audit + probe artifacts. The **feed** is the continuous,
ownership-gated write-back that turns those artifacts into live geometry:

- Registry alloys / effect_on_me (contentful signal of peer impact)
- derived Tension aggregate (tension_sum from components)
- later: Metric Stem discovery and Effective Freedom ratio

Without the feed the Surface is a sensor; with the feed it becomes metabolism.

## What may flow (v0 matrix)

| Receipt field / extractor | Sink | Gate | Notes |
|---------------------------|------|------|-------|
| relative_mass_proxy / interaction_density | Registry `effect_on_me_json` | owner | observational snapshot + tension_sum; revisioned |
| existence / continuity notes | already on Registry via signal path | owner | no double-write |
| Membrane policy observation | observational only | — | never becomes Access/Jurisdiction claim |
| derived Effective Freedom | live readout + optional profile | owner | deferred (needs continuous probe inputs) |
| new dimension candidates | Metric Stem catalogue | owner explicit | not auto-promoted in v0 |

Self-Mass remains **never** written from a self Geometry Receipt.

## Delivery modes

Field→sink mapping is this file. **How** the feed is delivered (hook / explicit /
adapter / none), honesty rules, capability declaration, and the harness adapter
sequence are specified in **`docs/geometry-feed-delivery.md`** (OS #44).

| Mode | Status |
|------|--------|
| **hook** | shipped — after successful apply + persist |
| **explicit** | shipped — `ie geometry feed` |
| **adapter** | contract locked — harness sequence in delivery doc |
| **none / lagging** | supported via no-DB or opt-out `emit_geometry_receipt=False` |

Local status: `geometry_feed: hook` (implies explicit available).

## Implementation (v0)

- `runtime/geometry_feed.py` — `feed_receipt`, `feed_pending`, `feed_capability`, `feed_modes_available`
- Schema migration 5 — `geometry_receipts.fed_at` for idempotency
- Hook wired in `runtime/apply.py` (best-effort; never fails apply)
- CLI: `ie geometry feed [--receipt-id | --all] [--force]`
- Status: `geometry_feed: hook`

## Ownership & non-goals

- Feed writes are owner-gated (local Identity).
- No path from Receipt into Stem / Vision / access-policy mutation.
- No self-declared Mass.
- No forced cross-Identity estimation.
- No silent promotion of Access/Jurisdiction into Metric Stem dimensions.

## Exit criteria

- [x] Design doc (this file)
- [x] Capability declaration on status: `geometry_feed: hook`
- [x] Explicit CLI path `ie geometry feed` (idempotent)
- [x] Hook path after Interact remains best-effort and never fails apply
- [x] Tests for write path + idempotent re-feed
- [x] Linked from `docs/next.md`, `docs/tensor.md`
- [x] Delivery modes contract (#44) in `docs/geometry-feed-delivery.md`

## Related

- Issue #8
- Issue #44 (delivery modes)
- `docs/geometry-feed-delivery.md`
- `docs/tensor.md`
- `docs/geometry-hook.md`
- `docs/effective-freedom.md`
