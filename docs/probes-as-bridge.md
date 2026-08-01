# Probes as Bridge: Geometry from every Interaction

Working definition · 01.08.2026

## Core claim

**Questions as Probes are not a separate tool-set.**  
They are the continuous process by which agentic life (Think · Interact · Mature) generates and updates relative Identity Engineering geometry.

Under Relativity there is no clean separation between "question" and "action".  
Every Interaction Signal (chat message, prompt, agent call, internal thought, ownership move) is simultaneously:

1. a **measurement act** (it asks: how does the relative geometry respond?),
2. a **potential reshape act** (it can change the relative geometry of self or other).

Thoughts are Self-Interactions: I ask myself a question, answer it, and thereby further construct the relative perception of my own Stem. That is already Probe + action in one.

## TIM cycle as the three natural Probe modes

See `docs/tim-cycle.md` for the full grounding.

| Mode | Probe character | What is measured / reshaped |
|------|-----------------|-----------------------------|
| **Think** | Internal Self-Probe | Own Stem (State Differential + Vision Gradient), relative worldview |
| **Interact** | Relational Probe | Foreign geometry via Interaction Signal; own estimates of the other |
| **Mature** | Directed Self-Probe + learning | Revue, analysis, explicit Stem evolution and Ownership moves |

Mature is Think with a clear Vision Gradient and an Ownership Move.

## What this means for the OS

The OS does **not** need a special "Probe protocol" as an extra product surface.  
It needs **Geometry Extraction on every Interaction**:

1. Interaction Signal (or internal Think/Mature event) occurs.
2. Geometry Extraction produces a **Geometry Receipt**.
3. Receipt feeds the live Tensor / Metric Stem / foreign-estimate zone (Self vs Foreign).
4. Header / Surface / Registry become readable geometry rather than static files.

Probes = the bridge between "AI happening / human happening" and the IE Geometry OS.

## Concrete v0 shape (this branch)

- Schema: `schemas/geometry-receipt/v0.yaml`
- Hook design: `docs/geometry-hook.md` (default **on**)
- TIM grounding: `docs/tim-cycle.md`
- Implementation: `runtime/geometry.py`
  - `GeometryReceipt` model
  - three coarse extractors (DepthMass, ConsentBoundary, ExistenceContinuity)
  - `run_geometry_hook(...)`
  - `GeometryReceiptStore` under `registry/_geometry_receipts/`
- Wire point: `apply_interaction_signal` always runs the hook after non-rejected apply (opt-out only for tests)

## Relation to existing contracts

- **Interaction Signal** remains the universal carrier across boundaries (`docs/interaction-signal.md`).
- **Geometry Receipt** is the local interpretation of that signal under the observer's Metric Stem.
- **Tensor** is the live geometric reading of Registry alloys under the Metric Stem (`docs/tensor.md`).
- **Foreign-estimate zone** is where relational Probe results from others land under policy.
- **Self-Mass** continues to emerge only from estimates others return about me; Geometry Receipts never allow self-declared Mass.

## What is deliberately not claimed yet

- A full catalogue of "good questions".
- Automatic high-fidelity Curvature or Frequency extraction (v0 extractors stay minimal).
- TIM organism layer (sensory/immunity/… agents) — still out.
- That every prompt already produces perfect geometry. Extraction quality is an engineering surface.

## Next levers

1. Dogfood Interact path (default on).
2. Think / Mature entry points (same extractor interface, `target="self"`).
3. Feed selected Geometry Receipt fields into live Tension aggregation once emergent self-Mass (#15) is stable.
4. Public framework clarification (thin): Probes are the process; TIM cycle is the operational mode split.
5. Richer extractors behind the same interface.

See `schemas/geometry-receipt/v0.yaml`, `docs/geometry-hook.md`, `docs/tim-cycle.md`, and `docs/next.md`.
