"""Opt-in local OpenSSH smoke for a verified image through the real encrypted channel."""

from __future__ import annotations

import base64
import hashlib
import json
import os
import shutil
import socket
import subprocess
import threading
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

from auditmanager.analysis.public import ModelRequest
from auditmanager.executors.model import RevisionRecord, RevisionSettings
from auditmanager.executors.ssh_adapter import SshCommandAdapter
from auditmanager.executors.ssh_probe import probe_ssh_command, probe_ssh_tunnel
from auditmanager.executors.ssh_transport import SshEndpoint, scan_host_key
from auditmanager.executors.ssh_tunnel_adapter import SshTunnelAdapter
from auditmanager.storage.public import derive_blob_id

pytestmark = pytest.mark.skipif(
    os.environ.get("EXEC_LOCAL_SSHD") != "1" or os.geteuid() != 0 or shutil.which("sshd") is None,
    reason="set EXEC_LOCAL_SSHD=1 on a root host with OpenSSH server",
)


def test_png_reaches_a_real_ssh_command_and_tunnel(tmp_path: Path) -> None:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    subprocess.run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(tmp_path / "host")],
                   check=True)
    subprocess.run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(tmp_path / "client")],
                   check=True)
    (tmp_path / "authorized_keys").write_text((tmp_path / "client.pub").read_text())
    command = tmp_path / "forced.py"
    command.write_text(
        "#!/usr/bin/python3\n"
        "import base64, json, sys\n"
        "task = json.load(sys.stdin)\n"
        "if 'image' in task:\n"
        "    assert base64.b64decode(task['image']['data']) == b'\\x89PNG\\r\\n\\x1a\\ncrop'\n"
        "print(json.dumps({'model': task['model'], 'output_text': 'seen' if 'image' in task else 'probe', "
        "'stop_reason': 'end_turn', 'input_tokens': 3, 'output_tokens': 1}))\n"
    )
    command.chmod(0o700)
    config = tmp_path / "sshd_config"
    config.write_text(
        f"Port {port}\nListenAddress 127.0.0.1\nHostKey {tmp_path / 'host'}\n"
        f"PidFile {tmp_path / 'pid'}\nAuthorizedKeysFile {tmp_path / 'authorized_keys'}\n"
        f"ForceCommand {command}\nPermitRootLogin yes\nPubkeyAuthentication yes\n"
        "PasswordAuthentication no\nKbdInteractiveAuthentication no\nUsePAM no\n"
        "StrictModes no\nLogLevel ERROR\n"
    )
    server = subprocess.Popen([str(Path(shutil.which("sshd")).resolve()), "-D", "-f",
                               str(config), "-E", str(tmp_path / "sshd.log")])
    try:
        for _ in range(100):
            if server.poll() is not None:
                log = tmp_path / "sshd.log"
                pytest.fail(log.read_text() if log.exists() else "sshd exited without a log")
            try:
                with socket.create_connection(("127.0.0.1", port), timeout=0.1):
                    break
            except OSError:
                time.sleep(0.05)
        else:
            pytest.fail("local sshd did not start")
        host_key = scan_host_key(SshEndpoint("127.0.0.1", port, "root"))
        settings = RevisionSettings(
            pin_id="claude-opus-5", gateway_model="claude-opus-5", billing="not_metered",
            allow_client_documents=True, timeout_seconds=30, ssh_host="localhost.test",
            ssh_port=port, ssh_user="root", host_key=host_key, ssh_profile="custom_command",
        )
        revision = RevisionRecord("excr_1", "exc_1", 1, datetime.now(timezone.utc), "usr_1", settings)
        png = b"\x89PNG\r\n\x1a\ncrop"
        digest = hashlib.sha256(png).hexdigest()
        request = ModelRequest("claude-opus-5", {
            "system": "system", "messages": [{"role": "user", "content": "describe"}],
            "images": [{"blob_id": str(derive_blob_id(sha256=digest, size=len(png))),
                        "portal_block_id": "blk_" + "a" * 32, "sha256": digest,
                        "size_bytes": len(png), "media_type": "image/png"}],
        }, image_bytes=png)

        class LocalPolicy:
            def check(self, host, remote_port, *, transport):
                assert (host, remote_port) == ("localhost.test", port)
                assert transport in ("ssh_command", "ssh_tunnel")
                return ("127.0.0.1",)

        response = SshCommandAdapter(revision, (tmp_path / "client").read_text(),
                                     LocalPolicy(), None).complete(request)
        assert response.output_text == "seen" and response.model == "claude-opus-5"
        checked = probe_ssh_command(settings, (tmp_path / "client").read_text(),
                                    policy=LocalPolicy())
        assert checked.outcome == "ok" and checked.reported_model == "claude-opus-5"

        seen = []

        class ModelHandler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                return

            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                seen.append((self.path, self.headers["Authorization"], body))
                raw = json.dumps({
                    "model": "claude-opus-5",
                    "choices": [{"message": {"role": "assistant", "content": "seen"},
                                 "finish_reason": "stop"}],
                    "usage": {"prompt_tokens": 3, "completion_tokens": 1},
                }).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)

        model_server = ThreadingHTTPServer(("127.0.0.1", 0), ModelHandler)
        model_thread = threading.Thread(target=model_server.serve_forever, daemon=True)
        model_thread.start()
        try:
            tunnel_settings = RevisionSettings(
                pin_id="claude-opus-5", gateway_model="claude-opus-5", billing="not_metered",
                allow_client_documents=True, timeout_seconds=30, api_flavour="openai_chat",
                base_url=f"http://127.0.0.1:{model_server.server_port}/api/v1",
                transport="ssh_tunnel", ssh_host="localhost.test", ssh_port=port,
                ssh_user="root", host_key=host_key,
            )
            tunnel_revision = RevisionRecord("excr_2", "exc_2", 1, datetime.now(timezone.utc),
                                             "usr_1", tunnel_settings)
            tunnel = SshTunnelAdapter(tunnel_revision, "http-key", (tmp_path / "client").read_text(),
                                      LocalPolicy(), None)
            forwarded = tunnel.complete(request)
            assert forwarded.output_text == "seen" and forwarded.model == "claude-opus-5"
            assert len(seen) == 1, seen
            assert seen[0][0] == "/api/v1/chat/completions"
            assert seen[0][1] == "Bearer http-key"
            content = seen[0][2]["messages"][-1]["content"]
            assert isinstance(content, list), seen[0][2]
            encoded = content[-1]["image_url"]["url"].split(",", 1)[1]
            assert base64.b64decode(encoded) == png
            tunnel_probe = probe_ssh_tunnel(tunnel_settings, "http-key",
                                            (tmp_path / "client").read_text(), policy=LocalPolicy())
            assert tunnel_probe.outcome == "ok" and tunnel_probe.reported_model == "claude-opus-5"
        finally:
            model_server.shutdown()
            model_server.server_close()
            model_thread.join(timeout=5)
    finally:
        server.terminate()
        server.wait(timeout=5)
