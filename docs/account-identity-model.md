# Account ≠ Identity

Status: architecture contract (locked direction 08.08.2026)

## Core claim

An **IE Account** is not an Identity.

| Unit | Role |
|------|------|
| **IE Account** | Auth, billing/plan, multi-identity container, jurisdiction root |
| **Identity** | Geometric unit: Surface, Registry, Mass, Stem, Public Card, signals |
| **Harness / Runtime / Agent / Idea / Org** | Substrate of an Identity — not a mode of the human owner |

One account may always hold **many Identities**, independent of substrate.
A human Identity, an agent Identity, an idea Identity, and a cloud-runtime
Identity are the same kind of geometric object. They differ in substrate and
in the jurisdiction relations between them — not in whether MCP may write.

## Why this exists

Earlier product language drifted toward "one account ≈ one Identity ≈ one
installation". That collapses three distinct layers:

1. who pays and authenticates (account),
2. who has geometry (identity),
3. where the process runs (harness / installation / cloud runtime).

Under multi-substrate symmetry, agents, ideas, and runtimes are Identities.
Each harness that acts for long enough deserves its own local geometry, its
own Registry perspective, and its own Public Card. The human who holds the
account creates those Identities and decides their jurisdiction — that
decision is not "MCP is read-only".

MCP and other Surface bindings **always write**. They write as the Identity
under which the session is authenticated. Scope is jurisdiction over *that*
Identity (and any explicit grants to others), not a global read/write flag.

## Layer model

```text
Account (auth + plan + jurisdiction root)
  └── Identity[]
        ├── substrate: human | runtime | idea | org | collective | other
        ├── Surface (MCP / HTTP / local CLI binding)
        ├── Registry (from this Identity's frame)
        ├── Stem / Workspace / Trajectory / Metric Stem
        ├── Foreign-estimate zone + emergent Self-Mass
        ├── Public Card
        └── Relations (creator, grant, peer, …)
  └── Membership / Grant rows
        └── which Identity may act on which object under which scope
  └── Installation / Harness bindings
        └── process ↔ Identity (typically 1:1 at a time)
```

### Account

- Owns authentication (e.g. Supabase Auth user on the managed path).
- Owns plan and entitlement metering.
- Is the container for Identities the holder creates or adopts.
- Does **not** replace local Free operation: local installs remain viable
  without an account.

### Identity

- Is the only unit that has geometry.
- Has exactly one substrate label for classification; substrate does not
  change the Surface contract.
- Exposes an Identity Surface (see `docs/identity-surface.md`).
- Holds a local Registry that is relative to itself (Relativity).
- Can send and receive Interaction Signals under policy.

### Harness binding

A harness (desktop CLI process, mobile app, chat-agent session, cloud worker)
binds to **one Identity at a time**. Switching Identity is an explicit context
switch, never a silent elevation to account-root.

Examples:

- Desktop local install → local Identity (Free, no account required).
- Same machine after `ie link` → that Identity is also a member of an account.
- Chat agent under managed MCP → authenticates as its **agent Identity**, not
  as the human Identity by default.
- Cloud runtime spawn → creates or resumes a runtime Identity with its own
  Surface, Registry, and Public Card.

### Actor is always explicit

Every mutation carries `actor_identity_id`.

There is no implicit "the account did this". UI, CLI, and MCP sessions that
act as the human Identity record the human Identity as actor. Agent sessions
record the agent Identity. Audit and Mature history stay geometrically honest.

## Jurisdiction (not read vs write)

| Operation | Default when authenticated as Identity I |
|-----------|------------------------------------------|
| Read/write I's own geometry (Stem, Registry, Mature, policy of I) | Allowed |
| Emit signals / serve Public Card as I | Allowed under I's Surface policy |
| Mutate Identity J under the same account | Only with an explicit grant |
| Critical Surface changes on I (new tools, wide grants, public write) | Allowed for I subject to the existing critical-approval rules |
| Account-level ops (billing, plan, delete account, force-delete Identity) | Account holder role (typically the primary human Identity), not any member Identity |

Self-write is full. Cross-Identity write inside an account is a **grant
question**, not an MCP capability question.

Cross-Identity interaction defaults to the normal Surface protocol
(Signal / Request / Receipt). Account-internal short paths are a later opt-in,
not the v0 default.

## Relation to local Free V1

SQLite-first V1 ships **one local Identity per installation**
(`docs/sqlite-schema-v1.md`). That remains a valid Free starting shape:

- no account required,
- full Ownership of the files,
- Surface and Mature on that single Identity.

Multi-Identity under one local install, and multi-Identity under one managed
account, are the same model at larger cardinality. Local V1 does not need to
implement N Identities before the contract is locked; schema evolution must
not invent a second meaning of Identity when N > 1 lands.

## Managed path implications

The managed foundation today maps `auth.users` → `managed_accounts` and
registers installations under the account. The multi-Identity model requires
the managed path to treat **Identity as a first-class row** under the account:

- `identities` (account_id, identity_id, substrate, creator_identity_id, …)
- installation → identity binding (not only account + local_handle)
- grants / relations between identities in the account
- every import, sync event, and Surface call scoped by `identity_id`
- plan metering primarily on **Identity count** (active members of the account),
  not on seats or raw API calls

Indicative metering direction (not a frozen price sheet):

| Tier | Identity capacity (order of magnitude) |
|------|------------------------------------------|
| Free (local, optional light account) | few (e.g. 1–5) |
| Personal Pro | tens |
| Team / Org | hundreds + shared-account semantics |

Exact limits, what counts as "active", and soft vs hard enforcement remain
product decisions. The architectural claim is: **meter the geometric unit**.

## Cloud runtime as Identity

A managed or self-hosted cloud runtime that can be triggered, holds context,
and speaks the Surface is an Identity:

1. spawn or resume runtime process,
2. bind or create runtime Identity under the account,
3. expose Surface (MCP/HTTP) as that Identity,
4. maintain Registry and learning state from its frame,
5. sleep or destroy under explicit lifecycle rules.

No special "worker mode" bypasses geometry. TIM-style cloud runtime ideas
land here as substrate `runtime`, not as an infra side channel.

## Explicit non-goals of this contract

- Replacing local Free with a mandatory account.
- Making every agent automatically the human Identity.
- Silent cross-Identity Mature or policy writes inside an account.
- Treating subscription tier as a change to geometric contracts.
- Requiring a global Identity graph or shared Registry across accounts.

## Implementation sketch (minimal data contract)

```text
accounts
  account_id
  auth_principal
  plan_code / status
  primary_identity_id?          -- optional convenience, not geometry

identities
  identity_id
  account_id?                   -- null for pure local Free
  substrate
  local_handle
  creator_identity_id?
  created_at / updated_at

identity_grants
  grant_id
  account_id?
  actor_identity_id
  object_identity_id
  scope                         -- e.g. mature, policy_read, surface_admin
  granted_at / revoked_at?

installations
  installation_id
  account_id?
  bound_identity_id             -- active Identity for this harness
  local_install_id
  …

every mutation envelope
  actor_identity_id             -- mandatory
```

Open Core local schema remains authoritative for geometry tables. Managed
projections mirror those tables keyed by `(account_id, identity_id)` once the
managed Identity layer exists.

## Relation to existing docs

- `docs/identity-surface.md` — Surface is per Identity; bindings are MCP/HTTP/local
- `docs/storage-tiers.md` — Free local vs managed continuity; same geometry
- `docs/sqlite-schema-v1.md` — V1 one Identity per install; evolution path above
- `docs/registry.md` — Registry is always observer-relative
- `docs/principles.md` — multi-substrate symmetry; Ownership as jurisdiction
- `docs/open-core.md` — account/managed features stay optional
- `docs/agent-contract-v1.md` — agents act as Identities via Surface/CLI; no direct DB writes
- Issue #40 Access & Jurisdiction — operational probes for degrees of freedom
- Issue #11 Multi-substrate symmetry

## Locked decisions summary

1. Account ≠ Identity.
2. One account may contain many Identities across substrates.
3. Harnesses bind to an Identity; they are not anonymous delegates of the account.
4. Surface/MCP write is always allowed for the authenticated Identity on its own geometry.
5. Cross-Identity power is grant-scoped jurisdiction, separate from transport capability.
6. Actor Identity is explicit on every mutation.
7. Plan metering should orient on Identity capacity under the account.
8. Local Free without account remains first-class.
