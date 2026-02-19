"""Handle audio content — Spotify podcasts, earnings calls, MP3 URLs."""

import re
import subprocess
from pathlib import Path
from urllib.parse import urlparse

from readlater.config import get_reading_dir
from readlater.library import add_item


def _slugify(text: str, max_len: int = 80) -> str:
    text = re.sub(r"[^\w\s-]", "", text.lower())
    text = re.sub(r"[-\s]+", "-", text).strip("-")
    return text[:max_len]


def is_audio_url(url: str) -> bool:
    """Check if a URL is an audio source we should handle specially."""
    lower = url.lower()
    # Spotify links
    if "open.spotify.com" in lower or "spotify.com/episode" in lower:
        return True
    # Apple Podcasts
    if "podcasts.apple.com" in lower:
        return True
    # Direct audio files
    if any(lower.endswith(ext) for ext in (".mp3", ".m4a", ".wav", ".ogg", ".aac")):
        return True
    # YouTube (could be an earnings call recording)
    if "youtube.com" in lower or "youtu.be" in lower:
        return True
    return False


def save_audio(url: str, title: str | None = None) -> dict:
    """
    Save an audio item to the library.

    - Spotify/Apple Podcasts/YouTube: saved as a link (can't download DRM content)
    - Direct audio URLs (.mp3, etc): downloaded to the reading folder
    """
    lower = url.lower()

    # Spotify — save as link, try to extract episode title
    if "spotify.com" in lower:
        if not title:
            title = _extract_spotify_title(url)
        item = add_item(
            title=title or "Spotify episode",
            content_type="audio",
            source_url=url,
            tags=["podcast", "spotify"],
        )
        print(f"  Saved Spotify link: {title or url}")
        return item

    # Apple Podcasts — save as link
    if "podcasts.apple.com" in lower:
        item = add_item(
            title=title or "Apple Podcasts episode",
            content_type="audio",
            source_url=url,
            tags=["podcast", "apple-podcasts"],
        )
        print(f"  Saved Apple Podcasts link: {title or url}")
        return item

    # YouTube — save as link (could be earnings call, interview, etc)
    if "youtube.com" in lower or "youtu.be" in lower:
        if not title:
            title = _extract_page_title(url)
        item = add_item(
            title=title or "YouTube video",
            content_type="audio",
            source_url=url,
            tags=["video"],
        )
        print(f"  Saved YouTube link: {title or url}")
        return item

    # Direct audio file — download it
    if any(lower.endswith(ext) for ext in (".mp3", ".m4a", ".wav", ".ogg", ".aac")):
        return _download_audio(url, title)

    # Unknown audio-ish URL — save as link
    item = add_item(
        title=title or urlparse(url).path.split("/")[-1] or "Audio",
        content_type="audio",
        source_url=url,
        tags=["audio"],
    )
    print(f"  Saved audio link: {title or url}")
    return item


def _download_audio(url: str, title: str | None) -> dict:
    """Download a direct audio file to the reading folder."""
    import urllib.request

    reading_dir = get_reading_dir()
    parsed = urlparse(url)
    filename = parsed.path.split("/")[-1] or "audio.mp3"

    if title:
        ext = Path(filename).suffix
        filename = _slugify(title) + ext

    dest = reading_dir / filename
    counter = 1
    while dest.exists():
        dest = dest.with_stem(f"{dest.stem}_{counter}")
        counter += 1

    print(f"  Downloading: {url}")
    urllib.request.urlretrieve(url, dest)
    print(f"  Saved: {dest}")

    item = add_item(
        title=title or dest.stem.replace("-", " ").title(),
        content_type="audio",
        source_url=url,
        local_file=dest.name,
        tags=["audio"],
    )
    return item


def _extract_spotify_title(url: str) -> str | None:
    """Try to get the episode title from a Spotify URL via the page."""
    try:
        import urllib.request
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        html = urllib.request.urlopen(req, timeout=10).read().decode(errors="replace")
        match = re.search(r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
        if match:
            title = match.group(1).strip()
            # Clean up " | Spotify" suffix
            title = re.sub(r"\s*[\|–—-]\s*Spotify.*$", "", title)
            return title
    except Exception:
        pass
    return None


def _extract_page_title(url: str) -> str | None:
    """Get the page title from a URL."""
    try:
        import urllib.request
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        html = urllib.request.urlopen(req, timeout=10).read().decode(errors="replace")
        match = re.search(r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
        if match:
            return match.group(1).strip()
    except Exception:
        pass
    return None
