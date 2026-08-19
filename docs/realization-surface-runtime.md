# Realization: Surface Runtime

The Identity Surface is realized by a **standard runtime** so Identities do not
hand-build MCP or HTTP servers.

## Local V1 (shipped)

| Binding | Entry | Notes |
|---------|-------|-------|
| CLI | `ie signal apply`, `ie status`, … | Primary human + script path |
| HTTP | `python -m runtime.http_handler` | Thin stdlib; same handlers |
| **MCP** | `ie surface mcp` / `python -m runtime.mcp_handler` | Identity-scoped stdio JSON-RPC |

All three share:

- deterministic apply + receipts
- foreign-estimate zone only for inbound writes
- policy (always-passed vs consent, quarantine)
- actor stamping (`actor_identity_id`) on structured results

MCP specifics: `docs/mcp-surface-v0.md`. Session binds to the single local
Identity; tools cannot target another Identity's geometry in V1.

## Managed (later)

Hosted Surface for Personal Pro / governed Spaces lives in `os-managed`.
Same operation semantics; different auth and membrane enforcement.

## Related

- Issue #29 (Surface Runtime v0)
- Issue #60 (MCP binding — closed)
- `docs/identity-surface.md`, `docs/agent-contract-v1.md`

## Tiers

| Tier | How the surface runs |
|------|----------------------|
| **Free local** | Local surface process or CLI-applied operations (`ie surface serve` / `ie signal apply`) reading policy + state from local store |
| **Personal Pro** | Managed surface endpoints per Identity (hosted runtime + Supabase state); same ops, auth as Identity, receipts |
| **Advanced** | Optional custom tools registered into the runtime after **approval**; still hosted inside the standard runtime sandbox, not arbitrary remote code by default |

MCP is a first-class binding of the same handlers as CLI/HTTP. When a session is authenticated as Identity I, MCP may write I's geometry under the same rules as local CLI. It is not a read-only agent mirror.

## Access policy as data

- Policy file / table owned by the Identity (or designated owner role)
- Critical mutations → approval request queue → holder confirms in a clear UI/CLI prompt
- Agents may propose policy changes on Identities they are granted to administer; they do not silently merge critical ones

## Custom tools

Flow:

1. Agent or user proposes a new tool (schema + effect description + requested scopes)
2. If critical (default: yes for new write tools) → approval
3. Runtime registers tool only after approval
4. Grants remain separate (who may call it)
5. Revoke removes tool and/or grants; audit keeps history

This prevents "someone else asks my agent to expose a write-everything tool" without an approval request on the target Identity.

## Security baseline (v0 intent)

- Authn on non-public ops (Identity-scoped)
- Rate limits on receive_interaction_signal
- Audit log of applies and rejects with actor_identity_id
- Quarantine / revoke paths
- No default public unscoped write
- Secrets never in policy files in cleartext

## Implementation order (suggested)

1. Spec ops + payload + receipt + foreign-estimate schema (docs + schemas) — done in parallel with these docs
2. Local apply path without network (`ie signal apply`) — deterministic, testable
3. Local HTTP surface (one process, standard routes)
4. Local MCP binding wrapping the same handlers (Identity-scoped write; initial slice implemented)
5. Managed Pro deployment of the same runtime per Identity under multi-identity accounts
6. Approval UX for critical policy/tool changes

## What this means for product

The product promise stays "Setz dir das einfach auf":

- Free: init local store + optional local surface
- Pro: account + many Identities + managed Surface URL per Identity + same mental model

Not: "implement OAuth, MCP, and a secure write API yourself."
