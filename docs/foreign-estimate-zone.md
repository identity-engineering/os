# Foreign-estimate zone

Locked 28.07.2026

## Purpose

This is the **only** region that inbound `receive_interaction_signal` writes into by default.

It stores, per sender:

- that they confirmed my existence in their frame
- how much interaction depth they attributed in each signal (and an accumulated value)
- optionally their coarse Mass estimate **of me** (and confidence)
- optionally consented richer fields

From the whole zone the Identity **derives**:

- **volume candidate** — how many (weighted) Identities are estimating / orbiting me
- **emergent self-Mass** — aggregation of others' estimates of me (never self-declared)

Derivation rule: **`docs/mass.md`** (weighted mean of `coarse_mass_estimate` by sender Mass × confidence × depth factor). Implementation: `runtime/mass.py`, CLI `ie mass`.

## Where it lives

Logical model is store-agnostic:

V1 stores the projection in the local database table
`foreign_estimates`, keyed by `(identity_id, sender_handle)`, inside
`<install-root>/.ie/ie.sqlite3`. The YAML schema under `schemas/` documents the
wire contract; it is not a mutable runtime store.

It is **not** mixed into the observer's alloy dimensions about *others* without an explicit local process. Inbound writes are "what they claim about the relation / about me", not "my full judgment of them".

## Apply algorithm (V1)

1. Authenticate caller; resolve `from`.
2. Check rate limits and quarantine status.
3. Validate payload against Interaction Signal schema.
4. For each field:
   - always-passed + policy allows → apply
   - consent field + grant allows → apply
   - else → mark rejected on receipt
5. Update Foreign Estimates and the local Registry continuity projection for an
   accepted signal; a first contact creates a minimal Registry entry.
6. Persist the canonical event, receipt, and Registry revision atomically.
7. A fully policy-rejected valid signal is still retained as an audit event and
   rejected receipt, without a domain projection.
8. Derived volume / self-Mass are recomputed on read (`ie mass` /
   `compute_mass_readout`); no owned numeric Self-Mass cache is written.

## Relation to my Registry entries about others

| Direction | Store |
|-----------|--------|
| What **I** estimate about **them** | `registry_entries` in my SQLite database (local, not foreign-written) |
| What **they** wrote **into me** about me / the relation | **foreign-estimate zone** |

Both feed geometry; only the second is surface-writable by them.

For self-Mass weights, the observer's `my_mass_estimate` of the sender (Registry) multiplies the sender's estimate of me (zone). See `docs/mass.md`.

## Human ownership

- Policy who may write is owned (critical changes → human approval).
- Quarantine / revoke: stop aggregation influence; keep history for audit.
- No path from `receive_interaction_signal` to "install new tool" or "widen grant" without the approval flow in `docs/identity-surface.md`.

## Schemas

- `schemas/foreign-estimate-zone/v0.yaml`
- `schemas/surface-operations/v0.yaml`
- `schemas/interaction-signal/v0.yaml`
- `docs/mass.md` — emergent self-Mass formula v0
