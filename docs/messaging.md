# Identity-Native Messaging Layer (Local)

**Status:** Phase 3 + HTTP surface  
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

1. Register / list Identity Cards (file store under `.ie/messaging/cards/`)
2. Send an Envelope (outbox + inbox + receipt)
3. Recognition check against the target Card’s `recognitionPolicy`
4. Consent grants for `mass-altering` / `stem-altering`
5. CLI: `ie messaging …`
6. Local HTTP surface: `ie messaging serve` / `python -m runtime.messaging_http`

Still out of scope: A2A adapter, collective Regulation execution, metabolization hooks into Mature, Managed Space federation.

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
ie messaging send --file envelope.json
ie messaging inbox
ie messaging show <messageId>
ie messaging serve --port 7420
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
```

Also: `python -m runtime.messaging_http --install <root> --port 7420`

## Storage layout (local Space)

```
.ie/
  messaging/
    cards/          # one JSON file per identityId
    inbox/          # received envelopes
    outbox/         # sent envelopes
    receipts/       # delivery / recognition / rejection receipts
    consents/       # mass-/stem-altering grants (target__sender.json)
```

All paths are under the IE install root resolved by `ie.paths`.

## Consent semantics

- A `consent-grant` message is sent **by the granter** (future impact target) **to the grantee** (future impact sender).
- Grant record: `targetId = from`, `senderId = to`.
- Subsequent envelopes with `impactHints` including `mass-altering` or `stem-altering` require a matching grant or are rejected.
