---
name: status
description: Summarize the bound Identity install (handle, peers, Mass, Freedom, geometry feed). Human-facing; agent uses CLI/MCP only.
---

# Status

## When invoked

1. Read install state:
   - CLI: `ie status --json`
   - MCP: `ie_status`
2. Optionally enrich:
   - `ie mass --json` / MCP `ie_mass`
   - `ie freedom --json` / MCP `ie_freedom`
   - `ie request list --json` / MCP `ie_requests_list`
3. Present a short human summary: handle, identity_id, peers, emergent self-Mass, effective freedom, pending requests, geometry feed capability.

## Rules

- Read-only. No SQLite edits.
- Always name the Identity you are summarizing (handle + identity_id when available).
