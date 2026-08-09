# Identity Engineering OS

**Installable operating layer for Identity Engineering.**

> "Hast du schon Identity Engineering? Setz dir das einfach auf."

Practical, SQLite-first local runtime of the Identity Engineering framework.
Turns geometric + ownership primitives into living, agent-readable projections
with a single transactional database per install.

**Open Core.** The local-first runtime, schemas and Free-tier CLI are open source (MIT). Managed Pro features remain closed. See [`docs/open-core.md`](docs/open-core.md).

## What this is (and is not)

**This is**
- Minimal, personal-first structure: initialize one local DB and the next interaction already updates geometry
- Core contracts: Stem, Trajectory, relative Mass, local Registry, Privacy defaults  
- Local Surface Runtime: Interaction Signals → Foreign Estimates, Registry continuity, receipts, **always-on Geometry Extraction** on Interact
- **TIM cycle** (Think · Interact · Mature) as Probe phases under Relativity  
- **Living-form lens**: Identity as operative form with membrane (Surface) and metabolism (Interaction → Geometry Receipt); agentic loop may be nuclear machinery inside - not the Identity itself  
- Foundation for environment adapters and free personal / paid collective CLI tiers

**This is not (yet)**
- Full digital-organism agent system (sensory / immunity / vitality / … modules)  
- Global social network or attention platform  
- Automatic Tensor rewrite from Geometry Receipts (storage is live; feed is **#8**)

## Orientation

Installability remains, but mutable runtime state is DB-only in V1 (`.ie/ie.sqlite3`).
`README.md` and `IE.md` in an install are orientation documents, not state.
The YAML files under `schemas/` and `templates/personal/` are contracts and
examples only; the runtime never reads them as mutable state.
Everything starts from Identity Engineering: relative Mass, living Tensor, Geometry Receipt as continuous Probe bridge, Stem, Surface as membrane, Ownership as relative degrees of freedom, multi-substrate symmetry, Privacy by design.

See `docs/probes-as-bridge.md`, `docs/tim-cycle.md`, `docs/living-form.md`.

## Minimal structure

```
os/
├── runtime/          # SQLite-first Surface Runtime + geometry hook
├── schemas/
├── templates/personal/
├── docs/
│   ├── principles.md
│   ├── open-core.md
│   ├── probes-as-bridge.md
│   ├── tim-cycle.md
│   ├── living-form.md
│   ├── geometry-hook.md
│   └── …
└── README.md
```

## Current status

- Local Registry + Metric Stem + Interaction Signal  
- SQLite-first V1 Surface Runtime (apply, receipts, thin HTTP)
- Geometry Receipt + always-on Interact hook (local storage; Tensor feed **#8**)  
- TIM grounded as Probe modes; living-form lens (cell nucleus article integrated)  
- Emergent self-Mass + public card + bidirectional sensor  
- Atomic Mature learning, persistent policy, DB integrity and backup commands
- Standard-first + Open Core ecosystem orientation

See `docs/next.md` and `docs/open-core.md`.

## Key docs

| Doc | Purpose |
|-----|---------|
| `docs/open-core.md` | Open Core vs Managed boundary |
| `docs/principles.md` | Invariants |
| `docs/probes-as-bridge.md` | Probes as continuous geometry process |
| `docs/tim-cycle.md` | Think / Interact / Mature as Probe modes |
| `docs/living-form.md` | Identity as living form; cell/organism lens |
| `docs/geometry-hook.md` | Always-on extraction after Interact |
| `docs/mass.md` | Emergent self-Mass + public card |
| `docs/identity-surface.md` | Membrane ops and policy |
| `docs/interaction-signal.md` | Signal across the membrane |
| `docs/surface-runtime-local.md` | How to run local apply / HTTP |
| `docs/managed-sync-queue.md` | Optional offline Managed queue and recovery |
| `docs/bidirectional-gravitational-sensor.md` | Outbound signal + inbound request/inbox |
| `docs/ecosystem-vision.md` | Standard vs platform horizon |
| `docs/next.md` | Praxis order |

## License

MIT. See [LICENSE](LICENSE).

## Related

- Framework + site: [identity-engineering/framework](https://github.com/identity-engineering/framework) · [identity-engineering.org](https://identity-engineering.org)  
- Personal grounding article: [KI ist nicht das neue Gehirn. Sie ist der Zellkern.](https://www.linkedin.com/pulse/ki-ist-nicht-das-neue-gehirn-sie-der-zellkern-jonas-siebler-ogokf) (Jonas Siebler, 15.06.2026)
