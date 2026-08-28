# Open Core Policy for IE OS

Locked 02.08.2026  
Space-first wording 09.08.2026  
Commercial terms moved out of this public repo 28.08.2026

## Stance

IE OS follows an **Open Core** model:

- The geometric contracts, local **mini-Space** runtime, CLI, schemas and local store are open source.
- Managed infrastructure, hosted continuity in the **IE-managed Space**, billing and governed-Space features remain closed.

Product language is **Space-first / Identity-scoped**. SQLite is the store engine for local and self-hosted Spaces, not the product center.

Commercial prices, plan caps and go-to-market copy do **not** live in this repository. They live in private `identity-engineering/os-managed` and, for team strategy, in Notion.

This matches `docs/ecosystem-vision.md`, `docs/space-model.md` and `docs/account-identity-model.md`.

## Boundary

| Layer | Contents | Visibility |
|-------|----------|------------|
| **Open Core** | Schemas, local Surface Runtime, Geometry Receipt, Registry contracts, Interaction Signal, IE operating cycle as Probe phases, living-form lens, local mini-Space (SQLite store), `ie` CLI for local operations, contract templates, tests, Space + Account≠Identity architecture docs | Public (this repository) |
| **Managed product** | Hosted SQL adapters, multi-device sync, account auth, billing, plan entitlements, SLA, Identity capacity under accounts, governed Spaces, hosted Surface features | Private (`identity-engineering/os-managed`) |

## Why this cut

1. **Standard first**  
   The Identity-Geometry contracts must be implementable by others without depending on our managed service. That maximises causal entropy of the standard itself.

2. **Local mini-Space remains viable**  
   People who want files on-device keep full ownership. No account is required for the local Geometry Loop. Local install = mini-Space (`docs/space-model.md`).

3. **Economic layer stays closed**  
   Billing, plan limits and hosted continuity do not change the geometric model. Keeping them out of this repo protects the business surface without polluting the open contracts.

4. **Account ≠ Identity**  
   Geometry lives on Identities. Accounts are product auth/plan only. Open Core must not imply "account required to be an Identity".

5. **Alignment with prior decisions**  
   Same logic as the IE Open Core strategy (core open, hosted platform closed).

## Implementation rules

- All code and docs that define the open contracts live in this repository and are released under MIT.
- Future managed adapters must not be required to run the local mini-Space path.
- Release artifacts for Open Core users (`brew install ie-os`, public tarballs) contain only the Open Core.
- Community contributions to the Open Core are welcome under the CONTRIBUTING rules. Review remains strict on geometric consistency and Ownership defaults.
- Public and entry docs prefer **Space / Identity / Account** wording over "SQLite-first product" language.
- Do not add price tables, Stripe IDs or plan SKUs to this repository.

## Related

- `docs/space-model.md`
- `docs/account-identity-model.md`
- `docs/storage-tiers.md`
- `docs/ecosystem-vision.md`
- `docs/principles.md`
- Private product terms: `identity-engineering/os-managed` `docs/pricing.md`, `docs/doc-surfaces.md`
- Public conceptual body: [identity-engineering/framework](https://github.com/identity-engineering/framework) · [/os](https://identity-engineering.org/os)
