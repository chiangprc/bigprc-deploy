#!/usr/bin/env python3
"""
BigPRC Local Preview Server — Nginx URL-rewrite emulation for local dev.
Run from project root:  python local_server.py [port]
"""
import http.server
import os
import sys
import re
import urllib.parse
import mimetypes

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
SITE_DIR = os.path.join(PROJECT_ROOT, "var", "www", "site", "web")
CUSTOM_PAGES = os.path.join(PROJECT_ROOT, "root", "custom-pages")
MAIN_HOMEPAGE = os.path.join(CUSTOM_PAGES, "index.html")
if not os.path.isfile(MAIN_HOMEPAGE):
    MAIN_HOMEPAGE = os.path.join(SITE_DIR, "index.html")

_GO_RE = re.compile(r'^/go/([a-zA-Z0-9_]+)$')
_SITE_RE = re.compile(r'^/site/(.*)$')
_JUMP_RE = re.compile(r'^/jump/')


class Handler(http.server.SimpleHTTPRequestHandler):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=PROJECT_ROOT, **kwargs)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        # ---- /go/<slug>  →  var/www/site/web/static/page/<slug>.html ----
        m = _GO_RE.match(path)
        if m:
            filepath = os.path.join(SITE_DIR, "static", "page", f"{m.group(1)}.html")
            if os.path.isfile(filepath):
                return self._serve_file(filepath, "text/html; charset=utf-8")
            self._send_404("Resource page not found")
            return

        # ---- /  →  main homepage ----
        if path == "/":
            return self._serve_file(MAIN_HOMEPAGE, "text/html; charset=utf-8")

        # ---- /list.html  →  resource list ----
        if path == "/list.html":
            filepath = os.path.join(SITE_DIR, "list.html")
            if os.path.isfile(filepath):
                return self._serve_file(filepath, "text/html; charset=utf-8")
            self._send_404("Resource list not generated yet")
            return

        # ---- /site/<subpath>  →  root/custom-pages/ first, then var/www/site/web/ ----
        m = _SITE_RE.match(path)
        if m:
            subpath = m.group(1)
            # 优先从 Git 管理的手工页面目录读取
            custom_filepath = os.path.join(CUSTOM_PAGES, subpath)
            if os.path.isfile(custom_filepath):
                ctype, _ = mimetypes.guess_type(custom_filepath)
                return self._serve_file(custom_filepath, ctype or "application/octet-stream")
            # 回退到自动生成的站点目录
            filepath = os.path.join(SITE_DIR, subpath)
            if os.path.isfile(filepath):
                ctype, _ = mimetypes.guess_type(filepath)
                return self._serve_file(filepath, ctype or "application/octet-stream")
            self._send_404("Site file not found")
            return

        # ---- /tools/*  →  root/custom-pages/tools/ ----
        if path.startswith("/tools/"):
            subpath = path[len("/tools/"):]
            filepath = os.path.join(CUSTOM_PAGES, "tools", subpath)
            if os.path.isfile(filepath):
                ctype, _ = mimetypes.guess_type(filepath)
                return self._serve_file(filepath, ctype or "application/octet-stream")
            self._send_404("Tool page not found")
            return

        # ---- /sitemap.xml  →  var/www/site/web/sitemap.xml ----
        if path == "/sitemap.xml":
            filepath = os.path.join(SITE_DIR, "sitemap.xml")
            if os.path.isfile(filepath):
                return self._serve_file(filepath, "application/xml; charset=utf-8")
            self._send_404("Sitemap not generated yet")
            return

        # ---- /jump/*  →  disabled in local preview ----
        if _JUMP_RE.match(path):
            return self._serve_html(
                "<html><body style='font-family:sans-serif;padding:40px;text-align:center'>"
                "<h3>External redirect disabled in local preview.</h3>"
                "<p>On the live site this would redirect to the cloud drive.</p>"
                "<p><a href='/'>Back to homepage</a></p>"
                "</body></html>"
            )

        # ---- favicon / static fallback → serve from project root ----
        super().do_GET()

    # ------------------------------------------------------------------
    def _serve_file(self, filepath, content_type):
        try:
            with open(filepath, "rb") as f:
                data = f.read()
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        except OSError:
            self._send_404("File read error")

    def _serve_html(self, body):
        data = f"<!DOCTYPE html>{body}".encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _send_404(self, msg):
        body = (f"<!DOCTYPE html><html><body style='font-family:sans-serif;padding:40px;text-align:center'>"
                f"<h2>404</h2><p>{msg}</p><p><a href='/'>Back to homepage</a></p></body></html>")
        data = body.encode("utf-8")
        self.send_response(404)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, format, *args):
        print(f"  {args[0]}")


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8765
    server = http.server.HTTPServer(("127.0.0.1", port), Handler)
    print(f"BigPRC Local Preview")
    print(f"  Root : {PROJECT_ROOT}")
    print(f"  URL  : http://127.0.0.1:{port}")
    print(f"  Stop : Ctrl+C")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
