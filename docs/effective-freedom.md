# Effective Freedom

Status: design note (proposal) · 09.08.2026  
Links: #40 Access & Jurisdiction probes, #8 Living Tension Tensor update protocol, `docs/tensor.md`, `docs/space-model.md`, `docs/identity-creation-jurisdiction.md`, Geometry Receipt `degrees_of_freedom` + `jurisdiction_shift`

## Core claim

**Effective Freedom** of an Identity is not the raw count of degrees of freedom.  
It is the ratio of unbound (or remaining) degrees of freedom to the intensity of opposing constraints in the living Tensor.

```text
effective_freedom  ≈  unbound_DoF  /  (1 + constraint_intensity)
```

The same numerical value can arise from:

- few DoF + near-zero blockers (e.g. a tightly bounded cell with almost no internal friction), or
- many DoF + high blockers (e.g. high-visibility public Identity under heavy jurisdiction, reputation and membrane constraints).

When constraint intensity approaches zero while any unbound DoF remain, effective freedom can grow without bound inside the protected membrane.  
When the membrane itself dissolves, the form is lost (see Space model: "Freedom without membrane dissolves").

This is the operational reading of Ownership (Access + Jurisdiction as relative degrees of freedom) under the Tension Field.

## Why this exists

Framework already treats freedom as relational and constrained:

- Space births degrees of freedom; constraints and forces reduce them into bound configurations (Particles).
- Ownership is the relative, gradual distribution of remaining Access and Jurisdiction.
- The living Tensor + Metric Stem already compute distances and tension from alloys.
- Geometry Receipt already carries a `degrees_of_freedom` stub (`unbound_estimate` + `constraints_noted`) and a `jurisdiction_shift` stub.

What was missing is an explicit derived quantity that turns the ratio into a first-class geometric signal usable by probes, the Tensor feed, and Ownership diagnostics.

## Mapping to existing contracts

| Concept | Existing home | Role for Effective Freedom |
|---------|---------------|----------------------------|
| Unbound DoF | Geometry Receipt `degrees_of_freedom.unbound_estimate`; Registry alloy dimensions with high value + low external binding | Numerator |
| Constraints / blockers | Geometry Receipt `constraints_noted` + `jurisdiction_shift`; Registry `perceived_ownership`; identity grants + Space membrane policy; relation `frame_distance` / asymmetry | Denominator |
| Living Tensor | Registry alloys + Metric Stem (live) | Place where the ratio is computed |
| Ownership probes | #40 | Primary diagnostic surface that produces and consumes the ratio |
| Continuous feed | #8 | Path that keeps the ratio live after every Geometry Receipt |

Creation-time jurisdiction packages (`docs/identity-creation-jurisdiction.md`) already supply the default Access + Jurisdiction grants that form part of the constraint field. Residual red-button and Child-revocation dynamics are part of the intensity calculation.

## Proposed v0 shape (derived, not primary storage)

### Per-dimension (optional, sparse)

```text
effective_freedom_d  =  unbound_weight_d  /  (1 + constraint_intensity_d)
```

- `unbound_weight_d` – from alloy value × confidence, or from an explicit unbound score on that dimension.
- `constraint_intensity_d` – aggregate of:
  - jurisdiction / grant weight on the dimension (Access + Jurisdiction scopes),
  - membrane policy caps (Space),
  - perceived ownership asymmetry,
  - relation frame_distance / pull when they act as binding forces,
  - residual or emergency levers when active.

### Aggregate (Identity-level)

A single scalar or small vector under the observer Metric Stem:

```text
effective_freedom  =  f( dimensional effective_freedoms, g_ij )
```

Computed live, exactly as tension and multi-dimensional distance are already derived.  
No new primary persistent state; only optional cached readout with confidence.

### Geometry Receipt extension (minimal)

Reuse and strengthen the existing stub:

```yaml
degrees_of_freedom:
  unbound_estimate: number
  constraints_noted: [string]
  constraint_intensity: number   # NEW optional 0–∞ or 0–1 scaled
  effective_freedom: number      # NEW optional derived ratio
  confidence: float
```

`jurisdiction_shift` remains the Ownership-oriented delta; once #40 defines Access/Jurisdiction subjects it can feed the intensity term.

## Probe surface (#40)

Candidate Space / Ownership probes that produce or refine the inputs:

1. How many unbound dimensional freedoms does this Identity currently hold?
2. Which relative positions / Access paths are fixed by external jurisdiction, habit, membrane policy or residual levers?
3. Where is binding too tight (rigidity → low effective freedom) or too loose (dissolution risk)?
4. What is the current effective-freedom profile (per key dimension and aggregate) relative to the last Mature?

These probes write Geometry Receipts (or Mature ownership notes). The continuous feed (#8) then updates the live derived quantity in the Tensor reading.

## Integration with #8 (Tensor feed)

After a Geometry Receipt is written:

1. Extract or refine `unbound_estimate` / `constraints_noted` / jurisdiction observations.
2. Recompute local `constraint_intensity` from current grants + membrane + relation fields.
3. Update the live Tensor reading (no silent rewrite of owned alloys).
4. Expose `effective_freedom` as a derived tension-adjacent signal for local entry / Header / diagnostics.

Exact aggregation rule and confidence propagation stay implementation detail under #8; this note only locks the semantic claim.

## Explicit non-goals (v0)

- Full high-order dependency tensors per dimension.
- Self-declared Mass or self-declared absolute freedom numbers.
- Automatic export of effective-freedom scores (stays observer-local by default).
- Treating the ratio as a Core Concept on the public framework site (stays OS-derived operational signal until promoted).
- Replacing causal-entropy / optionality_delta; the ratio is a configuration-space snapshot, optionality_delta is the local future-gradient partner.

## Relation to framework

- Space → birth of DoF, constraints reduce them.
- Ownership → relative Access + Jurisdiction distribution (the operational reading of the remaining DoF).
- Tension Field → the multidimensional opposing forces that form the intensity term.
- Causal Entropy → maximises future accessible optionality; effective freedom is the present configuration-space volume that causal entropy acts upon.

The design remains fully consistent with Relativity, membrane boundaries, and the prohibition on self-declared Mass.

## Next implementation levers

1. #40 – define Access/Jurisdiction subjects and the first Ownership probes that emit `constraint_intensity` and `effective_freedom` into Geometry Receipts.
2. #8 – include the ratio in the continuous Tensor/Tension feed path once receipts carry the fields.
3. Optional: light schema bump of `degrees_of_freedom` in `schemas/geometry-receipt/v0.yaml` (additive, backward-compatible).
4. Dogfood: run the probes on the personal Registry and observe whether low-DoF/low-blocker and high-DoF/high-blocker cases produce comparable effective-freedom readings.

## Locked decisions summary (this note)

1. Effective Freedom is a derived ratio, not a primary stored quantity.
2. Numerator = unbound / remaining DoF; denominator = constraint intensity from jurisdiction, membrane, relation and residual levers.
3. Geometry Receipt already has the right stubs; strengthen them rather than invent a parallel structure.
4. Primary ownership of the diagnostic surface is #40; continuous liveness is #8.
5. Stays relative, confidence-weighted, membrane-aware and ownership-controlled.
