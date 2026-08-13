---
name: card
description: Show the Public Card for the bound Identity (emergent self-Mass, last_mature_at, public fields only).
---

# Card

## When invoked

1. Fetch public card:
   - MCP: `ie_card`
   - CLI: use `ie status --json` and Mass readout; prefer MCP card when available
2. Present public fields only. Do not dump private Stem, full Registry, or policy secrets.

## Rules

- Read-only.
- `emergent_self_mass` is derived from foreign estimates; `last_mature_at` is freshness of owned learning — keep them distinct.
