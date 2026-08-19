# Identity Surface

Locked 28.07.2026  
Multi-identity account model linked 08.08.2026

## Core claim

Every Identity is a small **backend** for how the world may interact with it.

It exposes a controlled **Identity Surface**: a set of operations (read/write) with authentication, scopes, grants, receipts, and an explicit **access policy**.

The surface can be bound to:

- **MCP** (agent-native tool calls)
- **HTTP API** (universal clients)
- **Local emulation** (CLI / files for Free tier)

Same semantics, different bindings.

The local MCP binding starts one process for one validated `identity_id` and
uses the same apply, card, mass, status, and request handlers as the CLI. It
does not accept an identity selector per tool call. Local Free V1 rejects an
explicit `space_id` until membrane enforcement exists, rather than silently
falling back to an account-root context.

The Surface belongs to an **Identity**, not to an IE Account. An account may
hold many Identities; each has its own Surface, Registry frame, and Public
Card. See `docs/account-identity-model.md`.

## Why this exists

Session-start "please read a header and hopefully send three fields" is fragile.

Deterministic operations:

1. Caller invokes `receive_interaction_signal` (or equivalent) with the IE payload.
2. Callee policy decides accept / apply / reject / pending.
3. On apply, data lands in a **bounded foreign-estimate zone** inside the callee's state.
4. Caller receives a **receipt**.

Relative Mass, volume, and tension can update without the human re-typing estimates every time — while critical control stays owned.

## Minimal operations (v0 surface)

| Operation | Type | Purpose |
|-----------|------|---------|
| `receive_interaction_signal` | write (bounded) | Apply existence, depth_delta, optional mass estimate, optional consented fields into foreign-estimate zone |
| `request_estimate` | write (inbox) | Land an inbound estimate request; never auto-answered |
| `list_inbound_requests` | read (owner) | Inspect pending / historical estimate requests |
| `get_public_card` | read (minimal) | Discoverability: handle, substrate, accepts_ie_signals |
| `get_receipt` / list recent receipts | read | Audit and confirmation |
| `list_grants` / `revoke_grant` | policy | Inspect and cut access |

Further tools (rich dimension read/write, custom domain tools) are **opt-in** and subject to the access policy.

Owner-side operations on the same Identity (status, Mature, registry list, …)
use the same runtime handlers whether invoked via CLI, HTTP, or MCP. MCP is not
a read-only mirror of the CLI; when the session is authenticated as Identity I,
it may write I's geometry under the same rules as local CLI.

See `schemas/surface-operations/v0.yaml`, `docs/foreign-estimate-zone.md`, and `docs/estimate-request.md`.

## Bounded foreign-write zone

Authorized callers may write only into a scoped region, e.g.:

- estimates others hold **about me** (coarse_mass_estimate, confidence, timestamp, sender)
- interaction_depth / volume contributions
- optional consented dimension deltas

They must **not** by default write:

- Stem / Vision / core ownership markers
- Access policy itself
- Arbitrary registry entries about third parties
- New surface tools or scopes

This zone is the structural expression of **asymptotic ownership**: I never fully own the picture others form of me; that picture is allowed to land in me under policy and then feeds emergent Mass / volume / tension.

## Access policy ownership

The **access policy** of an Identity Surface has a clear owner:

| Criticality | Who may change policy / add tools / widen scopes |
|-------------|--------------------------------------------------|
| Uncritical routine | May be an approved agent acting under existing policy |
| **Critical** | **Identity holder** (human owner of a human Identity, or the designated owner role for a runtime/idea Identity) must approve out of the box in the IE standard |

Examples of **critical** (approval required by default):

- Creating a new offered tool on the surface
- Granting write access beyond the minimal signal zone
- Widening who may call the surface (e.g. from named peers to public)
- Changing revoke rules or disabling audit
- Binding a new MCP/API endpoint that exposes more state

Examples of **non-critical** (may be automated if policy allows):

- Applying a minimal authenticated signal into the foreign-estimate zone
- Emitting receipts
- Rotating non-secret operational metadata
- Listing or ignoring inbound estimate requests under existing policy
- Mature and registry updates **on the authenticated Identity itself**

Cross-Identity mutations under the same account (e.g. agent Mature on a human
Stem) require an explicit grant. They are not implied by sharing an account.
See `docs/account-identity-model.md`.

### Human-in-the-loop requirements

The IE standard must support, out of the box:

1. **Clear owner** of the access policy (Identity handle / account membership role)
2. **Approval requests** for critical changes (readable surface: what is requested, by whom, what scope)
3. **Revoke** functions that actually cut access and can quarantine prior writes where feasible
4. Separation between "AI that acts as its own Identity under grants" and "the human Identity" — an agent Identity is not a silent mode of the human

Speaking with "my AI" is interaction between Identities (or between harnesses bound to different Identities), not automatic elevation to the human's jurisdiction.

## Default apply policy (signals)

| Field class | Default behaviour (configurable per Identity) |
|-------------|-----------------------------------------------|
| Always-passed (existence, depth_delta) from authenticated IE peers | Auto-apply into foreign-estimate zone + rate limits + audit |
| Consent fields (mass estimate, dimensions_delta, …) | Only if grant/scope allows; else reject or pending review |
| Anonymous / unauthenticated | Reject or strictly limited public card only |

Stricter Identities may set everything to pending review. More open Identities may widen grants per peer.

## Estimate requests (inbox)

Inbound `request_estimate` never auto-answers. Load is inbox pressure, not mandatory estimation work. See `docs/estimate-request.md` and `docs/bidirectional-gravitational-sensor.md`.

## Identity as app

Each Identity:

- chooses which operations to enable
- chooses standard vs named-identity grants
- may expose additional tools later under approval rules
- remains multi-substrate (human, runtime, idea, org, …) — the surface is how others address that entity

An idea-Identity can have a surface too (often narrower). A runtime-Identity often exposes MCP naturally. A human-Identity typically holds account-level roles and may create other Identities under the account without absorbing them.

## Related docs

- `docs/account-identity-model.md` — Account ≠ Identity; harness binding; grants
- `docs/communication.md` — transport vs payload vs receipt
- `docs/local-entry.md` — AGENTS.md / local discoverability (not the inter-identity protocol)
- `docs/interaction-signal.md` — payload fields
- `docs/foreign-estimate-zone.md` — where applies land
- `docs/estimate-request.md` — inbound request + inbox
- `docs/realization-surface-runtime.md` — how this is implemented without every user coding a server
