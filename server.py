"""Cayman Mortgage Calculator: local app.

    .venv/bin/python server.py            # opens http://127.0.0.1:8787
    .venv/bin/python server.py --port 9000 --no-open

Serves the calculator with the latest listings built in, and scrapes the agency
websites in the background when the data is missing or more than 12 hours old.
The "Refresh listings" button on the page triggers a new scrape.
"""
from __future__ import annotations

import argparse
import json
import threading
import webbrowser
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import home
import page
from scraper import run as scrape_run

ROOT = Path(__file__).resolve().parent
STATIC = ROOT / "web" / "static"
MAX_AGE_HOURS = 4      # the published site refreshes on the same schedule

state = {"running": False, "last_error": "", "log": []}
lock = threading.Lock()


def current_data() -> dict:
    d = scrape_run.load() or {"generated_at": None, "sources": [], "listings": []}
    d["local"] = True
    return d


def age_hours(d: dict | None) -> float:
    if not d or not d.get("generated_at"):
        return 1e9
    t = datetime.fromisoformat(d["generated_at"])
    return (datetime.now(timezone.utc) - t).total_seconds() / 3600


def start_scrape() -> bool:
    with lock:
        if state["running"]:
            return False
        state.update(running=True, last_error="", log=[])

    def work():
        try:
            data = scrape_run.scrape(log=lambda m: (print(m), state["log"].append(m)))
            if data["listings"]:
                scrape_run.save(data)
            else:
                state["last_error"] = "No listings came back from any source."
        except Exception as e:  # keep the server alive
            state["last_error"] = f"{type(e).__name__}: {e}"
        finally:
            state["running"] = False
    threading.Thread(target=work, daemon=True).start()
    return True


class Handler(BaseHTTPRequestHandler):
    def _send(self, code: int, body: bytes, ctype: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, obj, code: int = 200) -> None:
        self._send(code, json.dumps(obj).encode(), "application/json")

    def do_GET(self):
        path = self.path.split("?")[0]
        if path in ("/", "/index.html"):
            body = home.render(current_data(), page.HOME_FRAGMENT.read_text())
            self._send(200, page.render_home(body).encode(), "text/html; charset=utf-8")
        elif path in ("/calculator", "/calculator/", "/calculator/index.html"):
            self._send(200, page.render_app(current_data()).encode(), "text/html; charset=utf-8")
        elif path in ("/rent-vs-buy", "/rent-vs-buy/", "/rent-vs-buy/index.html"):
            self._send(200, page.render_rent().encode(), "text/html; charset=utf-8")
        elif path in ("/equity", "/equity/", "/equity/index.html"):
            self._send(200, page.render_equity().encode(), "text/html; charset=utf-8")
        elif path == "/assets/app.css":
            self._send(200, page.CSS.read_bytes(), "text/css")
        elif path == "/assets/core.js":
            self._send(200, page.CORE.read_bytes(), "application/javascript")
        elif (STATIC / path.lstrip("/")).is_file() and ".." not in path:
            f = STATIC / path.lstrip("/")
            types = {".svg": "image/svg+xml", ".png": "image/png", ".ico": "image/x-icon",
                     ".webmanifest": "application/manifest+json", ".json": "application/json"}
            self._send(200, f.read_bytes(), types.get(f.suffix, "application/octet-stream"))
        elif path == "/api/listings":
            self._json(current_data())
        elif path == "/api/status":
            d = scrape_run.load()
            self._json({"running": state["running"], "error": state["last_error"], "log": state["log"][-10:],
                        "generated_at": d and d.get("generated_at")})
        else:
            self._send(404, b"Not found", "text/plain")

    def do_POST(self):
        if self.path.split("?")[0] == "/api/refresh":
            self._json({"started": start_scrape(), "running": True})
        else:
            self._send(404, b"Not found", "text/plain")

    def log_message(self, fmt, *args):  # quieter console
        if "/api/status" not in (args[0] if args else ""):
            super().log_message(fmt, *args)


def main():
    ap = argparse.ArgumentParser(description="Run the Cayman Mortgage Calculator locally.")
    ap.add_argument("--port", type=int, default=8787)
    ap.add_argument("--no-open", action="store_true", help="don't open a browser tab")
    a = ap.parse_args()
    if age_hours(scrape_run.load()) > MAX_AGE_HOURS:
        print("Listings are missing or stale; scraping in the background…")
        start_scrape()
    srv = ThreadingHTTPServer(("127.0.0.1", a.port), Handler)
    url = f"http://127.0.0.1:{a.port}/"
    print(f"Cayman Mortgage Calculator running at {url}  (Ctrl+C to stop)")
    if not a.no_open:
        webbrowser.open(url)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()
