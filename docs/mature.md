# Mature (TIM cycle · IE OS)

Status: operational contract · 14.08.2026 · Issue #92

## Naming

**Mature** is the name. Do not use Evolve for this layer. Mature is the third
TIM step and the existing CLI/MCP surface (`ie mature`).

## One act, three relations

Mature is always the same kind of work: directed, source-backed integration of
learning into an Identity’s substrate. What changes is the **relation**.

### Self-Mature

Learning for the **bound** Identity. Evidence under the install, notes, optional
stem / commitment / optionality. Surface: `ie mature` (CLI or MCP). Never writes
owned numeric Self-Mass; never edits SQLite outside the Surface.

### Foreign-Mature

Learning **for or about another Identity**. The carrier is an **Interaction
Signal**. The sender offers information the receiver may later Mature over
(as source), accept in part, or decline. Feedback to peers after interaction is
Foreign-Mature, not a side-channel chat or a tracker ticket.

### Standard-Mature

Same mechanism with the **open standard** as addressee — the Identity Engineering
/ OS / framework surface treated as a public Identity with a strong membrane.

**Propose is Signal-first.** Opening a GitHub issue or PR is optional
*materialization* for humans and CI, not the primary act. The semantic act is:
Signal → standard Identity → their Mature (and ops pipelines that may mirror
into issues).

## Inbound (standard → local)

Local is never a pure install of the standard. The standard is blueprint and
guidance; each Identity adapts.

For each artifact (skill text, template, contract note):

1. **Simple path** — local file is missing, or identical to the last applied
   standard pin → a clean update is allowed. Prefer still recording it as a
   Mature step with the standard change as source, so history stays causal.
2. **Adaptive path** — local was personalized → the standard change is
   **evidence**, not an overwrite. The Mature skill (human + agent) reads both
   sides, understands intent, and integrates without clobbering Identity-owned
   constructs — or declines and may Signal back.

No silent auto-sync over personalized Context Layer material. Writes go through
ContextStore only when Mature frees them. Geometry remains CLI/MCP only.

## Skills (human interface)

| Skill | Role |
|-------|------|
| `mature` | Self-Mature; also inbound integration when standard changes are sources |
| `signal` | Interact / Foreign-Mature carrier |
| `propose-to-standard` | Standard-Mature outbound (Signal-first; optional GitHub materialization) |

Agents read skill text and execute via CLI/MCP only.

## Implementation notes (v0)

- Skill texts and this doc lock the contract.
- Later: `ie standard status` / available-changes as **readout of sources** for
  Mature — not a blind apply command.
- Later: canonical standard Identity handle + proposal field schema on Signal.

## Related

- `docs/tim-cycle.md`, `docs/context-layer.md`, `docs/agent-contract-v1.md`
- Issues #92, #90, #9
