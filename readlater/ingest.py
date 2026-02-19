"""Ingest local files into the reading folder, converting to PDF when needed."""

import mimetypes
import shutil
import subprocess
import tempfile
from pathlib import Path

from readlater.config import get_reading_dir


# File types we can convert to PDF
CONVERTIBLE_TYPES = {
    ".html", ".htm",      # web pages saved locally
    ".txt", ".md",        # plain text / markdown
    ".docx", ".doc",      # Word documents
    ".epub",              # ebooks
    ".png", ".jpg", ".jpeg", ".gif", ".webp",  # images
}


def ingest_file(source: str | Path, filename: str | None = None) -> Path:
    """
    Copy a file into the reading folder. If it's not already a PDF,
    attempt to convert it.
    """
    source = Path(source).expanduser().resolve()
    if not source.exists():
        raise FileNotFoundError(f"File not found: {source}")

    reading_dir = get_reading_dir()
    suffix = source.suffix.lower()

    if suffix == ".pdf":
        # Already a PDF — just copy it
        dest = reading_dir / (filename or source.name)
        if dest.exists():
            dest = _unique_name(dest)
        shutil.copy2(source, dest)
        print(f"  Copied: {dest}")
        return dest

    # Try to convert
    out_name = (filename or source.stem) + ".pdf"
    dest = reading_dir / out_name
    if dest.exists():
        dest = _unique_name(dest)

    if suffix in {".html", ".htm"}:
        return _convert_html_file(source, dest)
    elif suffix in {".txt", ".md"}:
        return _convert_text_file(source, dest)
    elif suffix in {".docx", ".doc"}:
        return _convert_office_doc(source, dest)
    elif suffix == ".epub":
        return _convert_epub(source, dest)
    elif suffix in {".png", ".jpg", ".jpeg", ".gif", ".webp"}:
        return _convert_image(source, dest)
    else:
        raise ValueError(
            f"Don't know how to convert {suffix} to PDF. "
            f"Supported types: .pdf, {', '.join(sorted(CONVERTIBLE_TYPES))}"
        )


def _unique_name(path: Path) -> Path:
    counter = 1
    while path.exists():
        path = path.with_stem(f"{path.stem}_{counter}")
        counter += 1
    return path


def _convert_html_file(source: Path, dest: Path) -> Path:
    # Try playwright
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            page.goto(f"file://{source}", wait_until="networkidle", timeout=15_000)
            page.pdf(path=str(dest), format="Letter", print_background=True)
            browser.close()
        print(f"  Converted HTML -> PDF: {dest}")
        return dest
    except ImportError:
        pass

    # Try weasyprint
    try:
        import weasyprint

        doc = weasyprint.HTML(filename=str(source))
        doc.write_pdf(str(dest))
        print(f"  Converted HTML -> PDF: {dest}")
        return dest
    except ImportError:
        raise RuntimeError("Install playwright or weasyprint to convert HTML to PDF.")


def _convert_text_file(source: Path, dest: Path) -> Path:
    """Convert plain text or markdown to PDF via HTML intermediate."""
    text = source.read_text(errors="replace")
    suffix = source.suffix.lower()

    if suffix == ".md":
        # Try markdown -> HTML
        try:
            import markdown

            html_body = markdown.markdown(text, extensions=["fenced_code", "tables"])
        except ImportError:
            # Fall back to treating it as plain text
            escaped = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            html_body = f"<pre style='white-space:pre-wrap;'>{escaped}</pre>"
    else:
        escaped = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        html_body = f"<pre style='font-family:monospace;white-space:pre-wrap;'>{escaped}</pre>"

    html = (
        f"<html><head><meta charset='utf-8'>"
        f"<style>body{{font-family:sans-serif;padding:40px;max-width:800px;margin:auto;line-height:1.6;}}</style>"
        f"</head><body>{html_body}</body></html>"
    )

    # Write temp HTML then convert
    tmp = dest.with_suffix(".tmp.html")
    tmp.write_text(html)
    try:
        result = _convert_html_file(tmp, dest)
        return result
    finally:
        tmp.unlink(missing_ok=True)


def _convert_office_doc(source: Path, dest: Path) -> Path:
    """Convert Word docs using LibreOffice CLI."""
    try:
        subprocess.run(
            [
                "libreoffice", "--headless", "--convert-to", "pdf",
                "--outdir", str(dest.parent), str(source),
            ],
            check=True,
            capture_output=True,
            timeout=120,
        )
        # LibreOffice names the output after the source stem
        lo_output = dest.parent / (source.stem + ".pdf")
        if lo_output != dest:
            lo_output.rename(dest)
        print(f"  Converted {source.suffix} -> PDF: {dest}")
        return dest
    except FileNotFoundError:
        raise RuntimeError(
            "LibreOffice not found. Install it to convert Word documents:\n"
            "  apt install libreoffice-writer  (Linux)\n"
            "  brew install --cask libreoffice (macOS)"
        )


def _convert_epub(source: Path, dest: Path) -> Path:
    """Convert EPUB using Calibre's ebook-convert."""
    try:
        subprocess.run(
            ["ebook-convert", str(source), str(dest)],
            check=True,
            capture_output=True,
            timeout=120,
        )
        print(f"  Converted EPUB -> PDF: {dest}")
        return dest
    except FileNotFoundError:
        raise RuntimeError(
            "Calibre not found. Install it to convert EPUB files:\n"
            "  apt install calibre  (Linux)\n"
            "  brew install --cask calibre (macOS)"
        )


def _convert_image(source: Path, dest: Path) -> Path:
    """Convert image to PDF using Pillow."""
    try:
        from PIL import Image

        img = Image.open(source)
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
        img.save(str(dest), "PDF", resolution=150)
        print(f"  Converted image -> PDF: {dest}")
        return dest
    except ImportError:
        raise RuntimeError("Install Pillow to convert images to PDF: pip install Pillow")
