---
name: signal
description: Apply an Interaction Signal into the bound Identity foreign-estimate zone. Human invokes; agent uses ie signal apply or MCP ie_signal_apply.
---

# Signal (Interact)

## When invoked

1. Confirm bound Identity (`ie status --json` or MCP `ie_status`).
2. Build a valid Interaction Signal payload with the human (from, depth, estimates, transport).
3. Apply:
   - CLI: `ie signal apply --payload <file.json>` (or stdin)
   - MCP: `ie_signal_apply` with `signal` object
4. Report receipt status, accepted/rejected fields, Geometry Receipt id.

## Rules

- Destination must be the bound Identity (`to` / `to_handle`).
- Never treat `coarse_mass_estimate` as the sender's own Mass.
- Do not invent consent; use policy grants or explicit open-consent only when the human asks (dogfood).
- After apply, Geometry feed may run via hook; explicit path: `ie geometry feed` / MCP `ie_geometry_feed`.
