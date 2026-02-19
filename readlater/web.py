"""Fetch web pages and convert them to PDF."""

import re
import subprocess
import tempfile
from pathlib import Path
from urllib.parse import urlparse

from readlater.config import get_reading_dir


def _slugify(text: str, max_len: int = 80) -> str:
    """Turn a string into a safe filename slug."""
    text = re.sub(r"[^\w\s-]", "", text.lower())
    text = re.sub(r"[-\s]+", "-", text).strip("-")
    return text[:max_len]


def _title_from_html(html: str) -> str:
    """Extract <title> from raw HTML."""
    match = re.search(r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
    if match:
        return match.group(1).strip()
    return ""


def fetch_url_to_pdf(url: str, filename: str | None = None) -> Path:
    """
    Download a web page and save it as a PDF in the reading folder.

    Uses playwright (headless Chromium) for full JS rendering, falling back
    to a simpler wkhtmltopdf/weasyprint approach if playwright isn't available.
    """
    reading_dir = get_reading_dir()

    # Try playwright first (best quality — renders JS, handles SPAs)
    pdf_path = _try_playwright(url, filename, reading_dir)
    if pdf_path:
        return pdf_path

    # Fallback: wkhtmltopdf
    pdf_path = _try_wkhtmltopdf(url, filename, reading_dir)
    if pdf_path:
        return pdf_path

    # Fallback: weasyprint (pure-python, no external binary)
    return _try_weasyprint(url, filename, reading_dir)


def _output_path(url: str, filename: str | None, reading_dir: Path) -> Path:
    if filename:
        name = filename if filename.endswith(".pdf") else f"{filename}.pdf"
    else:
        name = _slugify(urlparse(url).netloc + "-" + urlparse(url).path) + ".pdf"
    return reading_dir / name


def _try_playwright(url: str, filename: str | None, reading_dir: Path) -> Path | None:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return None

    out = _output_path(url, filename, reading_dir)
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            page.goto(url, wait_until="networkidle", timeout=30_000)
            # Use page title for filename if we generated one
            if not filename:
                title = page.title()
                if title:
                    out = reading_dir / (_slugify(title) + ".pdf")
            page.pdf(path=str(out), format="Letter", print_background=True)
            browser.close()
        print(f"  Saved (playwright): {out}")
        return out
    except Exception as e:
        print(f"  Playwright failed: {e}")
        return None


def _try_wkhtmltopdf(url: str, filename: str | None, reading_dir: Path) -> Path | None:
    out = _output_path(url, filename, reading_dir)
    try:
        subprocess.run(
            ["wkhtmltopdf", "--quiet", "--enable-local-file-access", url, str(out)],
            check=True,
            capture_output=True,
            timeout=60,
        )
        print(f"  Saved (wkhtmltopdf): {out}")
        return out
    except (FileNotFoundError, subprocess.CalledProcessError):
        return None


def _try_weasyprint(url: str, filename: str | None, reading_dir: Path) -> Path:
    try:
        import weasyprint
    except ImportError:
        raise RuntimeError(
            "No PDF renderer available. Install one of:\n"
            "  pip install playwright && python -m playwright install chromium\n"
            "  apt install wkhtmltopdf\n"
            "  pip install weasyprint"
        )

    out = _output_path(url, filename, reading_dir)
    doc = weasyprint.HTML(url=url)
    doc.write_pdf(str(out))
    print(f"  Saved (weasyprint): {out}")
    return out
