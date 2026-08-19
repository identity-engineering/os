# Agent Contract for Local IE V1

This contract describes how CLI users, coding agents, and runtime adapters use
the local database without bypassing Identity Engineering semantics.

An agent process is typically bound to an **Identity** (its own substrate),
not to an anonymous account root. See `docs/account-identity-model.md`.

## Discovery

An agent should discover an install in this order:

1. explicit `--path`;
2. `IE_ROOT`;
3. the nearest parent containing `.ie/ie.sqlite3`;
4. the remembered active root.

`README.md` and `IE.md` explain the local surface, but they are not authority
for mutable state. The database is authoritative. A legacy `HEADER.yaml` may
be reported as a legacy install, but it is not silently treated as the V1
database.

When multiple Identities exist under one account or install, the agent must
know which `identity_id` (or local handle) it is bound to. Context switch is
explicit.

## Context Layer skills (human interface)

Standard skills live under `<install>/skills/<name>/SKILL.md` (see
`docs/context-layer.md`). Humans invoke them (e.g. `/mature`). **Agents read
the skill text and execute CLI/MCP commands** listed there. Skills are not a
second write API.

## MCP binding (local V1)

Agents that speak MCP may attach to the local Surface via stdio:

```text
ie surface mcp
# or: python -m runtime.mcp_handler --install <root>
```

Session is bound to one Identity (default install active; optional
`--identity-id` / `--handle`). Every tool result carries
`actor.actor_identity_id`. `ie_signal_apply` forces the destination to the
bound Identity. See `docs/mcp-surface-v0.md`.

## Read path

Agents should prefer stable commands and JSON output:

```text
ie status --json
ie registry list --json
ie mass --json
ie request list --json
ie db info --json
```

An MCP-capable agent may use the same local Surface Runtime after installing
the optional SDK extra:

```text
pip install ie-os[mcp]
ie-mcp --install /path/to/install --transport stdio
```

The MCP process is bound once at startup to the one local V1 Identity. The
optional `--identity-id` is an assertion, not a context switch. MCP tools do
not accept an identity selector, and every structured result includes
`actor_identity_id`, `identity_id`, and `space_id`. Local Free V1 has no
membrane tables yet; passing `--space-id` therefore fails closed instead of
silently treating the request as account-root access.

The initial local MCP tool set is:

- `get_status`
- `get_public_card`
- `get_mass`
- `list_inbound_requests`
- `receive_interaction_signal`

Mature and policy-changing Surface operations remain on the existing CLI and
runtime paths until their approval and grant envelopes are exposed explicitly.

Every JSON result should identify the relevant schema version and stable IDs.
Agents should use receipt IDs, event IDs, Mature IDs, and revision numbers when
referring to state rather than relying on display text or file paths.

The public card's `emergent_self_mass` and `last_mature_at` are different
signals. The former is a derived field readout from other Identities' estimates;
the latter is only a public freshness timestamp for the local owned learning
state. A Registry should retain both the peer's latest public Mature timestamp
and the peer Mature timestamp that was current when its local estimate was last
updated.

## Write path

Agents do not write SQLite directly and do not edit database files. They use
the CLI, runtime API, HTTP surface, or MCP adapter. A write operation must
return a structured result containing:

- status;
- stable ID(s);
- **actor_identity_id** (or equivalent handle resolved to that Identity);
- changed fields or revision markers;
- rejected fields and reasons, when applicable; and
- the next recoverable action, when the operation failed.

The runtime owns transaction boundaries. A caller must not emulate a multi-step
write by updating projections in separate commands when the operation has a
single transactional command.

Write capability is not reduced for agents as a class. An agent authenticated
as Identity I may write I's geometry under the same rules as a human using the
CLI as I. Writing another Identity's geometry requires an explicit grant.

## Interact rules

- Validate the signal contract before transport-specific handling.
- Never use `coarse_mass_estimate` as the sender's own Mass.
- Treat `sender_emergent_mass` as public sender geometry, not as a rating of the
  receiver.
- Do not infer consent from a signal merely because a field is present.
- Do not suppress a partial or rejected receipt; it is part of the audit path.
- Do not retry an accepted event without preserving idempotency or recording a
  new deliberate event.

## Mature rules

Mature is an owned learning operation on **a specific Identity**.

- When the agent is bound to Identity I, it may commit Mature on I subject to
  I's policy and evidence rules (same as CLI).
- When the agent proposes Mature on Identity J ≠ I, the runtime enforces grants;
  default is refuse.
- Critical policy or Surface changes still follow the critical-approval path in
  `docs/identity-surface.md`.
- Prefer the **mature** skill text + `ie mature` CLI for human-triggered sessions.

A Mature request should include:

- the target Identity (default: bound Identity);
- source references and the intended evidence mode;
- a short causal explanation;
- requested Stem, Workspace, and Registry changes;
- confidence where an estimate or dimension value changes; and
- explicit reassessment targets if peers should be asked for a fresh estimate.
