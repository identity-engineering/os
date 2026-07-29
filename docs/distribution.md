# Distribution vs product auth

Locked orientation 29.07.2026

## Two layers

| Layer | Question | Free user |
|-------|----------|-----------|
| **Distribution** | How does `ie` get onto the machine? | **No** GitHub account/token |
| **Product account** | No account / free account / pro account | Optional |

## Canonical public artifact host

**identity-engineering.org** — not GitHub as the primary download URL.

```text
https://identity-engineering.org/releases/ie-os/{version}/ie_os-{version}.tar.gz
```

Private git for development is fine. Bytes that Brew/pip download must be public on the org domain (R2, site static, or equivalent). See `docs/release.md`.

## Multi-channel packaging

| Channel | Audience | Priority |
|---------|----------|----------|
| **Homebrew** + **.org releases** | macOS | Primary |
| PyPI / pipx | Universal | Parallel, later |
| winget / apt | Windows / Linux | Later |

## Account capabilities (runtime)

| Account | Public registry metadata | Central hosting |
|---------|--------------------------|-----------------|
| No account | No | No |
| Free account | Yes (public fields) | No |
| Pro account | Yes | Yes |

## Related

- `docs/release.md`
- `docs/cli.md`
- Tap: [identity-engineering/homebrew-tap](https://github.com/identity-engineering/homebrew-tap)
