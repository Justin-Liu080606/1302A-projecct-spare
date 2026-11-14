"""Tiny standard-library local web UI for CS1302 Study Planner.

Only serves bundled static files, and only binds to loopback by default.
"""

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import threading
import webbrowser

from .planner import InputError, generate_plan

STATIC = Path(__file__).with_name("static")
FILES = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/static/style.css": ("style.css", "text/css; charset=utf-8"),
    "/static/app.js": ("app.js", "text/javascript; charset=utf-8"),
}


class AppHandler(BaseHTTPRequestHandler):
    def send_content(self, status, body, content_type):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy", "default-src 'self'; style-src 'self'; script-src 'self'; base-uri 'none'; object-src 'none'")
        self.end_headers()
        self.wfile.write(body)

    def send_json(self, status, data):
        self.send_content(status, json.dumps(data, ensure_ascii=False).encode("utf-8"),
                          "application/json; charset=utf-8")

    def do_GET(self):
        entry = FILES.get(self.path)
        if entry is None:
            self.send_json(404, {"error": "Page not found."})
            return
        filename, content_type = entry
        try:
            content = (STATIC / filename).read_bytes()
        except OSError:
            self.send_json(500, {"error": "Required web assets are missing. Please check the installation."})
            return
        self.send_content(200, content, content_type)

    def do_POST(self):
        if self.path != "/api/generate":
            self.send_json(404, {"error": "Unknown endpoint."})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= 65536:
                self.send_json(413, {"error": "Request body is empty or too large."})
                return
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            plan = generate_plan(payload)
        except (ValueError, UnicodeDecodeError, InputError) as exc:
            message = str(exc) if isinstance(exc, InputError) else "Invalid input. Please check subjects, dates, and time windows."
            self.send_json(400, {"error": message})
            return
        self.send_json(200, plan)


def run_web(port=8765, open_browser=True):
    """Start a local-only app. Stop with Ctrl+C."""
    try:
        server = ThreadingHTTPServer(("127.0.0.1", port), AppHandler)
    except OSError as exc:
        raise SystemExit(f"Could not start: port {port} is already in use. Try --port 8766.") from exc
    actual_port = server.server_address[1]
    url = f"http://127.0.0.1:{actual_port}/"
    print("\nSmart Study Planner is running")
    print("Open in your browser:", url)
    print("Press Ctrl+C to stop the server.\n")
    if open_browser:
        threading.Timer(0.5, webbrowser.open, args=(url,)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
    finally:
        server.server_close()
