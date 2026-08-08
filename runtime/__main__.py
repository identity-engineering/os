"""Minimal CLI entry for local apply (python -m runtime ...).

Full Typer CLI comes later (issue #18). This is only the deterministic apply path.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .apply import apply_from_dict
from .models import ApplyStatus
from .sqlite_store import SQLiteStore


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m runtime",
        description="IE OS Surface Runtime v0 – local deterministic apply",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    apply_p = sub.add_parser("apply", help="Apply an Interaction Signal from JSON file or stdin")
    apply_p.add_argument(
        "--install",
        "--registry",
        dest="install_root",
        required=True,
        help="Path to the IE install root (legacy alias: --registry)",
    )
    apply_p.add_argument("--to", help="Expected to_handle (surface identity check)")
    apply_p.add_argument("--open-consent", action="store_true", help="Apply consent fields without grants (dogfood)")
    apply_p.add_argument("--payload", help="Path to JSON payload (default: stdin)")

    args = parser.parse_args(argv)

    if args.cmd == "apply":
        if args.payload:
            raw = Path(args.payload).read_text(encoding="utf-8")
        else:
            raw = sys.stdin.read()
        payload = json.loads(raw)

        policy = (
            SQLiteStore.from_registry_root(args.install_root).load_policy(
                open_consent=True
            )
            if args.open_consent
            else None
        )
        receipt = apply_from_dict(
            payload,
            registry_root=args.install_root,
            policy=policy,
            expected_to_handle=args.to,
        )

        print(json.dumps(receipt.to_dict(), indent=2, ensure_ascii=False))
        if receipt.status in (ApplyStatus.REJECTED,):
            return 1
        return 0

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
