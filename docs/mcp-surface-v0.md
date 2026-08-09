# MCP Surface binding v0 (local, Identity-scoped)

Local Free installs expose the same Surface Runtime handlers over **stdio JSON-RPC** (Model Context Protocol subset).

## Binding rule

- Session authenticates as the **single install Identity** (`IdentitySession`).
- Every tool result includes `actor` with `actor_identity_id`.
- `ie_signal_apply` forces `to` / `to_handle` to the bound Identity. Cross-Identity write is not exposed in V1 tools.
- Optional `space_id` may be stamped on the actor envelope; membrane enforcement is not active in local V1.

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

## Related

- `runtime/mcp_session.py`, `runtime/mcp_handler.py`
- `docs/agent-contract-v1.md`, `docs/realization-surface-runtime.md`
- Issue #60, #29
