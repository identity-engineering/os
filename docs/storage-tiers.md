# Storage Tiers

Locked 27.07.2026  
Open Core boundary clarified 02.08.2026  
Multi-identity account model linked 08.08.2026  
Space membrane model linked 09.08.2026

## Decision

| Tier | Storage | Character | Visibility |
|------|---------|-----------|------------|
| **Free** | Local SQLite (`.ie/ie.sqlite3`) | Local **mini-Space**, full ownership, offline-first | Open Core (this repository) |
| **Personal Pro** | IE-managed SQL (start: Supabase) | Continuity in **IE-managed Space**, multi-identity, authenticated skill/MCP | Closed (managed path) |
| **Team/Corp premium** (direction) | Governed Space store (IE-federated or self-hosted) | Stronger membrane, isolation, federation to IE-managed | Closed / customer-operated |

Collective features layer as **Spaces**, not as a different geometry.

## Account, Identity, Space

- **Identity** always has geometry (Registry, Stem, Surface, …).
- **IE Account** is optional continuity + billing on the IE product (managed Space only).
- **Space** is the membrane host (`docs/space-model.md`). Local install = mini-Space.
- Free V1: one Identity per install, no account required.
- Default managed: Identities hosted in IE-managed Space.
- Team may fully operate inside IE-managed Space; **premium** is an additional
  governed Space (IE-hosted or self-hosted) with harder policy.

See `docs/account-identity-model.md` and `docs/space-model.md`.

## Principles

1. **Same logical schema** everywhere. Registry entries, Metric Stem, Interaction Signals and emergent views speak identical contracts whether the backend is local SQLite or managed Postgres. YAML remains a contract/example format.
2. **Skills and agents are storage-agnostic.** They never hard-code a backend. An adapter layer selects local files, local SQLite or managed SQL.
3. **Free remains local-first.** No account, no cloud dependency, full Ownership of the files. This path is part of the Open Core.
4. **Personal Pro is a managed convenience and continuity layer**, not a change of the geometric model. The user still owns the data; IE operates the infrastructure, backups and multi-device access. The implementation of this layer stays closed.
5. **Derived indexes** (vector index for distance queries, etc.) are always regenerable from the canonical store of the chosen tier.
6. **Mutations are Identity-scoped** (and Space-membrane-scoped when federated). Transport authenticates an Identity; it does not write as an anonymous account root.
7. **Registry stays observer-relative** even when many Identities share a Space host.

## Implementation sketch (start)

- Free: SQLite is the canonical local source of truth (mini-Space). The runtime exposes CLI/API projections; schemas and examples remain readable YAML in the repository.
- Personal Pro: Supabase (Postgres) with the same geometry tables plus account, identity membership, space membership, grants, and installation→identity bindings. Row Level Security + authenticated access; skills/MCP use the managed connection. Lives in the private managed repository / modules.
- Governed Spaces (later): same geometry contracts behind a harder membrane; IE-federated hosting or customer self-host; federation descriptors toward IE-managed without full private upload by default.
- Migration path: export/import between local and managed so users can move tiers without losing geometry.

## What this enables

- Clear Free → Pro → Team membrane story without betraying local-first.
- Device-independent work for paying users.
- Multiple Identities under accounts without collapsing them into the human Identity.
- Team isolation as Space policy, not as a second geometric model.
- Open Core that others can implement and extend without depending on our managed service.

## Related

- `docs/space-model.md`
- `docs/account-identity-model.md`
- `docs/open-core.md`
