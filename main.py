#!/usr/bin/env python3
"""
Lego Inventory – Proxy Server
Forwards requests to Notion API and Brickset API.
Deploy to Render.com as a free web service.
"""

from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.request, urllib.error, os, sys

PORT = int(os.environ.get("PORT", 3456))
NOTION_API   = "https://api.notion.com/v1"
BRICKSET_API = "https://brickset.com/api/v3.asmx"

class ProxyHandler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        print(f"  [{args[1]}] {args[0]}", flush=True)

    def send_cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PATCH, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization, Notion-Version")

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_cors_headers()
        self.end_headers()

    def do_GET(self):    self.proxy("GET")
    def do_POST(self):   self.proxy("POST")
    def do_PATCH(self):  self.proxy("PATCH")
    def do_DELETE(self): self.proxy("DELETE")

    def proxy(self, method):
        # Health check
        if self.path == "/health":
            self.send_response(200)
            self.send_cors_headers()
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"status":"ok"}')
            return

        # Route: /brickset/... → Brickset API
        if self.path.startswith("/brickset/"):
            brickset_path = self.path[len("/brickset"):]  # e.g. /getSets?params=...
            url = f"{BRICKSET_API}{brickset_path}"
            print(f"  → {method} {url}", flush=True)
            self.forward(method, url, notion=False)
            return

        # Route: everything else → Notion API
        url = f"{NOTION_API}{self.path}"
        print(f"  → {method} {url}", flush=True)
        self.forward(method, url, notion=True)

    def forward(self, method, url, notion=True):
        length = int(self.headers.get("Content-Length", 0))
        body   = self.rfile.read(length) if length else None

        req = urllib.request.Request(url, data=body, method=method)
        if notion:
            req.add_header("Authorization",  self.headers.get("Authorization", ""))
            req.add_header("Content-Type",   "application/json")
            req.add_header("Notion-Version", self.headers.get("Notion-Version", "2022-06-28"))
        else:
            req.add_header("Content-Type", "application/x-www-form-urlencoded")

        try:
            with urllib.request.urlopen(req) as resp:
                data = resp.read()
                self.send_response(resp.status)
                self.send_cors_headers()
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(data)
        except urllib.error.HTTPError as e:
            data = e.read()
            print(f"  ✗ Error {e.code}: {data.decode()[:200]}", flush=True)
            self.send_response(e.code)
            self.send_cors_headers()
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(data)

if __name__ == "__main__":
    print(f"\n🧱  Lego Inventory Proxy running on port {PORT}", flush=True)
    print(f"   Notion  → {NOTION_API}", flush=True)
    print(f"   Brickset → {BRICKSET_API}", flush=True)
    print(f"   Press Ctrl+C to stop.\n", flush=True)
    HTTPServer(("0.0.0.0", PORT), ProxyHandler).serve_forever()
