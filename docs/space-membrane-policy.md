# Space membrane policy (runtime)

Status: operational v0 (OS #82)  
Contract base: `docs/space-model.md` (Membrane security)

## Claim

`spaces.policy_json` is the **Boundary of the Space Identity** at the OS
layer. It decides what may **leave** (export) and what may **enter** (inbound
Surface fields). It does not replace:

- Identity-level Surface policy (`LocalPolicy`: grants, quarantine)
- Jurisdiction grants between Identities
- Account / billing roles

Membrane is **additive**. Local Free mini-Spaces default to owner-sovereign
on-device behaviour.

## Schema (`policy_json`)

```json
{
  "version": 1,
  "export": {
    "mode": "owner_full",
    "allow_tables": null,
    "deny_tables": []
  },
  "inbound": {
    "mode": "surface_default",
    "allow_fields": null,
    "deny_fields": []
  }
}
```

### Export modes

| Mode | Behaviour |
|------|-----------|
| `owner_full` | All known geometry tables may leave, minus `deny_tables` |
| `allowlist` | Only tables/groups in `allow_tables` (minus deny) |
| `denylist` | All tables except `deny_tables` |

Selectors may be **table names** or **groups**:

| Group | Tables |
|-------|--------|
| `identity_core` | install, identity, privacy_defaults, stem_state, stem_revisions |
| `metric` | metric_dimensions, metric_pairs |
| `registry` | registry_entries, revisions, dimension values/revisions |
| `interaction` | interaction_events, apply_receipts, foreign_estimates, estimate_requests |
| `workspace` | workspace_items, revisions, evidence_sources |
| `geometry` | geometry_receipts, sources, mature_events, trajectory_entries |
| `policy` | consent_grants, quarantines, policy_events |

Stripped tables are reported in export metadata (`membrane.stripped_tables`).
Checksum covers the post-filter payload only.

### Inbound modes

| Mode | Behaviour |
|------|-----------|
| `surface_default` | Surface `LocalPolicy` decides; membrane only applies `deny_fields` |
| `allowlist` | Intersect Surface candidates with `allow_fields` |
| `denylist` | Surface candidates minus `deny_fields` |

Inbound fields: `existence`, `interaction_depth_delta`, `sender_emergent_mass`,
`sender_last_mature_at`, `coarse_mass_estimate`, `mass_confidence`,
`dimensions_delta`, `relation_pull`.

Membrane strips are recorded on the apply receipt reason
(`membrane_stripped=…`). They never open a path into Stem or Vision.

## Local defaults

On Space create (`kind=local`), runtime writes `default_local_membrane_policy()`:

- export `owner_full` — backup / migration remains possible offline
- inbound `surface_default` — existing consent/quarantine behaviour unchanged

Empty `{}` or invalid JSON normalises to the same defaults (fail open for the
local owner path; never invent a second geometry model).

## Enforcement points

1. **Export** — `runtime/export.py` filters tables after query, before checksum.
2. **Inbound apply** — `runtime/apply.py` intersects Surface-allowed fields with
   membrane inbound rules when a primary Space policy is available.
3. **Module** — `runtime/membrane.py` (parse, filter, defaults).

## Explicit non-goals (v0)

- `space_trust` / federation table
- Cross-install membrane negotiation
- Governed Space premium defaults (harder membrane later)
- CLI policy mutators beyond show (follow-up)
- Auto grant / jurisdiction mutation via membrane

## Related

- `docs/space-model.md`
- `docs/managed-space-identity.md`
- `runtime/membrane.py`, `runtime/export.py`, `runtime/apply.py`
- Issue #82
