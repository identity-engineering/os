# Language strategy (locked)

Decision date: 29.07.2026

## Decision

**IE OS core and CLI are Python** for v0 and v1.

- Runtime: existing `runtime/` (apply, policy, storage, HTTP)
- CLI: `ie` via **Typer** (`ie/` package, entry point in `pyproject.toml`)
- Schemas and Identity artifacts remain **language-neutral** (YAML/JSON)

This is intentional, not a default by accident.

## What this is not

| Non-goal | Reason |
|----------|--------|
| IE OS kernel = LangGraph (or any agent framework) | Kernel is deterministic policy + contracts + local gravitational sensor |
| Rewrite to Go/Rust before distribution hurts | Premature; Python + Brew/public artifacts is enough for now |
| CLI language defines the Identity | Identity = Stem, Header, Registry, foreign-estimate zone, Surface policy — artifacts and invariants |

## Layering (stable model)

```text
Identity artifacts     language-neutral files + schemas
        ↑
ie CLI + Surface Runtime     Python (this decision)
        ↑
Optional agents              any runtime (Claude, Hermes, OpenClaw,
                             LangGraph, …) that call `ie` / HTTP / MCP
```

A LangGraph (or other) agent may **represent or operate** an Identity by using the IE CLI and Surface — it does not need to *be* the OS.

## Tension / registry graphs

Relative Mass, volume, and tension are **IE framework concepts**.
They are implemented as deterministic updates and derived views over Registry + foreign-estimate data.

Agent workflow graphs (LangGraph-style) are optional orchestration **above** that layer, not a substitute for it.

## Comparison note (OpenClaw, Hermes, …)

Those projects are **agent harnesses** (chat, tools, memory, skills).
IE OS is an **identity-geometry runtime**.
Their language choices are weak precedent for this core; useful only as ecosystem context.

## Go / other languages — explicit triggers only

Revisit a Go (or Rust) CLI or core **only if** one of these is real:

1. Single static binary without Python on the target machine is a hard requirement
2. winget/apt/brew packaging is blocked in practice by the Python dependency
3. Performance/isolation needs that the current core cannot meet

Until then: do not dual-track stacks.

## Distribution (orthogonal)

Language choice does not replace the need for **public release artifacts** (so Free install needs no GitHub token).
See `docs/distribution.md`. Brew-first via public tarball/wheel is fine; PyPI and other channels can follow in parallel with the same version.

## Related

- `docs/cli.md`
- `docs/distribution.md`
- `docs/principles.md`
- `docs/ecosystem-vision.md`
