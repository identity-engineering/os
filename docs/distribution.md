# Distribution vs product auth

Locked orientation 29.07.2026

## Two layers

| Layer | Question | Free user |
|-------|----------|-----------|
| **Distribution** | How does `ie` get onto the machine? | **No** GitHub account/token |
| **Product account** | No account / free account / pro account | Optional; only when they choose Login or Create |

Private **git for development** must not force tokens onto Free installers.
What must be public is the **released package** (or release artifact).

## Multi-channel packaging (not either/or)

Ship the **same** versioned package through several installers over time:

| Channel | Audience | Priority |
|---------|----------|----------|
| **Homebrew** (`identity-engineering/tap` → later core) | macOS default UX | **Primary for Mac** |
| **PyPI + pipx** | Linux/Mac/Windows, agents, CI | **Primary universal** |
| **winget** | Windows | Later |
| **apt** / other native | Linux distros | Later |
| Optional: signed binaries | Air-gapped / minimal | Later |

**Why PyPI even if you prefer Brew?**

- Homebrew Formulae for Python CLIs usually install from a **public** source of truth (often PyPI or a public tarball).
- One wheel on PyPI feeds: `pipx`, the Brew formula, and later other wrappers.
- Brew alone does not cover Windows/Linux users or headless agents.

So: **Brew as the Mac front door**, **PyPI as the shared package backend** — not competitors.

## Account capabilities (runtime)

| Account | Public registry metadata of others | Central hosting |
|---------|--------------------------------------|-----------------|
| No account | No | No |
| Free account | Yes (public fields only) | No |
| Pro account | Yes | Yes (IE managed surface / DB) |

Local Stem, Registry, and signal apply work in all modes under Ownership defaults.

## Homebrew + private git (current footgun)

If the Formula `url` points at a **private** GitHub archive, Brew needs a token.
That violates the Free distribution rule.

Fix: point Formula at **PyPI** or a **public** release asset after the first publish; keep the git repo private for day-to-day work if desired.

## Related

- `docs/cli.md`
- `docs/storage-tiers.md`
- `docs/ecosystem-vision.md`
- Tap: [identity-engineering/homebrew-tap](https://github.com/identity-engineering/homebrew-tap)
