# Realization: Surface Runtime (not hand-built servers per Identity)

Locked 28.07.2026  
Multi-identity account model linked 08.08.2026

## The hard problem

If every Identity had to implement its own MCP server and HTTP API correctly, the system would fail:

- most humans cannot or will not do it
- custom servers are error-prone and insecure
- policy bugs become ownership bugs

## Design principle

**IE OS ships a standard Identity Surface Runtime.**

The Identity supplies **configuration + data** (access policy, grants, foreign-estimate store, optional extra tool defs under approval).
The runtime supplies **correct, tested implementation** of the minimal operations on MCP and/or HTTP.

Users do not "build the backend from scratch". They **enable and configure** a surface.

The runtime always runs **as a specific Identity**. Account membership selects which Identities exist; it does not collapse them into one Surface. See `docs/account-identity-model.md`.

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
4. MCP binding wrapping the same handlers (full Identity-scoped write)
5. Managed Pro deployment of the same runtime per Identity under multi-identity accounts
6. Approval UX for critical policy/tool changes

## What this means for product

The product promise stays "Setz dir das einfach auf":

- Free: init local store + optional local surface
- Pro: account + many Identities + managed Surface URL per Identity + same mental model

Not: "implement OAuth, MCP, and a secure write API yourself."
