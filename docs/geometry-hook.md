# Geometry Hook (v0)

Working design · 01.08.2026

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

## Pipeline

```
InteractionSignal (+ apply Receipt)
        ↓
Geometry Extraction
        ↓
Geometry Receipt (local)
        ↓
registry/_geometry_receipts/
```

Local by default. Does not cross the membrane unless future consent allows coarse fragments.

## v0 extractors (coarse, deterministic)

1. **DepthMassExtractor** — relative_mass_proxy + interaction_density tension  
2. **ConsentBoundaryExtractor** — jurisdiction/access from applied vs rejected consent fields  
3. **ExistenceContinuityExtractor** — relation continuity from existence + prior depth

## Storage

```
registry/
  _foreign_estimates/
  _geometry_receipts/
  _inbound_requests/
```

## Non-goals of v0

- High-fidelity Curvature / Frequency / Space DoF extraction  
- Writing receipts into Metric Stem weights or Stem files  
- Cross-boundary export of Geometry Receipts  
- Self-Mass from self receipts

## Related

- `schemas/geometry-receipt/v0.yaml`  
- `runtime/geometry.py`  
- `docs/probes-as-bridge.md`  
- `docs/tim-cycle.md`  
- `docs/living-form.md`  
