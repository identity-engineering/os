# Storage Tiers

Locked 27.07.2026  
Open Core boundary clarified 02.08.2026  
Multi-identity account model linked 08.08.2026  
Space membrane model linked 09.08.2026  
Product path updated 28.08.2026: Free Managed is the recommended entry

Price sheet: `docs/pricing.md`.

## Decision

| Path | Storage | Character | Visibility |
|------|---------|-----------|------------|
| **Free Managed** | IE-managed SQL (start: Supabase) | Recommended entry. Account + continuity in the **IE-managed Space**. Hard cap: 3 Identities. | Closed managed path |
| **Local private Space** | Local SQLite (`.ie/ie.sqlite3`) | Separate private mini-Space for people who want data on-device. Not the default product. | Open Core (this repository) |
| **Personal Pro** | IE-managed SQL + optional 1 connected Local Space | Continuity, more Identity slots, history, basic policy, Local-Space connector | Closed (managed path) |
| **Team / Corp** | Governed Space store (IE-federated or self-hosted) | Stronger membrane, isolation, federation to IE-managed | Closed / customer-operated |

Collective features layer as **Spaces**, not as a different geometry.

## Account, Identity, Space

- **Identity** always has geometry (Registry, Stem, Surface, …).
- **IE Account** is auth + billing on the IE product (managed Space). Required for Free Managed and above.
- **Space** is the membrane host (`docs/space-model.md`).
- Local private Space: no account required. Isolated by default. Connector rules are specified later; Pro is the intended unlock for 1 connected Local Space.
- Default product path: Identities hosted in IE-managed Space.
- Team may fully operate inside IE-managed Space; **premium** is an additional governed Space (IE-hosted or self-hosted) with harder policy.

See `docs/account-identity-model.md`, `docs/space-model.md`, and `docs/pricing.md`.

## Principles

1. **Same logical schema** everywhere. Registry entries, Metric Stem, Interaction Signals and emergent views speak identical contracts whether the backend is local SQLite or managed Postgres. YAML remains a contract/example format.
2. **Skills and agents are storage-agnostic.** They never hard-code a backend. An adapter layer selects local files, local SQLite or managed SQL.
3. **Local remains viable and Open Core.** No account is required for a private local Space. This is not the recommended Free product; it is the private alternative.
4. **Free Managed is the easy entry.** Continuity, multi-device, and standard skills live here under a hard Identity cap.
5. **Personal Pro is capacity + connector**, not a change of the geometric model. The user still owns the data; IE operates managed infrastructure. The implementation of this layer stays closed.
6. **Derived indexes** (vector index for distance queries, etc.) are always regenerable from the canonical store of the chosen path.
7. **Mutations are Identity-scoped** (and Space-membrane-scoped when federated). Transport authenticates an Identity; it does not write as an anonymous account root.
8. **Registry stays observer-relative** even when many Identities share a Space host.

## Implementation sketch (start)

- Free Managed: same geometry tables plus account, identity membership, space membership, grants, and installation→identity bindings. Row Level Security + authenticated access. Lives in the private managed repository / modules. Cap: 3 Identities.
- Local private Space: SQLite is the canonical on-device source of truth. The runtime exposes CLI/API projections; schemas and examples remain readable YAML in the repository.
- Personal Pro: same managed store with higher Identity capacity, full history, and one Local-Space connector.
- Governed Spaces (later): same geometry contracts behind a harder membrane; IE-federated hosting or customer self-host; federation descriptors toward IE-managed without full private upload by default.
- Migration path: export always. Managed link / connector policy comes later and is expected to be plan-gated.

## What this enables

- Managed as the recommended product path without abandoning Open Core local runtime.
- Clear Free Managed → Pro → Team membrane story.
- Device-independent work from the first recommended install.
- Multiple Identities under accounts without collapsing them into the human Identity.
- Team isolation as Space policy, not as a second geometric model.
- Open Core that others can implement and extend without depending on our managed service.

## Related

- `docs/pricing.md`
- `docs/space-model.md`
- `docs/account-identity-model.md`
- `docs/open-core.md`
