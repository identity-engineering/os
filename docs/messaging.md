# Identity-Native Messaging Layer (Local)

**Status:** Phase 3 + HTTP + A2A + Regulation + Metabolize  
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
5. Collective Regulation (`central` / `specialist` / `fan-out` + damping)
6. **Metabolization** – record processing of an accepted message; optional Mature commit

Still out of scope: Managed Space federation, full A2A task protocol, auto-metabolize policies.

## Design principles (binding)

1. Build on A2A/MCP – do not replace them.
2. Server as router – Envelope visible; Payload Ownership-controlled.
3. Local-first – works without Managed Space.
4. Causal Entropic Forces – mass-/stem-altering requires explicit consent.
5. Feature branch + explicit approval before merge to main.

## Metabolization (Biology Single)

After delivery, the receiving Identity may metabolize a message:

```
ie messaging metabolize <messageId> --notes "…" [--classification task] [--mature]
```

- Always writes `.ie/messaging/metabolized/<messageId>.json`
- Emits a `metabolized` receipt toward the original sender
- With `--mature`: snapshots the envelope under `trajectory/messaging/` and runs `commit_mature` (stem + workspace observation)

## Collective Regulation

| `routing` | Behaviour |
|-----------|-----------|
| `central` | Collective inbox only |
| `specialist` | First registered specialist |
| `fan-out` | Collective + all registered specialists |

Optional `damping.maxMessagesPerWindow` / `windowSeconds`.

## CLI

```
ie messaging card register --file card.json
ie messaging a2a export <identityId>
ie messaging send --file envelope.json
ie messaging inbox
ie messaging metabolize <messageId> --mature
ie messaging serve --port 7420
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

## Storage layout

```
.ie/messaging/
  cards/
  inbox/
  outbox/
  receipts/
  consents/
  damping/
  metabolized/
```
