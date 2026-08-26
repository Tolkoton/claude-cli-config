"""Mount get_repo_stars on a real HTTP server: GET /repos/<owner>/<name>/stars

Run:  python3 serve.py 8000
Then: curl -s localhost:8000/repos/astral-sh/ruff/stars
"""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer

from stars import NO_ANSWER, Fetched, get_repo_stars


class UrllibClient:
    """The real client. Any transport failure becomes NO_ANSWER — the handler
    decides what that means, this only reports what happened."""

    def __init__(self, timeout: float = 5.0) -> None:
        self.timeout = timeout

    def get(self, url: str) -> Fetched:
        request = urllib.request.Request(url, headers={"User-Agent": "live-build"})
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                return Fetched(response.status, json.load(response))
        except urllib.error.HTTPError as exc:
            return Fetched(exc.code, None)
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
            return Fetched(NO_ANSWER, None)


class Handler(BaseHTTPRequestHandler):
    client = UrllibClient()

    def do_GET(self) -> None:
        parts = self.path.strip("/").split("/")
        if len(parts) != 4 or parts[0] != "repos" or parts[3] != "stars":
            self._reply(404, {"error": "no such route"})
            return
        self._reply(*get_repo_stars(parts[1], parts[2], self.client))

    def _reply(self, status: int, body: dict) -> None:
        payload = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    print(f"listening on http://localhost:{port}")
    HTTPServer(("", port), Handler).serve_forever()
