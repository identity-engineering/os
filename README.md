# Identity Engineering OS

**Installable operating layer for Identity Engineering.**

> "Hast du schon Identity Engineering? Setz dir das einfach auf."

Practical **Space-first** runtime of the Identity Engineering framework.
A local install is a **mini-Space**: one machine hosting one (or few) Identities
with full Ownership of the data. Mutable state lives in a single transactional
SQLite database per install (the store engine — not the product center).

**Open Core.** Local mini-Space runtime, schemas and Free-tier CLI are open source (MIT).
Managed continuity in the IE-managed Space remains closed. See [`docs/open-core.md`](docs/open-core.md).

## What this is (and is not)

**This is**
- Personal-first **mini-Space**: initialize one local Space and the next interaction already updates geometry
- Core contracts: Stem, Trajectory, relative Mass, local Registry, Privacy defaults
- Local Surface Runtime: Interaction Signals → Foreign Estimates, Registry continuity, receipts, **always-on Geometry Extraction** on Interact
- **IE operating cycle** (Think · Interact · Mature) as Probe phases under Relativity
- **Living-form lens**: Identity as operative form with membrane (Surface / Boundary) and metabolism (Interaction → Geometry Receipt); agentic loop may be nuclear machinery inside — not the Identity itself
- **Account ≠ Identity**: geometry lives on Identities; an IE Account is optional continuity/billing on the managed path
- Foundation for environment adapters and free personal / paid collective tiers

**This is not (yet)**
- Full digital-organism agent system (sensory / immunity / vitality / … modules)
- Global social network or attention platform
- Automatic Tensor rewrite from Geometry Receipts (storage is live; feed is **#8**)
- A requirement to use managed hosting for the geometry loop

## Orientation

Installability remains. Mutable runtime state is DB-only in V1 (`.ie/ie.sqlite3`)
inside a local mini-Space.
`README.md` and `IE.md` in an install are orientation documents, not state.
The YAML files under `schemas/` and `templates/personal/` are contracts and
examples only; the runtime never reads them as mutable state.

Everything starts from Identity Engineering: relative Mass, living Tensor,
Geometry Receipt as continuous Probe bridge, Stem, Surface as membrane,
Ownership as relative degrees of freedom, multi-substrate symmetry, Privacy by design.

See `docs/space-model.md`, `docs/account-identity-model.md`, `docs/probes-as-bridge.md`,
`docs/probe-cycle.md`, `docs/living-form.md`.

## Minimal structure

```
os/
├── runtime/          # Surface Runtime + geometry hook (SQLite store)
├── schemas/
├── templates/personal/
├── docs/
│   ├── principles.md
│   ├── open-core.md
│   ├── space-model.md
│   ├── account-identity-model.md
│   ├── probes-as-bridge.md
│   ├── probe-cycle.md
│   ├── living-form.md
│   ├── geometry-hook.md
│   └── …
└── README.md
```

## Current status

- Local Registry + Metric Stem + Interaction Signal
- Local mini-Space Surface Runtime (apply, receipts, thin HTTP; SQLite store)
- Geometry Receipt + always-on Interact hook (local storage; Tensor feed **#8**)
- Think/Interact/Mature grounded as Probe modes; living-form lens (cell nucleus article integrated)
- Emergent self-Mass + public card + bidirectional sensor
- Atomic Mature learning, persistent policy, DB integrity and backup commands
- Space membrane + Account ≠ Identity contracts locked; multi-Space / multi-Identity capacity next
- Standard-first + Open Core ecosystem orientation

See `docs/next.md` and `docs/open-core.md`.

## Key docs

| Doc | Purpose |
|-----|---------|
| `docs/open-core.md` | Open Core vs Managed boundary |
| `docs/space-model.md` | Space as membrane host; local mini-Space |
| `docs/account-identity-model.md` | Account ≠ Identity |
| `docs/storage-tiers.md` | Free / managed / governed Space tiers |
| `docs/principles.md` | Invariants |
| `docs/probes-as-bridge.md` | Probes as continuous geometry process |
| `docs/probe-cycle.md` | Think / Interact / Mature as Probe modes |
| `docs/living-form.md` | Identity as living form; cell/organism lens |
| `docs/geometry-hook.md` | Always-on extraction after Interact |
| `docs/mass.md` | Emergent self-Mass + public card |
| `docs/identity-surface.md` | Membrane ops and policy |
| `docs/interaction-signal.md` | Signal across the membrane |
| `docs/surface-runtime-local.md` | How to run local apply / HTTP |
| `docs/local-operations-v1.md` | Everyday local mini-Space operations |
| `docs/cli.md` | `ie` command reference |
| `docs/managed-sync-queue.md` | Optional offline Managed queue and recovery |
| `docs/bidirectional-gravitational-sensor.md` | Outbound signal + inbound request/inbox |
| `docs/ecosystem-vision.md` | Standard vs platform horizon |
| `docs/next.md` | Praxis order |

## License

MIT. See [LICENSE](LICENSE).

## Related

- Framework + site: [identity-engineering/framework](https://github.com/identity-engineering/framework) · [identity-engineering.org](https://identity-engineering.org) · public OS face: [/os](https://identity-engineering.org/os)
- Personal grounding article: [KI ist nicht das neue Gehirn. Sie ist der Zellkern.](https://www.linkedin.com/pulse/ki-ist-nicht-das-neue-gehirn-sie-der-zellkern-jonas-siebler-ogokf) (Jonas Siebler, 15.06.2026)
