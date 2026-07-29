# Release process (Brew-first)

Goal: **token-free** `brew install ie-os` for Free users.

## Canonical public URLs

```text
https://identity-engineering.org/releases/ie-os/{version}/ie_os-{version}.tar.gz
https://identity-engineering.org/releases/ie-os/{version}/ie_os-{version}-py3-none-any.whl
```

Example:

```text
https://identity-engineering.org/releases/ie-os/0.1.0/ie_os-0.1.0.tar.gz
```

Homebrew Formula `url` **must** use this host.

**Storage:** Cloudflare R2 (preferred), served under the org domain.  
Private `identity-engineering/os` is build source only. No separate public GitHub dist repo.

## Versioning

- `pyproject.toml` → `0.1.0`
- Git tag → `v0.1.0`
- URL path + Formula `version` → `0.1.0`

## Ship a release

### A. Tag

```bash
git checkout main && git pull
git tag -a v0.1.0 -m "ie-os 0.1.0"
git push origin v0.1.0
```

### B. CI (`release.yml`)

On tag `v*`:

1. Bundle templates into the package
2. Build sdist + wheel
3. Attach assets to the GitHub Release on **os** (team access)
4. **Publish to org domain** via Cloudflare R2 (see dedicated issue) so the `.org` URLs resolve

### C. Checksum + Formula

```bash
shasum -a 256 ie_os-0.1.0.tar.gz
```

Update [`homebrew-tap` Formula/ie-os.rb](https://github.com/identity-engineering/homebrew-tap):

```ruby
url "https://identity-engineering.org/releases/ie-os/0.1.0/ie_os-0.1.0.tar.gz"
version "0.1.0"
sha256 "<real hash>"
```

### D. Verify

```bash
curl -I https://identity-engineering.org/releases/ie-os/0.1.0/ie_os-0.1.0.tar.gz
brew update && brew install ie-os
ie --version && ie init
```

## Related

- Issue: Cloudflare R2 releases under identity-engineering.org
- `docs/distribution.md`
- `docs/cli.md`
