"""Helpers for persisting Xiaomi device credentials."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Tuple

from .constants import CONFIG_FILE


def load_credentials() -> Tuple[str | None, str | None]:
    """Load saved IP/token pair if the config file exists."""
    if not CONFIG_FILE.exists():
        return None, None

    try:
        data = json.loads(CONFIG_FILE.read_text())
        return data.get("ip"), data.get("token")
    except (ValueError, OSError):
        return None, None


def save_credentials(ip: str, token: str) -> None:
    """Persist credentials in the user's home directory."""
    payload = {"ip": ip, "token": token}
    try:
        CONFIG_FILE.write_text(json.dumps(payload, indent=2))
    except OSError:
        # Saving errors should not crash the UI; log/ignore.
        pass


def delete_credentials() -> None:
    """Remove saved credentials."""
    try:
        CONFIG_FILE.unlink(missing_ok=True)
    except OSError:
        pass


__all__ = ["load_credentials", "save_credentials", "delete_credentials"]

