# Identity-Native Messaging Layer (Local)

**Status:** Phase 3 skeleton  
**Framework gap:** [framework#102](https://github.com/identity-engineering/framework/issues/102)  
**Tracking:** [#107](https://github.com/identity-engineering/os/issues/107)

## What this is

A local-first messaging service for Identities (human, agent, collective, hybrid).
It sits **on top of** the existing Interaction Signal path (`ie signal apply`, geometry estimates).
It does **not** replace Interaction Signals.

| Layer | Purpose |
|-------|---------|
| Interaction Signal (existing) | Geometry exchange (Mass estimates, depth, Mature linkage) |
| Identity Messaging (this) | General Identity-to-Identity communication (tasks, context, consent, coordination) |

## Phase 3 scope (skeleton)

1. Register / list Identity Cards (file store under `.ie/messaging/cards/`)
2. Send an Envelope (stored under `.ie/messaging/outbox/` + target inbox)
3. List inbox / show message
4. Recognition check against the target Card’s `recognitionPolicy`
5. Emit a simple Receipt
6. CLI: `ie messaging …`

Out of scope for this skeleton: network transport, A2A adapter, collective Regulation execution, metabolization hooks into Mature.

## Design principles (binding)

1. Build on A2A/MCP – do not replace them.
2. Server as router – Envelope visible; Payload Ownership-controlled.
3. Local-first – works without Managed Space.
4. Causal Entropic Forces – mass-/stem-altering requires explicit consent.
5. Feature branch + explicit approval before merge to main.

## Schema source of truth

Conceptual schemas live in the framework branch:

- `docs/messaging/06-identity-card-schema.md`
- `docs/messaging/07-message-envelope-schema.md`

OS copies minimal JSON schemas under `schemas/messaging/` for runtime validation later.

## CLI (Phase 3)

```
ie messaging card register --file card.json
ie messaging card list
ie messaging card show <identityId>
ie messaging send --file envelope.json
ie messaging inbox
ie messaging show <messageId>
```

## Storage layout (local Space)

```
.ie/
  messaging/
    cards/          # one JSON file per identityId
    inbox/          # received envelopes
    outbox/         # sent envelopes
    receipts/       # delivery / recognition / rejection receipts
```

All paths are under the IE install root resolved by `ie.paths`.
