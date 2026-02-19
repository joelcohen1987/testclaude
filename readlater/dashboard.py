"""Mobile-friendly web dashboard — your unified content list."""

import json
import mimetypes
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from readlater.config import get_reading_dir
from readlater.library import get_items, mark_consumed, sync_folder

DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-title" content="ReadLater">
<title>ReadLater</title>
<style>
  :root {
    --bg: #f5f5f5; --card: #fff; --text: #222; --muted: #888;
    --accent: #1976d2; --accent-light: #e3f2fd;
    --green: #4caf50; --orange: #ff9800; --purple: #9c27b0;
  }
  @media (prefers-color-scheme: dark) {
    :root {
      --bg: #121212; --card: #1e1e1e; --text: #e0e0e0; --muted: #888;
      --accent: #64b5f6; --accent-light: #1a2a3a;
    }
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    background: var(--bg); color: var(--text);
    padding: 16px; max-width: 700px; margin: 0 auto;
    -webkit-font-smoothing: antialiased;
  }
  h1 { font-size: 24px; margin-bottom: 16px; }
  .filters {
    display: flex; gap: 8px; margin-bottom: 16px; flex-wrap: wrap;
  }
  .filter-btn {
    padding: 6px 14px; border-radius: 20px; border: 1px solid var(--muted);
    background: var(--card); color: var(--text); font-size: 14px;
    cursor: pointer; transition: all 0.15s;
  }
  .filter-btn.active {
    background: var(--accent); color: white; border-color: var(--accent);
  }
  .item {
    background: var(--card); border-radius: 12px; padding: 16px;
    margin-bottom: 12px; box-shadow: 0 1px 3px rgba(0,0,0,0.08);
    display: flex; align-items: center; gap: 14px;
    text-decoration: none; color: var(--text);
    transition: transform 0.1s;
    cursor: pointer;
  }
  .item:active { transform: scale(0.98); }
  .icon {
    width: 44px; height: 44px; border-radius: 10px;
    display: flex; align-items: center; justify-content: center;
    font-size: 22px; flex-shrink: 0;
  }
  .icon-pdf { background: #ffebee; }
  .icon-audio { background: #e8f5e9; }
  .icon-link { background: #e3f2fd; }
  .icon-video { background: #fff3e0; }
  .details { flex: 1; min-width: 0; }
  .title {
    font-size: 15px; font-weight: 600;
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
  }
  .meta { font-size: 12px; color: var(--muted); margin-top: 4px; }
  .tag {
    display: inline-block; font-size: 11px; padding: 2px 8px;
    border-radius: 10px; background: var(--accent-light); color: var(--accent);
    margin-right: 4px;
  }
  .done-btn {
    width: 32px; height: 32px; border-radius: 50%;
    border: 2px solid var(--muted); background: none;
    cursor: pointer; flex-shrink: 0; font-size: 16px;
    display: flex; align-items: center; justify-content: center;
    transition: all 0.15s;
  }
  .done-btn:hover { border-color: var(--green); color: var(--green); }
  .empty {
    text-align: center; color: var(--muted); padding: 60px 20px;
    font-size: 16px;
  }
  .count { font-size: 13px; color: var(--muted); margin-bottom: 12px; }
</style>
</head>
<body>

<h1>ReadLater</h1>

<div class="filters">
  <button class="filter-btn active" data-filter="all">All</button>
  <button class="filter-btn" data-filter="pdf">PDFs</button>
  <button class="filter-btn" data-filter="audio">Audio</button>
  <button class="filter-btn" data-filter="link">Links</button>
</div>

<div class="count" id="count"></div>
<div id="list"></div>

<script>
let items = [];
let filter = 'all';

async function load() {
  const res = await fetch('/api/items');
  items = await res.json();
  render();
}

function render() {
  const filtered = filter === 'all' ? items : items.filter(i => i.type === filter);
  const list = document.getElementById('list');
  const count = document.getElementById('count');
  count.textContent = filtered.length + ' item' + (filtered.length !== 1 ? 's' : '');

  if (filtered.length === 0) {
    list.innerHTML = '<div class="empty">Nothing here yet.<br>Save something with the Chrome extension or CLI.</div>';
    return;
  }

  list.innerHTML = filtered.map(item => {
    const icon = item.type === 'pdf' ? '&#128196;'
      : item.type === 'audio' ? '&#127911;'
      : item.tags && item.tags.includes('video') ? '&#9654;&#65039;'
      : '&#128279;';
    const iconClass = item.tags && item.tags.includes('video') ? 'icon-video'
      : 'icon-' + item.type;

    const href = item.local_file
      ? '/files/' + encodeURIComponent(item.local_file)
      : item.source_url || '#';

    const date = new Date(item.added).toLocaleDateString('en-US', {
      month: 'short', day: 'numeric'
    });

    const tags = (item.tags || []).map(t => '<span class="tag">' + t + '</span>').join('');

    return '<div style="display:flex;align-items:center;gap:0;">'
      + '<a class="item" style="flex:1;" href="' + href + '" target="_blank">'
      + '<div class="icon ' + iconClass + '">' + icon + '</div>'
      + '<div class="details">'
      + '<div class="title">' + (item.title || 'Untitled') + '</div>'
      + '<div class="meta">' + date + ' &middot; ' + item.type + ' ' + tags + '</div>'
      + '</div>'
      + '</a>'
      + '<button class="done-btn" onclick="markDone(\'' + item.id + '\')" title="Mark as read">&#10003;</button>'
      + '</div>';
  }).join('');
}

async function markDone(id) {
  await fetch('/api/done?id=' + encodeURIComponent(id), { method: 'POST' });
  items = items.filter(i => i.id !== id);
  render();
}

document.querySelectorAll('.filter-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    filter = btn.dataset.filter;
    render();
  });
});

load();
// Auto-refresh every 30 seconds
setInterval(load, 30000);
</script>
</body>
</html>
"""


class DashboardHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)

        if parsed.path == "/" or parsed.path == "":
            self._respond_html(DASHBOARD_HTML)

        elif parsed.path == "/api/items":
            sync_folder()  # pick up any new PDFs
            items = get_items(include_consumed=False)
            self._respond_json(items)

        elif parsed.path.startswith("/files/"):
            self._serve_file(parsed.path[7:])  # strip "/files/"

        else:
            self._respond(404, "Not found")

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/done":
            params = parse_qs(parsed.query)
            item_id = params.get("id", [None])[0]
            if item_id:
                mark_consumed(item_id)
                self._respond_json({"status": "ok"})
            else:
                self._respond(400, "Missing id")
        else:
            self._respond(404, "Not found")

    def _serve_file(self, filename: str):
        """Serve a file from the reading folder."""
        from urllib.parse import unquote
        filename = unquote(filename)
        reading_dir = get_reading_dir()
        file_path = reading_dir / filename

        # Security: don't allow path traversal
        if ".." in filename or not file_path.resolve().is_relative_to(reading_dir.resolve()):
            self._respond(403, "Forbidden")
            return

        if not file_path.exists():
            self._respond(404, "File not found")
            return

        mime_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
        data = file_path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", mime_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Content-Disposition", f'inline; filename="{filename}"')
        self.end_headers()
        self.wfile.write(data)

    def _respond_html(self, html: str):
        data = html.encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _respond_json(self, obj):
        data = json.dumps(obj, default=str).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _respond(self, code: int, msg: str):
        data = msg.encode()
        self.send_response(code)
        self.send_header("Content-Type", "text/plain")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, format, *args):
        pass  # quiet


def run_dashboard(port: int = 8247):
    server = HTTPServer(("0.0.0.0", port), DashboardHandler)
    print(f"ReadLater dashboard running at:")
    print(f"  This computer:  http://localhost:{port}")
    print(f"  Other devices:  http://<your-computer-ip>:{port}")
    print(f"\nOpen this URL on your iPhone, iPad, or any browser.")
    print("Press Ctrl+C to stop.\n")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nDashboard stopped.")
        server.server_close()
