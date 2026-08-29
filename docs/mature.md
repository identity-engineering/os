# Mature (IE operating cycle · IE OS)

Status: operational contract · 14.08.2026 · Issue #92
Stem lock: `docs/stem.md` (2026-08-29)

## Naming

**Mature** is the name. Do not use Evolve for this layer. Mature is the third
operating phase and the existing CLI/MCP surface (`ie mature`).

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

## Mature forms the Stem

Every accepted `commit_mature` calls `_apply_stem` (`runtime/mature.py`).
That is the only write path onto `stem_state`.

What it persists today:

- `state_differential.latest_summary`
- `vision_gradient.latest_shift`
- `coherence.latest_note`
- merge of owner-supplied `substance_json`
- `substance_json.last_mature` (mature_id, notes, source_ids, optional
  ownership_move / optionality_delta)
- incremented `revision` plus a full row in `stem_revisions`

The current snapshot *is* framework `x(t)` (Particles as a reading).
The revision series *is* the worldline sample set (Preference / Frequency
as readings). Rebuild-projections replays these rows. It does not Mature.

Interact never writes Stem. Foreign-Mature never writes the receiver's Stem.
Named aspects and binding claims, if any, arrive as supplied `substance`
through this same function. They do not get a second module.

The Stem form is still thin (prose + bag). Thickening it is Mature work,
not a new operating phase.

## Skills (human interface)

| Skill | Role |
|-------|------|
| `mature` | Self-Mature; also inbound integration when standard changes are sources |
| `signal` | Interact / Foreign-Mature carrier |
| `propose-to-standard` | Standard-Mature outbound (Signal-first; optional GitHub materialization) |

Agents read skill text and execute via CLI/MCP only.

## Implementation notes (v0)

- Skill texts and this doc lock the contract.
- Live write path: `runtime/mature.py` · `commit_mature` · `_apply_stem`.
- YAML schemas document shape. They are not read as mutable state.
- Later: `ie standard status` / available-changes as **readout of sources** for
  Mature — not a blind apply command.
- Later: canonical standard Identity handle + proposal field schema on Signal.

## Related

- `docs/stem.md`, `docs/particles.md`, `docs/preference.md`
- `docs/probe-cycle.md`, `docs/context-layer.md`, `docs/agent-contract-v1.md`
- Issues #92, #90, #9
