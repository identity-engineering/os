# Distribution vs product auth

Locked orientation 29.07.2026

## The confusion

> Why would a private repo force every Free user to have a GitHub token?

It should not. That was a **packaging accident**, not a product rule.

Two different layers:

| Layer | Question | Free user |
|-------|----------|-----------|
| **Distribution** | How does the `ie` binary/package get onto my machine? | Must work with **zero** GitHub account / token |
| **Product auth** | Do I use only local files, or also a Pro cloud/surface account? | Free = no account; Pro = login when they choose |

## Why Homebrew hit a token wall

The first Formula pointed at `github.com/identity-engineering/os/...tar.gz`.

If that repository is **private**, GitHub refuses the download without credentials.
Homebrew is only fetching **source code of the tool** — not authenticating the user into IE Pro.

So:

- Private **source repo** → installers that fetch from GitHub need auth
- That blocks the Free promise even though Free features need no IE account

## Correct Free install paths (no GitHub rights)

Any one of these is enough:

1. **PyPI** (preferred for Python CLI): `pip install ie-os` / `pipx install ie-os`
2. **Public release artifacts**: tagged tarball or wheel on a **public** URL (GitHub Releases on a public repo, or object storage)
3. **Homebrew Formula** that installs from PyPI or a public archive (not from a private git tree)
4. Optional later: signed binaries

The private `os` repo can stay private for **development**. What must be public is the **released package** (or the release tarball), not everyone's Identity data.

## Product tiers (runtime behavior)

| Tier | Install | Data | Auth |
|------|---------|------|------|
| **Free** | Public package | Local directory from `ie init` (`~/ie` default) | None |
| **Pro** | Same CLI | Local + optional managed surface / DB | Account only when enabling Pro features |

`ie init` asks free vs pro so the path is clear; in v0, Pro is a stub and still creates a local install only.

Commands that need Pro auth (later): link account, sync to managed surface, team policies — not `init`, `status`, `signal apply` on local files.

## Rules of thumb

1. Never require GitHub credentials to use Free IE.
2. Never require an IE account to use Free local commands.
3. Keep authoring in a private repo if we want; **publish** wheels/tags for distribution.
4. Homebrew tap stays valid once the Formula’s `url` points at a public artifact or PyPI — not at a private archive.

## Related

- `docs/cli.md`
- `docs/ecosystem-vision.md`
- `docs/storage-tiers.md`
- Tap: [identity-engineering/homebrew-tap](https://github.com/identity-engineering/homebrew-tap)
