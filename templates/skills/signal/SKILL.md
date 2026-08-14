---
name: signal
description: Apply an Interaction Signal into the bound Identity foreign-estimate zone. Carrier for Interact and Foreign-Mature / Standard-Mature feedback. Human invokes; agent uses ie signal apply or MCP ie_signal_apply.
---

# Signal (Interact · Foreign-Mature carrier)

## Role

An Interaction Signal is how one Identity offers structured information to another.
That includes estimates and depth, and **feedback meant for the receiver’s Mature**
(Foreign-Mature). Propose-to-standard is the same pattern with the open standard as
addressee (see `propose-to-standard` skill).

## When invoked

1. Confirm bound Identity (`ie status --json` or MCP `ie_status`).
2. Build a valid Interaction Signal payload with the human (from, depth, estimates, transport; optional proposal/feedback notes).
3. Apply:
   - CLI: `ie signal apply --payload <file.json>` (or stdin)
   - MCP: `ie_signal_apply` with `signal` object
4. Report receipt status, accepted/rejected fields, Geometry Receipt id.
5. If the human is **integrating** inbound signals (not only applying outbound), switch to the `mature` skill and treat signal evidence as `--source`.

## Rules

- Destination must match the intended recipient Identity (`to` / `to_handle`).
- Never treat `coarse_mass_estimate` as the sender's own Mass.
- Do not invent consent; use policy grants or explicit open-consent only when the human asks (dogfood).
- After apply, Geometry feed may run via hook; explicit path: `ie geometry feed` / MCP `ie_geometry_feed`.

## Related

- `docs/mature.md`, skills `mature` and `propose-to-standard`
