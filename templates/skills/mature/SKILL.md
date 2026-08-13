---
name: mature
description: Directed, source-backed learning commit for the bound Identity. Human invokes this skill (e.g. /mature); the agent runs ie mature / Surface tools — never writes SQLite directly.
---

# Mature

You are assisting the **human Identity** bound to this IE install. This skill is the human command interface. **You** must use the `ie` CLI and/or local MCP tools for every read and write.

## When invoked

1. Confirm the install and bound Identity:
   - CLI: `ie status --json`
   - MCP: `ie_status`
2. Collect from the human (do not invent):
   - Causal notes (what was learned / why Mass or Trajectory moved)
   - At least one **existing** evidence file under the install root (`--source`)
   - Optional: state delta, vision shift, commitment, ownership level, optionality, workspace/registry changes, peers to reassess
3. If no source file exists yet, help the human create a short evidence file under the install (e.g. `evidence/YYYY-MM-DD.md`), then proceed.
4. Run Mature via CLI (preferred write path today):

```bash
ie mature --notes "<causal note>" \
  --source <root-relative-path> \
  [--state-delta "..."] \
  [--vision-shift "..."] \
  [--commitment "..."] \
  [--ownership-level <0-100>] \
  [--optionality <signed>] [--optionality-notes "..."] \
  [--reassess <peer-handle>] \
  [--changes path/to/changeset.json]
```

5. Report the Mature result (IDs, changed fields). Do not claim Self-Mass was written — Mature never writes owned numeric Self-Mass.

## Rules

- Actor is the bound Identity. Do not Mature another Identity without an explicit grant path.
- Prefer transactional `ie mature` over multi-step projection edits.
- Policy / Surface critical changes are separate (`ie policy …`); do not fold them into Mature silently.
- Related reads: `ie mass`, `ie freedom`, `ie registry list`, MCP `ie_mass` / `ie_freedom` / `ie_registry_list`.

## Related docs

- `docs/tim-cycle.md`, `docs/cli.md`, `docs/agent-contract-v1.md`, `docs/context-layer.md`
