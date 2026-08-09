# Geometry Receipt → Tension / Tensor / Registry feed

Status: design lock (v0) · opens implementation of OS #8

Related: `docs/tensor.md`, `docs/geometry-hook.md`, `docs/probes-as-bridge.md`,
`docs/effective-freedom.md`, issue #8, issue #44 (delivery modes)

## Core claim

Geometry Receipts are already written after Interact (and later Think/Mature).
They are local audit + probe artifacts. The **feed** is the continuous,
ownership-gated write-back that turns those artifacts into live geometry:

- Registry alloys (contentful dimensions of peers / self aspects)
- Metric Stem (observer basis + sparse g_ij when discovery warrants)
- derived Tension aggregate
- derived Effective Freedom ratio

Without the feed the Surface is a sensor; with the feed it becomes metabolism.

## What may flow (v0 matrix)

| Receipt field / extractor | Sink | Gate | Notes |
|---------------------------|------|------|-------|
| relative_mass_proxy / interaction_density | Registry peer alloy (depth / continuity) | owner or grant | already partially continuous via Interact projection; feed makes it explicit and versioned |
| existence / continuity notes | Registry continuity projection | owner | no silent overwrite of owned estimates |
| Membrane policy observation | observational only | — | never becomes Access/Jurisdiction claim (see #40 / #61) |
| derived Effective Freedom | live readout + optional profile | owner | computed from Access/Jurisdiction probes + constraint intensity; see `docs/effective-freedom.md` |
| new dimension candidates | Metric Stem catalogue (discovery) | owner explicit | never auto-promoted |

Self-Mass remains **never** written from a self Geometry Receipt. It continues to emerge only from foreign estimates (`docs/mass.md`).

## Delivery modes (from #44)

| Mode | When | Quality |
|------|------|---------|
| **hook** | after successful `apply_interaction_signal` | best: Interact → Receipt → feed in one path |
| **explicit** | `ie geometry feed` / batch | idempotent, re-runnable |
| **adapter** | session-end harness | works without kernel hooks |
| **none / lagging** | zone only | sensor lives; Tensor feed deferred |

v0 ships **hook + explicit**. Adapter contract is documented only.

## Ownership & non-goals

- Feed writes are owner-gated (local Identity) or grant-scoped once multi-Identity lands.
- No path from Receipt into Stem / Vision / access-policy mutation.
- No self-declared Mass.
- No forced cross-Identity estimation.
- No silent promotion of Access/Jurisdiction into Metric Stem dimensions.

## Exit criteria (this issue / PR sequence)

- [ ] Design doc (this file) on main
- [ ] Capability declaration on status / local entry: `geometry_feed: hook | explicit | adapter | none`
- [ ] Explicit CLI path `ie geometry feed` (idempotent)
- [ ] Hook path after Interact remains best-effort and never fails apply
- [ ] Tests for at least one write path + one read of derived Tension / Effective Freedom
- [ ] Linked from `docs/next.md`, `docs/tensor.md`, `docs/geometry-hook.md`

## Implementation order (after design lands)

1. Schema / status surface for feed capability
2. Explicit feed command + library entry (`runtime/geometry_feed.py` or extension of `runtime/geometry.py`)
3. Wire hook (default on, opt-out for tests)
4. Derived Effective Freedom readout
5. Adapter sequence note for chat/agent harnesses

## Related

- Issue #8 (this work)
- Issue #44 (delivery modes)
- `docs/tensor.md` — Tensor is live reading, not a separate file
- `docs/geometry-hook.md` — Receipt production (already shipped)
- `docs/effective-freedom.md` — derived ratio
- `docs/next.md` — #8 is the current top lever
