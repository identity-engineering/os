# Managed multi-Identity + Space membership

Status: design contract for OS #80 (post-#77 local foundation)
Local schema remains source of truth for Free. Managed is additive Pro mirror.

## Goal

Mirror the local Space + multi-Identity foundation onto the **managed / account**
path so manage-first is operational, not only local Free.

Local already has (schema v8):

- `spaces` (kind: local | ie_managed | governed)
- `space_memberships` (primary_host, status)
- `install.active_identity_id`
- N identities per install (UNIQUE(install_id) dropped)

Managed must use the **same logical model** under account binding without a
parallel geometry.

## Binding rules (locked)

1. **Account ≠ Identity** remains law (`docs/account-identity-model.md`).
2. Account is auth + billing surface only. Geometry lives on Identity.
3. **Installation ↔ Identity** binding stays install-scoped:
   - `install.active_identity_id` selects the local active Identity
   - one install may host many Identities (local Free already)
   - one account may host many Identities across many installs
4. When an install links to an account (`install.account_id` / `account_mode`),
   the local Identity rows and their primary Space memberships become candidates
   for managed mirror. No forced migration of pure Free installs.
5. Active Identity remains install-local. Account never silently elevates to
   account-root for Surface/MCP writes.
6. Space kind on managed mirror is typically `ie_managed` with hosting
   `ie_federated`. Local mini-Space stays `kind=local`, `hosting=local_device`.

## Managed table mirror (Postgres / Supabase sketch)

Same shapes as local Open Core. Indicative only; full DDL lives with Phase 3
(#24).

```text
managed_accounts
  account_id          -- maps auth.users
  plan_code / status
  primary_identity_id?  -- convenience, not geometry

managed_installations
  installation_id
  account_id?
  local_install_id    -- client-side install_id when linked
  bound_identity_id   -- currently bound / last active
  space_id?           -- primary managed Space context when known
  …

identities            -- same columns as local identity +
  account_id?         -- null for pure local Free never linked
  primary_space_id?

spaces                -- same columns as local spaces
  -- kind often 'ie_managed' for account-hosted rows

space_memberships     -- same PK (space_id, identity_id)

identity_grants       -- already local; mirror under account for cross-device
```

Geometry tables (registry, stem, …) stay Identity-scoped. Space rows add
membership and membrane only.

## managed_sync streams (extension of existing queue)

Existing queue already supports durable envelopes and recovery
(`docs/managed-sync-queue.md`). Today only `interaction.signal` is validated.

Additional streams for the multi-Identity / Space layer (v0 contract):

| Stream pattern | entity_type | Purpose |
|----------------|-------------|---------|
| `identity:{id}:interaction` | `interaction.signal` | already shipped |
| `identity:{id}:profile` | `identity.profile` | handle, preferred_name, substrate, accepts flags |
| `install:{id}:membership` | `space.membership` | space_id, identity_id, primary_host, status |
| `space:{id}:policy` | `space.policy` | policy_json changes (membrane defaults) |

Conflict policy:

- **Local Free is authoritative offline.** Managed is optional continuity.
- On link: local rows win for identity/space that already exist; managed may
  supply additional memberships from other devices under the same account.
- Idempotency remains event_id + idempotency_key + payload checksum.
- No silent overwrite of local Stem/Registry from managed without explicit
  import path.

Implementation of the new entity_type validators is deferred until the managed
HTTP surface accepts them (#24). Local queue schema needs no change; only
envelope validation widens later.

## CLI / product surface (minimal, non-blocking)

- `ie status` / identity list already show active Identity and space when present.
- Future: mark Identities that have a managed mirror vs local-only (read
  `install.account_id` + optional managed flag).
- `ie login` / account link remains on Phase-3 issues (#25/#26). This contract
  does not implement auth.

## Explicit non-goals (this slice)

- Stripe / webhook / billing (#26)
- Full Supabase schema + RLS (#24)
- Cross-install federation / membrane export runtime
- Multi-human membership across Spaces
- Changing Stem / Registry geometry contracts

## Exit criteria mapping

- [x] Design note: this file
- [x] Links to #24 / #25 / #26 without blocking on them
- [x] Local schema remains source of truth for Free; managed additive
- [ ] `docs/next.md` stays aligned (updated in same PR)

## Related

- #77 local Space + multi-Identity foundation (closed)
- #79 active Identity on all local call sites (closed)
- `docs/space-model.md`, `docs/account-identity-model.md`
- `docs/managed-sync-queue.md`, `docs/storage-tiers.md`
- Phase 3: #24 Supabase schema + Auth + RLS, #25 auth/login surface, #26 Stripe
