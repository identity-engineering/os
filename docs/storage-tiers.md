# Storage Tiers

Locked 27.07.2026  
Open Core boundary clarified 02.08.2026

## Decision

| Tier | Storage | Character | Visibility |
|------|---------|-----------|------------|
| **Free** | Local SQLite (`.ie/ie.sqlite3`) | Full ownership, offline-first, "Setz dir das einfach auf" | Open Core (this repository) |
| **Personal Pro** | IE-managed SQL (start: Supabase) | Device-independent, backups, central truth, authenticated skill access | Closed (managed path) |

Collective / organisation features can layer on top later.

## Principles

1. **Same logical schema** everywhere. Registry entries, Metric Stem, Interaction Signals and emergent views speak identical contracts whether the backend is local SQLite or managed Postgres. YAML remains a contract/example format.
2. **Skills and agents are storage-agnostic.** They never hard-code a backend. An adapter layer selects local files, local SQLite or managed SQL.
3. **Free remains local-first.** No account, no cloud dependency, full Ownership of the files. This path is part of the Open Core.
4. **Personal Pro is a managed convenience and continuity layer**, not a change of the geometric model. The user still owns the data; IE operates the infrastructure, backups and multi-device access. The implementation of this layer stays closed.
5. **Derived indexes** (vector index for distance queries, etc.) are always regenerable from the canonical store of the chosen tier.

## Implementation sketch (start)

- Free: SQLite is the canonical local source of truth. The runtime exposes CLI/API
	projections; schemas and examples remain readable YAML in the repository.
- Personal Pro: Supabase (Postgres) with the same tables; Row Level Security + authenticated access; skill uses the managed connection. Lives in the private managed repository / modules.
- Migration path: export/import between local files and managed tables so users can move tiers without losing geometry.

## What this enables

- Clear, sellable Personal Pro subscription without betraying the free local-first promise.
- Device-independent work for paying users.
- Clean separation of geometric contracts from infrastructure concerns.
- Open Core that others can implement and extend without depending on our managed service.

## Related

- `docs/open-core.md`
