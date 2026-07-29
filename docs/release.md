# Release process (Brew-first)

Goal: **token-free** `brew install ie-os` for Free users.

Private `identity-engineering/os` may stay private. **Public** artifacts live on:

**[identity-engineering/ie-os-dist](https://github.com/identity-engineering/ie-os-dist)**

## Versioning

- Package version in `pyproject.toml` → e.g. `0.1.0`
- Git tag → `v0.1.0` (leading `v`)
- Homebrew formula version → `0.1.0` (same number, no `v`)

## One-time setup

1. Repo `ie-os-dist` is public (already created).
2. CI secret on `os` (optional automation): `DIST_REPO_TOKEN` — PAT with `contents: write` on `ie-os-dist`.
3. Without the secret: upload assets manually after the workflow builds them (see below).

## Ship a release

### A. Tag (from main, clean tree)

```bash
git checkout main && git pull
# ensure pyproject.toml version matches
git tag -a v0.1.0 -m "ie-os 0.1.0"
git push origin v0.1.0
```

### B. GitHub Actions (`release.yml`)

On tag `v*`:

1. Copies `templates/personal` → `ie/templates/personal` (bundled for wheel/sdist)
2. Builds sdist + wheel (`python -m build`)
3. Creates a GitHub Release on **os** with those assets (visible to repo collaborators)
4. If `DIST_REPO_TOKEN` is set: also creates/uploads the same assets on **ie-os-dist** (public)

### C. Manual public upload (if no token)

1. Download `ie_os-0.1.0.tar.gz` (sdist) from the private os release  
   or build locally: `pip install build && python -m build`
2. On [ie-os-dist](https://github.com/identity-engineering/ie-os-dist):
   - Create release tag `v0.1.0`
   - Attach **sdist** as `ie_os-0.1.0.tar.gz` (setuptools default name)
3. Compute checksum:

```bash
shasum -a 256 ie_os-0.1.0.tar.gz
```

### D. Update Homebrew formula

In [homebrew-tap](https://github.com/identity-engineering/homebrew-tap) `Formula/ie-os.rb`:

- `url` → public dist asset  
  `https://github.com/identity-engineering/ie-os-dist/releases/download/v0.1.0/ie_os-0.1.0.tar.gz`
- `sha256` → real hash (not `:no_check`)
- `version` → `0.1.0`

### E. Verify

```bash
brew tap identity-engineering/tap
brew install ie-os
ie --version
ie init   # interactive
```

No `HOMEBREW_GITHUB_API_TOKEN` required for the download.

## Artifact names

| File | Role |
|------|------|
| `ie_os-0.1.0.tar.gz` | sdist — **preferred for Brew** (pip install from source tree) |
| `ie_os-0.1.0-py3-none-any.whl` | wheel — pipx / pip |

Exact sdist name follows setuptools (`ie_os` vs `ie-os`); check `dist/` after build.

## Parallel channels (later)

Same tag, additional publishers:

- PyPI (`twine upload dist/*`)
- winget / apt

Same version string everywhere.

## Related

- `docs/distribution.md`
- `docs/cli.md`
- `docs/language-strategy.md`
