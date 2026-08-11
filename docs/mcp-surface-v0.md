# MCP Surface binding v0 (local, Identity-scoped)

Local Free installs expose the same Surface Runtime handlers over **stdio JSON-RPC** (Model Context Protocol subset).

## Binding rule

- Session authenticates as the **single install Identity** (`IdentitySession`).
- Session binds to the primary local Space by default, or to an explicit Space
	only when that Identity has an active persisted membership.
- Every tool result includes `actor` with `actor_identity_id`.
- The actor envelope also includes the bound `space_id`.
- `ie_signal_apply` forces `to` / `to_handle` to the bound Identity. Cross-Identity write is not exposed in V1 tools.
- Tool calls re-check the Space membrane: Surface access is required for every
	tool, `public_card` for `ie_card`, and `interaction_signal` for
	`ie_signal_apply`. A revoked membership therefore stops an existing session.

See `docs/account-identity-model.md` and `docs/space-model.md`.

## Run

```bash
# Against the active install (IE_ROOT or nearest .ie/ie.sqlite3)
python -m runtime.mcp_handler

# Explicit path
python -m runtime.mcp_handler --install ~/ie

# CLI entry (same process)
ie surface mcp
ie surface mcp --path ~/ie
```

Wire any MCP-capable agent/client to the stdio process. Protocol version: `2024-11-05`.

## Tools (v0)

| Tool | Role |
|------|------|
| `ie_status` | Install summary + actor |
| `ie_card` | Public card (emergent self-Mass, last_mature_at) |
| `ie_mass` | Emergent self-Mass readout (optional contributor detail) |
| `ie_signal_apply` | Apply Interaction Signal into foreign-estimate zone |
| `ie_registry_list` | Peer handles |

All tools share the same policy, receipts, and geometry paths as CLI/HTTP.

## Non-goals (v0)

- Managed-hosted MCP (belongs in `os-managed`)
- N Identities per local install
- Auto-approve critical Surface policy changes
- Full MCP resource/prompt surfaces beyond tools

## Exit criteria (#60)

- [x] Local MCP server runs against a Free install
- [x] Tools cannot bypass Identity binding
- [x] Tests for apply + at least one read path via MCP
- [x] Docs updated; #29 MCP checkbox closable

Space binding is local Schema 9 state. A verified inbound Space can be known
without becoming addressable, but it cannot bind an MCP session until a future
membership workflow creates an active membership.

## Related

- `runtime/mcp_session.py`, `runtime/mcp_handler.py`
- `docs/agent-contract-v1.md`, `docs/realization-surface-runtime.md`
- Issue #60, #29
