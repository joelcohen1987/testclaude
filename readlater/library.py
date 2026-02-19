"""Unified content library — tracks PDFs, audio, and links in one place."""

import json
import re
from datetime import datetime
from pathlib import Path

from readlater.config import get_config, get_reading_dir

LIBRARY_FILE = "readlater-library.json"


def _library_path() -> Path:
    return get_reading_dir() / LIBRARY_FILE


def _load_library() -> list[dict]:
    path = _library_path()
    if path.exists():
        return json.loads(path.read_text())
    return []


def _save_library(items: list[dict]):
    path = _library_path()
    path.write_text(json.dumps(items, indent=2, default=str))


def _slugify(text: str, max_len: int = 80) -> str:
    text = re.sub(r"[^\w\s-]", "", text.lower())
    text = re.sub(r"[-\s]+", "-", text).strip("-")
    return text[:max_len]


def add_item(
    title: str,
    content_type: str,  # "pdf", "audio", "link"
    source_url: str | None = None,
    local_file: str | None = None,
    tags: list[str] | None = None,
) -> dict:
    """Add an item to the unified library."""
    item = {
        "id": datetime.now().strftime("%Y%m%d%H%M%S") + "-" + _slugify(title, 30),
        "title": title,
        "type": content_type,
        "source_url": source_url,
        "local_file": local_file,
        "tags": tags or [],
        "added": datetime.now().isoformat(),
        "consumed": False,
    }
    items = _load_library()
    items.insert(0, item)  # newest first
    _save_library(items)
    return item


def mark_consumed(item_id: str):
    items = _load_library()
    for item in items:
        if item["id"] == item_id:
            item["consumed"] = True
            item["consumed_at"] = datetime.now().isoformat()
            break
    _save_library(items)


def remove_item(item_id: str):
    items = _load_library()
    items = [i for i in items if i["id"] != item_id]
    _save_library(items)


def get_items(include_consumed: bool = False, content_type: str | None = None) -> list[dict]:
    items = _load_library()
    if not include_consumed:
        items = [i for i in items if not i.get("consumed")]
    if content_type:
        items = [i for i in items if i["type"] == content_type]
    return items


def sync_folder():
    """
    Scan the reading folder for PDFs that aren't in the library yet
    and add them. This keeps the library in sync if you add files manually.
    """
    reading_dir = get_reading_dir()
    items = _load_library()
    known_files = {i.get("local_file") for i in items if i.get("local_file")}

    added = 0
    for pdf in sorted(reading_dir.glob("*.pdf")):
        if pdf.name == LIBRARY_FILE:
            continue
        if pdf.name not in known_files:
            add_item(
                title=pdf.stem.replace("-", " ").replace("_", " ").title(),
                content_type="pdf",
                local_file=pdf.name,
            )
            added += 1

    if added:
        print(f"  Added {added} new PDF(s) to library.")
    return added
