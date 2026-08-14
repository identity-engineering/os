---
name: mature
description: Directed, source-backed learning for the bound Identity (Self-Mature). Also used to integrate standard or foreign sources without blind overwrite. Human invokes; agent uses ie mature / Surface tools — never writes SQLite directly.
---

# Mature

You assist the **human Identity** bound to this IE install. This skill is the human command interface. **You** use the `ie` CLI and/or local MCP for every read and write.

Mature is the IE name for TIM’s third step. Prefer this word over Evolve.

## Relations (same act)

- **Self-Mature** — learning into this Identity’s substrate.
- **Foreign-Mature** — treat inbound Interaction Signals (and related evidence) as sources when the human is integrating peer feedback.
- **Standard-Mature (inbound)** — when the open standard changed, treat those changes as **sources**, not as a package install. Local is never a pure copy of the standard.

## When invoked (Self-Mature)

1. Confirm install and bound Identity: `ie status --json` or MCP `ie_status`.
2. Collect from the human (do not invent):
   - Causal notes
   - At least one **existing** evidence file under the install root (`--source`)
   - Optional: state delta, vision shift, commitment, ownership level, optionality, workspace/registry changes, peers to reassess
3. If no source file exists yet, help create a short evidence file under the install (e.g. `evidence/YYYY-MM-DD.md`), then proceed.
4. Run:

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

5. Report the result (IDs, changed fields). Do not claim Self-Mass was written.

## When invoked (inbound standard or foreign sources)

1. Obtain the change as **evidence** (diff, new skill text, signal payload, contract note) under the install root or as an explicit source path.
2. For each artifact:
   - If local is missing or clearly uncustomized vs last known standard pin → propose a **simple update** (still run Mature with that source so history stays causal).
   - If local was personalized → **adaptive path**: read standard/foreign intent and local intent; propose integration that preserves Identity-owned constructs; or decline. Do not overwrite silently.
3. Context Layer writes (skills) only via human-approved edits the agent performs after Mature reasoning — prefer documenting the decision in evidence, then `ie mature`, then editing skill files if the human agrees. Geometry stays CLI/MCP only.
4. Optional: Signal back to the standard or peer if the adaptive path rejects or improves the proposal (`propose-to-standard` / `signal` skills).

## Rules

- Actor is the bound Identity. Do not Mature another Identity without an explicit grant path.
- Prefer transactional `ie mature` over multi-step projection edits.
- Policy / Surface critical changes stay on `ie policy …`.
- Related reads: `ie mass`, `ie freedom`, `ie registry list`, MCP equivalents.

## Related docs

- `docs/mature.md`, `docs/tim-cycle.md`, `docs/cli.md`, `docs/agent-contract-v1.md`, `docs/context-layer.md`
