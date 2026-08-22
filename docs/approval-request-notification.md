# Approval Request + Notification Channel

Status: architecture contract (design lock 22.08.2026)

Related: `docs/identity-surface.md`, `docs/estimate-request.md`, `docs/account-identity-model.md`, `docs/identity-creation-jurisdiction.md`

## Core claim

**Approval Request** and **Request Inbox** are the same primitive:

> An Identity is asked for a confirmation.

Estimate requests (`request_estimate`) are one *kind* of Approval Request.
Critical Surface changes, connector binds, wide grants, and other policy-gated
actions are the same kind of object with a different `kind`.

**Notification Channel** is how the asked Identity learns that a request is waiting.
It is bound to the Identity (typically the human / Owner Identity), not to the Account.

## Why this exists

Without a unified request + delivery path:

- Estimate inbox and "critical approval" drift into two different UIs.
- Owned Identities (agents, ideas, runtimes) cannot cleanly ask their Owner for confirmation.
- Mobile / push / 2FA as the human's Identity surface has nowhere to attach.

This contract unifies them under the existing Jurisdiction model:
Owner role + grants decide *who* may approve; the request + channel decide *how* the ask lands.

## Approval Request (unified inbox item)

```text
approval_requests
  request_id
  kind                    -- estimate | critical_surface | connector_bind | grant_widen | custom
  from_identity_id        -- who is asking
  to_identity_id          -- who must confirm (often the Owner / policy_admin holder)
  object_identity_id?     -- Identity whose surface/policy is affected (if different from to)
  scope / summary         -- human-readable: what is requested, by whom, what scope
  payload                 -- kind-specific structured body
  status                  -- pending | approved | denied | ignored | quarantine | expired
  created_at / resolved_at?
  resolved_by_identity_id?
  reply_receipt_id?
```

### Rules (locked direction)

1. A request **never** auto-answers. Load is inbox pressure, not forced work.
2. Only Identities with the right jurisdiction (Owner / `policy_admin` / explicit grant) may resolve critical kinds.
3. Estimate kind remains available to any peer under Surface policy (same as today).
4. Critical kinds (`critical_surface`, `connector_bind`, `grant_widen`, …) default to the Owner / designated owner role of the object Identity.
5. Resolve actions are audited (`actor_identity_id`, reason, timestamp).

### Relation to existing estimate inbox

`estimate_requests` is the v0 specialization of this table for `kind=estimate`.
When the unified store lands, estimate rows migrate or are projected as the same primitive.
CLI `ie request …` becomes the general entry point; estimate-specific flags remain.

## Notification Channel

```text
notification_channels
  channel_id
  identity_id             -- the Identity that receives pings (usually human / Owner)
  kind                    -- push_mobile | app_inbox | email | webhook | other
  endpoint / device_ref   -- opaque delivery target (token, device id, URL)
  status                  -- active | paused | revoked
  created_at / last_used_at?
```

### Rules

1. Channels belong to an **Identity**, never to the Account as geometry.
2. The human Owner Identity is the natural place for `push_mobile` (phone = that Identity's authenticator).
3. Delivery is best-effort + audited; failure does not auto-approve.
4. Multiple channels per Identity are allowed (app + push).
5. Critical Approval Requests **should** attempt delivery on active channels of `to_identity_id`.

### Mobile as Owner Identity

The clean path the product aims at:

- Normal mobile phone ↔ human / Owner Identity (`jonas-managed` or successor).
- AI agents, ideas, runtimes = **separate Identities** created and owned by the human.
- When an owned Identity needs critical confirmation, an Approval Request is created with `to_identity_id = Owner`.
- Notification Channel on the Owner Identity pings the phone (2FA-style confirm).
- Owner resolves in app or push → grant / policy change applies under audit.

## Flow: owned Identity asks Owner

```text
1. Agent Identity A (owned) wants critical action
   (e.g. bind new MCP connector, widen grant, add surface tool).

2. Runtime creates Approval Request:
     kind = critical_surface | connector_bind | …
     from = A
     to   = Owner Identity (policy_admin / designated owner role)
     object = A (or the Identity whose policy is affected)

3. Request lands in Owner's unified inbox (pending).

4. Notification Channel(s) on Owner fire (push / app).

5. Owner resolves (approve | deny | ignore | quarantine).

6. On approve: the pending action runs under audit as Owner (or under the grant that Owner just issued).
   On deny/ignore: action does not run; receipt records the decision.
```

Self-write on A's own non-critical geometry stays full (no request).
Only **critical** or **cross-jurisdiction** steps enter this path.

## Policy mapping (existing)

| Existing concept | Role here |
|------------------|-----------|
| `policy_admin` / Owner role | Default `to_identity_id` for critical kinds |
| Creation-time default grants | Establish who is Owner / residual for a new Identity |
| Critical approval rules (`identity-surface.md`) | Which actions produce an Approval Request |
| Estimate request inbox | `kind=estimate` specialization |
| Residual emergency lever | Separate from ordinary approve; still audited |

No new "account-root" power. Actor remains an Identity. Account stays auth/billing.

## Explicit non-goals (this contract)

- Auto-approve by timeout without explicit policy
- Notification as a substitute for jurisdiction (channel delivers; grants decide)
- Binding push tokens to the Account instead of an Identity
- Forcing every signal or Mature through the inbox
- Implementing a full push provider in Open Core (channel is the contract; delivery adapters are product)

## Implementation sketch (minimal)

```text
1. Unify schema: approval_requests (kind-discriminated) + notification_channels
2. Project existing estimate_requests as kind=estimate
3. Surface ops:
     create_approval_request / list_inbound_requests / resolve_request
     register_notification_channel / list_channels / revoke_channel
4. On critical action path: create request → notify channels of to_identity → wait for resolve
5. Managed path: same tables keyed by identity_id; mobile app binds channel to human Identity
```

Local Free V1 keeps the estimate-only store until the unified migration.
Managed Pro is the natural first host for push channels.

## Locked decisions summary

1. Approval Request = any confirmation ask to an Identity; estimate is one kind.
2. Request Inbox is the home of all such asks for that Identity.
3. Notification Channel is bound to the Identity that should be reached.
4. Critical actions by owned Identities create an Approval Request to the Owner / policy_admin holder.
5. Mobile phone is the preferred Notification Channel of the human Owner Identity.
6. Jurisdiction (grants, owner role, residual) decides *who may resolve*; channel only delivers.
7. No auto-answer; no silent account-root elevation.

## Related

- `docs/identity-surface.md` – critical approval, human-in-the-loop
- `docs/estimate-request.md` – v0 estimate specialization
- `docs/account-identity-model.md` – Account ≠ Identity; grants
- `docs/identity-creation-jurisdiction.md` – default owner package, residual
- Issue #40 Access & Jurisdiction
