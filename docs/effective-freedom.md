# Effective Freedom

Status: **v0 readout implemented** · 13.08.2026  
Code: `runtime/freedom.py`, CLI `ie freedom`  
Links: #40, #8, `docs/tensor.md`, `docs/geometry-feed.md`, Geometry Receipt `degrees_of_freedom`

## Core claim

**Effective Freedom** is not the raw count of degrees of freedom.  
It is the ratio of unbound (or remaining) degrees of freedom to the intensity of opposing constraints in the living Tensor.

```text
effective_freedom  ≈  unbound_DoF  /  (1 + constraint_intensity)
```

## Implementation (v0)

- `compute_freedom_readout(install_root)` — derived only, no primary storage
- `ie freedom [--json] [--detail]`
- Surfaced on `ie status` and `ie reindex`
- Formula version `0`

### Inputs used today

| Input | Role |
|-------|------|
| Geometry Receipt `unbound_estimate` (recent window) | numerator |
| Receipt `constraints_noted` | intensity |
| Registry `effect_on_me` tension_sum (geometry feed) | intensity |
| Active quarantines | intensity |
| Residual identity grants | intensity |
| Optional self Access/Jurisdiction probe | numerator + intensity |
| Baseline unbound `0.5` | cold start |

### Non-goals

No Stem write, no self-declared Mass, no automatic export, no new table.

## Design background

Same numerical value can arise from few DoF + near-zero blockers, or many DoF + high blockers. When constraint intensity approaches zero while unbound DoF remain, effective freedom can grow inside the membrane. When the membrane dissolves, the form is lost.

Ownership (Access + Jurisdiction as relative degrees of freedom) is the operational reading under the Tension Field. Continuous feed (#8) keeps tension inputs live; probes (#40) refine unbound and bind scores.

## Locked decisions

1. Derived ratio, not primary storage.
2. Numerator = unbound DoF; denominator = constraint intensity.
3. Reuse Geometry Receipt stubs rather than parallel structures.
4. Relative, confidence-weighted, ownership-controlled.
