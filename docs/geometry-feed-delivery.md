# Geometry feed delivery modes

Status: **contract locked** · OS #44  
Related: `docs/geometry-feed.md` (#8 field→sink), `docs/surface-runtime-local.md`,
`docs/cli.md`, `docs/mcp-surface-v0.md`

## What this issue owns

**How** the Geometry Receipt reaches the live Registry / Tension path.

It does **not** own what fields may write into which sink. That matrix lives in
`docs/geometry-feed.md` (OS #8).

Not every Identity harness has an apply-hook. Local CLI/Surface can run **hook**
feed after Interact. Chat agents, foreign runtimes, or batch jobs may only
support **explicit** or **adapter** feed. This document is the honesty layer so
an Identity never claims a live Tensor when the delivery path cannot deliver it.

## Modes

| Mode | When | Quality | Limits | How the Identity should understand it |
|------|------|---------|--------|----------------------------------------|
| **hook** | After successful `apply_interaction_signal` + persist | Best: Interact → Receipt → alloy in one path | Needs Surface/CLI/MCP runtime with the apply path | Every Interaction metabolizes geometry |
| **explicit** | `ie geometry feed` / batch / library `feed_pending` | Idempotent, re-runnable | Must be triggered | Metabolism on demand; Receipts wait until fed |
| **adapter** | Session-end harness writes signals/receipts then calls feed | Works without kernel hooks | Quality depends on harness protocol | I am an adapter, not the kernel |
| **none / lagging** | Zone / foreign-estimate path only | Self-Mass may still live from estimates | Do not claim live Tensor feed | Sensor lives; Tensor feed deferred |

### Local Surface (shipped)

- **hook** — wired in `runtime/apply.py` after persist (best-effort; never fails apply)
- **explicit** — `ie geometry feed [--receipt-id \| --all] [--force]` and `feed_pending`
- Status surface: `geometry_feed: hook` (implies explicit is also available)

### Capability declaration

Primary status field (local entry / `ie status`):

```text
geometry_feed: hook | explicit | adapter | none
```

Semantics:

| Value | Meaning |
|-------|---------|
| `hook` | Apply path runs feed automatically; explicit also available |
| `explicit` | No apply-hook; feed must be invoked deliberately |
| `adapter` | External harness owns the sequence; kernel feed APIs may still be called |
| `none` | No feed path claimed (no DB, or deliberately lagging) |

Local kernel helper: `runtime.geometry_feed.feed_capability(install_root)`.

- Returns `hook` when a local IE database exists (Surface Runtime present).
- Returns `none` when no database is present.
- Does **not** invent `adapter` for local installs. Adapter is declared by the
  **harness** status surface (skill, agent runtime, foreign host), not by the
  local kernel.

Optional detail list for diagnostics: `feed_modes_available(install_root)` →
`["hook", "explicit"]` or `[]`.

## Honesty rules

What may be claimed in each mode:

| Claim | hook | explicit | adapter | none |
|-------|------|----------|---------|------|
| "Every Interact metabolizes Registry geometry" | yes | no | only if harness always runs the sequence | no |
| "Pending Receipts can be fed on demand" | yes | yes | yes (if feed API reachable) | no |
| "Live Tensor is continuously updated" | yes (for peer Interact) | after explicit feed runs | after harness completes sequence | no |
| "Self-Mass emerges from foreign estimates" | yes (independent of feed) | yes | yes | yes |
| "I have a live Tension Tensor without feed" | no | no | no | no |

Rules:

1. **Capability is a claim about the path, not about content quality.** A hook
   that never receives Interact signals still correctly reports `hook`.
2. **Receipts without `fed_at` are not live geometry.** They are audit + probe
   artifacts until fed.
3. **Self-Mass must not be justified by feed mode.** It emerges from foreign
   estimates in the zone, independent of Geometry Receipt feed.
4. **Adapter must not impersonate hook.** If the harness is the only reason feed
   runs, status is `adapter` (or `explicit` if the user triggers it).
5. **none / lagging is valid.** High-Mass Identities may deliberately defer feed;
   they must not claim continuous metabolism.

## Adapter sequence (harness contract)

Minimal sequence for chat agents, skills, or foreign runtimes that do not own
the apply-hook:

```text
1. Write Interaction Signal  →  apply path (CLI / library / MCP tool)
                                or equivalent validated persist into the local DB
2. Confirm Geometry Receipt  →  optional; apply already emits one for Interact
3. Run feed                  →  ie geometry feed
                                or feed_pending(install_root)
                                or feed_receipt(install_root, receipt_id)
4. Read status               →  geometry_feed capability + fed counts if needed
```

Notes:

- Step 1 must use the same policy gates as Surface Runtime (consent, quarantine).
- Step 3 is idempotent (`fed_at`); safe to re-run.
- Session-end is the natural adapter moment: batch pending receipts, then feed.
- Adapter quality is harness-owned. The kernel only guarantees that explicit feed
  is correct and idempotent when invoked.

### Session-end reference (not product brand)

Harnesses may document a local prompt or skill step such as:

```text
After the interaction session: if IE install root is known,
run `ie geometry feed` (or library feed_pending) so Receipts
reach Registry effect_on_me. Do not claim live Tensor until fed.
```

This is an adapter instruction, not a required product surface.

## MCP / HTTP

MCP Surface binding and thin HTTP re-use the same apply handlers as CLI. When
those handlers run, **hook** feed applies the same way as local CLI apply.

Harnesses that only call MCP tools sporadically without a guaranteed post-apply
feed still count as **adapter** unless they always close the loop.

## Explicit non-goals

- Replacing #8 field→sink mapping or Mass invariants
- Building a global attention or social feed
- Forcing every substrate to support hooks
- Auto-declaring adapter mode from inside the local kernel
- Changing Stem / Vision / access-policy from any feed path

## Exit criteria

- [x] `docs/geometry-feed-delivery.md` (this file)
- [x] Capability field documented (`geometry_feed` on status)
- [x] Adapter sequence specified (signal → optional receipt → feed)
- [x] Linked from `docs/geometry-feed.md`, `docs/next.md`, `docs/cli.md`, `docs/tensor.md`

## Related

- Issue #44 (this contract)
- Issue #8 (field→sink feed implementation)
- Issue #29 Surface Runtime
- `docs/geometry-feed.md`
- `docs/surface-runtime-local.md`
- `docs/mcp-surface-v0.md`
