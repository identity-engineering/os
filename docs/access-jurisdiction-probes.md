# Access & Jurisdiction probes

Status: operational contract (v0, closes issue #40)

Related: `docs/identity-creation-jurisdiction.md`, `docs/account-identity-model.md`,
`docs/space-model.md`, `docs/metric-stem.md`, Framework Ownership blog + gap #32

## Core claim

Ownership (framework) is the relative distribution of degrees of freedom:

| Layer | Question |
|-------|----------|
| **Access** | Who can reach, use, observe, or be affected by the thing? |
| **Jurisdiction** | Who can decide about the thing (goals, constraints, transfer, destroy, redefine boundary)? |
| **Sovereignty** | Highest relative jurisdiction an Identity exercises over its own Stem |

The only durable claim is over the Identity Stem. Everything else is better
described as Access Agreements. This document operationalizes **measurement**
of those degrees of freedom so the OS can store and later feed them into Metric
Stem / Registry without inventing legal title.

Operational power (who *holds* grants) lives in `identity_grants` and the
creation package (`docs/identity-creation-jurisdiction.md`). Probes measure
*perceived / observed* degrees of freedom. The two layers must not be confused.

## Probe protocols (v0)

### Access probe

Maps current Access degrees of freedom for a given object relative to the
observer.

| Field | Meaning |
|-------|---------|
| `reach` | Can the observer reach / address the object (known vs addressable)? |
| `use` | Can the observer use or act through the object under policy? |
| `observe` | Can the observer read public or consented signals / card / estimates? |
| `affected_by` | Is the observer causally affected by the object's trajectory? |

Each field is either a relative score in `[0, 1]` with confidence, or a short
qualitative tag (`none` / `limited` / `open`) plus confidence. Both forms are
valid; scores are preferred when the observer has enough interaction depth.

### Jurisdiction probe

Maps decision rights / constraint power over the same object.

| Field | Meaning |
|-------|---------|
| `decide_goals` | Who may set or shift goals for the object? |
| `constrain` | Who may constrain uses, Surface policy, or membrane caps? |
| `transfer` | Who may transfer grants or membership? |
| `destroy` | Who may retire / freeze / quarantine the object? |
| `redefine_boundary` | Who may change the Boundary (Surface, consent, visibility)? |

Same score-or-tag shape as Access. Residual emergency levers (if any) are
recorded under `constrain` / `destroy` with an explicit `residual: true` note,
never as silent full admin.

### Output shape

```text
access_jurisdiction_profile
  profile_id
  observer_identity_id          -- always the local Identity in V1
  object_kind                   -- self | peer | stem_aspect | space
  object_ref                    -- peer_handle | "self" | aspect name | space_id
  observed_at                   -- UTC RFC3339
  confidence                    -- 0.0–1.0 overall
  access_json                   -- { reach, use, observe, affected_by, ... }
  jurisdiction_json             -- { decide_goals, constrain, transfer, destroy, redefine_boundary, ... }
  notes
  source                        -- owner_probe | mature | cli | agent
  revision
  created_at / updated_at
```

Profiles are **owned learning state**. They are never written by inbound
Interaction Signals. Foreign estimates and Registry `perceived_ownership_json`
may *inspire* a later owner probe; they do not auto-populate this table.

## Storage

Table `access_jurisdiction_profiles` (SQLite-first V1).

- One row per (observer, object_kind, object_ref, revision chain).
- Current projection + append-only history via revision counter.
- Owner-gated write path only (local Identity / explicit actor that holds
  `grant_admin` or is the object itself for self-probes).

Registry entries keep `perceived_ownership_json` as a lightweight peer-facing
summary; the profile table is the canonical measured record when the owner
commits a probe.

## Write path (owner-gated)

```bash
# Commit an Access + Jurisdiction profile for a peer (or self)
ie jurisdiction probe --object peer:alice \
  --access '{"reach":0.8,"use":0.3,"observe":0.9,"affected_by":0.6}' \
  --jurisdiction '{"decide_goals":0.1,"constrain":0.2,"transfer":0.0,"destroy":0.0,"redefine_boundary":0.1}' \
  --confidence 0.7 \
  --notes "post-interaction assessment"

ie jurisdiction show --object peer:alice
ie jurisdiction list
```

Library entry points live in `runtime/jurisdiction.py`:

- `write_profile(...)` — validates shape, writes under local `identity_id`
- `get_profile(...)` / `list_profiles(...)`

Actor is always the local Identity in V1. Cross-Identity writes require an
active grant (`grant_admin` or equivalent) and are deferred until multi-Identity
creation lands.

## Relation to creation package and residual

- Creation-time grants (`identity_grants`) answer "who may act".
- Probes answer "what degrees of freedom do I currently perceive".
- Residual emergency lever is a grant flag; a probe may *observe* its presence
  under `constrain` / `destroy` but cannot create or widen residual power.
- Child revocation of ordinary grants is grant-plane; probes simply re-measure
  after the fact.

## Relation to Space membrane

Space membrane policy (export / inbound) is a separate enforcement surface
(`docs/space-model.md`, issue #61). A probe may record membrane-relative Access
(e.g. `reach` limited by parent Space) but does not itself enforce membrane
rules. Known ≠ addressable remains grant + membrane, not a probe output alone.

## Metric Stem / dimensions

Access and Jurisdiction fields are candidates for contentful Metric Stem
dimensions (issue #16). v0 does **not** auto-promote them. Owners may introduce
dimensions via Mature / dimension discovery after a probe is committed.

## Explicit non-goals (v0)

- Automatic legal ownership claims
- Forced mutual estimation of Access/Jurisdiction between peers
- Silent write from Interaction Signal into profiles
- Promotion of Ownership to a public Core Concept page (framework decision)
- Residual emergency grant transfer / revoke through the ordinary path
- Persisted Space membership and full membrane enforcement (issue #61 follow-up)

Ordinary grant transfer and revoke are available through
`ie jurisdiction grant`; the residual path remains intentionally separate.
Public Space boundary export and inbound verification are available through
`ie space boundary`, but they do not yet create membership or enforce endpoint
and signal policy without persisted Space state.

## Exit criteria mapping (#40)

| Criterion | Status |
|-----------|--------|
| `docs/access-jurisdiction-probes.md` | this document |
| Minimal schema for Access/Jurisdiction profile | `access_jurisdiction_profiles` |
| Owner-gated write path (CLI + library) | `ie jurisdiction probe` + `runtime/jurisdiction.py` |
| Linked from Stem / Metric / next.md | yes |
| Cross-ref framework gap #32 + Ownership blog | yes |

## Related

- Issue #40 (this contract)
- Issue #61 (probes + Space membrane alignment)
- `docs/identity-creation-jurisdiction.md` — grants + residual
- `docs/sqlite-schema-v1.md` — table definition
- Framework: [Ownership as Relative Jurisdiction](https://identity-engineering.org/blog/ownership-as-relative-jurisdiction/)
- Framework gap #32
