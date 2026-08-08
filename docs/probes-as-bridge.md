# Probes as Bridge: Geometry from every Interaction

Working definition · 01.08.2026  
Updated 02.08.2026 — honest storage vs feed path; Mass source order

## Core claim

**Questions as Probes are not a separate tool-set.**  
They are the continuous process by which agentic life (Think · Interact · Mature) generates and updates relative Identity Engineering geometry.

Under Relativity there is no clean separation between "question" and "action".  
Every Interaction Signal (chat message, prompt, agent call, internal thought, ownership move) is simultaneously:

1. a **measurement act** (it asks: how does the relative geometry respond?),
2. a **potential reshape act** (it can change the relative geometry of self or other).

Thoughts are Self-Interactions: I ask myself a question, answer it, and thereby further construct the relative perception of my own Stem. That is already Probe + action in one.

## TIM cycle + living-form lens

See `docs/tim-cycle.md` (discipline cross) and `docs/living-form.md` (cell / organism perspective).

| Mode | Probe character | What is measured / reshaped |
|------|-----------------|-----------------------------|
| **Think** | Internal Self-Probe (inside the membrane) | Own Stem, relative worldview |
| **Interact** | Relational Probe (across the membrane) | Foreign geometry via Interaction Signal |
| **Mature** | Directed Self-Probe + learning | Integrate new reality; Ownership Move |

Identity is the living operative form (Surface as membrane, Geometry Receipt as metabolic product).  
An agentic loop may be nuclear machinery *inside* that form — it is not the Identity.

## What this means for the OS

Geometry Extraction on every Interaction:

1. Interaction Signal (or internal Think/Mature event) occurs.  
2. Geometry Extraction **writes a local Geometry Receipt** into the SQLite table
	`geometry_receipts`, linked to `geometry_receipt_sources`.
3. Interact also updates the accepted Registry continuity projection in the same
	transaction; Geometry remains an audit/probe interpretation, not a silent
	rewrite of owned estimates.
4. Mature is the explicit owner-controlled path for Stem, Workspace, Registry,
	and Trajectory learning changes. Continuous derived Tensor/Tension feed is
	still tracked as **OS #8**.
5. Local entry / Surface / Registry are projections over the DB, not mutable
	YAML files.

Probes = the bridge between "AI happening / human happening" and the IE Geometry OS.  
Storage of the bridge artifact is shipped; continuous write-back into the Tensor is the next heartbeat.

## Concrete V1 shape (this branch)

- Schema: `schemas/geometry-receipt/v0.yaml`  
- Hook: `docs/geometry-hook.md` (default **on** after Interact)  
- TIM: `docs/tim-cycle.md`  
- Living form: `docs/living-form.md`  
- Implementation: `runtime/geometry.py` + always-on path in `runtime/apply.py`

### relative_mass_proxy (Interact, target = sender)

The Mass the observer may treat as "real" for the **sender** is the sender's **emergent self-Mass**: the same normalized weighted process as local Self-Mass (`docs/mass.md`), derived only from *inbound estimates of them*.

Sources (priority):

1. `signal.sender_emergent_mass` — they attach their current readout on the signal  
2. Last stored `sender_emergent_mass` in the foreign-estimate zone  
3. `public_card.emergent_self_mass` — same number from their public card (`GET /ie/v0/card`)

Never: `coarse_mass_estimate` (that is their estimate *of the observer*).  
Never: Self-Mass of the observer from a self Geometry Receipt.

### Membrane policy observation (stub)

Consent applied/rejected is recorded as an observational note only.  
It is **not** Access/Jurisdiction geometry. Full Ownership operationalization: **OS #40**.

## Relation to existing contracts

- **Interaction Signal** — carrier across the membrane  
- **Geometry Receipt** — local metabolic interpretation under the observer Metric Stem  
- **Tensor** — live geometric reading of Registry alloys (feed from Receipts: **#8**)  
- **Foreign-estimate zone** — bounded region where others' signals land  
- **Self-Mass** — emerges only from foreign estimates; never from self Geometry Receipts

## Non-claims

- No full catalogue of "good questions"  
- No high-fidelity Curvature/Frequency extraction in v0  
- No TIM organism-agent layer in v0  
- No Identity = LLM loop  
- No automatic Tensor/Registry rewrite from Geometry Receipts in v0 (see #8)  
- No Access/Jurisdiction scores from membrane stubs in v0 (see #40)

## Next levers

1. Dogfood Interact path (default on).  
2. Think / Mature entry points (`target=self`).  
3. **Feed Geometry Receipt into Tension / Tensor / Registry** — **#8**.  
4. **Access & Jurisdiction probes / membrane policy** — **#40**.  
5. Optional public framework note: Probes as process; TIM as operational phase split; living-form as lens.  
6. Richer extractors behind the same interface.

See `schemas/geometry-receipt/v0.yaml`, `docs/geometry-hook.md`, `docs/tim-cycle.md`, `docs/living-form.md`.
