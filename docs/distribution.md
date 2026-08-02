# Distribution vs product auth

Locked orientation 29.07.2026

## Two layers

| Layer | Question | Free user |
|-------|----------|-----------|
| **Distribution** | How does `ie` get onto the machine? | **No** GitHub account/token |
| **Product account** | No account / free account / pro account | Optional |

## Canonical public artifact host

**identity-engineering.org** only:

```text
https://identity-engineering.org/releases/ie-os/2026.8.2/ie_os-2026.8.2.tar.gz
```

The Git tag keeps the date form `vYYYY.MM.DD` for one-release-per-day
idempotency. The public path and filename use the normalized package version
(`YYYY.M.D`), so the installed CLI prints the same version:

```text
ie-os 2026.8.2
```

Backend: **Cloudflare R2**, served through the existing Pages Function. Private
`identity-engineering/os` is build source only. There is no public GitHub dist
repository.

The Homebrew Formula uses the normalized tarball URL and the SHA-256 of that
exact R2 object. See `docs/release.md` for the automated release contract.

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
