# Identity-Native Messaging Layer (Local)

**Status:** Phase 3 + HTTP + A2A adapter  
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

## Current scope

1. Register / list Identity Cards
2. Send Envelope (outbox + inbox + receipt)
3. Recognition + consent grants
4. CLI: `ie messaging …`
5. Local HTTP surface
6. **A2A adapter** – Identity Card ↔ Agent Card mapping (discovery only; no A2A task runtime)

Still out of scope: collective Regulation execution, metabolization hooks into Mature, Managed Space federation, full A2A task protocol.

## Design principles (binding)

1. Build on A2A/MCP – do not replace them.
2. Server as router – Envelope visible; Payload Ownership-controlled.
3. Local-first – works without Managed Space.
4. Causal Entropic Forces – mass-/stem-altering requires explicit consent.
5. Feature branch + explicit approval before merge to main.

## Schema source of truth

Conceptual schemas live in the framework repo:

- `docs/messaging/06-identity-card-schema.md`
- `docs/messaging/07-message-envelope-schema.md`

## CLI

```
ie messaging card register --file card.json
ie messaging card list
ie messaging card show <identityId>
ie messaging a2a export <identityId>
ie messaging a2a import-card --file agent-card.json
ie messaging send --file envelope.json
ie messaging inbox
ie messaging show <messageId>
ie messaging serve --port 7420 --identity <identityId>
```

## HTTP surface (default `127.0.0.1:7420`)

```
GET  /ie/v0/messaging/health
GET  /ie/v0/messaging/cards
GET  /ie/v0/messaging/cards/<identityId>
POST /ie/v0/messaging/cards
POST /ie/v0/messaging/messages
GET  /ie/v0/messaging/inbox
GET  /ie/v0/messaging/messages/<messageId>
GET  /ie/v0/messaging/agent-card/<identityId>
POST /ie/v0/messaging/import-agent-card
GET  /.well-known/agent-card.json
```

`/.well-known/agent-card.json` uses `--identity` if set, otherwise the sole registered card.

## A2A mapping notes

- Export puts IE fields under `x-ie` so pure A2A clients can ignore them.
- Import accepts A2A v1.0 `supportedInterfaces` and legacy top-level `url`.
- Skills map to IE `capabilities`; reverse on export.
- This adapter is **discovery-only** – it does not implement A2A Tasks / streaming.

## Storage layout (local Space)

```
.ie/
  messaging/
    cards/
    inbox/
    outbox/
    receipts/
    consents/
```

## Consent semantics

- A `consent-grant` message is sent **by the granter** (future impact target) **to the grantee** (future impact sender).
- Grant record: `targetId = from`, `senderId = to`.
- Subsequent envelopes with `impactHints` including `mass-altering` or `stem-altering` require a matching grant or are rejected.
