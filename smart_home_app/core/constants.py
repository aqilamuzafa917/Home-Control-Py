"""Shared constants used across the Smart Home application."""

from __future__ import annotations

import os
from pathlib import Path

# --- Theme ---
COLOR_BG = "#1C1C1E"
COLOR_CARD = "#2C2C2E"
COLOR_TEXT = "#FFFFFF"
COLOR_TEXT_SEC = "#98989D"
COLOR_ACCENT = "#0A84FF"
COLOR_GREEN = "#30D158"
COLOR_ORANGE = "#FF9F0A"
COLOR_RED = "#FF453A"
COLOR_BTN_SEC = "#3A3A3C"
COLOR_POWER_OFF = "#3A3A3C"
COLOR_POWER_ON = "#FFFFFF"
COLOR_POWER_ON_TEXT = "#000000"

# --- Hardware constants ---
WIZ_PORT = 38899

# --- Xiaomi device properties ---
PROP_POWER = {"siid": 2, "piid": 1}
PROP_MODE = {"siid": 2, "piid": 4}
PROP_AQI = {"siid": 3, "piid": 4}
PROP_FAVORITE = {"siid": 9, "piid": 11}
PROP_FILTER = {"siid": 4, "piid": 1}

# --- Config ---
CONFIG_FILE = Path.home() / ".xiaomi_config.json"
XIAOMI_CONFIG = CONFIG_FILE
ICSEE_CONFIG = Path.home() / ".home_control_config.json"
LOG_FILE = Path.home() / ".home_control.log"

# --- UI ---
ICON_WIDTH = 40
DEFAULT_TEMP = 4200
DEFAULT_DIMMING = 100

# --- Misc ---
APP_TITLE = "Home Control Py"
DEFAULT_SIZE = (1024, 600)
MIN_SIZE = (800, 500)
DEFAULT_COUNTRY = "sg"

__all__ = [
    "ICON_WIDTH",
    "COLOR_BG",
    "COLOR_CARD",
    "COLOR_TEXT",
    "COLOR_TEXT_SEC",
    "COLOR_ACCENT",
    "COLOR_GREEN",
    "COLOR_ORANGE",
    "COLOR_RED",
    "COLOR_BTN_SEC",
    "COLOR_POWER_OFF",
    "COLOR_POWER_ON",
    "COLOR_POWER_ON_TEXT",
    "WIZ_PORT",
    "PROP_POWER",
    "PROP_MODE",
    "PROP_AQI",
    "PROP_FAVORITE",
    "PROP_FILTER",
    "CONFIG_FILE",
    "APP_TITLE",
    "DEFAULT_SIZE",
    "MIN_SIZE",
    "DEFAULT_TEMP",
    "DEFAULT_DIMMING",
    "DEFAULT_COUNTRY",
    "XIAOMI_CONFIG",
    "ICSEE_CONFIG",
    "LOG_FILE",
]

