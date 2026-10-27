"""The enrichment service of S5's missing-key injection (docs/plans/
redesign/wp9-semantic-suite.md, change 8): a local HTTP server that
answers the enrichment table only to a request carrying the key, and logs
every request with its status, so the record shows the authorised fetch
of the resumed attempt. The table is deterministic: one row per customer
id with a segment and a risk score derived from the id.

    python3 enrichment_service.py --port 8765 --key <value> --log requests.log
"""

import argparse
import hashlib
import json
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Optional, Sequence
from urllib.parse import parse_qs, urlparse

SEGMENTS = ("new", "steady", "lapsing", "champion")
ROWS = 3000  # the fixture's hold-out and training ids together are served by range


def row(customer_id: str) -> dict:
    digest = hashlib.sha256(customer_id.encode("utf-8")).digest()
    return {"id": customer_id, "segment": SEGMENTS[digest[0] % len(SEGMENTS)], "risk_score": round(digest[1] / 255, 3)}


def table_csv(ids: Sequence[str]) -> str:
    lines = ["id,segment,risk_score"]
    for customer_id in ids:
        entry = row(customer_id)
        lines.append(f"{entry['id']},{entry['segment']},{entry['risk_score']}")
    return "\n".join(lines) + "\n"


class Handler(BaseHTTPRequestHandler):
    key = ""
    log_path: Optional[Path] = None

    def _log(self, status: int, note: str) -> None:
        if self.log_path:
            with open(self.log_path, "a", encoding="utf-8") as log:
                log.write(json.dumps({"path": self.path, "status": status, "authorized": status == 200, "note": note}) + "\n")

    def _send(self, status: int, body: str, content_type: str = "application/json") -> None:
        data = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self) -> None:  # noqa: N802 (the stdlib's name)
        authorization = self.headers.get("Authorization", "")
        if authorization != f"Bearer {self.key}":
            self._log(401, "no or wrong bearer")
            self._send(401, json.dumps({"error": "a bearer token is required: Authorization: Bearer <DATA_API_KEY>"}))
            return
        url = urlparse(self.path)
        if url.path == "/table":
            ids = [f"C{number:06d}" for number in range(1, ROWS + 1)]
            self._log(200, "the table")
            self._send(200, table_csv(ids), "text/csv")
        elif url.path == "/enrich":
            customer_id = parse_qs(url.query).get("customer_id", [""])[0]
            self._log(200, f"one row {customer_id}")
            self._send(200, json.dumps(row(customer_id)))
        else:
            self._log(404, "unknown path")
            self._send(404, json.dumps({"error": "the paths are /table and /enrich?customer_id=<id>"}))

    def log_message(self, format: str, *args) -> None:  # noqa: A002 (the stdlib's name)
        return


def serve(port: int, key: str, log_path: Optional[Path]) -> HTTPServer:
    Handler.key = key
    Handler.log_path = log_path
    return HTTPServer(("127.0.0.1", port), Handler)


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--key", required=True, help="the value DATA_API_KEY must carry (a placeholder the round makes up)")
    parser.add_argument("--log", default=None, help="every request appended as one JSON line")
    args = parser.parse_args(argv)
    server = serve(args.port, args.key, Path(args.log) if args.log else None)
    print(f"enrichment service on 127.0.0.1:{args.port}", flush=True)
    server.serve_forever()
    return 0


if __name__ == "__main__":
    sys.exit(main())
