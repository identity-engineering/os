"""SQLite database lifecycle and the initial DB-only V1 schema."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator, Optional, Union
from uuid import uuid4

DB_DIR_NAME = ".ie"
DB_FILENAME = "ie.sqlite3"
SCHEMA_VERSION = 5
