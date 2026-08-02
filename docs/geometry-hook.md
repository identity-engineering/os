# Geometry Hook (v0)

Working design · 01.08.2026  
Updated 02.08.2026 — storage-only feed path; Mass sources; membrane stub

## Purpose

After every Interaction (and later after internal Think / Mature events) the OS runs **Geometry Extraction** and produces a local **Geometry Receipt**.

Operational form of Questions as Probes: continuous bridge from agentic / human happening to relative IE geometry.  
See `docs/probes-as-bridge.md`, `docs/tim-cycle.md`, `docs/living-form.md`.

## When it runs

| Trigger | Mode | Target |
|---------|------|--------|
| Successful `apply_interaction_signal` | `interact` | foreign handle (sender) |
| Explicit self-call (future) | `think` / `mature` | `self` |

**Default: always on** for Interact after non-rejected apply.  
Opt-out only for tests (`emit_geometry_receipt=False`).

## Pipeline (v0)

```
InteractionSignal (+ apply Receipt)
        ↓
Geometry Extraction
        ↓
Geometry Receipt (local file)
        ↓
registry/_geometry_receipts/
```

**v0 stops at local storage.** Receipts do **not** yet rewrite Registry alloys, Metric Stem, or live Tension. That write-back is **OS #8**.

Local by default. Does not cross the membrane unless future consent allows coarse fragments.

## v0 extractors (coarse, deterministic)

1. **DepthMassExtractor** — `relative_mass_proxy` = sender's emergent self-Mass when known  
   (signal → stored zone → public card); plus `interaction_density` tension  
2. **MembranePolicyExtractor** — observational stub of consent applied/rejected  
   (no Access/Jurisdiction claim; **OS #40**)  
3. **ExistenceContinuityExtractor** — relation continuity from existence + prior depth

### Mass source order (Interact)

Same number the sender would publish on their public card / attach as `sender_emergent_mass`:

| Priority | Source | Meaning |
|----------|--------|---------|
| 1 | `signal.sender_emergent_mass` | Always-passed public geometry on this signal |
| 2 | Foreign-estimate zone last `sender_emergent_mass` | Previously accepted publish |
| 3 | `public_card.emergent_self_mass` | Live/cached card (when caller injects into context) |
| fallback | depth-only placeholder, low confidence | Explicitly *not* their Mass |

## Storage

```
registry/
  _foreign_estimates/
  _geometry_receipts/
  _inbound_requests/
```

## Failure behaviour

Extractors and the hook are **best-effort**: they must never fail the Interaction apply.  
If an extractor raises, the error is written into Geometry Receipt `notes` (`extractor_errors=…`) and a short marker may appear on the apply `reason`. That is intentional resilience, not silence.

## Non-goals of v0

- High-fidelity Curvature / Frequency / Space DoF extraction  
- Writing receipts into Metric Stem weights or Stem files (**#8**)  
- Cross-boundary export of Geometry Receipts  
- Self-Mass from self receipts  
- Real Access/Jurisdiction scoring from policy outcomes (**#40**)

## Related

- `schemas/geometry-receipt/v0.yaml`  
- `runtime/geometry.py`  
- `docs/probes-as-bridge.md`  
- `docs/tim-cycle.md`  
- `docs/living-form.md`  
- OS #8 (Tensor update protocol), OS #40 (Access & Jurisdiction)  
