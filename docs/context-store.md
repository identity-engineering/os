# ContextStore adapters (v0)

Status: operational · 14.08.2026 · Issues #95, #96

## Role

**ContextStore** supplies Identity-scoped **skill and context text**. It does not
hold geometry. Geometry remains `.ie/ie.sqlite3` via CLI / MCP / HTTP.

## Contract

```text
ContextStore
  kind → local_fs | notion | …
  list_skills() → SkillRef[]
  read_skill(name) → SkillDocument
  write_skill(name, body) → SkillDocument   # may be read-only for some adapters
```

Config: `<install>/.ie/context_store.json`

```json
{ "adapter": "local_fs" }
```

or

```json
{
  "adapter": "notion",
  "root_page_id": "<uuid>",
  "skills_parent_id": "<optional uuid>",
  "skills_child_title": "Skills"
}
```

Notion token: `IE_NOTION_TOKEN` or `NOTION_TOKEN` (never in the repo).

## Adapters

| Adapter | Skills location | Write |
|---------|-----------------|-------|
| `local_fs` | `<install>/skills/<name>/SKILL.md` | yes |
| `notion` | Child pages under Skills parent | read-first (v0) |

## CLI

```bash
ie context skills
ie context skill mature
ie adapters status
ie adapters set local_fs
ie adapters set notion --root-page-id <id>
```

## Related

- `docs/context-layer.md`, `docs/storage-tiers.md`
- Runtime: `runtime/context_store.py`, `runtime/notion_context_store.py`
