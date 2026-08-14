# Identity Context Layer (v0)

Status: operational contract · 13.08.2026 · Issue #90 · Store adapters #95/#96

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
  mirror or point at these files; adapters deepen under #5.

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
| `mature` | Source-backed learning commit via `ie mature` |
| `status` | Install / Identity summary |
| `signal` | Interaction Signal apply |
| `card` | Public card readout |
| `propose-to-standard` | Feedback issue/PR toward open OS/framework standard |

## Storage

- **v0 default:** local files under the install root (`skills/`) via **ContextStore** `local_fs`.
- **Notion:** ContextStore adapter (`docs/context-store.md`, #96) — read-first.
- Config: `.ie/context_store.json`; CLI `ie context` / `ie adapters`.

## Discovery

- `IE.md` points agents at `skills/` and at CLI/MCP.
- `docs/local-entry.md` remains discovery of the **install**, not skill content.
- `docs/agent-contract-v1.md` remains the semantic contract for tool use.

## Related

- Issues #90, #91, #92, #95, #96, #5, #9
- `docs/tim-cycle.md`, `docs/account-identity-model.md`, `docs/context-store.md`
