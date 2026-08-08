# Local entry (install discoverability)

Locked 28.07.2026

## Role

Local entry is **only** how agents and tools discover *this* install on disk or in a DB.

It is **not** the inter-identity communication protocol and is **not** sent as a Vision package to others.

## Preferred integration (maximize existing standards)

1. **AGENTS.md** (or CLAUDE.md / stack-equivalent) contains a short IE block: local_handle, paths or connection pointer, privacy defaults, schema version, optional surface endpoint URL.
2. If no AGENTS ecosystem exists, optional **IE.md** with the same block.
3. Structured V1 state lives in Registry / Metric Stem / foreign-estimate zone
	in `<install-root>/.ie/ie.sqlite3`. YAML files under `schemas/` describe
	contracts and examples; they are not mutable runtime state.

`IE.md` is a discovery aid only. Agents must use the CLI or runtime API for
state reads and writes.

## Minimal local fields

- identity.local_handle
- substrate
- pointers: registry, dimension_catalogue, surface policy location, optional surface base URL
- privacy defaults aligned with signal contract
- schema_version

State differential / vision anchors belong to Stem / trajectory work, not to inter-identity messaging. They may appear locally later; they are not the communication header.

## Relation to Header branch

Earlier "HEADER.yaml" drafts mixed local entry with communication. The living rule is:

- **Local entry** = discoverability for *my* agents
- **Identity Surface** = how *others* call me
