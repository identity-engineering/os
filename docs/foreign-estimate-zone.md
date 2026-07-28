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

## Where it lives

Logical model is store-agnostic:

| Store | Example layout |
|-------|----------------|
| Files | `registry/_foreign_estimates/{sender_handle}.yaml` |
| SQLite / Supabase | table `foreign_estimates` keyed by (owner_id, sender_handle) |

It is **not** mixed into the observer's alloy dimensions about *others* without an explicit local process. Inbound writes are "what they claim about the relation / about me", not "my full judgment of them".

## Apply algorithm (v0)

1. Authenticate caller; resolve `from`.
2. Check rate limits and quarantine status.
3. Validate payload against Interaction Signal schema.
4. For each field:
   - always-passed + policy allows → apply
   - consent field + grant allows → apply
   - else → mark rejected on receipt
5. Update `last_signal_at`, `signal_count`, depth accumulation.
6. Persist audit + issue **receipt** (`applied` / `partial` / `rejected`).
7. Invalidate or recompute derived volume / self-Mass caches if any.

## Relation to my Registry entries about others

| Direction | Store |
|-----------|--------|
| What **I** estimate about **them** | my `registry/{their_handle}.yaml` (local, not foreign-written) |
| What **they** wrote **into me** about me / the relation | **foreign-estimate zone** |

Both feed geometry; only the second is surface-writable by them.

## Human ownership

- Policy who may write is owned (critical changes → human approval).
- Quarantine / revoke: stop aggregation influence; keep history for audit.
- No path from `receive_interaction_signal` to "install new tool" or "widen grant" without the approval flow in `docs/identity-surface.md`.

## Schemas

- `schemas/foreign-estimate-zone/v0.yaml`
- `schemas/surface-operations/v0.yaml`
- `schemas/interaction-signal/v0.yaml`
