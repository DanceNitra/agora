"""
Tiny zero-dependency web server for the AI support-agent demo. Serves the chat widget and answers
questions through the same grounded agent (services/support_agent/support_agent.py).

Run:   python server.py        then open http://localhost:8800
Stop:  Ctrl-C

For a client you'd deploy this (or the answer() function) behind their site and embed widget.html.
"""
from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

from support_agent import answer

HERE = Path(__file__).resolve().parent
PORT = 8800


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass  # quiet

    def do_GET(self):
        html = (HERE / "widget.html").read_text(encoding="utf-8")
        body = html.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        if self.path != "/ask":
            self.send_response(404)
            self.end_headers()
            return
        n = int(self.headers.get("Content-Length", 0))
        try:
            q = json.loads(self.rfile.read(n) or b"{}").get("question", "")
            ans = answer(q) if q.strip() else "Please type a question."
        except Exception as e:
            ans = f"[error: {str(e)[:120]}]"
        body = json.dumps({"answer": ans}).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    print(f"AI support-agent demo running at http://localhost:{PORT}  (Ctrl-C to stop)")
    HTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
