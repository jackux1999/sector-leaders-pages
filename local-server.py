#!/usr/bin/env python3
import json
import subprocess
import sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


ROOT = Path(__file__).resolve().parent
HOST = "127.0.0.1"
PORT = 8765


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def do_POST(self):
        if self.path.split("?", 1)[0] != "/refresh":
            self.send_error(404)
            return

        try:
            result = subprocess.run(
                [sys.executable, str(ROOT / "generate-sector-data.py")],
                cwd=str(ROOT),
                capture_output=True,
                text=True,
                timeout=90,
            )
            ok = result.returncode == 0
            payload = {
                "ok": ok,
                "stdout": result.stdout[-4000:],
                "stderr": result.stderr[-4000:],
            }
            self.send_response(200 if ok else 500)
        except Exception as exc:
            payload = {"ok": False, "error": str(exc)}
            self.send_response(500)

        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main():
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"Serving {ROOT}")
    print(f"Open http://{HOST}:{PORT}/index.html")
    print("Press Ctrl+C to stop.")
    server.serve_forever()


if __name__ == "__main__":
    main()
