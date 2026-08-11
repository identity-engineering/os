# Space model

Status: architecture contract (locked direction 09.08.2026; framework alignment same day)

## Core claim

**Registry** stays with the **observing Identity**.
**Space** is the **membrane host**: where Identities are registered, where
Surface/MCP runs, and where jurisdiction policy is enforced.

| Unit | Meaning |
|------|---------|
| **Registry** | Observer-relative perception of other Identities (geometry frame) |
| **Space** | Host / membrane / jurisdiction plane (deployment + membership + policy) |
| **IE-managed Space** | Canonical bootstrap/public Space operated by IE |
| **Governed Space** | Isolated Team/Corp Space (IE-hosted federated or self-hosted) with stronger membrane policy |
| **IE Account** | Auth + billing on the IE product only - lives in IE-managed, not in every Space |

Local Free is not a failed cloud path. It is the minimal Space: one machine
hosting one (or few) Identities. IE-managed is one Space among many, with
network bootstrap and account responsibilities. Team premium is the right to
run an additional governed Space - not the only way to use IE as a team.

### Framework alignment (one Space)

Framework and OS name the **same** Space. Scientific lenses cut different aspects;
OS is where those aspects become operable together.

| Lens | Aspect of the same Space |
|------|--------------------------|
| **Physics** | Degrees of freedom / configuration arena |
| **Biology** | Boundary (membrane, selective exchange) |
| **OS** | Installable host: membership, Surface, membrane policy |

There are not two Spaces (framework vs operational). Open formal work on the
public site (e.g. metric / dimensionality) is incomplete **description** of this
Space, not a second ontology.

**Boundary is scale-invariant.** Every Identity has Boundary (Surface, consent,
jurisdiction edge) - human, agent, idea, org, and Space Identity. A Space
membrane is the Boundary of the **Space Identity**, not a collective-only
primitive. Member Identities keep their own Boundaries inside the host
(Multicellularity: nested membranes). Emergence is the scale jump when the
whole acquires its own trajectory and therefore its own Boundary.

Public framework pages: `/framework/space`, `/framework/boundary`,
`/framework/multicellularity`, `/os`.

## Why "Space" not "Registry host"

Calling the host a "registry" overloaded the observer-relative Registry and
suggested a shared team perception store. That would break Relativity.

A Space may **store** many Identities' data and run many Surfaces. Each member
Identity still holds its **own** relative Registry. The Space does not flatten
fifty observers into one alloy.

## Space-ID and sovereign Identity

Every Space has a **Space-ID**.

**Default:** Space-ID is 1:1 with a sovereign **Space Identity** (typically
substrate `org` or `collective`). That Identity is what appears in other
Identities' Registries, carries public Mass correlation, and is the membrane's
outward form - i.e. the form that **has** Boundary at collective scale.

- Creating a Team/Corp Space normally creates this Space Identity with it.
- A purely private membrane without a public Space Identity remains possible;
  it is the exception, not the product default.
- Additional brands, products, or sub-teams **inside** a Space are further
  Identities (idea/org/…), not nested Space-IDs by default.
- Explicit **sub-Spaces** are allowed later as governed children; membership
  cascades downward while primary hosting rules (below) still apply.

Biology lens (operational):

- **Space host** implements degrees of freedom + membrane policy together.
- **Space Identity** is the living form that membrane presents outward.
- **Membership** is Multicellularity-style nesting: members remain bounded
  units under host policy; they are not clones of the Space Identity.
- Trajectory effects (time in field, proximity to Stem, rotation) can change
  how Mass is perceived in relation to that Space Identity without dissolving
  member Boundaries.

## Layer stack (with Account ≠ Identity)

```text
IE Account (managed only: auth, plan)
  └── may create / pay for Identities and optional governed Spaces

Space (space_id = sovereign Space Identity by default)
  ├── membrane policy (what enters / leaves)  ← Boundary of Space Identity
  ├── membership → Identity IDs (reference, not clone; nested Boundaries)
  ├── hosts Surfaces (MCP / HTTP / local) for members
  └── may store space-allowed projections

Identity
  ├── one Stem / Tensor (primary host)
  ├── own relative Registry
  ├── own Boundary (Surface / consent / jurisdiction edge)
  ├── may be member of many Spaces
  └── harnesses / agents = further Identities (space-bound as needed)
```

See also `docs/account-identity-model.md` and
`docs/identity-creation-jurisdiction.md` (creator lineage + default grants).

## Many Spaces, one bootstrap

```text
IE-managed Space          ← accounts, public/default hosting, discovery
    ↑ membership / federation
Governed Space (Team)     ← stronger policy; IE-federated or self-hosted
Governed Space (Corp)     ← isolation + professional controls
Local mini-Space          ← Free install on a machine
```

All governed Spaces can **federate** toward IE-managed (become known, address
reachable Identities under policy) without uploading full private geometry.
"Known in IE-managed" means host descriptor, endpoints, policy caps, and
optional Public Cards - not a silent full Stem/Registry mirror.

**Known is not addressable by default.** Whether a member Identity that is
registered or discovered in a parent/main Space can be called on its Surface is
a grant + membrane decision. Creation-time jurisdiction packages and residual
emergency levers govern who may set those caps
(`docs/identity-creation-jurisdiction.md`).

### Product tiers (direction, not price sheet)

| Mode | What you get |
|------|----------------|
| **Free local** | Mini-Space on device; no account required |
| **Personal / default managed** | Identities hosted in IE-managed Space |
| **Team in IE-managed** | Fully valid: many Identities under accounts in the managed Space - not "premium isolation" |
| **Team/Corp premium** | **Additional governed Space** (IE-hosted federated **or** customer self-hosted) with harder overall membrane policy, isolation, and governance. Especially billable when IE operates that Space |

Premium is the **membrane**, not the right to exist as a team inside IE-managed.

## One human Identity, many Spaces

| Rule | Detail |
|------|--------|
| Human person | **One** Identity; primary host typically IE-managed Space |
| Agent / harness | Own Identity; usually bound to the Space where it operates |
| Join Space B | **Membership / registration** in B - not a second human Identity |
| Tensor / Stem | **One per Identity**, not per Space |
| Space-local effect | Policy, visible signals, grants, optional space-local projections |
| Actor context | Mutations carry `actor_identity_id` and, when relevant, `space_id` |

Hierarchy:

1. Primary host holds canonical geometry for that Identity.
2. Other Spaces **reference** the same `identity_id` via membership.
3. Sub-Spaces may register members downward; primary hosting stays explicit.
4. Work in Space A can change the one Tensor; Space B sees consequences only
   through membrane-allowed signals, cards, and grants - not by reading A's
   private store.

Harnesses remain distinct Identities (already locked). Multi-Space human work
is a richer tension field of **one** Identity, not multiple selves.

## Membrane security

The hard problem is not "one ID in many Spaces". It is **what the membrane
passes**.

Required controls:

1. **Space jurisdiction** - what membership allows Space B to know or write.
2. **Export policy** - which events, estimates, and fragments may leave.
3. **Inbound policy** - what may enter from IE-managed or other Spaces.
4. **No silent cross-Space Stem writes** - only Surface paths and explicit grants.
5. **Audit** - `actor_identity_id` + `space_id` on governed mutations.

### IAM as operational analogy (not a category replacement)

Enterprise IAM already names federation, principals, realms, and least
privilege. Useful mapping for implementation vocabulary:

| IAM term | IE reading |
|----------|------------|
| Principal | Identity |
| Realm / tenant | Space |
| Federation | Membership + trust between Spaces |
| Least privilege | Grants / Surface scopes |
| Policy enforcement point | Space membrane (Surface Runtime) |

IE must not collapse into a classical IdP product. Geometry stays primary;
IAM informs membrane enforcement and federation ops. A deeper framework
engagement with information-security Identity Engineering can follow as a
documented gap or foundations note without blocking this contract.

## Minimal data sketch

```text
spaces
  space_id                      -- = sovereign Space Identity id by default
  kind                          -- ie_managed | governed | local
  hosting                       -- ie_federated | self | local_device
  parent_space_id?              -- sub-Space cascade
  policy_json                   -- membrane defaults (Boundary of Space Identity)
  created_at / updated_at

space_memberships
  space_id
  identity_id
  primary_host                  -- bool: this Space is canonical host for geometry
  status                        -- active | revoked | invited
  joined_at / revoked_at?

space_trust / federation
  from_space_id
  to_space_id
  capabilities                  -- discover, address, relay_signals, …
  established_at

every mutation envelope
  actor_identity_id             -- always required
  space_id                      -- required when a Space membrane applies
                                -- (local mini-Space V1 may omit until Space rows exist)
```

Geometry tables remain Identity-scoped as in Open Core. Space rows add
hosting, membership, and membrane - they do not replace `registry_entries`.
There is no separate "collective Boundary" table: outer membrane is policy on
the Space / Space Identity; member Boundary is each Identity's Surface.

## Local V1 boundary slice

The local runtime exposes a public Space boundary descriptor through
`runtime/membrane.py` and:

```bash
ie space boundary export --to ~/ie-boundary.json --space-id <space-id>
ie space boundary verify --from ~/ie-boundary.json --space-id <space-id>
```

The descriptor contains the Space ID, public host metadata, an explicit
`full_private_geometry: false` export policy, and a checksum. It does not
contain the private SQLite tables or deterministic Identity-space export. A
verified inbound descriptor is classified as `known`, never implicitly
`addressable`, and never grants private-geometry access. This is the first
membrane contract slice, not full cross-Space enforcement: membership,
federation, endpoint policy, and signal gating still need persisted Space state.

## Relation to local Free V1

A local install is a **local mini-Space**:

- one Identity per install in V1,
- Registry remains observer-relative inside that Identity,
- no account required,
- optional later link: membership of that Identity into IE-managed Space
  without abandoning local sovereignty.

SQLite is the store engine for local / self-hosted Spaces, not the product
center. Product language is **Space-first / Identity-scoped** (see issue #59).

## Explicit non-goals (this contract)

- Implementing federated multi-region hosting ops in v0
- Forcing every team onto a governed Space
- Uploading full private geometry when a Space becomes "known" in IE-managed
- Shared team Registry that replaces per-Identity Registries
- Multiple human Identities for one person because they work in two Spaces
- A second Boundary concept for teams (use Space Identity Boundary + membership)
- Freezing Team/Corp price numbers

## Locked decisions summary

1. Registry = observer-relative; Space = membrane host.
2. Many Spaces; IE-managed is bootstrap, not the only host.
3. Space-ID defaults to sovereign Space Identity (org/collective).
4. Extra brands inside a Space are further Identities, not automatic new Spaces.
5. Human: one Identity, one Tensor; multi-Space via membership.
6. Agents/harnesses: separate Identities, typically space-bound.
7. Team default in IE-managed is valid; premium = additional governed Space.
8. Governed Space may be IE-federated or self-hosted; both are Team/Corp features.
9. Membrane policy governs cross-Space visibility; IAM informs, geometry leads.
10. Local Free remains a first-class mini-Space.
11. Framework and OS share one Space (physics degrees of freedom + biology Boundary + OS host).
12. Boundary is scale-invariant; Space membrane = Boundary of the Space Identity; members nest under Multicellularity, not a second Boundary primitive.

## Related

- `docs/account-identity-model.md` - Account ≠ Identity
- `docs/identity-creation-jurisdiction.md` - creator lineage, default grants, residual red button
- `docs/registry.md` - observer-relative Registry only
- `docs/identity-surface.md` - Surface per Identity; membrane approval rules
- `docs/storage-tiers.md` - Free local vs managed continuity
- `docs/living-form.md` - membrane / metabolism lens
- `docs/principles.md` - multi-substrate; relative by default
- Framework site: `/framework/space`, `/framework/boundary`, `/framework/multicellularity`, `/os`
- Issue #40 Access & Jurisdiction
- Issue #11 Multi-substrate symmetry
- Issue #59 Space-first Open Core wording
