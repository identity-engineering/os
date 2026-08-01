# TIM Cycle as IE Probe Modes

Working definition · 01.08.2026

## Status

TIM (Think · Interact · Mature) was previously held at arm's length: useful as an installability lesson, but not imported into IE OS because it was not yet Framework-grounded.

**Probes-as-Bridge changes that.**  
Once every Interaction is understood as measurement + potential reshape under Relativity, the three phases become the natural modes of the Probe process itself — not a foreign organism layer.

This doc pulls **only the cycle** into IE OS.  
Biology-inspired agents, Dynamic Governance, and full TIM organism patterns remain out (see `docs/principles.md` §7).

## The cycle, grounded

| Mode | IE character | Geometry target | Typical outputs |
|------|--------------|-----------------|-----------------|
| **Think** | Internal Self-Probe | Own Stem (State Differential + Vision Gradient), relative worldview | Geometry Receipt `mode=think`, `target=self` |
| **Interact** | Relational Probe | Foreign geometry via Interaction Signal; own estimates of the other | Interaction Signal + Geometry Receipt `mode=interact` |
| **Mature** | Directed Self-Probe + learning | Revue, analysis, explicit Stem evolution | Geometry Receipt `mode=mature` + optional Ownership Move |

Mature is Think with a clear Vision Gradient and an Ownership Move (commitment, jurisdiction claim).

There is no separate "question vs action" split. Under Relativity every mode is both measurement and potential reshape.

## Operational mapping (v0)

| Mode | Entry point today | Geometry Hook |
|------|-------------------|---------------|
| Interact | `apply_interaction_signal` / Surface `receive_interaction_signal` | **Always on** after non-rejected apply |
| Think | Not yet a first-class CLI op (follow-up: `ie probe think`) | Same extractor interface, `target=self` |
| Mature | Not yet a first-class CLI op (follow-up: `ie probe mature`) | Same interface + optional `ownership_move` field |

Extractors stay mode-aware only where needed; most geometry fields are shared.

## What this is not

- Not a re-introduction of TIM as a product brand.
- Not sensory / immunity / vitality / creativity / stability agents.
- Not a claim that TIM science is proven; it is an operational cycle that fits Relativity + Probes.
- Not a requirement that every human or agent names the phases explicitly. The OS can run Geometry Extraction without the user saying "I am Maturing."

## Why this is safe to pull in now

1. **Framework-grounded**: Relativity + Questions as Probes already imply continuous geometry from interaction. TIM names the natural self/other/learning split of that process.
2. **Minimal surface**: Only three mode labels on Geometry Receipt + documentation. No new organism contracts.
3. **Installability continuity**: The original TIM lesson (files that live on the next interaction) is preserved and strengthened by always-on Geometry Receipts.

## Next

1. Dogfood Interact path (already wired, default on).
2. Thin Think / Mature entry points sharing `runtime/geometry.py`.
3. Optional public framework note: TIM cycle as operational Probe modes (not a new Core Concept).

See `docs/probes-as-bridge.md`, `docs/geometry-hook.md`, `schemas/geometry-receipt/v0.yaml`.
