"""Configuration management for readlater."""

import json
import os
from pathlib import Path

DEFAULT_CONFIG_DIR = Path.home() / ".readlater"
DEFAULT_READING_DIR = Path.home() / "Reading"
CONFIG_FILE = DEFAULT_CONFIG_DIR / "config.json"

DEFAULT_CONFIG = {
    "reading_dir": str(DEFAULT_READING_DIR),
    "email": {
        "gmail": {
            "enabled": False,
            "imap_server": "imap.gmail.com",
            "email": "",
            "app_password": "",
            "folder": "INBOX",
            "label_filter": "ReadLater",
            "mark_as_read": True,
        },
        "outlook": {
            "enabled": False,
            "imap_server": "outlook.office365.com",
            "email": "",
            "app_password": "",
            "folder": "INBOX",
            "label_filter": "ReadLater",
            "mark_as_read": True,
        },
    },
    "web": {
        "timeout": 30,
        "wait_for_js": True,
    },
    "onenote": {
        "client_id": "",
        "section_id": "",
        "auto_sync": False,
    },
}


def get_config() -> dict:
    """Load config from disk, creating defaults if needed."""
    if not CONFIG_FILE.exists():
        save_config(DEFAULT_CONFIG)
    with open(CONFIG_FILE) as f:
        return json.load(f)


def save_config(config: dict):
    """Write config to disk."""
    DEFAULT_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)


def get_reading_dir() -> Path:
    """Return the central reading folder path, creating it if needed."""
    config = get_config()
    reading_dir = Path(config["reading_dir"])
    reading_dir.mkdir(parents=True, exist_ok=True)
    return reading_dir


def configure_email(provider: str, email: str, app_password: str, label_filter: str = "ReadLater"):
    """Set up email credentials for a provider."""
    config = get_config()
    if provider not in config["email"]:
        raise ValueError(f"Unknown provider: {provider}. Use 'gmail' or 'outlook'.")
    config["email"][provider]["enabled"] = True
    config["email"][provider]["email"] = email
    config["email"][provider]["app_password"] = app_password
    config["email"][provider]["label_filter"] = label_filter
    save_config(config)
