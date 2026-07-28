# Communication model

Locked 28.07.2026

## Separation of layers

| Layer | What it is | What it is not |
|-------|------------|----------------|
| **Transport** | A2A, HTTP, MCP session, webhook, CLI, file drop | The meaning of Mass / depth |
| **Payload** | IE Interaction Signal schema | A new TCP stack |
| **Receipt** | accepted / applied / rejected / partial | TCP ACK alone |
| **Surface** | Operations + policy on the Identity | Chat prose |
| **Local entry** | How *my* agent finds *my* install | What I broadcast as Vision |

Uniformity = same payload + same operations + same receipt semantics on any transport.
Receipt ensures the callee actually applied (or refused) the write into its foreign-estimate zone.

## Inside an IE-standardized network

Both sides speak the Identity Surface contract.

- Prefer MCP tool call or HTTP POST to `receive_interaction_signal`
- Minimal payload always allowed under peer auth (per callee policy)
- Consent fields only with grant
- Receipt required for the sender to know the effect

## Outside IE (non-IE Identities)

- No assumption the other side hosts a surface
- Inbound: whatever channel exists (chat, email, API, A2A without IE payload) is **interpreted locally** into *my* Registry by me / my agent under *my* policy
- Outbound: only what the channel understands; optional IE payload if the other side accepts it
- No forced foreign-write into non-IE systems

## MCP and HTTP

Both are **bindings** of the same Identity Surface:

- **MCP** — primary for agent-native discovery and tool calls
- **HTTP API** — primary for universal clients, automation, managed Pro

Custom HTTP headers may carry routing/version (`IE-Schema-Version`, `IE-From`, `IE-To`); body carries the payload. That is compatible with REST and with envelope-style agent protocols.

A2A (or similar) may carry the same payload as a message part. IE does not replace A2A; it defines the semantic part.

## What is never the default inter-identity content

- Full Vision / Stem broadcast
- Unscoped write into another Identity's core
- Silent tool installation on another surface

See Identity Surface for grants and human approval of critical changes.
