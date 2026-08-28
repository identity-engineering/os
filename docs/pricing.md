# Pricing direction (Go-Live)

Status: product direction locked 23.08.2026, written 28.08.2026  
Connector / Local-link rules remain open and will be specified later.

Canonical product pricing lives here. `docs/storage-tiers.md` describes storage backends. This file describes what we sell and recommend.

## Stance

**Managed is the main path.** Free Managed is the easy entry we recommend.
Local is a separate private Space for people who want the data on their machine.
We meter **Identity capacity and membrane strength**, not seats and not API calls.

Supersedes older TIM / IE stories that priced Personal at ~70 EUR, used Start / Core / Growth company packages as the product ladder, or treated local-first as the Free product.

## Tiers

| Tier | Price | Character | Limits (start) | Included | Not included |
|------|-------|-----------|----------------|----------|--------------|
| **Free Managed** | 0 EUR | Main path, easy entry | 3 Identities in the IE-managed Space | Account, continuity, backups, multi-device, standard skills + Mature, Surface (local MCP + thin managed), Geometry Loop | Extra Identity slots, long history / full retention, advanced policy, Local-Space connector |
| **Local (private Space)** | 0 EUR | Separate private path | Local geometry remains usable; connector rules later | Full local Geometry Loop, CLI, local MCP, Context Layer, export | No default Managed link. Isolated on purpose. |
| **Personal Pro** | **9 EUR / month** or **90 EUR / year** | Paid continuity + capacity | About 10-15 Identities + **1 Local Space with connector** | Everything in Free Managed, more slots, full history, basic policy / grants, Local-Space connector, early-support priority | Governed Space |
| **Team** | from **59 EUR / month** (or 590 EUR / year) per Governed Space | Membrane strength | Higher Identity capacity | Harder membrane, isolation, audit, optional self-hosted federation | Enterprise extras |
| **Enterprise** | custom | later | custom | SLA, SSO, dedicated | - |

Team and Enterprise stay waitlist until first external Geometry Loop runs and first paying Pro users exist.

## What we price

Billable units:

1. Identity slots in the IE-managed Space
2. Multi-device continuity and backup / history retention
3. Local-Space connector (Pro)
4. Policy / jurisdiction depth
5. Governed Space (Team)

Not paywalled:

- Geometric contracts
- Local Geometry Loop itself
- Emergent Mass
- Export
- Account ≠ Identity

## Init paths

- Recommended: `ie init --managed` (account, Free Managed)
- Private: `ie init --local` (no account)

Exact CLI flags can land later. The product default is Managed.

## Open items (later)

- Exact Local ↔ Managed connector policy
- Whether a pure Local install may later attach to Managed without Pro
- Soft vs hard local Identity limits
- Stripe price IDs and public `/os` table after first external run

## Related

- `docs/storage-tiers.md`
- `docs/open-core.md`
- `docs/account-identity-model.md`
- `docs/space-model.md`
