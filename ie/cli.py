"""ie — Identity Engineering OS CLI (SQLite-first V1)."""

from __future__ import annotations

# Implementation lives in ie.cli_app to keep this module a stable entrypoint.
from ie.cli_app import app

if __name__ == "__main__":
    app()
