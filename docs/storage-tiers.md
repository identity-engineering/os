# Storage Tiers

Locked 27.07.2026  
Open Core boundary clarified 02.08.2026  
Multi-identity account model linked 08.08.2026  
Space membrane model linked 09.08.2026  
Commercial price sheet removed from this public repo 28.08.2026

This file describes **storage backends and Space kinds**. Plan prices and Identity caps live in the private managed repository, not here.

## Decision

| Space kind | Storage | Character | Visibility |
|------|---------|-----------|------------|
| **Local mini-Space** | Local SQLite (`.ie/ie.sqlite3`) | On-device, full ownership, no account required | Open Core (this repository) |
| **IE-managed Space** | Hosted SQL (start: Supabase) | Continuity, account auth, multi-Identity membership | Closed (`identity-engineering/os-managed`) |
| **Governed Space** | IE-federated or self-hosted store | Stronger membrane, isolation, federation toward IE-managed | Closed / customer-operated |

Collective features layer as **Spaces**, not as a different geometry.

## Account, Identity, Space

- **Identity** always has geometry (Registry, Stem, Surface, …).
- **IE Account** is auth + billing on the IE product (managed Space only).
- **Space** is the membrane host (`docs/space-model.md`). Local install = mini-Space.
- Local path: no account required.
- Managed path: Identities hosted in the IE-managed Space.
- A team may operate inside the IE-managed Space. A **governed Space** is an additional membrane, not a second geometry.

See `docs/account-identity-model.md` and `docs/space-model.md`.

## Principles

1. **Same logical schema** everywhere. Registry entries, Metric Stem, Interaction Signals and emergent views speak identical contracts whether the backend is local SQLite or managed Postgres. YAML remains a contract/example format.
2. **Skills and agents are storage-agnostic.** They never hard-code a backend. An adapter layer selects local files, local SQLite or managed SQL.
3. **Local remains first-class Open Core.** No account is required for the core geometry loop. Local install = mini-Space.
4. **Managed is continuity and hosting**, not a change of the geometric model. The user still owns the data; IE operates the infrastructure. That implementation stays closed.
5. **Derived indexes** are always regenerable from the canonical store of the chosen Space kind.
6. **Mutations are Identity-scoped** (and Space-membrane-scoped when federated). Transport authenticates an Identity; it does not write as an anonymous account root.
7. **Registry stays observer-relative** even when many Identities share a Space host.
8. **Plan metering** (when a product plan exists) orients on Identity capacity and membrane strength. Exact numbers are not part of this public contract.

## Implementation sketch (start)

- Local: SQLite is the canonical local source of truth (mini-Space). The runtime exposes CLI/API projections; schemas and examples remain readable YAML in this repository.
- IE-managed Space: same geometry tables plus account, identity membership, space membership, grants, and installation→identity bindings. Row Level Security + authenticated access. Lives in the private managed repository.
- Governed Spaces (later): same geometry contracts behind a harder membrane; IE-federated hosting or customer self-host; federation descriptors toward IE-managed without full private upload by default.
- Migration path: export/import between local and managed so users can move Spaces without losing geometry.

## What this enables

- A public standard that others can implement without depending on our hosted service.
- Device-independent work for users on the managed path.
- Multiple Identities under accounts without collapsing them into the human Identity.
- Team isolation as Space policy, not as a second geometric model.

## Related

- `docs/space-model.md`
- `docs/account-identity-model.md`
- `docs/open-core.md`
- Private product terms: `identity-engineering/os-managed` `docs/pricing.md`
