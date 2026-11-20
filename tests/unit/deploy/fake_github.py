"""A stand-in for the two things the norms release needs from GitHub: the REST API the publisher calls (releases, assets, uploads) and
the downloads the installer's `curl` makes. For the tests of `infra/norms/publish_bundle_release.py` and of the installer's release
path; it follows the shapes of GitHub's API for exactly the fields those two read.

Faults a test can ask for, each by name: an upload that fails, an upload that leaves a half-made asset, a download that is cut off
once, an asset that is missing, an asset whose bytes differ from what was published, an API that demands a token. Range requests are
answered (206) because the installer resumes with `curl -C -`. Every request is logged, with the token reduced to a flag.

Also `make_bundle`: a tiny bundle directory the stand's own rules accept, of incompressible files, so a few kilobytes make several
parts at a small part size.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

CONTENT_KEY = "undated+1d.0a1bafe103ff"


def make_bundle(parent: Path, *, tamper: bool = False, files: int = 3, size: int = 20_000) -> Path:
    """`<parent>/<content key>+<sha256 of SHA256SUMS>/` holding `manifest.json` and random objects, SHA256SUMS listing them."""
    contents = {"manifest.json": b'{"snapshot": "stand-in"}\n'}
    for number in range(files):
        contents[f"objects/{number:02x}/doc{number}.pdf"] = b"%PDF-1.7 " + os.urandom(size)
    listing = "".join(f"{hashlib.sha256(data).hexdigest()}  {name}\n" for name, data in sorted(contents.items()))
    digest = hashlib.sha256(listing.encode()).hexdigest()
    bundle = parent / f"{CONTENT_KEY}+{digest}"
    for name, data in contents.items():
        path = bundle / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data + (b"X" if tamper and name == "manifest.json" else b""))
    (bundle / "SHA256SUMS").write_text(listing)
    return bundle


class FakeGithub:
    def __init__(self, repo: str = "acme-co/audit-install", token: str | None = "ghp_testtokenvalue0123456789") -> None:
        self.repo = repo
        self.token = token                      # the API refuses a request that does not carry it (None: no check)
        self.releases: dict[str, dict] = {}
        self.next_id = 1000
        self.requests: list[dict] = []
        self.fail_uploads: dict[str, int] = {}           # asset name -> how many uploads of it answer 500
        self.starter_on_failure = False                  # a failed upload leaves a half-made asset behind
        self.drop_download: dict[str, int] = {}          # asset name -> bytes sent before the connection is cut, once
        self.missing: set[str] = set()                   # asset names answered 404
        self.altered: dict[str, bytes] = {}              # asset name -> bytes served instead of the real ones
        self.require_download_token = False              # the asset endpoint wants the token (a private repository)
        self.uploads_of: dict[str, int] = {}
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), self._handler())
        self.server.daemon_threads = True
        self.port = self.server.server_address[1]
        self.base = f"http://127.0.0.1:{self.port}"
        self.thread = threading.Thread(target=self.server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)
        self.thread.start()

    def close(self) -> None:
        self.server.shutdown()
        self.server.server_close()

    # ------------------------------------------------------------------------------------------------ state helpers
    def release(self, tag: str) -> dict | None:
        return self.releases.get(tag)

    def asset_bytes(self, tag: str, name: str) -> bytes:
        for asset in self.releases[tag]["assets"]:
            if asset["name"] == name:
                return asset["_content"]
        raise KeyError(name)

    def seed_release(self, tag: str) -> dict:
        self.next_id += 1
        release = {"id": self.next_id, "tag_name": tag, "name": tag, "assets": [], "draft": False, "prerelease": False}
        self.releases[tag] = release
        return release

    def seed_asset(self, tag: str, name: str, content: bytes, *, state: str = "uploaded", label: str | None = None, size: int | None = None) -> dict:
        self.next_id += 1
        asset = {"id": self.next_id, "name": name, "size": len(content) if size is None else size, "state": state,
                 "label": label, "_content": content}
        self.releases[tag]["assets"].append(asset)
        return asset

    def public(self, release: dict) -> dict:
        shown = {k: v for k, v in release.items() if k != "assets"}
        shown["upload_url"] = f"{self.base}/uploads/repos/{self.repo}/releases/{release['id']}/assets{{?name,label}}"
        shown["assets"] = [{k: v for k, v in a.items() if not k.startswith("_")} for a in release["assets"]]
        return shown

    # --------------------------------------------------------------------------------------------------- handler
    def _handler(self):
        fake = self

        class Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def log_message(self, *args):
                return

            def _note(self) -> None:
                header = self.headers.get("Authorization", "")
                fake.requests.append({"method": self.command, "path": self.path, "range": self.headers.get("Range"),
                                      "authorized": bool(fake.token) and header == f"Bearer {fake.token}",
                                      "anonymous": not header, "accept": self.headers.get("Accept")})

            def _json(self, status: int, body=None) -> None:
                payload = json.dumps(body).encode() if body is not None else b""
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

            def _api_ok(self) -> bool:
                if fake.token is not None and self.headers.get("Authorization") != f"Bearer {fake.token}":
                    self._json(401, {"message": "Bad credentials"})
                    return False
                return True

            def _bytes(self, content: bytes, *, drop_after: int | None = None) -> None:
                total = len(content)
                start, end, status = 0, total - 1, 200
                spec = self.headers.get("Range")
                if spec:
                    match = re.fullmatch(r"bytes=(\d+)-(\d*)", spec)
                    if match:
                        start = int(match.group(1))
                        end = int(match.group(2)) if match.group(2) else total - 1
                        end = min(end, total - 1)
                        status = 206
                        if start >= total:
                            self.send_response(416)
                            self.send_header("Content-Range", f"bytes */{total}")
                            self.send_header("Content-Length", "0")
                            self.end_headers()
                            return
                body = content[start:end + 1]
                self.send_response(status)
                self.send_header("Content-Type", "application/octet-stream")
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Accept-Ranges", "bytes")
                if status == 206:
                    self.send_header("Content-Range", f"bytes {start}-{end}/{total}")
                self.end_headers()
                if self.command == "HEAD":
                    return
                if drop_after is not None and drop_after < len(body):
                    self.wfile.write(body[:drop_after])
                    self.wfile.flush()
                    self.close_connection = True
                    self.connection.shutdown(2)
                    return
                self.wfile.write(body)

            def do_GET(self) -> None:  # noqa: N802
                self._note()
                path = urlparse(self.path).path
                match = re.fullmatch(rf"/repos/{re.escape(fake.repo)}/releases/tags/(.+)", path)
                if match:
                    if not self._api_ok():
                        return
                    release = fake.releases.get(match.group(1))
                    return self._json(200, fake.public(release)) if release else self._json(404, {"message": "Not Found"})
                match = re.fullmatch(rf"/repos/{re.escape(fake.repo)}/releases/assets/(\d+)", path)
                if match:
                    if fake.require_download_token and self.headers.get("Authorization") != f"Bearer {fake.token}":
                        return self._json(404, {"message": "Not Found"})
                    for release in fake.releases.values():
                        for asset in release["assets"]:
                            if asset["id"] == int(match.group(1)):
                                if asset["name"] in fake.missing:
                                    return self._json(404, {"message": "Not Found"})
                                content = fake.altered.get(asset["name"], asset["_content"])
                                return self._bytes(content, drop_after=fake.drop_download.pop(asset["name"], None))
                    return self._json(404, {"message": "Not Found"})
                match = re.fullmatch(rf"/{re.escape(fake.repo)}/releases/download/([^/]+)/(.+)", path)
                if match:
                    release = fake.releases.get(match.group(1))
                    name = match.group(2)
                    if release is None or name in fake.missing or not any(a["name"] == name for a in release["assets"]):
                        return self._json(404, {"message": "Not Found"})
                    content = fake.altered.get(name) or fake.asset_bytes(match.group(1), name)
                    return self._bytes(content, drop_after=fake.drop_download.pop(name, None))
                self._json(404, {"message": "Not Found"})

            do_HEAD = do_GET  # noqa: N815

            def do_POST(self) -> None:  # noqa: N802
                self._note()
                if not self._api_ok():
                    return
                parsed = urlparse(self.path)
                length = int(self.headers.get("Content-Length") or 0)
                if parsed.path == f"/repos/{fake.repo}/releases":
                    body = json.loads(self.rfile.read(length) or b"{}")
                    if body["tag_name"] in fake.releases:
                        return self._json(422, {"message": "Validation Failed"})
                    release = fake.seed_release(body["tag_name"])
                    release.update(name=body.get("name"), body=body.get("body"), make_latest=body.get("make_latest"))
                    return self._json(201, fake.public(release))
                match = re.fullmatch(rf"/uploads/repos/{re.escape(fake.repo)}/releases/(\d+)/assets", parsed.path)
                if match:
                    query = parse_qs(parsed.query)
                    name = query["name"][0]
                    label = query.get("label", [None])[0]
                    data = self.rfile.read(length)
                    fake.uploads_of[name] = fake.uploads_of.get(name, 0) + 1
                    release = next((r for r in fake.releases.values() if r["id"] == int(match.group(1))), None)
                    if release is None:
                        return self._json(404, {"message": "Not Found"})
                    if any(a["name"] == name for a in release["assets"]):
                        return self._json(422, {"message": "Validation Failed", "errors": [{"code": "already_exists"}]})
                    if fake.fail_uploads.get(name, 0) > 0:
                        fake.fail_uploads[name] -= 1
                        if fake.starter_on_failure:
                            fake.seed_asset(release["tag_name"], name, b"", state="starter", size=0)
                        return self._json(500, {"message": "Server Error"})
                    asset = fake.seed_asset(release["tag_name"], name, data, label=label)
                    return self._json(201, {k: v for k, v in asset.items() if not k.startswith("_")})
                self._json(404, {"message": "Not Found"})

            def do_DELETE(self) -> None:  # noqa: N802
                self._note()
                if not self._api_ok():
                    return
                match = re.fullmatch(rf"/repos/{re.escape(fake.repo)}/releases/assets/(\d+)", urlparse(self.path).path)
                if match:
                    for release in fake.releases.values():
                        before = len(release["assets"])
                        release["assets"] = [a for a in release["assets"] if a["id"] != int(match.group(1))]
                        if len(release["assets"]) != before:
                            self.send_response(204)
                            self.send_header("Content-Length", "0")
                            self.end_headers()
                            return
                self._json(404, {"message": "Not Found"})

        return Handler
