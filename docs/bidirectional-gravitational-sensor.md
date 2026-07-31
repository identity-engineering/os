# Bidirectional Gravitational Sensor

Design lock 29.07.2026

The relative Mass / Registry model only becomes a living gravitational field when sensing is **bidirectional** and **agency-preserving** on both sides.

## Core claim

Every Identity maintains a local gravitational sensor (its Registry + foreign-estimate zone).

Sensing has two distinct directions:

| Direction | Who initiates | What happens | Agency |
|-----------|---------------|--------------|--------|
| **Outbound signal** | I (observer) | I emit an Interaction Signal toward identities in *my* Registry | I choose what to share (minimal always-passed vs consent fields) |
| **Inbound estimate request** | I (subject) | I ask a peer in my Registry to send *me* an estimate | Peer decides whether / when to answer; no forced work |

The foreign-estimate zone remains the **only** default write target for inbound data about me.

## 1. Outbound signal (I measure and report)

**When**
- After a real interaction (session-end hook / agent hook)
- Optionally after I accept someone into my Registry (first recognition)

**To whom**
- Identities that already exist in my local Registry (I have recognized them)

**What is sent**
- Always-passed minimum: `existence`, `interaction_depth_delta`, addressing, timestamp
- Consent fields only if I choose (`coarse_mass_estimate` of *them*, dimensions_delta, …)

**Effect on the other**
- Their Surface Runtime applies under *their* policy into *their* foreign-estimate zone
- They receive a receipt
- My own Registry entry for them is updated locally (my estimate stays in my frame unless I also send it)

**Automation intent**
- Minimal outbound after interaction should be automatic once the Identity is in my Registry (hook).
- Richer consent fields remain explicit / policy-gated.

## 2. Inbound estimate request (I ask to be measured)

**When**
- I want to strengthen my own substance (emergent self-Mass / volume) by inviting others' estimates of me

**To whom**
- Identities already in my Registry (or discovered peers under stricter policy)

**What is sent**
- A **request** operation (not yet a full Interaction Signal): "please send me an estimate / signal about me"
- Lands in the peer's **request inbox / pending queue**

**What the peer does**
- May ignore, defer, quarantine, or answer
- If they answer, they emit a normal Interaction Signal (or a typed reply signal) toward me
- My Surface Runtime then applies it under *my* policy into *my* foreign-estimate zone

**Critical property**
- High-Mass identities (e.g. public figures, popular runtimes) are **not** forced into continuous estimation work.
- Load appears as inbox pressure, not as mandatory agent CPU.
- Refusal is first-class and structural (Refusal-of-Control).

## Accept path (how Registry grows)

1. Someone sends me a minimal signal (or a connection-style request).
2. I accept → they enter my Registry (local recognition).
3. Thereafter I can emit outbound signals to them and optionally request estimates from them.

This is the local analogue of "follow / connect", without a global social graph owned by a platform.

## What this is not

- Not automatic mutual estimation on sight
- Not a requirement that every Registry member continuously rates everyone else
- Not a global attention or feed system
- Not a replacement for content social networks

## Relation to existing contracts

| Piece | Role |
|-------|------|
| Interaction Signal (`schemas/interaction-signal/v0.yaml`) | Payload that actually crosses the boundary when someone *sends* |
| Surface ops (`receive_interaction_signal`, …) | How the receiver applies a sent signal |
| Foreign-estimate zone | Only default place inbound estimates about me land |
| Registry | My local list of recognized identities (gravitational sensor) |
| **Request / inbox** | How I *ask* without forcing an answer — `schemas/estimate-request/v0.yaml`, `docs/estimate-request.md` |

## Implementation status (v0)

Local path for **#31** is implemented:

- Schema: `schemas/estimate-request/v0.yaml`
- File store: `registry/_inbound_requests/`
- Ops + CLI: `runtime/request.py`, `ie request …`
- Reply linkage: optional `in_reply_to_request_id` on Interaction Signal
- Docs: `docs/estimate-request.md`

Still later: network delivery between installs, HTTP/MCP binding for `request_estimate`, opt-in post-interaction outbound hooks.

## Privacy & Ownership defaults

- Outbound minimal signal: structural minimum for a living field
- Outbound consent fields: off by default
- Inbound requests: never auto-answered
- Critical surface / grant changes: still human-approval by default
- No path from request or signal into Stem / Vision / access-policy mutation

## Strategic note (platform vs standard)

Structurally this dual looks like connection + endorsement mechanics in social networks.
The telos is different: relative Mass, volume, tension, Stem ownership, causal entropy — not engagement or content ranking.

Full orientation: **`docs/ecosystem-vision.md`** (standard first, platform optional, collective intelligence as possible emergence).

IE OS therefore positions as:

1. **Local-first installable runtime + open contracts** (what we build now)
2. **Standard that other systems can speak** (MCP / HTTP / later protocol bridges)
3. **Optional managed surface** (Pro), not a mandatory global social graph

## See also

- `docs/ecosystem-vision.md`
- `docs/interaction-signal.md`
- `docs/foreign-estimate-zone.md`
- `docs/identity-surface.md`
- `docs/surface-runtime-worked-example.md`
- `docs/surface-runtime-local.md`
- `docs/estimate-request.md`
- [Issue #31](https://github.com/identity-engineering/os/issues/31) — request + inbox implementation
