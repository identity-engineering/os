# MCP Surface binding v0 → owner surface (local, Identity-scoped)

Local Free installs expose the same Surface Runtime handlers over **stdio JSON-RPC** (Model Context Protocol subset).

## Binding rule

- Session authenticates as **one** Identity in the install.
- Default: install `active_identity_id`.
- Override for process lifetime: `--identity-id` or `--handle` (does **not** mutate install active).
- Every tool result includes `actor` with `actor_identity_id`.
- `ie_signal_apply` forces `to` / `to_handle` to the bound Identity. Cross-Identity write is not exposed in local tools.
- Optional `space_id` may be stamped on the actor envelope.

See `docs/account-identity-model.md` and `docs/space-model.md`.

## Run

```bash
# Against the active install Identity
ie surface mcp
python -m runtime.mcp_handler --install ~/ie

# Pin a non-active local Identity for this process only
ie surface mcp --path ~/ie --handle agent-runtime
ie surface mcp --identity-id <uuid>
```

Wire any MCP-capable agent/client to the stdio process. Protocol version: `2024-11-05`.

### Zero-friction config

```bash
ie surface mcp-config
ie surface mcp-config --format cursor --handle agent-runtime
ie surface mcp-config --format generic --identity-id <uuid> --path ~/ie
```

Prints a ready-to-paste JSON snippet with absolute install path and optional Identity pin.

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
| `ie_identity_list` | Identities in this install; marks session-bound |

All tools share the same policy, receipts, and geometry paths as CLI/HTTP.

## Non-goals (current local surface)

- Managed-hosted MCP (see #86, `os-managed`)
- In-process Identity switch without restart (restart with `--identity-id` instead)
- `ie_mature` via MCP (source-file contract → follow-up)
- Auto-approve critical Surface policy changes
- Full MCP resource/prompt surfaces beyond tools

## Exit criteria

### v0 (#60) — done

- [x] Local MCP server runs against a Free install
- [x] Tools cannot bypass Identity binding
- [x] Tests for apply + at least one read path via MCP

### Owner surface (#84) — done

- [x] Owner tools + `ie surface mcp-config`

### Multi-Identity bind (#87)

- [x] `--identity-id` / `--handle` session bind without mutating install active
- [x] mcp-config can pin Identity
- [x] Tests for alternate bind

## Related

- `runtime/mcp_session.py`, `runtime/mcp_handler.py`, `ie/mcp_cmd.py`
- `docs/agent-contract-v1.md`, `docs/realization-surface-runtime.md`
- Issues #60, #84, #86, #87, #29
