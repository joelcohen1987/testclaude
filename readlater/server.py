"""Tiny local HTTP server that the Chrome extension talks to."""

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

from readlater.config import get_reading_dir

DEFAULT_PORT = 24247  # "READ" on a phone keypad :)


class ReadLaterHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path == "/save":
            self._handle_save()
        elif self.path == "/save-html":
            self._handle_save_html()
        else:
            self._respond(404, {"error": "Not found"})

    def do_GET(self):
        if self.path == "/status":
            self._respond(200, {"status": "running", "reading_dir": str(get_reading_dir())})
        else:
            self._respond(404, {"error": "Not found"})

    def do_OPTIONS(self):
        """Handle CORS preflight for the Chrome extension."""
        self.send_response(200)
        self._cors_headers()
        self.send_header("Content-Length", "0")
        self.end_headers()

    def _handle_save(self):
        """Save a URL as PDF."""
        try:
            body = self._read_body()
            url = body.get("url", "").strip()
            title = body.get("title", "").strip() or None
            if not url:
                self._respond(400, {"error": "Missing 'url' field"})
                return

            # Run in background thread so we respond immediately
            def do_save():
                try:
                    from readlater.web import fetch_url_to_pdf
                    fetch_url_to_pdf(url, filename=title)
                except Exception as e:
                    print(f"  Error saving {url}: {e}")

            threading.Thread(target=do_save, daemon=True).start()
            self._respond(200, {"status": "saving", "url": url})

        except Exception as e:
            self._respond(500, {"error": str(e)})

    def _handle_save_html(self):
        """Save raw HTML content as PDF (for email bodies captured by the extension)."""
        try:
            body = self._read_body()
            html = body.get("html", "")
            title = body.get("title", "page").strip()
            if not html:
                self._respond(400, {"error": "Missing 'html' field"})
                return

            def do_save():
                try:
                    import re
                    from datetime import datetime
                    from pathlib import Path

                    slug = re.sub(r"[^\w\s-]", "", title.lower())
                    slug = re.sub(r"[-\s]+", "-", slug).strip("-")[:80]
                    datestamp = datetime.now().strftime("%Y%m%d-%H%M")
                    reading_dir = get_reading_dir()
                    pdf_path = reading_dir / f"{datestamp}-{slug}.pdf"

                    # Try playwright
                    try:
                        from playwright.sync_api import sync_playwright
                        with sync_playwright() as p:
                            browser = p.chromium.launch()
                            page = browser.new_page()
                            page.set_content(html, wait_until="networkidle", timeout=15_000)
                            page.pdf(path=str(pdf_path), format="Letter", print_background=True)
                            browser.close()
                        print(f"  Saved HTML content: {pdf_path}")
                        return
                    except ImportError:
                        pass

                    # Try weasyprint
                    try:
                        import weasyprint
                        doc = weasyprint.HTML(string=html)
                        doc.write_pdf(str(pdf_path))
                        print(f"  Saved HTML content: {pdf_path}")
                        return
                    except ImportError:
                        pass

                    # Fallback: save as HTML
                    html_path = pdf_path.with_suffix(".html")
                    html_path.write_text(html)
                    print(f"  No PDF renderer — saved as HTML: {html_path}")

                except Exception as e:
                    print(f"  Error saving HTML: {e}")

            threading.Thread(target=do_save, daemon=True).start()
            self._respond(200, {"status": "saving", "title": title})

        except Exception as e:
            self._respond(500, {"error": str(e)})

    def _read_body(self) -> dict:
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length)
        return json.loads(raw)

    def _cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def _respond(self, code: int, data: dict):
        self.send_response(code)
        self._cors_headers()
        self.send_header("Content-Type", "application/json")
        body = json.dumps(data).encode()
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        print(f"  [server] {args[0]}")


def run_server(port: int = DEFAULT_PORT):
    """Start the local readlater server."""
    server = HTTPServer(("127.0.0.1", port), ReadLaterHandler)
    print(f"ReadLater server running on http://127.0.0.1:{port}")
    print(f"PDFs will be saved to: {get_reading_dir()}")
    print("Press Ctrl+C to stop.\n")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
        server.server_close()
