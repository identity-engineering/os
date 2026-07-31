# Emergent Self-Mass (v0)

Issue #15. Locked operational rule 31.07.2026.

Self-Mass is **never self-declared**. It is derived only from estimates others
have written into the foreign-estimate zone under policy.

## Inputs (per sender)

From `registry/_foreign_estimates/{sender}.yaml` (see `schemas/foreign-estimate-zone/v0.yaml`):

| Symbol | Field | Meaning |
|--------|-------|--------|
| E_i | `coarse_mass_estimate` | Sender i's estimate of **me** (0–100). Required for contribution. |
| c_i | `mass_confidence` | Sender's confidence in that estimate (0–1). Default **0.5** if missing. |
| d_i | `accumulated_depth` | Sum of applied `interaction_depth_delta` from this sender. |
| q_i | `quarantine` | If true → **excluded** from aggregation. |
| existence | `existence_confirmed` | Used for volume; mass contribution still requires E_i. |

From the observer's local Registry `registry/{sender}.yaml`:

| Symbol | Field | Meaning |
|--------|-------|--------|
| M_i | `my_mass_estimate` | **My** relative Mass of the sender (0–100). How much weight their judgment carries in my frame. |

If there is no Registry entry for the sender, use cold-start **M_unknown = 10**
(low non-zero: an unknown estimator still counts a little, not as a heavy peer).

## Weight

```
depth_factor(d) = d / (1 + d)          # diminishing returns; d=0 → 0
w_i = (M_i / 100) * c_i * max(depth_factor(d_i), ε)
```

with **ε = 0.01** so a rare estimate with near-zero recorded depth still has a
tiny non-zero weight (avoids total silence from floating-point edge cases).

## Emergent self-Mass

```
if Σ w_i == 0:
    self_Mass = null                  # unobserved — not a default number
else:
    self_Mass = Σ (w_i * E_i) / Σ w_i   # weighted mean on 0–100 scale
```

This is a **derived readout**, not a field others write and not a Stem claim.

## Volume candidate

Two related quantities:

1. **volume_count** — number of non-quarantined senders with `existence_confirmed`
2. **volume_weighted** — Σ depth_factor(d_i) over those same senders

Volume answers "how many (weighted) orbits are sensing me". Self-Mass answers
"what density do those orbits attribute to me, weighted by how much Mass I
attribute to them".

## Cold-start

| Situation | Behaviour |
|-----------|-----------|
| No foreign-estimate records | self_Mass = null, volume = 0 |
| Existence signals only (no E_i) | volume > 0 possible; self_Mass still null |
| First E_i arrives | self_Mass becomes that estimate (single weight) |
| Unknown sender (no Registry row) | M_i = 10 |

There is **no** bootstrap self-rating. Unobserved means unobserved.

## Explicit open questions (v0)

- **Decay**: should old estimates lose weight over wall-clock time? (not in v0)
- **Gaming**: high M_i + low integrity peers — quarantine and grant policy are the first controls; more later
- **Confidence floor**: default c_i = 0.5 is a pragmatism, not derived physics
- **M_unknown = 10**: tunable; document if changed
- **Reciprocity**: using my estimate of their Mass (M_i) couples frames; intentional under Relativity

## Implementation

- Code: `runtime/mass.py` → `compute_mass_readout(registry_root)`
- CLI: `ie mass` (live readout + optional per-contributor table)
- `ie reindex` calls the same function (no persistent cache required in v0)
- Tests: `tests/test_mass.py`

## Non-goals

- Writing self_Mass into HEADER or Stem automatically
- Publishing self_Mass on the public card by default
- Replacing the observer's `my_mass_estimate` of others (that stays local judgment)

## Related

- `docs/foreign-estimate-zone.md`
- `docs/interaction-signal.md`
- `docs/bidirectional-gravitational-sensor.md`
- Issue #6 Mass Proxies, #15 this rule
