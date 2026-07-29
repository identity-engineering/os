# Distribution vs product auth

Locked orientation 29.07.2026

## Two layers

| Layer | Question | Free user |
|-------|----------|-----------|
| **Distribution** | How does `ie` get onto the machine? | **No** GitHub account/token |
| **Product account** | No account / free account / pro account | Optional; only when they choose Login or Create |

Private **git for development** must not force tokens onto Free installers.
Public artifacts: **[identity-engineering/ie-os-dist](https://github.com/identity-engineering/ie-os-dist)**.

See `docs/release.md` for the Brew-first ship process.

## Multi-channel packaging

| Channel | Audience | Priority |
|---------|----------|----------|
| **Homebrew** (`identity-engineering/tap`) | macOS | **Primary for Mac** |
| **Public sdist on ie-os-dist** | Brew source + manual pip | **Required for token-free** |
| **PyPI + pipx** | Universal | Parallel, later |
| **winget** / **apt** | Windows / Linux | Later |

Brew Formula `url` must point at **ie-os-dist** (or PyPI), never at a private archive.

## Account capabilities (runtime)

| Account | Public registry metadata of others | Central hosting |
|---------|--------------------------------------|-----------------|
| No account | No | No |
| Free account | Yes (public fields only) | No |
| Pro account | Yes | Yes |

## Related

- `docs/release.md`
- `docs/cli.md`
- `docs/language-strategy.md`
- Tap: [identity-engineering/homebrew-tap](https://github.com/identity-engineering/homebrew-tap)
