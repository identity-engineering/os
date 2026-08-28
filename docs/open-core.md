# Open Core Policy for IE OS

Locked 02.08.2026  
Space-first wording 09.08.2026  
Product path updated 28.08.2026: recommended Free is Managed; local stays Open Core

## Stance

IE OS follows an **Open Core** model:

- The geometric contracts, local **mini-Space** runtime, CLI, schemas and local store are open source.
- Managed infrastructure, hosted continuity in the **IE-managed Space**, billing and advanced collective / governed-Space features remain closed.

Product language is **Space-first / Identity-scoped**. SQLite is the store engine for local and self-hosted Spaces - not the product center.

**Recommended product entry is Free Managed** (`docs/pricing.md`). Local is the private alternative, not the default Free plan.

This matches the ecosystem orientation in `docs/ecosystem-vision.md` and the Space / Account contracts in `docs/space-model.md` and `docs/account-identity-model.md`.

## Boundary

| Layer | Contents | Visibility |
|-------|----------|------------|
| **Open Core** | Schemas, local Surface Runtime, Geometry Receipt, Registry contracts, Interaction Signal, IE operating cycle as Probe phases, living-form lens, local mini-Space (SQLite store), `ie` CLI for local operations, contract templates, tests, Space + Account≠Identity architecture docs | Public (this repository) |
| **Managed (Free + Pro + Team)** | Hosted SQL adapters, multi-device sync, account auth, billing, SLA, Identity capacity under accounts, collective/organisational governed Spaces, Pro Surface features, Local-Space connector | Private (separate repository or private modules) |

## Why this cut

1. **Standard first**  
   The Identity-Geometry contracts must be implementable by others without depending on our managed service. That maximises causal entropy of the standard itself.

2. **Local mini-Space remains viable**  
   People who want files on-device keep full ownership. No account is required for the local Geometry Loop. Local install = private mini-Space (`docs/space-model.md`). This path is Open Core, not the recommended Free product.

3. **Economic layer stays clean**  
   Free Managed sells easy entry under a 3-Identity cap. Pro sells capacity, history and a Local-Space connector. Team sells membrane strength. None of this changes the geometric model. Keeping managed closed protects the business surface without polluting the open contracts.

4. **Account ≠ Identity**  
   Geometry lives on Identities. Accounts are product auth/plan only. Open Core must not imply "account required to be an Identity". The recommended product path does require an account.

5. **Alignment with prior decisions**  
   Same logic as the IE Open Core strategy (core open, hosted platform closed).

## Implementation rules

- All code and docs that define the open contracts live in this repository and are released under MIT.
- Future managed adapters must not be required to run the local private mini-Space path.
- Release artifacts for local / Open Core users (`brew install ie-os`, public tarballs) contain only the Open Core.
- Community contributions to the Open Core are welcome under the CONTRIBUTING rules. Review remains strict on geometric consistency and Ownership defaults.
- Public and entry docs prefer **Space / Identity / Account** wording over "SQLite-first product" language.
- Product copy recommends Free Managed first. Local is described as the private Space option.

## Related

- `docs/pricing.md`
- `docs/space-model.md`
- `docs/account-identity-model.md`
- `docs/storage-tiers.md`
- `docs/ecosystem-vision.md`
- `docs/principles.md`
- Public conceptual body: [identity-engineering/framework](https://github.com/identity-engineering/framework) · [/os](https://identity-engineering.org/os)
