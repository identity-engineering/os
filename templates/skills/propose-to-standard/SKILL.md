---
name: propose-to-standard
description: Standard-Mature outbound — turn a local learning into feedback for the open IE standard. Signal-first; optional GitHub issue as materialization. Human invokes; agent uses CLI/MCP only.
---

# Propose to standard (Standard-Mature)

## Purpose

Local Self-Mature improves **this** Identity. Collective improvement needs a path
to the shared standard. The standard is treated as a **public Identity**
(Identity Engineering / OS / framework), not only as a git repo.

**Primary act: Interaction Signal** toward that standard Identity (Foreign-/
Standard-Mature carrier). Opening a GitHub issue or PR is optional **materialization**
for humans and CI — not a substitute for the Signal.

## When invoked

1. Summarize the learning with the human (gap, what broke, proposed contract or skill change, evidence).
2. **Signal-first (required when a standard recipient handle/endpoint exists):**
   - Build an Interaction Signal whose payload carries a structured proposal
     (e.g. kind `standard_proposal` or clear notes fields: gap, proposal, evidence refs).
   - Apply via `ie signal apply` / MCP `ie_signal_apply` toward the standard Identity
     when the human has that destination configured.
   - Until a canonical standard handle is published, still **draft** the signal payload
     with the human and store it as evidence under the install.
3. **Optional materialization:** open a GitHub issue on `identity-engineering/os`
   (ops) or `identity-engineering/framework` (public concept) with the same summary.
   Do not push or merge to `main` without explicit human approval.
4. Close the loop locally if the human wants: evidence file + `ie mature` noting that
   standard feedback was filed (Signal and/or issue).

## Rules

- Prefer Signal semantics over tracker-only workflows.
- Do not auto-update remote repos.
- Inbound absorption of standard changes is **Mature over sources** (see `mature` skill and `docs/mature.md`) — not blind install.
- Geometry and policy stay on CLI/MCP.

## Related

- `docs/mature.md`, skills `mature` and `signal`, issue #92
