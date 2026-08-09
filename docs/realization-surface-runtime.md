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
