"""Update the checked-in IE OS Homebrew formula release metadata."""

from __future__ import annotations

import argparse
import re
from pathlib import Path


PUBLIC_VERSION_PATTERN = re.compile(
    r"^[0-9]{4}\.(?:[1-9]|1[0-2])\.(?:[1-9]|[12][0-9]|3[01])$"
)
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
URL_PATTERN = re.compile(
    r'^(?P<indent>\s*)url "https://identity-engineering\.org/releases/ie-os/[^/]+/ie_os-[^"]+\.tar\.gz"$'
)
VERSION_PATTERN = re.compile(r'^(?P<indent>\s*)version "(?P<value>[^"]+)"$')
SHA_PATTERN = re.compile(r'^(?P<indent>\s*)sha256 "(?P<value>[0-9a-f]{64})"$')


def update_formula(formula_path: Path, *, public_version: str, sha256: str) -> bool:
    if not PUBLIC_VERSION_PATTERN.fullmatch(public_version):
        raise ValueError(f"Invalid public version: {public_version}")
    if not SHA256_PATTERN.fullmatch(sha256):
        raise ValueError("SHA-256 must contain exactly 64 lowercase hexadecimal characters")

    original = formula_path.read_text(encoding="utf-8")
    lines = original.splitlines(keepends=True)
    bodies = [line.rstrip("\r\n") for line in lines]
    url_matches = [(index, URL_PATTERN.fullmatch(body)) for index, body in enumerate(bodies)]
    version_matches = [
        (index, VERSION_PATTERN.fullmatch(body)) for index, body in enumerate(bodies)
    ]
    sha_matches = [(index, SHA_PATTERN.fullmatch(body)) for index, body in enumerate(bodies)]

    url_matches = [(index, match) for index, match in url_matches if match]
    version_matches = [(index, match) for index, match in version_matches if match]
    sha_matches = [(index, match) for index, match in sha_matches if match]
    if len(url_matches) != 1 or len(version_matches) != 1 or len(sha_matches) != 1:
        raise ValueError("Expected exactly one URL, version, and SHA-256 formula line")

    url_index, url_match = url_matches[0]
    version_index, version_match = version_matches[0]
    sha_index, sha_match = sha_matches[0]
    if not url_index < version_index < sha_index:
        raise ValueError("Expected formula lines in URL, version, sha256 order")
    indent = url_match.group("indent")
    if version_match.group("indent") != indent or sha_match.group("indent") != indent:
        raise ValueError("Formula release metadata must use one indentation level")

    newline = "\n"
    if lines[url_index].endswith("\r\n"):
        newline = "\r\n"
    elif not lines[url_index].endswith("\n"):
        newline = ""

    public_url = (
        f"https://identity-engineering.org/releases/ie-os/{public_version}/"
        f"ie_os-{public_version}.tar.gz"
    )
    lines[url_index] = f'{indent}url "{public_url}"{newline}'
    lines[version_index] = f'{indent}version "{public_version}"{newline}'
    lines[sha_index] = f'{indent}sha256 "{sha256}"{newline}'
    updated = "".join(lines)
    if updated == original:
        return False
    formula_path.write_text(updated, encoding="utf-8")
    return True


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("formula", type=Path)
    parser.add_argument("--version", required=True, dest="public_version")
    parser.add_argument("--sha256", required=True)
    arguments = parser.parse_args()

    try:
        changed = update_formula(
            arguments.formula,
            public_version=arguments.public_version,
            sha256=arguments.sha256,
        )
    except (OSError, ValueError) as error:
        parser.error(str(error))
    print("updated" if changed else "already current")


if __name__ == "__main__":
    main()