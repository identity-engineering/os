# Realization: Surface Runtime (not hand-built servers per Identity)

Locked 28.07.2026

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

## Tiers

| Tier | How the surface runs |
|------|----------------------|
| **Free local** | Local surface process or CLI-applied operations (`ie surface serve` / `ie signal apply`) reading policy + state from local store |
| **Personal Pro** | Managed surface endpoints per Identity (hosted runtime + Supabase state); same ops, auth, receipts |
| **Advanced** | Optional custom tools registered into the runtime after **human approval**; still hosted inside the standard runtime sandbox, not arbitrary remote code by default |

## Access policy as data

- Policy file / table owned by the human (or designated owner)
- Critical mutations → approval request queue → human confirms in a clear UI/CLI prompt
- Agents may propose policy changes; they do not silently merge critical ones

## Custom tools

Flow:

1. Agent or user proposes a new tool (schema + effect description + requested scopes)
2. If critical (default: yes for new write tools) → human approval
3. Runtime registers tool only after approval
4. Grants remain separate (who may call it)
5. Revoke removes tool and/or grants; audit keeps history

This prevents "someone else asks my agent to expose a write-everything tool" without the human owner seeing an approval request.

## Security baseline (v0 intent)

- Authn on non-public ops
- Rate limits on receive_interaction_signal
- Audit log of applies and rejects
- Quarantine / revoke paths
- No default public unscoped write
- Secrets never in policy files in cleartext

## Implementation order (suggested)

1. Spec ops + payload + receipt + foreign-estimate schema (docs + schemas) — done in parallel with these docs
2. Local apply path without network (`ie signal apply`) — deterministic, testable
3. Local HTTP surface (one process, standard routes)
4. MCP binding wrapping the same handlers
5. Managed Pro deployment of the same runtime
6. Approval UX for critical policy/tool changes

## What this means for product

The product promise stays "Setz dir das einfach auf":

- Free: init local store + optional local surface
- Pro: account + managed surface URL + same mental model

Not: "implement OAuth, MCP, and a secure write API yourself."
