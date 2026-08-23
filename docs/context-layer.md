# Identity Context Layer (v0)

Status: operational contract · 13.08.2026 · Issue #90

## Role

The **Context Layer** is workspace-facing material bound to an **Identity**:
skills, prompts, instructions, and related harness files. It is not the
geometry database. Mutable geometry remains in `.ie/ie.sqlite3` and is only
mutated through CLI / runtime / HTTP / MCP.

## Skills

- **Bound to Identity**, not to Account or to Space-as-folder.
- A Team / Org / idea that holds shared skills is itself an Identity; members
  reach those skills through **Access / Jurisdiction grants** on that Identity.
- **Format is not prescribed** by IE. Canonical templates ship as
  `templates/skills/<name>/SKILL.md` and are copied to
  `<install-root>/skills/<name>/SKILL.md` on `ie init`.
- Harness vendors (`.claude/`, `.github/`, `.grok/`, chat skill stores) may
  mirror or point at these files; adapters deepen under #5 / #95.

### Division of labor (locked)

| Actor | Role |
|-------|------|
| **Human** | Invokes skills (e.g. `/mature`) as the Identity command interface |
| **Agent** | Reads skill text; executes **CLI and/or MCP** for all IE reads/writes |
| **Runtime** | Owns transactions, policy, receipts, actor stamps |

Skills must not instruct agents to edit SQLite or bypass Surface policy.

### Standard skills (v0)

| Skill | Purpose |
|-------|---------|
| `mature` | Self-Mature; inbound standard/foreign sources via Mature (see `docs/mature.md`) |
| `status` | Install / Identity summary |
| `signal` | Interact; Foreign-Mature carrier |
| `card` | Public card readout |
| `propose-to-standard` | Standard-Mature outbound (Signal-first) |

## Storage

- **v0:** local files under the install root (`skills/`).
- **Next:** ContextStore adapters (#95, #96), including Notion read-first.

Inbound updates from the open standard are **Mature over sources**, not silent
file overwrite of personalized skills (`docs/mature.md`, #92).

## Discovery

- `IE.md` points agents at `skills/` and at CLI/MCP.
- `docs/local-entry.md` remains discovery of the **install**, not skill content.
- `docs/agent-contract-v1.md` remains the semantic contract for tool use.

## Related

- Issues #90, #91, #92, #95, #96, #5, #9
- `docs/mature.md`, `docs/probe-cycle.md`, `docs/account-identity-model.md`
