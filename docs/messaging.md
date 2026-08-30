# Identity-Native Messaging Layer (Local)

**Status:** Local core and installed test paths verified; real dogfood runs through Jonas's Grok MCP connector against `main`
**Framework gap:** [framework#102](https://github.com/identity-engineering/framework/issues/102)  
**Tracking:** [#107](https://github.com/identity-engineering/os/issues/107)
**Dogfood evidence:** [`docs/messaging-dogfood.md`](messaging-dogfood.md)

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

The local core is delivered through the installable `ie` command. CLI calls,
local MCP calls, source overrides, worktree runs, automated scripts, and
assistant-run flows are test paths only; they are not Dogfood evidence. The only
current Dogfood path is Jonas using the Grok MCP connector against the code on
`main`. Homebrew remains a supported installation and test path; the repository
checkout is a development surface. A2A remains discovery-only by design: IE
imports and exports Identity Cards and serves well-known cards, while the
external agent runtime owns task execution.

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

Consent audit records grant decisions in `.ie/messaging/consent_audit/`.
Rejected Recognition, Consent, and Damping decisions remain immutable
`rejected` receipts and are surfaced by `ie messaging status`; they do not emit
a duplicate consent-audit event.

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
ie messaging status --json
ie messaging a2a export <identityId>
ie messaging send --file envelope.json
ie messaging inbox
ie messaging metabolize <messageId> --mature
ie messaging serve --port 7420
```

## MCP (local stdio)

Agents without computer use can use the Identity Messaging surface through
the canonical local MCP endpoint:

```text
ie surface mcp --path <install-root>
```

Available Messaging tools are `ie_messaging_cards`, `ie_messaging_card`,
`ie_messaging_status`, `ie_messaging_card_register`, `ie_messaging_inbox`,
`ie_messaging_send`, and `ie_messaging_metabolize`. Every result carries the
bound actor. The status readout lists receipts by type, active consents and
append-only consent audit events, metabolization records, Damping windows, and
the reason for every rejection. Card
registration forces `identityId` to that actor, send forces `from`, inbox is
receiver-filtered, and metabolization refuses messages addressed to another
Identity. Context skills are available through `ie_context_list` and
`ie_context_get`.

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
  consent_audit/
  damping/
  metabolized/
```
