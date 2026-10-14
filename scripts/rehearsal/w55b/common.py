"""Shared pieces of the W55B-REHEARSAL-01 tools: where outputs go, what a figure carries, the guards.

Every tool in this directory writes only under ``.local/rehearsal-w55b/`` (git-ignored) and talks
only to the lane's own loopback ports. A figure is never written without its context: the
worktree's ``HEAD`` and whether the tree is clean, ``/proc/loadavg``, ``MemAvailable`` and the
free disk at the moment it was taken (owner ruling ``R-122``).

Guards refuse with ``SystemExit`` and never with ``assert``: ``python -O`` strips an assert, and a
stripped guard would let a tool aim at another session's stack.
"""

from __future__ import annotations

import http.client
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / ".local" / "rehearsal-w55b"
FIGURES = OUT / "figures"

#: The lane's private ports (the brief's allocation). Nothing else is ever addressed.
POSTGRES_PORT = 57480
S3_PORTS = (61080, 61081)
API_PORT = 57580
HEALTH_PORT = 57581
WEB_PORT = 31680
INSTANCE = "auditmanager-w55b-rehearsal"
LANE_PORTS = frozenset({POSTGRES_PORT, *S3_PORTS, API_PORT, HEALTH_PORT, WEB_PORT})

GiB = 1024 ** 3
MiB = 1024 ** 2
#: The brief's floor before any heavy step.
MIN_AVAILABLE_BYTES = 3 * GiB
MIN_FREE_DISK_BYTES = 5 * GiB
#: How long a heavy step waits for memory before the lane stops and says so.
CAPACITY_WAIT_SECONDS = 20 * 60


def ensure_out() -> Path:
    """The output directory, created, after proving git ignores it."""
    OUT.mkdir(parents=True, exist_ok=True)
    FIGURES.mkdir(parents=True, exist_ok=True)
    probe = subprocess.run(
        ["git", "-C", str(ROOT), "check-ignore", "-q", str(OUT / "probe")], check=False
    )
    if probe.returncode != 0:
        raise SystemExit(f"refusing to write: {OUT} is not ignored by git")
    return OUT


def meminfo_kib(key: str) -> int:
    for line in Path("/proc/meminfo").read_text().splitlines():
        if line.startswith(key + ":"):
            return int(line.split()[1])
    raise SystemExit(f"/proc/meminfo has no {key}")


def tree() -> dict[str, Any]:
    head = subprocess.run(
        ["git", "-C", str(ROOT), "rev-parse", "HEAD"], capture_output=True, text=True, check=True
    ).stdout.strip()
    status = subprocess.run(
        ["git", "-C", str(ROOT), "status", "--porcelain", "-uall"],
        capture_output=True, text=True, check=True,
    ).stdout
    return {"head": head, "clean": status.strip() == ""}


def context() -> dict[str, Any]:
    """What every figure records beside itself."""
    usage = shutil.disk_usage("/")
    return {
        "at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "tree": tree(),
        "loadavg": Path("/proc/loadavg").read_text().split()[:3],
        "mem_available_kib": meminfo_kib("MemAvailable"),
        "disk_free_bytes": usage.free,
    }


def gate_running() -> list[str]:
    """Command lines of any ``make`` process that is running a gate on this host."""
    found = []
    for entry in Path("/proc").iterdir():
        if not entry.name.isdigit():
            continue
        try:
            if (entry / "comm").read_text().strip() != "make":
                continue
            cmdline = (entry / "cmdline").read_bytes().replace(b"\0", b" ").decode(errors="replace")
        except OSError:
            continue
        if "gate" in cmdline.split():
            found.append(f"{entry.name}: {cmdline.strip()}")
    return found


def capacity_gate(step: str, *, wait_seconds: int = CAPACITY_WAIT_SECONDS) -> dict[str, Any]:
    """Wait until the host can take a heavy step; stop the lane after ``wait_seconds``.

    Returns the context measured when the step was allowed to start.
    """
    started = time.monotonic()
    while True:
        snapshot = context()
        short = []
        if snapshot["mem_available_kib"] * 1024 < MIN_AVAILABLE_BYTES:
            short.append(f"MemAvailable {snapshot['mem_available_kib']} KiB < 3 GiB")
        if snapshot["disk_free_bytes"] < MIN_FREE_DISK_BYTES:
            short.append(f"disk free {snapshot['disk_free_bytes']} B < 5 GiB")
        gates = gate_running()
        if gates:
            short.append(f"make gate running: {gates}")
        if not short:
            print(f"[capacity] {step}: ok, load {snapshot['loadavg']}, "
                  f"MemAvailable {snapshot['mem_available_kib'] // 1024} MiB, "
                  f"disk free {snapshot['disk_free_bytes'] // MiB} MiB", file=sys.stderr)
            return snapshot
        if time.monotonic() - started > wait_seconds:
            raise SystemExit(f"[capacity] {step}: still short after {wait_seconds} s: {short}")
        print(f"[capacity] {step}: waiting: {short}", file=sys.stderr)
        time.sleep(30)


def write_figures(name: str, payload: dict[str, Any]) -> Path:
    """One JSON file per phase, with the context taken now."""
    ensure_out()
    document = {"phase": name, "context": context(), **payload}
    path = FIGURES / f"{name}.json"
    path.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"[figures] {path.relative_to(ROOT)}", file=sys.stderr)
    return path


# ------------------------------------------------------------------ the API process


def vm_kib(pid: int, key: str) -> int:
    for line in Path(f"/proc/{pid}/status").read_text().splitlines():
        if line.startswith(key + ":"):
            return int(line.split()[1])
    raise SystemExit(f"/proc/{pid}/status has no {key}")


def reset_peak(pid: int) -> int:
    """Reset the process's high-water mark to its current resident set; return VmHWM after."""
    Path(f"/proc/{pid}/clear_refs").write_text("5")
    return vm_kib(pid, "VmHWM")


def listening_pid(port: int) -> int | None:
    """The PID that holds a listening TCP socket on ``port``, read from ``ss``."""
    out = subprocess.run(
        ["ss", "-ltnpH", f"sport = :{port}"], capture_output=True, text=True, check=False
    ).stdout
    for token in out.replace(",", " ").split():
        if token.startswith("pid="):
            return int(token[4:])
    return None


def own_api_pid() -> int:
    """The API process this lane started, proved by its PID file, its cwd and its port."""
    pid_file = OUT / "api.pid"
    if not pid_file.is_file():
        raise SystemExit("no API PID file: start the API with stack.py api-start")
    pid = int(pid_file.read_text().strip())
    try:
        cwd = Path(f"/proc/{pid}/cwd").resolve()
        cmdline = Path(f"/proc/{pid}/cmdline").read_bytes().replace(b"\0", b" ").decode()
    except OSError:
        raise SystemExit(f"the API process {pid} is gone") from None
    if cwd != ROOT or "infra/deploy/serve.py" not in cmdline:
        raise SystemExit(f"PID {pid} is not this worktree's serve.py (cwd {cwd})")
    if listening_pid(API_PORT) != pid:
        raise SystemExit(f"PID {pid} does not hold the lane's API port {API_PORT}")
    return pid


# ------------------------------------------------------------------ HTTP


def require_lane_origin(origin: str) -> tuple[str, int]:
    """Refuse any origin that is not loopback on one of this lane's ports."""
    parts = urlsplit(origin)
    if parts.scheme != "http" or parts.hostname not in ("127.0.0.1", "localhost"):
        raise SystemExit(f"refusing origin {origin!r}: only loopback http is this lane's")
    if parts.port not in LANE_PORTS:
        raise SystemExit(f"refusing origin {origin!r}: port {parts.port} is not this lane's")
    return parts.hostname, parts.port


class Api:
    """A bearer-token client of the lane's API. The token comes from the environment only."""

    def __init__(self, origin: str, token: str | None = None) -> None:
        self.host, self.port = require_lane_origin(origin)
        self.token = token

    def call(self, method: str, path: str, *, body: bytes | None = None,
             headers: dict[str, str] | None = None, timeout: float = 900) -> tuple[int, dict, bytes]:
        conn = http.client.HTTPConnection(self.host, self.port, timeout=timeout)
        sent = dict(headers or {})
        if self.token:
            sent["Authorization"] = f"Bearer {self.token}"
        conn.request(method, path, body=body, headers=sent)
        response = conn.getresponse()
        data = response.read()
        conn.close()
        return response.status, dict(response.getheaders()), data

    def json(self, method: str, path: str, payload: Any = None, *,
             headers: dict[str, str] | None = None) -> tuple[int, Any]:
        body = None if payload is None else json.dumps(payload).encode()
        sent = {"Content-Type": "application/json"} if body is not None else {}
        sent.update(headers or {})
        status, _, data = self.call(method, path, body=body, headers=sent)
        try:
            return status, json.loads(data) if data else None
        except ValueError:
            return status, {"_not_json": data[:200].decode(errors="replace")}


def token_from_env() -> str:
    token = os.environ.get("REHEARSAL_BEARER", "").strip()
    if not token:
        raise SystemExit("REHEARSAL_BEARER is not set (the account's bearer token, from the environment)")
    return token
