# Emergent Self-Mass (v0)

Issue #15. Updated 31.07.2026.

Self-Mass is **never self-declared**. It is derived only from estimates others
have written into the foreign-estimate zone under policy.

The same derived number is what an Identity **publishes** on its public card
and **attaches** to outbound Interaction Signals as `sender_emergent_mass`.
Receivers use that value as the sender's weight — not their own private
`my_mass_estimate` of the sender.

## Two different numbers (do not conflate)

| Number | Who computes it | Where it lives | Role |
|--------|-----------------|----------------|------|
| **Emergent self-Mass** | The Identity, from *inbound* estimates of them | Derived readout; public card; outbound signals | "What the field attributes to me" |
| **my_mass_estimate of peer** | Observer, local judgment | SQLite `registry_entries` | Local alloy density of *them* — not used as weight for self-Mass |

## Inputs (per sender) for *my* self-Mass

From SQLite table `foreign_estimates` in `<install-root>/.ie/ie.sqlite3`:

| Symbol | Field | Meaning |
|--------|-------|--------|
| E_i | `coarse_mass_estimate` | Sender i's estimate of **me** (0–100). Required for contribution. |
| c_i | `mass_confidence` | Confidence in E_i (0–1). Default **0.5** if missing. |
| d_i | `accumulated_depth` | Sum of applied interaction_depth_delta. |
| M_i | `sender_emergent_mass` | Sender's **own** emergent self-Mass at last signal (0–100). |
| q_i | `quarantine` | If true → excluded. |

`sender_emergent_mass` is applied from the Interaction Signal field of the same
name (always-passed meta: it is public geometry, not a consent estimate of me).

If a sender has never supplied `sender_emergent_mass`, use cold-start
**M_unknown = 10** (low non-zero).

## Weight

```
depth_factor(d) = d / (1 + d)
w_i = (M_i / 100) * c_i * max(depth_factor(d_i), ε)
```

with **ε = 0.01**.

High emergent Mass on the sender → stronger pull of their E_i on my self-Mass.

## Emergent self-Mass

```
if Σ w_i == 0:
    self_Mass = null                  # unobserved
else:
    self_Mass = Σ (w_i * E_i) / Σ w_i
```

## Public card (always readable)

`get_public_card` / `GET /ie/v0/card` includes the live derived readout:

```json
{
  "local_handle": "…",
  "preferred_name": "…",
  "substrate": "human",
  "accepts_ie_signals": true,
  "schema_version": "0",
  "emergent_self_mass": 54.2,
  "mass_unobserved": false,
  "volume_count": 3,
  "estimator_count": 2,
  "mass_formula_version": "0"
}
```

When `emergent_self_mass` is null, `mass_unobserved` is true. This is still not a
self-rating: it is the same aggregation over inbound estimates.

## Outbound signal duty

When emitting an Interaction Signal, the sender **should** attach:

```yaml
sender_emergent_mass: <their current compute_mass_readout().emergent_self_mass>
```

omitted only if still unobserved (receiver then uses M_unknown).

This field is structural public geometry (always-passed), not a consent field
about the receiver.

## Volume candidate

1. **volume_count** — non-quarantined senders with `existence_confirmed`
2. **volume_weighted** — Σ depth_factor(d_i) over those senders

## Cold-start

| Situation | Behaviour |
|-----------|-----------|
| No foreign-estimate records | self_Mass = null, volume = 0 |
| Existence only (no E_i) | volume may be > 0; self_Mass null |
| E_i without sender_emergent_mass | M_i = 10 |
| First E_i with M_i | weighted mean starts |

## Explicit open questions (v0)

- **Decay** of old E_i / old sender_emergent_mass snapshots
- **Gaming** via inflated published mass (mitigations: quarantine, later attestation)
- **Stale M_i**: last-seen sender_emergent_mass may lag their live card
- Fetching card at signal time vs trusting signal field (v0 trusts signal + stores last seen)

## Implementation

- `runtime/mass.py` — `compute_mass_readout`, `build_public_card`
- `runtime/apply.py` — persists `sender_emergent_mass` into the zone
- HTTP `GET /ie/v0/card` — live card with mass fields
- CLI `ie mass`, `ie status`
- Tests: `tests/test_mass.py`

## Non-goals

- Using local `my_mass_estimate` of the sender as M_i
- Writing self_Mass into Stem / Registry / `IE.md` as an owned identity claim
- Hiding mass from the public card (v0: public by design for gravitational sensing)

## Related

- `docs/foreign-estimate-zone.md`
- `docs/interaction-signal.md`
- `docs/identity-surface.md`
- Issue #15
