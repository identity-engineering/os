# Open Core Policy for IE OS

Locked 02.08.2026

## Stance

IE OS follows an **Open Core** model:

- The geometric contracts, local-first runtime, CLI, schemas and Free-tier storage are open source.
- Managed infrastructure, hosted continuity, billing and advanced collective features remain closed.

This matches the ecosystem orientation already stated in `docs/ecosystem-vision.md` and the TIM Open Core strategy we previously designed.

## Boundary

| Layer | Contents | Visibility |
|-------|----------|------------|
| **Open Core** | Schemas, local Surface Runtime, Geometry Receipt, Registry contracts, Interaction Signal, TIM as Probe phases, living-form lens, Free local storage (YAML/SQLite), `ie` CLI for local operations, personal templates, tests | Public (this repository) |
| **Managed / Pro** | Hosted SQL adapters, multi-device sync, account auth beyond stub, billing, SLA, collective/organisational governance modules, Pro Surface features | Private (separate repository or private modules) |

## Why this cut

1. **Standard first**  
   The Identity-Geometry contracts must be implementable by others without depending on our managed service. That maximises causal entropy of the standard itself.

2. **Local-first remains viable**  
   Free users keep full ownership of their files. No account is required for the core geometry loop.

3. **Economic layer stays clean**  
   Managed Pro sells continuity and convenience. It does not change the geometric model. Keeping it closed protects the business surface without polluting the open contracts.

4. **Alignment with prior decisions**  
   Same logic as the TIM Open Core strategy (core open, advanced features + hosted platform closed).

## Implementation rules

- All code and docs that define the open contracts live in this repository and are released under MIT.
- Future managed adapters must not be required to run the local Free path.
- Release artifacts for Free users (`brew install ie-os`, public tarballs) contain only the Open Core.
- Community contributions to the Open Core are welcome under the CONTRIBUTING rules. Review remains strict on geometric consistency and Ownership defaults.

## Related

- `docs/ecosystem-vision.md`
- `docs/principles.md`
- `docs/storage-tiers.md`
- Public conceptual body: [identity-engineering/framework](https://github.com/identity-engineering/framework)
