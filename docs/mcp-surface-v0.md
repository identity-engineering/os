# MCP Surface binding v0 → owner surface (local, Identity-scoped)

Local Free installs expose the same Surface Runtime handlers over **stdio JSON-RPC** (Model Context Protocol subset).

This local stdio surface is a development, integration, and test path. It is not
the current user Dogfood path; real Dogfood is Jonas's use of the Grok MCP
connector against the current code on `main`.

The canonical local endpoint is `ie surface mcp`. It implements the MCP
`initialize`, `tools/list`, and `tools/call` methods over newline-delimited
JSON-RPC 2.0. This is the agent path for installations where the agent has no
computer-use interface.

## Binding rule

- Session authenticates as **one** Identity in the install.
- Default: install `active_identity_id`.
- Override for process lifetime: `--identity-id` or `--handle` (does **not** mutate install active).
- Every tool result includes `actor` with `actor_identity_id`.
- `ie_signal_apply` forces `to` / `to_handle` to the bound Identity. Cross-Identity write is not exposed in local tools.
- `ie_context_list` and `ie_context_get` read only installed Context Layer files under the bound install root.
- `ie_messaging_card_register` forces `identityId` to the bound Identity, even when the request supplies another value.
- `ie_messaging_send` forces `from` to the bound Identity.
- `ie_messaging_inbox` returns only Envelopes addressed to the bound Identity.
- `ie_messaging_metabolize` refuses messages addressed to another Identity.
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
| `ie_context_list` | Installed Context Layer documents |
| `ie_context_get` | Read one installed Context Layer document |
| `ie_messaging_cards` | Locally registered Messaging Cards |
| `ie_messaging_status` | Receipts, consent audit, metabolization, damping, and rejection reasons |
| `ie_messaging_card` | Read one public Messaging Card |
| `ie_messaging_card_register` | Register the bound Identity's Card |
| `ie_messaging_inbox` | Messages addressed to the bound Identity |
| `ie_messaging_send` | Send an Identity Messaging Envelope |
| `ie_messaging_metabolize` | Record processing; optionally commit Mature |

All tools share the same policy, receipts, and geometry paths as CLI/HTTP.

## Non-goals (current local surface)

- Managed-hosted MCP (see #86, `os-managed`)
- In-process Identity switch without restart (restart with `--identity-id` instead)
- Direct `ie_mature` or arbitrary policy changes via MCP; `ie_messaging_metabolize` is the narrow explicit Mature bridge for an addressed message
- Auto-approve critical Surface policy changes
- Full MCP resource/prompt surfaces beyond tools

## Exit criteria

### v0 (#60) — done

- [x] Local MCP server runs against a Free install
- [x] Tools cannot bypass Identity binding
- [x] Tests for apply + at least one read path via MCP
- [x] Context read path for agents without computer use
- [x] Messaging Card, send, inbox, and metabolization tools
- [x] RPC tests for sender spoofing and bound receiver isolation

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
