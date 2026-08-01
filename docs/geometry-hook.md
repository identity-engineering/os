# Geometry Hook (v0)

Working design · 01.08.2026

## Purpose

After every Interaction (and, later, after internal Think / Mature events) the OS runs a **Geometry Extraction** step that produces a local **Geometry Receipt**.

This is the operational form of "Questions as Probes": the continuous bridge from agentic life to relative IE geometry. See `docs/probes-as-bridge.md`.

## When it runs

| Trigger | Mode | Target |
|---------|------|--------|
| Successful `receive_interaction_signal` / `apply_interaction_signal` | `interact` | foreign handle (sender) |
| Explicit self-call (CLI / future agent) | `think` or `mature` | `self` |

v0 ships the **Interact path** first (wired into local apply). Think / Mature are the same extractor interface with different `mode` and `target="self"`.

## Pipeline

```
InteractionSignal (+ apply Receipt)
        ↓
Geometry Extraction (observer Metric Stem context, optional)
        ↓
Geometry Receipt (local)
        ↓
Store under registry/_geometry_receipts/   (audit + later Tensor feed)
```

The Geometry Receipt is **local by default**. It does not cross the boundary unless future consent fields explicitly allow coarse fragments.

## Extractor contract

An extractor is a pure function:

```text
extract(signal, apply_receipt, context) → partial GeometryReceipt fields
```

Multiple extractors run; results are merged sparsely (only fields with confidence > 0). Missing / low-confidence fields stay absent.

### v0 extractors (coarse, deterministic)

1. **DepthMassExtractor**  
   From `interaction_depth_delta` + optional `sender_emergent_mass` / `coarse_mass_estimate` produce a relative_mass_proxy hint and a tension component on interaction density.

2. **ConsentBoundaryExtractor**  
   From which consent fields were applied vs rejected, note a jurisdiction / access observation (how open the current policy surface was for this peer).

3. **ExistenceContinuityExtractor**  
   From existence + signal_count / accumulated_depth (if prior foreign-estimate record available) note a simple stem-continuity / relation-stability hint.

These are intentionally coarse. They prove the pipeline without claiming high-fidelity Curvature or Frequency measurement.

## Storage layout

```
registry/
  _foreign_estimates/
    peer-alice.yaml
  _geometry_receipts/
    <receipt_id>.yaml     # one file per Geometry Receipt
  _inbound_requests/
    …
```

## Opt-in behaviour (v0)

- Default: Geometry Hook is **off** on apply (no behaviour change for existing callers).
- Enable with `emit_geometry_receipt=True` on apply, or CLI flag / env later.
- When enabled, a Geometry Receipt is written after a non-rejected apply; failures in extraction never fail the Interaction apply itself (best-effort, logged on the apply Receipt reason or a sibling field).

## Explicit non-goals of v0

- Automatic high-quality Curvature / Frequency / Space DoF extraction
- Writing Geometry Receipt contents into Metric Stem weights or Stem files
- Cross-boundary export of Geometry Receipts
- Self-Mass derivation from self Geometry Receipts (still forbidden)

## Next after this slice

1. Dogfood the Interact path with real signals.
2. Add Think / Mature entry points (CLI `ie probe think` / `ie probe mature` sketches).
3. Feed selected Geometry Receipt fields into live Tension aggregation once #15 (emergent self-Mass) is stable.
4. Richer extractors behind the same interface.

## Related

- `schemas/geometry-receipt/v0.yaml`
- `runtime/geometry.py`
- `docs/probes-as-bridge.md`
- `docs/interaction-signal.md`
- `docs/tensor.md`
