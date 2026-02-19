"""Fetch emails via IMAP and convert to PDF."""

import email
import imaplib
import re
import tempfile
from datetime import datetime
from email import policy
from email.message import EmailMessage
from pathlib import Path

from readlater.config import get_config, get_reading_dir


def _slugify(text: str, max_len: int = 80) -> str:
    text = re.sub(r"[^\w\s-]", "", text.lower())
    text = re.sub(r"[-\s]+", "-", text).strip("-")
    return text[:max_len]


def _email_body_to_html(msg: EmailMessage) -> str:
    """Extract a readable HTML representation from an email message."""
    html_part = None
    text_part = None

    if msg.is_multipart():
        for part in msg.walk():
            ct = part.get_content_type()
            if ct == "text/html" and html_part is None:
                html_part = part.get_content()
            elif ct == "text/plain" and text_part is None:
                text_part = part.get_content()
    else:
        ct = msg.get_content_type()
        if ct == "text/html":
            html_part = msg.get_content()
        elif ct == "text/plain":
            text_part = msg.get_content()

    subject = msg.get("Subject", "(no subject)")
    sender = msg.get("From", "unknown")
    date = msg.get("Date", "")

    header_html = (
        f"<div style='font-family:sans-serif;padding:20px;border-bottom:1px solid #ccc;'>"
        f"<h2>{subject}</h2>"
        f"<p><strong>From:</strong> {sender}<br>"
        f"<strong>Date:</strong> {date}</p>"
        f"</div>"
    )

    if html_part:
        # Inject our header before the body
        body = html_part
    elif text_part:
        escaped = text_part.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        body = f"<pre style='font-family:sans-serif;padding:20px;white-space:pre-wrap;'>{escaped}</pre>"
    else:
        body = "<p>No readable content found.</p>"

    return f"<html><body>{header_html}{body}</body></html>"


def _html_to_pdf(html: str, output_path: Path) -> Path:
    """Convert an HTML string to PDF."""
    # Try playwright
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            page.set_content(html, wait_until="networkidle", timeout=15_000)
            page.pdf(path=str(output_path), format="Letter", print_background=True)
            browser.close()
        return output_path
    except ImportError:
        pass

    # Try weasyprint
    try:
        import weasyprint

        doc = weasyprint.HTML(string=html)
        doc.write_pdf(str(output_path))
        return output_path
    except ImportError:
        pass

    # Fallback: write as HTML (still readable)
    html_path = output_path.with_suffix(".html")
    html_path.write_text(html)
    raise RuntimeError(
        f"No PDF renderer available. Email saved as HTML instead: {html_path}\n"
        "Install playwright or weasyprint for PDF conversion."
    )


def _extract_pdf_attachments(msg: EmailMessage, reading_dir: Path) -> list[Path]:
    """Pull out any PDF attachments and save them directly."""
    saved = []
    for part in msg.walk():
        ct = part.get_content_type()
        fn = part.get_filename()
        if fn and (ct == "application/pdf" or fn.lower().endswith(".pdf")):
            out = reading_dir / fn
            # Avoid overwriting
            counter = 1
            while out.exists():
                stem = out.stem
                out = reading_dir / f"{stem}_{counter}.pdf"
                counter += 1
            out.write_bytes(part.get_payload(decode=True))
            saved.append(out)
            print(f"  Attachment saved: {out}")
    return saved


def fetch_emails(
    provider: str | None = None,
    max_emails: int = 20,
    save_body: bool = True,
    save_attachments: bool = True,
    search_criteria: str | None = None,
) -> list[Path]:
    """
    Connect to configured email accounts via IMAP and pull reading material.

    - PDF attachments are saved directly.
    - Email bodies are converted to PDF.
    - By default, looks for emails matching the label_filter in config.

    Returns list of saved file paths.
    """
    config = get_config()
    reading_dir = get_reading_dir()
    saved_files: list[Path] = []

    providers = [provider] if provider else ["gmail", "outlook"]

    for prov in providers:
        prov_config = config["email"].get(prov)
        if not prov_config or not prov_config.get("enabled"):
            if provider:
                print(f"  {prov} is not configured. Run: readlater config-email {prov}")
            continue

        print(f"Connecting to {prov} ({prov_config['imap_server']})...")
        try:
            imap = imaplib.IMAP4_SSL(prov_config["imap_server"])
            imap.login(prov_config["email"], prov_config["app_password"])
        except Exception as e:
            print(f"  Failed to connect to {prov}: {e}")
            continue

        folder = prov_config.get("folder", "INBOX")
        imap.select(folder)

        # Build search query
        if search_criteria:
            query = search_criteria
        else:
            label = prov_config.get("label_filter", "")
            if label and prov == "gmail":
                query = f'(X-GM-LABELS "{label}" UNSEEN)'
            elif label:
                query = f"(UNSEEN)"
            else:
                query = "(UNSEEN)"

        status, msg_ids = imap.search(None, query)
        if status != "OK" or not msg_ids[0]:
            print(f"  No matching emails in {prov}/{folder}")
            imap.logout()
            continue

        ids = msg_ids[0].split()[-max_emails:]
        print(f"  Found {len(ids)} email(s) to process.")

        for mid in ids:
            status, data = imap.fetch(mid, "(RFC822)")
            if status != "OK":
                continue
            raw = data[0][1]
            msg = email.message_from_bytes(raw, policy=policy.default)

            subject = msg.get("Subject", "no-subject")
            date_str = msg.get("Date", "")
            slug = _slugify(subject)
            datestamp = datetime.now().strftime("%Y%m%d")

            print(f"  Processing: {subject}")

            # Save PDF attachments
            if save_attachments:
                saved_files.extend(_extract_pdf_attachments(msg, reading_dir))

            # Convert email body to PDF
            if save_body:
                html = _email_body_to_html(msg)
                pdf_name = f"email-{datestamp}-{slug}.pdf"
                pdf_path = reading_dir / pdf_name
                try:
                    result = _html_to_pdf(html, pdf_path)
                    saved_files.append(result)
                    print(f"  Email body saved: {result}")
                except RuntimeError as e:
                    print(f"  Warning: {e}")

            # Mark as read if configured
            if prov_config.get("mark_as_read"):
                imap.store(mid, "+FLAGS", "\\Seen")

        imap.logout()

    return saved_files
