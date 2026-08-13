# Local Space + multi-Identity (v0)

Status: **in progress on `feat/local-space-multi-identity-77`** · OS #77

## Goal

Make the Space / multi-Identity contracts operable **locally**:

- explicit `spaces` + `space_memberships` rows
- N Identities per install
- active Identity context for CLI

Managed path and federation stay follow-ups.

## Runtime pieces (this branch)

| Piece | Role |
|-------|------|
| `runtime/space_bootstrap.py` | v8 migration helper + `create_additional_identity` |
| `runtime/context.py` | active Identity + space list |
| `ie identity list\|create\|use` | multi-Identity CLI |
| `ie space list\|show` | mini-Space visibility |
| `docs/next.md` | reduced plan; #77 is **Now** |

## Migration note

Schema version **8** is applied by `apply_local_space_multi_identity_migration`
(Python, not pure SQL) so `identity.install_id` can lose its UNIQUE constraint
without breaking FK rebuilds. Wire-in lives in `runtime/database.py` migrate()
(`SCHEMA_VERSION = 8`).

## Non-goals

- Managed Space rows / account binding
- Cross-install federation
- Membrane export/inbound enforcement

## Related

- Issue #77
- `docs/space-model.md`
- `docs/account-identity-model.md`
