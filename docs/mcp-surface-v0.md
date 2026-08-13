# MCP Surface binding v0 → owner surface (local, Identity-scoped)

Local Free installs expose the same Surface Runtime handlers over **stdio JSON-RPC** (Model Context Protocol subset).

## Binding rule

- Session authenticates as the install's **active Identity** (`IdentitySession`).
- Every tool result includes `actor` with `actor_identity_id`.
- `ie_signal_apply` forces `to` / `to_handle` to the bound Identity. Cross-Identity write is not exposed in local tools.
- Optional `space_id` may be stamped on the actor envelope.

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

### Zero-friction config

```bash
ie surface mcp-config                 # Claude Desktop style (default)
ie surface mcp-config --format cursor
ie surface mcp-config --format generic --path ~/ie
```

Prints a ready-to-paste JSON snippet with absolute install path so the client does not depend on active-root discovery.

## Tools

| Tool | Role |
|------|------|
| `ie_status` | Install summary + actor |
| `ie_card` | Public card (emergent self-Mass, last_mature_at) |
| `ie_mass` | Emergent self-Mass readout (optional contributor detail) |
| `ie_freedom` | Effective Freedom readout (optional source detail) |
| `ie_signal_apply` | Apply Interaction Signal into foreign-estimate zone |
| `ie_geometry_feed` | Explicit Geometry Receipt → Registry feed |
| `ie_grants_list` | Jurisdiction grants on the bound Identity |
| `ie_requests_list` | Inbound estimate-request inbox |
| `ie_registry_list` | Peer handles |
| `ie_identity_list` | Identities in this install + active marker |

All tools share the same policy, receipts, and geometry paths as CLI/HTTP.

## Non-goals (current local surface)

- Managed-hosted MCP (belongs in `os-managed`)
- MCP session switch across Identities (active only; list is read-only)
- `ie_mature` via MCP (source-file contract → follow-up)
- Auto-approve critical Surface policy changes
- Full MCP resource/prompt surfaces beyond tools

## Exit criteria

### v0 (#60) — done

- [x] Local MCP server runs against a Free install
- [x] Tools cannot bypass Identity binding
- [x] Tests for apply + at least one read path via MCP
- [x] Docs updated; #29 MCP checkbox closable

### Owner surface (#84)

- [x] Owner tools: freedom, geometry feed, grants, requests, identity list
- [x] `ie surface mcp-config` helper
- [x] Tests extended; docs + `next.md` aligned

## Related

- `runtime/mcp_session.py`, `runtime/mcp_handler.py`, `ie/mcp_cmd.py`
- `docs/agent-contract-v1.md`, `docs/realization-surface-runtime.md`
- Issue #60 (closed), #84, #29
