"""Minimal dotenv loader for offline test environments."""

from __future__ import annotations

import os
from pathlib import Path


def load_dotenv(path: str = ".env") -> bool:
    env_path = Path(path)
    if not env_path.exists():
        return False
    for raw in env_path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())
    return True
