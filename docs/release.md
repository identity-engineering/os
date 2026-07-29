# Release process (Brew-first)

Goal: **token-free** `brew install ie-os` for Free users.

## Canonical public URLs (org domain)

Installable artifacts are served under **identity-engineering.org**, not as the primary user-facing GitHub URL:

```text
https://identity-engineering.org/releases/ie-os/{version}/ie_os-{version}.tar.gz
https://identity-engineering.org/releases/ie-os/{version}/ie_os-{version}-py3-none-any.whl
```

Example:

```text
https://identity-engineering.org/releases/ie-os/0.1.0/ie_os-0.1.0.tar.gz
```

Homebrew Formula `url` **must** use this host.

Storage behind the domain (implementation detail):

| Backend | Role |
|---------|------|
| Cloudflare R2 / S3 + custom domain | Preferred long-term |
| Static files on the Astro site (`public/releases/…`) | Fine for early releases |
| GitHub `ie-os-dist` | Optional mirror only — not the canonical URL |

Private `identity-engineering/os` stays the build source. Users never need repo access.

## Versioning

- Package version in `pyproject.toml` → e.g. `0.1.0`
- Git tag → `v0.1.0`
- Path segment + Homebrew `version` → `0.1.0` (no `v`)

## Ship a release

### A. Tag

```bash
git checkout main && git pull
git tag -a v0.1.0 -m "ie-os 0.1.0"
git push origin v0.1.0
```

### B. CI (`release.yml`)

On tag `v*`:

1. Bundle `templates/personal` → `ie/templates/personal`
2. `python -m build` → sdist + wheel in `dist/`
3. GitHub Release on **os** (collaborators; optional)
4. **Publish to org domain** (required for Brew):
   - Upload `dist/*` to the releases prefix (R2/S3 or site `public/releases/ie-os/0.1.0/`)
   - Ensure HTTPS and stable paths as above

### C. Checksum

```bash
shasum -a 256 ie_os-0.1.0.tar.gz
```

### D. Homebrew formula

[`identity-engineering/homebrew-tap`](https://github.com/identity-engineering/homebrew-tap) `Formula/ie-os.rb`:

```ruby
url "https://identity-engineering.org/releases/ie-os/0.1.0/ie_os-0.1.0.tar.gz"
version "0.1.0"
sha256 "<real hash>"
```

### E. Verify

```bash
curl -I https://identity-engineering.org/releases/ie-os/0.1.0/ie_os-0.1.0.tar.gz
brew tap identity-engineering/tap
brew install ie-os
ie --version
ie init
```

No GitHub token for the end user.

## One-time DNS / hosting setup

Pick one:

**Astro site (simplest early)**  
Commit or CI-copy files into the website repo under `public/releases/ie-os/{version}/` and deploy. Paths are immediately on `identity-engineering.org`.

**Cloudflare R2 (preferred at scale)**  
- Bucket + public access via custom domain `identity-engineering.org` path or `downloads.identity-engineering.org`  
- CI: `wrangler r2 object put` (or AWS-compatible API) after build  
- Optional: redirect `/releases/*` on the main site to the bucket

**GitHub mirror (optional)**  
Keep uploading to `ie-os-dist` for redundancy; Formula still points at **.org**.

## Related

- `docs/distribution.md`
- `docs/cli.md`
- Website: [identity-engineering.org](https://identity-engineering.org)
