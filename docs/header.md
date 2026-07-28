# Local entry vs Identity Surface (Header clarification)

Updated 28.07.2026

The name "Header" was misleading. Two different things were mixed:

1. **Local entry** — how *my* agent discovers *my* install (see `docs/local-entry.md`). Prefer AGENTS.md IE block; YAML only as one serialization.
2. **Identity Surface** — how *others* invoke operations on me (see `docs/identity-surface.md`). MCP and/or HTTP bindings of the same ops; bounded foreign-write; human approval for critical policy.

Inter-identity communication does **not** pass Vision by default. It passes the Interaction Signal into a policy-governed zone (see `docs/interaction-signal.md`, `docs/communication.md`).

Templates such as `templates/personal/HEADER.yaml` may be repurposed or renamed to a local-entry manifest in a follow-up commit; semantics above take precedence over older field lists that included vision_gradient as if it were a communication header.
