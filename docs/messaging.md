# Identity-Native Messaging Layer (Local)

**Status:** Phase 3 + HTTP + A2A + Collective Regulation  
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

1. Identity Cards + send / inbox / receipts
2. Recognition + consent grants
3. CLI + local HTTP surface
4. A2A adapter (discovery only)
5. **Collective Regulation** – `central` / `specialist` / `fan-out` + damping

Still out of scope: metabolization hooks into Mature, Managed Space federation, full A2A task protocol.

## Design principles (binding)

1. Build on A2A/MCP – do not replace them.
2. Server as router – Envelope visible; Payload Ownership-controlled.
3. Local-first – works without Managed Space.
4. Causal Entropic Forces – mass-/stem-altering requires explicit consent.
5. Feature branch + explicit approval before merge to main.

## Collective Regulation

On a Card with `type: "collective"` and a `regulation` block:

| `routing` | Behaviour |
|-----------|-----------|
| `central` | Deliver only to the collective inbox |
| `specialist` | Deliver to the first *registered* specialist (fallback: collective) |
| `fan-out` | Deliver to collective **and** every registered specialist |

Specialists still apply their own Recognition policy. Routed specialist copies get `routedFrom`, `originalMessageId`, and a fresh `messageId`.

Optional damping:

```json
"regulation": {
  "routing": "fan-out",
  "specialists": ["…", "…"],
  "damping": { "maxMessagesPerWindow": 20, "windowSeconds": 60 }
}
```

## CLI

```
ie messaging card register --file card.json
ie messaging card list
ie messaging a2a export <identityId>
ie messaging a2a import-card --file agent-card.json
ie messaging send --file envelope.json
ie messaging inbox
ie messaging serve --port 7420 --identity <identityId>
```

## HTTP surface (default `127.0.0.1:7420`)

```
GET  /ie/v0/messaging/health
GET  /ie/v0/messaging/cards
POST /ie/v0/messaging/cards
POST /ie/v0/messaging/messages
GET  /ie/v0/messaging/inbox
GET  /ie/v0/messaging/agent-card/<identityId>
POST /ie/v0/messaging/import-agent-card
GET  /.well-known/agent-card.json
```

## A2A mapping notes

- Export puts IE fields under `x-ie`.
- Import accepts A2A v1.0 `supportedInterfaces` and legacy top-level `url`.
- Discovery-only – no A2A task runtime.

## Storage layout

```
.ie/messaging/
  cards/
  inbox/
  outbox/
  receipts/
  consents/
  damping/          # per-collective rate windows
```

## Consent semantics

- `consent-grant` is sent **by the granter** (future impact target) **to the grantee**.
- Grant record: `targetId = from`, `senderId = to`.
- `mass-altering` / `stem-altering` require a matching grant.
