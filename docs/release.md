# Release process

Goal: **token-free** `brew install ie-os` for Free users. `main` is the reviewed
source branch. Releases are created directly from a tested `main` commit; there
is no release PR and no release merge step.

## Version contract

The Git tag is the release source of truth:

| Surface | Format | Example |
|---------|--------|---------|
| Git tag | `vYYYY.MM.DD` | `v2026.08.02` |
| Public URL path | PEP 440 normalized | `2026.8.2` |
| Artifact filename | `ie_os-YYYY.M.D` | `ie_os-2026.8.2.tar.gz` |
| Python metadata and CLI | PEP 440 normalized | `2026.8.2` |

`setuptools-scm` derives the package version from the tag. A clean editable
checkout without an installed distribution reports a development version.
The build already emits normalized artifact names; no post-build rename is
needed.

## CI gate (`ci.yml`)

The CI workflow runs for:

- every pull request targeting `main`
- every push to `main`, including a completed merge
- merge queue check requests

It runs the test suite on Python 3.10, 3.11, and 3.12, then builds and installs
the package once. Configure all four checks as required branch-protection
checks before allowing a merge:

```text
CI / test (Python 3.10)
CI / test (Python 3.11)
CI / test (Python 3.12)
CI / package
```

The daily release workflow does not run the test suite. It verifies that the
push CI workflow completed successfully for the exact `main` SHA before it
creates a tag. This keeps tests in the development gate while preventing an
untested commit from entering the release path.

## Developer artifact (`dev-artifact.yml`)

Use the manual Developer Artifact workflow to test a branch, tag, or SHA as an
installed package without creating a release tag or publishing to R2, GitHub
Releases, or Homebrew. It runs the full test suite, builds a dev-only PEP 440
version, installs the wheel in a fresh virtual environment, and runs
`scripts/dogfood_free.sh` as an installed-package smoke test. The resulting
wheel, sdist, and test script are uploaded as a GitHub Actions artifact for
seven days.

```bash
gh workflow run dev-artifact.yml \
	--repo identity-engineering/os \
	--ref feature/my-change
gh run list --repo identity-engineering/os --workflow dev-artifact.yml --limit 1
gh run download <run-id> --repo identity-engineering/os -D /tmp/ie-os-dev
```

The downloaded artifact can be installed and tested locally:

```bash
python3 -m venv /tmp/ie-os-dev-venv
/tmp/ie-os-dev-venv/bin/pip install /tmp/ie-os-dev/dist/ie_os-*.whl
IE_BIN=/tmp/ie-os-dev-venv/bin/ie \
	PYTHON_BIN=/tmp/ie-os-dev-venv/bin/python \
	bash /tmp/ie-os-dev/scripts/dogfood_free.sh
```

This package path validates bundled templates and the installed `ie` entry
point. It is automated testing only and does not count as Jonas's Dogfood;
real Dogfood uses the Grok MCP connector against code on `main`.
`pip install -e .` remains useful for the faster source-tree loop.

## Daily tag workflow (`daily-release.yml`)

The schedule runs at `01:00 UTC`. The release date is derived in
`Europe/Berlin`; GitHub may delay scheduled jobs, so the date is always computed
at runtime.

The workflow:

1. stops successfully when today's tag already exists
2. compares `main` with the latest valid date tag
3. stops successfully when no new `main` commit exists
4. requires a successful `CI` push run for the current `main` SHA
5. fetches `main` again and aborts if it advanced during the check
6. creates one annotated, immutable `vYYYY.MM.DD` tag directly on that SHA

Manual dispatch supports a date override and a dry run. A dry run is enabled
by default and never creates a tag.

## Tag publisher (`release.yml`)

The tag workflow accepts the date-tag shape only. It then:

1. verifies the successful merge CI run for the tagged SHA
2. bundles `templates/personal` and builds an sdist and wheel
3. uses the normalized files emitted by `setuptools-scm`
4. uploads both files to Cloudflare R2 under `releases/ie-os/YYYY.M.D/`
5. verifies the public tarball size, checksum, and immutable cache header
6. creates the GitHub Release on `identity-engineering/os`
7. updates `Formula/ie-os.rb` and opens a pull request against `homebrew-tap/main`

The public URLs are:

```text
https://identity-engineering.org/releases/ie-os/2026.8.2/ie_os-2026.8.2.tar.gz
https://identity-engineering.org/releases/ie-os/2026.8.2/ie_os-2026.8.2-py3-none-any.whl
```

Cloudflare R2 is the deployment target for CLI releases. The existing Pages
Function serves the R2 objects under `identity-engineering.org`.

## One-time GitHub setup

### Release token

Create a fine-grained token or GitHub App installation token and store it as
the repository secret `IE_RELEASE_TOKEN` in `identity-engineering/os`:

- repository access: `identity-engineering/os` and `identity-engineering/homebrew-tap`
- `Contents: Read and write` on both repositories
- `Pull requests: Read and write` on `identity-engineering/homebrew-tap`
- `Actions: Read` on `identity-engineering/os`

The token is used to create the date tag and to push the Homebrew formula
commit. The workflow never force-pushes a tag or a tap branch.

### R2 secrets

The repository also needs these Actions secrets:

```text
CF_R2_ACCESS_KEY_ID
CF_R2_SECRET_ACCESS_KEY
```

They must have write access to the `ie-os-releases` bucket. The R2 endpoint is
kept as a non-secret account endpoint in the workflow.

### Branch protection

Protect `main` and require the four CI checks listed above for pull requests.
Protect `v*` tags against updates and deletion. Protect `homebrew-tap/main` and
require a pull request for formula changes. The release token creates a
versioned formula branch and pull request; it does not need a bypass for the
protected default branch.

The repositories currently use solo-maintainer mode: a pull request is
required, but no second-person approval is required because the organization
has one active collaborator. Once a second maintainer is added, raise the
required approval count to one and enable code-owner reviews.

## First run

After merging these workflow and packaging changes:

```bash
gh workflow run "Daily Release Tag" --repo identity-engineering/os --ref main
```

Leave the default `dry_run=true` for the first run. Then dispatch it again with
`dry_run=false`. Since there is currently no date tag, the first successful run
uses the current `Europe/Berlin` date and starts the tag publisher.

Verify the GitHub Release, both R2 URLs, the Homebrew formula checksum, and:

```bash
brew update
brew upgrade ie-os
ie --version
```

If CI is still running or failed for `main`, the daily workflow creates no tag;
the next scheduled run can retry. If publishing fails after the tag exists,
rerun the tag workflow for that immutable tag instead of moving the tag.

## Related

- `docs/distribution.md`
- `docs/cli.md`
- [Homebrew tap](https://github.com/identity-engineering/homebrew-tap)
