#!/usr/bin/env python3
"""Start and stop the lane's own API and Next processes, by the PID this tool started.

    python scripts/rehearsal/w55b/stack.py api-start | api-stop | web-start | web-stop | status

The API is the repository's entry point, ``infra/deploy/serve.py``, configured from the lane's
``.env`` (parsed as data, never sourced) plus the variables the INGEST report's recipe names:
``AUDITMANAGER_PROVIDER_MODE=recorded``, the deployment secret ``AUDITMANAGER_API_TOKEN`` (taken
from the environment variable ``REHEARSAL_API_SECRET``, never written to a tracked file), the lane's
ports, the loopback bind. ``EXECUTION_ROLE`` is left unset, so the run carrier is a thread of the
serving process and the stages run in the process whose memory the driver samples.

Next is ``npx next start`` on the lane's web port with ``AUDITMANAGER_API_UPSTREAM`` pointing at
the API and the same secret; it must have been built (``npm --prefix web run build``) first.

Each process is started in a session of its own; its PID is written under
``.local/rehearsal-w55b/``. Stopping signals only that PID's process group, and only after the
PID's working directory and the port it holds prove it is this lane's. Nothing is ever matched by
name: this host runs other sessions' stacks.
"""

from __future__ import annotations

import argparse
import http.client
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import common  # noqa: E402

API_LOG = common.OUT / "api.log"
WEB_LOG = common.OUT / "web.log"
API_PID = common.OUT / "api.pid"
WEB_PID = common.OUT / "web.pid"


def dotenv() -> dict[str, str]:
    path = common.ROOT / ".env"
    if not path.is_file():
        raise SystemExit("no .env in the worktree: copy .env.example and set the lane's values")
    values: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip().removeprefix("export ").strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, _, value = line.partition("=")
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        values[name.strip()] = value
    if values.get("FOUNDATION_INSTANCE") != common.INSTANCE:
        raise SystemExit(f".env names instance {values.get('FOUNDATION_INSTANCE')!r}, not {common.INSTANCE}")
    if values.get("POSTGRES_PORT") != str(common.POSTGRES_PORT):
        raise SystemExit(".env does not carry the lane's PostgreSQL port")
    return values


def secret() -> str:
    value = os.environ.get("REHEARSAL_API_SECRET", "").strip()
    if len(value) < 16:
        raise SystemExit("REHEARSAL_API_SECRET is not set (the deployment secret, from the environment)")
    return value


def wait_http(port: int, path: str, seconds: int) -> bool:
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        try:
            conn = http.client.HTTPConnection("127.0.0.1", port, timeout=3)
            conn.request("GET", path)
            status = conn.getresponse().status
            conn.close()
            if status < 500:
                return True
        except OSError:
            pass
        time.sleep(1)
    return False


def api_start() -> int:
    common.ensure_out()
    if common.listening_pid(common.API_PORT) is not None:
        raise SystemExit(f"port {common.API_PORT} is already held")
    common.capacity_gate("api-start")
    env = dict(os.environ) | dotenv() | {
        "PYTHONPATH": str(common.ROOT / "src"),
        "AUDITMANAGER_API_TOKEN": secret(),
        "AUDITMANAGER_PROVIDER_MODE": "recorded",
        "AUDITMANAGER_API_PORT": str(common.API_PORT),
        "AUDITMANAGER_HEALTH_PORT": str(common.HEALTH_PORT),
        "AUDITMANAGER_BIND_HOST": "127.0.0.1",
    }
    env.pop("EXECUTION_ROLE", None)
    env.pop("REHEARSAL_API_SECRET", None)
    log = API_LOG.open("ab")
    child = subprocess.Popen(
        [str(common.ROOT / ".venv/bin/python"), str(common.ROOT / "infra/deploy/serve.py")],
        cwd=common.ROOT, env=env, stdout=log, stderr=subprocess.STDOUT, start_new_session=True,
    )
    API_PID.write_text(f"{child.pid}\n")
    if not wait_http(common.HEALTH_PORT, "/readyz", 180):
        raise SystemExit(f"the API (pid {child.pid}) never became ready; see {API_LOG}")
    pid = common.own_api_pid()
    print(f"api: pid {pid} ready on 127.0.0.1:{common.API_PORT} (health {common.HEALTH_PORT}); "
          f"VmRSS {common.vm_kib(pid, 'VmRSS')} KiB")
    return 0


def _stop(pid_file: Path, port: int, expect_cwd: Path, what: str) -> int:
    if not pid_file.is_file():
        print(f"{what}: no PID file, nothing to stop")
        return 0
    pid = int(pid_file.read_text().strip())
    try:
        cwd = Path(f"/proc/{pid}/cwd").resolve()
    except OSError:
        print(f"{what}: pid {pid} is already gone")
        pid_file.unlink()
        return 0
    holder = common.listening_pid(port)
    holder_group = os.getpgid(holder) if holder is not None else None
    if cwd != expect_cwd:
        raise SystemExit(f"{what}: pid {pid} runs in {cwd}, not {expect_cwd}; refusing to signal it")
    if holder is not None and holder_group != pid:
        raise SystemExit(f"{what}: port {port} is held by pid {holder} outside group {pid}; refusing")
    os.killpg(pid, signal.SIGTERM)
    for _ in range(60):
        if common.listening_pid(port) is None:
            break
        time.sleep(0.5)
    else:
        os.killpg(pid, signal.SIGKILL)
    pid_file.unlink()
    print(f"{what}: process group {pid} stopped; port {port} free: {common.listening_pid(port) is None}")
    return 0


def api_stop() -> int:
    return _stop(API_PID, common.API_PORT, common.ROOT, "api")


def web_start() -> int:
    common.ensure_out()
    if not (common.ROOT / "web" / ".next" / "BUILD_ID").is_file():
        raise SystemExit("web/.next is not built: NEXT_PUBLIC_API_BASE_URL=/bff/v1 "
                         "NEXT_PUBLIC_INSTANCE_LABEL=w55b-rehearsal npm --prefix web run build")
    if common.listening_pid(common.WEB_PORT) is not None:
        raise SystemExit(f"port {common.WEB_PORT} is already held")
    env = dict(os.environ) | {
        "AUDITMANAGER_API_UPSTREAM": f"http://127.0.0.1:{common.API_PORT}",
        "AUDITMANAGER_API_TOKEN": secret(),
        "NODE_ENV": "production",
    }
    env.pop("REHEARSAL_API_SECRET", None)
    log = WEB_LOG.open("ab")
    child = subprocess.Popen(
        ["npx", "next", "start", "-p", str(common.WEB_PORT), "-H", "127.0.0.1"],
        cwd=common.ROOT / "web", env=env, stdout=log, stderr=subprocess.STDOUT, start_new_session=True,
    )
    WEB_PID.write_text(f"{child.pid}\n")
    if not wait_http(common.WEB_PORT, "/login", 120):
        raise SystemExit(f"Next (pid {child.pid}) never answered; see {WEB_LOG}")
    holder = common.listening_pid(common.WEB_PORT)
    print(f"web: group {child.pid}, port {common.WEB_PORT} held by pid {holder} "
          f"(group {os.getpgid(holder) if holder else None})")
    return 0


def web_stop() -> int:
    return _stop(WEB_PID, common.WEB_PORT, common.ROOT / "web", "web")


def status() -> int:
    for name, pid_file, port in (("api", API_PID, common.API_PORT), ("web", WEB_PID, common.WEB_PORT)):
        pid = pid_file.read_text().strip() if pid_file.is_file() else None
        print(f"{name}: pid file {pid}; port {port} held by {common.listening_pid(port)}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("command", choices=("api-start", "api-stop", "web-start", "web-stop", "status"))
    args = parser.parse_args(argv)
    return {"api-start": api_start, "api-stop": api_stop, "web-start": web_start,
            "web-stop": web_stop, "status": status}[args.command]()


if __name__ == "__main__":
    sys.exit(main())
