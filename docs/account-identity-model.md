# Account ≠ Identity

Status: architecture contract (locked direction 08.08.2026)  
Space membrane model linked 09.08.2026 - see `docs/space-model.md`  
Identity creation lineage + default jurisdiction linked 09.08.2026 - see `docs/identity-creation-jurisdiction.md`

## Core claim

An **IE Account** is not an Identity.

| Unit | Role |
|------|------|
| **IE Account** | Auth, billing/plan on the IE product (IE-managed Space only) |
| **Identity** | Geometric unit: Surface, Registry, Mass, Stem, Public Card, signals |
| **Space** | Membrane host: membership, Surface hosting, jurisdiction policy (`docs/space-model.md`) |
| **Harness / Runtime / Agent / Idea / Org** | Substrate of an Identity - not a mode of the human owner |

One account may always hold **many Identities**, independent of substrate.
A human Identity, an agent Identity, an idea Identity, and a cloud-runtime
Identity are the same kind of geometric object. They differ in substrate and
in the jurisdiction relations between them - not in whether MCP may write.

Identities are **members of Spaces**. Registry remains observer-relative on
each Identity. Hosting and membrane policy live on the Space.

## Why this exists

Earlier product language drifted toward "one account ≈ one Identity ≈ one
installation". That collapses distinct layers:

1. who pays and authenticates on IE (account),
2. who has geometry (identity),
3. where membrane and hosting jurisdiction sit (space),
4. where the process runs (harness / installation / cloud runtime).

Under multi-substrate symmetry, agents, ideas, and runtimes are Identities.
Each harness that acts for long enough deserves its own local geometry, its
own Registry perspective, and its own Public Card. The human who holds the
account creates those Identities and decides their jurisdiction - that
decision is not "MCP is read-only".

MCP and other Surface bindings **always write**. They write as the Identity
under which the session is authenticated. Scope is jurisdiction over *that*
Identity (and any explicit grants to others), not a global read/write flag.

## Layer model

```text
IE Account (auth + plan; managed Space only)
  └── may pay for Identities and optional governed Spaces

Space (membrane host; space_id ≈ sovereign Space Identity)
  └── Membership → Identity[]
        ├── substrate: human | runtime | idea | org | collective | other
        ├── Surface (MCP / HTTP / local CLI binding)
        ├── Registry (from this Identity's frame)
        ├── Stem / Workspace / Trajectory / Metric Stem
        ├── Foreign-estimate zone + emergent Self-Mass
        ├── Public Card
        └── Relations (creator, grant, peer, …)
  └── membrane policy + federation toward other Spaces

Installation / Harness bindings
  └── process ↔ Identity (typically 1:1 at a time) in a Space context
```

### Account

- Owns authentication (e.g. Supabase Auth user on the managed path).
- Owns plan and entitlement metering for the IE product.
- Is **not** the geometric container; Spaces and Identities are.
- Does **not** replace local Free operation: local mini-Spaces remain viable
  without an account.

### Identity

- Is the only unit that has personal/agent geometry (Stem, relative Registry).
- Has exactly one substrate label for classification; substrate does not
  change the Surface contract.
- Exposes an Identity Surface (see `docs/identity-surface.md`).
- Holds a local Registry that is relative to itself (Relativity).
- Can send and receive Interaction Signals under policy.
- May be a **member of many Spaces** with **one** Tensor / primary host
  (see `docs/space-model.md`).
- Records factual **creator lineage** and receives a **default jurisdiction
  grant package** at creation (see `docs/identity-creation-jurisdiction.md`).

### Harness binding

A harness (desktop CLI process, mobile app, chat-agent session, cloud worker)
binds to **one Identity at a time**. Switching Identity is an explicit context
switch, never a silent elevation to account-root.

Examples:

- Desktop local install → local Identity in a local mini-Space (Free, no account).
- Same machine after `ie link` → that Identity gains membership in IE-managed Space.
- Chat agent under managed MCP → authenticates as its **agent Identity**, not
  as the human Identity by default.
- Cloud runtime spawn → creates or resumes a runtime Identity with its own
  Surface, Registry, and Public Card.

### Actor is always explicit

Every mutation carries `actor_identity_id`. Governed/cross-membrane work also
carries `space_id` when the membrane applies.

There is no implicit "the account did this". UI, CLI, and MCP sessions that
act as the human Identity record the human Identity as actor. Agent sessions
record the agent Identity. Audit and Mature history stay geometrically honest.

## Jurisdiction (not read vs write)

| Operation | Default when authenticated as Identity I |
|-----------|------------------------------------------|
| Read/write I's own geometry (Stem, Registry, Mature, policy of I) | Allowed |
| Emit signals / serve Public Card as I | Allowed under I's Surface policy and current Space membrane |
| Mutate Identity J under the same account or Space | Only with an explicit grant |
| Critical Surface changes on I (new tools, wide grants, public write) | Allowed for I subject to the existing critical-approval rules |
| Account-level ops (billing, plan, delete account) | Account holder role (typically the primary human Identity) |
| Create governed Space / change Space membrane | Plan-gated Team/Corp capability + Space admin role |

Self-write is full. Cross-Identity write is a **grant question**, not an MCP
capability question. Cross-Space visibility is a **membrane question**.

Cross-Identity interaction defaults to the normal Surface protocol
(Signal / Request / Receipt). Account- or Space-internal short paths are a
later opt-in, not the v0 default.

**Creation-time default grants** give the creator an initial transferable
jurisdiction package over the new Identity (policy, visibility, surface admin).
Ordinary grants are revocable by the Child; a narrow residual emergency lever
remains for the creator line. Full semantics: `docs/identity-creation-jurisdiction.md`.

## Relation to local Free V1

SQLite-first V1 ships **one local Identity per installation**
(`docs/sqlite-schema-v1.md`). That remains a valid Free mini-Space:

- no account required,
- full Ownership of the files,
- Surface and Mature on that single Identity.

Multi-Identity and multi-Space are the same model at larger cardinality.
Local V1 does not need N Identities before the contract is locked; schema
evolution must not invent a second meaning of Identity when N > 1 lands.

## Managed path implications

The managed foundation maps `auth.users` → `managed_accounts` and registers
installations under the account. The multi-Identity **and** Space models
require the managed path to treat:

- **Identity** as a first-class row,
- **Space** as membrane host (IE-managed Space first; governed Spaces later),
- installation → identity binding (and space context),
- grants between identities (including creation-time default packages),
- membership of identities in Spaces,
- every import, sync event, and Surface call scoped by `identity_id`
  (and `space_id` when membrane-bound),
- plan metering on **Identity capacity** and, for premium, **governed Space**
  capability - not only raw API calls.

Indicative metering direction (not a frozen price sheet):

| Tier | Direction |
|------|-----------|
| Free (local mini-Space, optional light account) | few Identities |
| Personal Pro | more Identities in IE-managed Space |
| Team / Org | many Identities in managed Space **and/or** governed Space (IE-federated or self-hosted) |

Exact limits remain product decisions. Architecture: **meter geometry and
membrane**, not seats alone.

## Cloud runtime as Identity

A managed or self-hosted cloud runtime that can be triggered, holds context,
and speaks the Surface is an Identity:

1. spawn or resume runtime process,
2. bind or create runtime Identity (membership in a Space),
3. expose Surface (MCP/HTTP) as that Identity,
4. maintain Registry and learning state from its frame,
5. sleep or destroy under explicit lifecycle rules.

No special "worker mode" bypasses geometry. Legacy cloud-runtime ideas land
here as substrate `runtime`, not as an infra side channel.

## Explicit non-goals of this contract

- Replacing local Free with a mandatory account.
- Making every agent automatically the human Identity.
- Silent cross-Identity Mature or policy writes.
- Treating subscription tier as a change of geometric contracts.
- Requiring a global shared Registry across Spaces.
- Multiple human Identities for one person because they work in two Spaces.

## Implementation sketch (minimal data contract)

```text
accounts
  account_id
  auth_principal
  plan_code / status
  primary_identity_id?          -- optional convenience, not geometry

spaces                           -- see docs/space-model.md
  space_id
  kind / hosting / policy

identities
  identity_id
  account_id?                   -- null for pure local Free
  primary_space_id?             -- canonical host Space when known
  substrate
  local_handle
  creator_identity_id?          -- factual lineage; see identity-creation-jurisdiction.md
  created_at / updated_at

space_memberships
  space_id
  identity_id
  primary_host
  status

identity_grants
  grant_id
  actor_identity_id
  object_identity_id
  scope
  residual?                     -- narrow emergency lever flag
  transferable
  space_id?
  granted_at / revoked_at?
  granted_by_identity_id

installations
  installation_id
  account_id?
  bound_identity_id
  space_id?
  local_install_id
  …

every mutation envelope
  actor_identity_id             -- mandatory
  space_id?                     -- when membrane applies
```

Open Core local schema remains authoritative for geometry tables. Managed
projections mirror those tables keyed by identity (and space membership) once
the managed Identity/Space layer exists.

## Relation to existing docs

- `docs/space-model.md` - Space membrane host; multi-Space membership
- `docs/identity-creation-jurisdiction.md` - creator lineage, default grants, residual red button
- `docs/identity-surface.md` - Surface is per Identity; bindings are MCP/HTTP/local
- `docs/storage-tiers.md` - Free local vs managed continuity; same geometry
- `docs/sqlite-schema-v1.md` - V1 one Identity per install; evolution path above
- `docs/registry.md` - Registry is always observer-relative
- `docs/principles.md` - multi-substrate symmetry; Ownership as jurisdiction
- `docs/open-core.md` - account/managed features stay optional
- `docs/agent-contract-v1.md` - agents act as Identities via Surface/CLI; no direct DB writes
- Issue #40 Access & Jurisdiction - operational probes for degrees of freedom
- Issue #11 Multi-substrate symmetry

## Locked decisions summary

1. Account ≠ Identity.
2. One account may create/pay for many Identities; geometry lives on Identities.
3. Spaces host membership and membrane; Registry stays per observing Identity.
4. Harnesses bind to an Identity; they are not anonymous delegates of the account.
5. Surface/MCP write is always allowed for the authenticated Identity on its own geometry.
6. Cross-Identity power is grant-scoped; cross-Space visibility is membrane-scoped.
7. Actor Identity is explicit on every mutation; `space_id` when membrane applies.
8. Plan metering orients on Identity capacity and governed-Space capability.
9. Local Free without account remains first-class (mini-Space).
10. Identity creation records lineage and issues a transferable default jurisdiction package; ordinary Parent grants are Child-revocable; residual emergency lever is narrow and audited (`docs/identity-creation-jurisdiction.md`).
