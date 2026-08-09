# Identity creation lineage and default jurisdiction

Status: architecture contract (design lock 09.08.2026)

Related: `docs/account-identity-model.md`, `docs/space-model.md`, `docs/identity-surface.md`, issue #40

## Core claim

Creating an Identity is two things at once:

1. **Lineage** (factual origin): who brought this Identity into existence.
2. **Jurisdiction package** (operational power): a default set of grants issued at creation time.

Parent-Child is therefore not a second geometry layer and not classical ownership of the Child's Stem. It is **creator lineage + transferable default grants**, with a narrow residual emergency lever for the original creator line.

The Child's Stem remains the Child's. Sovereignty over the Stem stays with the Identity that holds it. Jurisdiction over policy, visibility, and Surface is relative and grant-scoped.

## Why this exists

Without an explicit creation-time jurisdiction model:

- Nested Spaces and member Identities lack a clear answer to "who may set policy for this Identity?".
- Identities that become known in a parent or main Space risk being treated as public merely because they are registered.
- Governance of agents, ideas, and local mini-Spaces drifts into either silent account-root power or no residual control at all.

This contract closes that gap with primitives already sketched: `creator_identity_id`, grants, Space membrane, and Surface policy.

## Lineage (descriptive)

Every Identity records its creator when known:

```text
identities
  identity_id
  creator_identity_id?     -- factual parent; null only for bootstrap / genesis cases
  ...
```

Lineage is audit history, not automatic full power. Grandparent relations are reconstructible from the creator chain. They do **not** confer silent elevation.

## Default jurisdiction package (normative at creation)

On successful Identity creation the runtime issues a **default grant set** to the creator (or to a designated initial admin Identity when creation is delegated).

Indicative scopes (names may evolve; semantics locked):

| Scope | Initial meaning |
|-------|-----------------|
| `policy_admin` | Change Surface access policy, consent defaults, criticality rules for this Identity |
| `visibility_control` | Set discovery / addressability caps (known vs reachable) relative to Spaces and peers |
| `surface_admin` | Manage non-critical Surface tooling under existing critical-approval rules |
| `grant_admin` | Issue and revoke ordinary grants on this Identity (not residual) |

These grants are **roles in effect**, not permanent titles. They start with the creator and are transferable.

### Transfer

Any holder of a transferable grant may hand it to another Identity (individual, team admin Identity, or Space-admin role) under audit. After transfer, the previous holder loses that operational power unless a new grant is issued. Lineage (`creator_identity_id`) does not change.

### Child revocation of ordinary Parent power

The Child Identity may revoke ordinary grants held over it (including those that originated as the creation-time default set), subject to audit. This preserves agency: a mature agent or idea Identity is not permanently subordinate in policy merely because it was spawned.

## Residual red button (narrow, non-ordinary)

The original creator line retains a **residual emergency capability** that is not fully extinguished by ordinary Child revocation.

| Residual may | Residual must not |
|--------------|-------------------|
| Emergency Surface freeze / quarantine of the Child Identity | Silent Stem, Vision, or Mature writes |
| Force a visibility / membrane-cap re-evaluation | Unrestricted policy rewrite without audit |
| Trigger audit-visible emergency policy caps | Automatic Grandparent elevation up the lineage chain |

Properties of the residual:

- Always audited (`actor_identity_id`, reason, timestamp).
- Narrow by default; widening it is itself a critical policy change.
- Does not equal full admin. It is a last lever, not a standing override of the Child's Stem sovereignty.
- Implementation may bind residual to the original `creator_identity_id` or to an explicit residual grant that cannot be fully stripped by the Child alone (product decision under #40 probes).

Grandparent residual is **not** automatic. Only the direct creation package and any explicitly assigned residual apply unless a later policy states otherwise.

## Known vs addressable

Registration or discovery in a parent Space (including IE-managed / main Space) does not imply addressability.

- **Known**: membrane-allowed existence, host descriptor, or minimal Public Card stub.
- **Addressable**: Surface endpoints and grants that allow others to call the Identity.

`visibility_control` (and Space membrane policy) decide the difference. Parent or current grant holders set the caps; Child agency and residual interact as above.

This is the operational answer for Identities that bubble up from nested or open Spaces into a main Space without becoming public by default.

## Relation to Space nesting

Space nesting (`parent_space_id`) and Identity creation lineage are parallel, not identical:

- A Space Identity is created like any Identity; it receives the same lineage + default grant package.
- Member Identities inside a Space keep their own creator lineage and grants.
- Space membrane policy constrains what may cross the Space Boundary; it does not replace Identity-level grants.
- Multicellularity: nested membranes. Member Boundaries stay intact under host policy.

## Relation to Ownership (framework)

Framework Ownership (Access + Jurisdiction as relative degrees of freedom) remains the conceptual reading frame. This OS contract operationalizes **Jurisdiction at creation time** without promoting Ownership to a new Core Concept or claiming legal title.

Sovereignty over the Stem is still the highest relative jurisdiction an Identity exercises over itself. Creation grants are Access Agreements with default weight, not property.

## Explicit non-goals

- Parent as absolute owner of the Child Stem
- Automatic Grandparent override of intermediate Parents
- Silent account-root power over all Identities under an account
- Treating "registered in main Space" as public Surface access
- Residual red button as unrestricted admin
- Replacing Space membrane policy with lineage alone

## Implementation sketch (minimal)

```text
identities
  identity_id
  creator_identity_id?
  ...

identity_grants
  grant_id
  actor_identity_id          -- grantee
  object_identity_id         -- the Identity whose policy/surface is affected
  scope                      -- policy_admin | visibility_control | ...
  residual?                  -- bool or separate residual table
  transferable               -- bool
  space_id?                  -- when grant is membrane-scoped
  granted_at / revoked_at?
  granted_by_identity_id

creation transaction
  1. insert identity (creator_identity_id set)
  2. insert default grant set to creator (transferable, residual flag as designed)
  3. optional membership row if created inside a Space
  4. audit receipt
```

Local Free V1 may continue with a single Identity per install; the contract applies when multi-Identity and managed creation land.

## Locked decisions summary

1. Creation records factual lineage (`creator_identity_id`).
2. Creation issues a default, transferable jurisdiction grant set to the creator.
3. Ordinary Parent grants are revocable by the Child.
4. A narrow residual emergency lever remains for the creator line; it is audited and not full admin.
5. Grandparent power is not automatic.
6. Known in a Space is not the same as addressable; visibility is grant + membrane.
7. Stem sovereignty stays with the Identity; Parent-Child is lineage + grants, not ownership of geometry.
8. Operational detail and probes live under issue #40; this doc is the creation-time lock.

## Related

- `docs/account-identity-model.md` - Account ≠ Identity; grants; actor envelopes
- `docs/space-model.md` - Space membrane; membership; parent_space_id
- `docs/identity-surface.md` - Surface policy ownership; critical approval
- Issue #40 - Access & Jurisdiction probes and storage
- Framework: Ownership as Relative Jurisdiction (blog); gap #32
