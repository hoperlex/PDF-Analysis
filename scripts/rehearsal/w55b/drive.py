#!/usr/bin/env python3
"""Drive the lane's API through one phase and write that phase's figures.

    python scripts/rehearsal/w55b/drive.py account
    python scripts/rehearsal/w55b/drive.py upload --bundle PATH --phase NAME [--project-name N] [--redact]
    python scripts/rehearsal/w55b/drive.py start-refused --phase NAME --version-uid V
    python scripts/rehearsal/w55b/drive.py run --phase NAME --version-uid V [--timeout S]
    python scripts/rehearsal/w55b/drive.py blocks --phase NAME --version-uid V [--redact]
    python scripts/rehearsal/w55b/drive.py fetch --version-uid V --into DIR      # the PDF and every crop
    python scripts/rehearsal/w55b/drive.py scope --phase NAME     # the API scope's memory.peak so far

Secrets come from the environment only: ``REHEARSAL_LOGIN`` and ``REHEARSAL_PASSWORD`` (the account
``account`` provisions through the API itself, starting from the migration's seeded ``admin``),
from which each command signs in afresh (a credential lives an hour). The origin is the lane's API
on loopback, and nothing else is accepted.

Memory: before an upload or a run the API process's high-water mark is reset
(``/proc/<pid>/clear_refs``) and its ``VmRSS`` is sampled every 0.25 s; after a run each stage's
peak is read from the samples inside that stage's ``started_at``..``finished_at`` (from
``stage_result``), and the kernel's ``VmHWM`` gives the phase's peak independently.

``--redact`` is for the owner's real export (F-7): the figures then hold statuses, counts, sizes
and timings, never a name, a text or an identifier from inside the document.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import common  # noqa: E402
from sampler import RssSampler  # noqa: E402

ORIGIN = f"http://127.0.0.1:{common.API_PORT}"
SEED_LOGIN, SEED_PASSWORD = "admin", "password"    # migration 0006's published seed
LOGIN_ENV, PASSWORD_ENV = "REHEARSAL_LOGIN", "REHEARSAL_PASSWORD"
TERMINAL = {"published", "partial", "failed", "cancelled"}
STATE = common.OUT / "state.json"
PROGRESS_LOG = common.OUT / "progress.jsonl"
CHECKPOINTS = (1, 10, 50, 100, 250, 500)


def progress_summary(start: float, end: float) -> dict:
    """The API's resident set after the k-th page (or crop) of each stage's passes.

    Read from ``progress.jsonl``, which ``instrumented_serve.py`` writes; grouped by the stage
    that made the call and by the pass (``extract``: pdfplumber; ``pagebox``: PDFium's page-box
    check; ``render`` and ``publish``: each crop).
    """
    if not PROGRESS_LOG.is_file():
        return {}
    groups: dict[str, list[dict]] = {}
    for raw in PROGRESS_LOG.read_text(encoding="utf-8").splitlines():
        record = json.loads(raw)
        if start <= record["t"] <= end:
            groups.setdefault(f"{record['stage']}/{record['what']}", []).append(record)
    out = {}
    for name, records in groups.items():
        at = {str(k): records[k - 1]["rss_kib"] for k in CHECKPOINTS if k <= len(records)}
        at["last"] = records[-1]["rss_kib"]
        out[name] = {"count": len(records), "first_t": records[0]["t"], "last_t": records[-1]["t"],
                     "last_n": records[-1]["n"], "rss_kib_after_k": at,
                     "max_rss_kib": max(r["rss_kib"] for r in records)}
    return out


def _code(body) -> str | None:
    """The catalog code of an error envelope (``error_code``)."""
    if not isinstance(body, dict):
        return None
    return body.get("error_code") or body.get("code")


def _env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise SystemExit(f"{name} is not set")
    return value


def sign_in(login: str, password: str) -> tuple[int, dict]:
    status, body = common.Api(ORIGIN).json("POST", "/auth/token", {"login": login, "password": password})
    return status, body or {}


def api() -> common.Api:
    status, body = sign_in(_env(LOGIN_ENV), _env(PASSWORD_ENV))
    if status != 200:
        raise SystemExit(f"sign-in refused: {status} {_code(body)}")
    return common.Api(ORIGIN, body["token"])


def key(prefix: str) -> dict[str, str]:
    return {"Idempotency-Key": f"{prefix}-{uuid.uuid4().hex[:24]}"}


def remember(phase: str, **values) -> None:
    state = json.loads(STATE.read_text()) if STATE.is_file() else {}
    state.setdefault(phase, {}).update(values)
    STATE.write_text(json.dumps(state, indent=2) + "\n")


# ------------------------------------------------------------------ account


def account() -> int:
    """The seeded admin, its password changed and its profile completed, as INGEST did."""
    login, password = _env(LOGIN_ENV), _env(PASSWORD_ENV)
    status, _ = sign_in(login, password)
    if status == 200:
        print("account: exists and signs in")
        return 0
    status, body = sign_in(SEED_LOGIN, SEED_PASSWORD)
    if status != 200:
        raise SystemExit(f"the seeded account does not sign in: {status} {_code(body)}")
    seeded = common.Api(ORIGIN, body["token"])
    status, body = seeded.json("POST", "/auth/password",
                               {"current_password": SEED_PASSWORD, "new_password": password})
    if status != 200:
        raise SystemExit(f"password change refused: {status} {body}")
    changed = common.Api(ORIGIN, body["token"])
    status, body = changed.json("PATCH", "/me", {"last_name": "Репетиция", "first_name": "Стенд",
                                                "email": login})
    if status != 200:
        raise SystemExit(f"profile completion refused: {status} {body}")
    status, _ = sign_in(login, password)
    print(f"account: provisioned; sign-in as the new login answers {status}")
    return 0 if status == 200 else 1


# ------------------------------------------------------------------ upload


def bff_cookie() -> str:
    """A session cookie of the lane's Next BFF, from its own sign-in form (``POST /bff/v1/session``)."""
    import http.client
    from urllib.parse import urlencode

    origin = f"http://127.0.0.1:{common.WEB_PORT}"
    body = urlencode({"login": _env(LOGIN_ENV), "password": _env(PASSWORD_ENV)}).encode()
    conn = http.client.HTTPConnection("127.0.0.1", common.WEB_PORT, timeout=60)
    conn.request("POST", "/bff/v1/session", body=body, headers={
        "Content-Type": "application/x-www-form-urlencoded", "Origin": origin, "Sec-Fetch-Site": "same-origin"})
    response = conn.getresponse()
    response.read()
    cookies = [value for name, value in response.getheaders() if name.lower() == "set-cookie"]
    conn.close()
    for cookie in cookies:
        if cookie.startswith("am_session="):
            return cookie.split(";", 1)[0]
    raise SystemExit(f"the BFF sign-in answered {response.status} with no session cookie")


def _stream_upload(client: common.Api, project: str, archive: Path, filename: str,
                   via_bff: str | None = None) -> tuple[int, dict, float]:
    import http.client

    boundary = "----w55brehearsal" + uuid.uuid4().hex
    pre = (f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"{filename}\"\r\n"
           "Content-Type: application/zip\r\n\r\n").encode()
    post = f"\r\n--{boundary}--\r\n".encode()
    size = archive.stat().st_size
    port = common.WEB_PORT if via_bff else client.port
    conn = http.client.HTTPConnection(client.host, port, timeout=1800)
    started = time.monotonic()
    if via_bff:
        conn.putrequest("POST", f"/bff/v1/projects/{project}/documents")
        conn.putheader("Cookie", via_bff)
        conn.putheader("Origin", f"http://127.0.0.1:{common.WEB_PORT}")
        conn.putheader("Sec-Fetch-Site", "same-origin")
    else:
        conn.putrequest("POST", f"/projects/{project}/documents")
        conn.putheader("Authorization", f"Bearer {client.token}")
    for name, value in key("upload").items():
        conn.putheader(name, value)
    conn.putheader("Content-Type", f"multipart/form-data; boundary={boundary}")
    conn.putheader("Content-Length", str(len(pre) + size + len(post)))
    conn.endheaders()
    conn.send(pre)
    with archive.open("rb") as handle:
        while chunk := handle.read(1 << 20):
            conn.send(chunk)
    conn.send(post)
    response = conn.getresponse()
    data = response.read()
    elapsed = time.monotonic() - started
    conn.close()
    try:
        body = json.loads(data)
    except ValueError:
        body = {"_not_json": True}
    return response.status, body, elapsed


def upload(bundle: Path, phase: str, project_name: str, redact: bool, project_uid: str | None,
           via_bff: bool = False) -> int:
    at_start = common.capacity_gate(f"upload {phase}")
    client = api()
    if project_uid is None:
        status, body = client.json("POST", "/projects", {"name": project_name}, headers=key("project"))
        if status != 201:
            raise SystemExit(f"createProject: {status} {body}")
        project_uid = body["project_uid"]
    pid = common.own_api_pid()
    cookie = bff_cookie() if via_bff else None
    web_pid = common.listening_pid(common.WEB_PORT) if via_bff else None
    web = {}
    if web_pid is not None:
        web = {"pid": web_pid, "rss_before_kib": common.vm_kib(web_pid, "VmRSS"),
               "vmhwm_after_reset_kib": common.reset_peak(web_pid),
               "scope_before": common.cgroup_memory(web_pid)}
        web_sampler = RssSampler(web_pid).start()
    idle_rss = common.vm_kib(pid, "VmRSS")
    hwm_reset = common.reset_peak(pid)
    sampler = RssSampler(pid).start()
    t0 = time.time()
    scope_before = common.cgroup_memory(pid)
    status, body, seconds = _stream_upload(client, project_uid, bundle, "bundle.zip", cookie)
    t1 = time.time()
    sampler.stop()
    if web_pid is not None:
        web_sampler.stop()
        web.update({"vmhwm_after_kib": common.vm_kib(web_pid, "VmHWM"),
                    "sampled": web_sampler.peak_between(t0, t1),
                    "scope_after": common.cgroup_memory(web_pid)})
    hwm_after = common.vm_kib(pid, "VmHWM")
    scope_after = common.cgroup_memory(pid)
    peak = sampler.peak_between(t0, t1)
    response = {"status": status}
    if status == 201:
        response.update({"page_count": body.get("page_count"), "byte_size": body.get("byte_size"),
                         "manifest_roles": sorted(e.get("role") for e in body.get("input_manifest", []))})
        if not redact:
            response.update({"version_uid": body.get("version_uid"),
                             "source_filename": body.get("source_filename")})
        remember(phase, project_uid=project_uid, version_uid=body.get("version_uid"))
    else:
        response.update({"error_code": _code(body), "details": body.get("details")})
    common.write_figures(phase, {
        "what": ("upload of one portal bundle, streamed with a Content-Length, through the lane's Next BFF "
                 "(no nginx)" if via_bff else
                 "upload of one portal bundle, streamed with a Content-Length, loopback API (no BFF, no nginx)"),
        "web_process": web,
        "context_at_start": at_start,
        "archive_bytes": bundle.stat().st_size,
        "response": response,
        "wall_seconds": round(seconds, 2),
        "api_pid": pid,
        "rss_before_kib": idle_rss,
        "vmhwm_after_reset_kib": hwm_reset,
        "vmhwm_after_kib": hwm_after,
        "vmhwm_growth_kib": hwm_after - hwm_reset,
        "sampled": peak,
        "scope_before": scope_before,
        "scope_after": scope_after,
        "rss_series": sampler.series(),
    })
    print(f"{phase}: {status} in {seconds:.2f} s; VmHWM {hwm_reset} -> {hwm_after} KiB "
          f"(+{(hwm_after - hwm_reset) / 1024:.1f} MiB); sampled peak {peak.get('peak_rss_kib')} KiB")
    if status == 201 and not redact:
        print(f"version_uid {body.get('version_uid')} project_uid {project_uid}")
    return 0 if status == 201 else 1


# ------------------------------------------------------------------ database reads


def _db_url() -> str:
    from stack import dotenv

    return dotenv()["DATABASE_URL"].replace("postgresql+psycopg://", "postgresql://")


def db_rows(sql: str, params: tuple = ()) -> list[tuple]:
    import psycopg

    with psycopg.connect(_db_url()) as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return cur.fetchall()


_COUNTED = ("audit_run", "job", "attempt", "command_record", "stage_result", "model_call",
            "provider_call_effect", "lease")


def table_counts() -> dict[str, int]:
    return {table: db_rows(f"SELECT count(*) FROM {table}")[0][0] for table in _COUNTED}


# ------------------------------------------------------------------ the refused start


def start_refused(phase: str, version_uid: str) -> int:
    client = api()
    runs_status, runs_before = client.json("GET", f"/versions/{version_uid}/runs")
    before = table_counts()
    started = time.monotonic()
    status, body = client.json("POST", "/runs", {"version_uid": version_uid}, headers=key("run"))
    seconds = time.monotonic() - started
    after = table_counts()
    _, runs_after = client.json("GET", f"/versions/{version_uid}/runs")
    created = {table: after[table] - before[table] for table in _COUNTED if after[table] != before[table]}
    common.write_figures(phase, {
        "what": "startRun over a version above the analysis input budget",
        "response": {"status": status, "code": _code(body),
                     "retryable": (body or {}).get("retryable"), "details": (body or {}).get("details")},
        "wall_seconds": round(seconds, 3),
        "runs_listed_before": len((runs_before or {}).get("items", [])) if runs_status == 200 else None,
        "runs_listed_after": len((runs_after or {}).get("items", [])),
        "rows_before": before,
        "rows_after": after,
        "rows_created": created,
    })
    print(f"{phase}: {status} {_code(body)} {(body or {}).get('details')}; rows created: {created or 'none'}")
    ok = status == 422 and _code(body) == "analysis_input_budget_exceeded" and not created
    return 0 if ok else 1


# ------------------------------------------------------------------ a run


def _parse(ts) -> float | None:
    if ts is None:
        return None
    if isinstance(ts, datetime):
        return ts.timestamp()
    return datetime.fromisoformat(str(ts).replace("Z", "+00:00")).timestamp()


def docker_stats() -> dict:
    names = [f"{common.INSTANCE}-postgres-1", f"{common.INSTANCE}-s3-1"]
    out = subprocess.run(["docker", "stats", "--no-stream", "--format", "{{.Name}}\t{{.MemUsage}}\t{{.CPUPerc}}", *names],
                         capture_output=True, text=True, check=False).stdout
    return {line.split("\t")[0]: line.split("\t")[1:] for line in out.strip().splitlines() if line}


def store_bytes() -> dict:
    """The S3 volume's bytes on disk, and the available blobs by media type from the database."""
    volume = f"{common.INSTANCE}-s3-data"
    mount = subprocess.run(["docker", "volume", "inspect", "-f", "{{.Mountpoint}}", volume],
                           capture_output=True, text=True, check=True).stdout.strip()
    du = subprocess.run(["du", "-sb", mount], capture_output=True, text=True, check=True).stdout.split()[0]
    rows = db_rows("SELECT media_type, count(*), coalesce(sum(size_bytes), 0) FROM blob "
                   "WHERE state = 'available' GROUP BY media_type ORDER BY media_type")
    return {"s3_volume_bytes_on_disk": int(du),
            "available_blobs": {m: {"count": c, "bytes": int(b)} for m, c, b in rows}}


def run(phase: str, version_uid: str, timeout: int, redact: bool) -> int:
    at_start = common.capacity_gate(f"run {phase}")
    client = api()
    pid = common.own_api_pid()
    rss_before = common.vm_kib(pid, "VmRSS")
    hwm_reset = common.reset_peak(pid)
    store_before = store_bytes()
    scope_before = common.cgroup_memory(pid)
    sampler = RssSampler(pid).start()
    t0 = time.time()
    status, body = client.json("POST", "/runs", {"version_uid": version_uid}, headers=key("run"))
    if status != 202:
        sampler.stop()
        common.write_figures(phase, {"response": {"status": status, "code": _code(body),
                                                  "details": (body or {}).get("details")}})
        print(f"{phase}: startRun answered {status} {_code(body)}")
        return 1
    run_id = body["run_id"]
    remember(phase, run_id=run_id, version_uid=version_uid)
    states, last, mid_stats, signed_at, vanished = [], None, None, time.time(), None
    status_body: dict = {}
    while time.time() - t0 < timeout:
        if not Path(f"/proc/{pid}").exists():
            vanished = time.time()
            states.append({"t": round(vanished - t0, 1), "api_process": "gone"})
            break
        if time.time() - t0 > 20 and mid_stats is None:
            mid_stats = docker_stats()
        if time.time() - signed_at > 1800:          # a credential lives an hour
            client, signed_at = api(), time.time()
        try:
            code, status_body = client.json("GET", f"/runs/{run_id}")
        except OSError as error:
            states.append({"t": round(time.time() - t0, 1), "error": type(error).__name__})
            time.sleep(2)
            continue
        state = (status_body or {}).get("state")
        if state != last:
            states.append({"t": round(time.time() - t0, 1), "state": state})
            last = state
        if state in TERMINAL:
            break
        time.sleep(2)
    t1 = time.time()
    sampler.stop()
    hwm_after = common.vm_kib(pid, "VmHWM") if vanished is None else None
    scope_after = common.cgroup_memory(pid) if vanished is None else {}
    rows = db_rows("SELECT stage_id, status, metrics, error, started_at, finished_at FROM stage_result "
                   "WHERE run_id = %s ORDER BY started_at NULLS LAST", (run_id,))
    stages = []
    for stage_id, stage_status, metrics, error, started_at, finished_at in rows:
        start, end = _parse(started_at), _parse(finished_at)
        if start and not end and vanished:
            end = vanished
        entry = {"stage_id": stage_id, "status": stage_status, "metrics": metrics,
                 "error_code": (error or {}).get("code"),
                 "error_reason": ((error or {}).get("details") or {}).get("reason"),
                 "started_at": str(started_at), "finished_at": str(finished_at),
                 "wall_seconds": round(end - start, 2) if start and end else None,
                 "memory": sampler.peak_between(start, end) if start and end else None}
        if redact:
            entry["error_message"] = None
        else:
            entry["error_message"] = (error or {}).get("message")
        stages.append(entry)
    terminal = (status_body or {})
    common.write_figures(phase, {
        "what": "startRun then getRunStatus every 2 s until terminal; stages from stage_result",
        "context_at_start": at_start,
        "run_state": terminal.get("state"),
        "terminal_reason": terminal.get("terminal_reason"),
        "terminal_detail": terminal.get("terminal_detail"),
        "state_changes": states,
        "wall_seconds_to_terminal": round(t1 - t0, 1),
        "api_pid": pid,
        "rss_before_kib": rss_before,
        "vmhwm_after_reset_kib": hwm_reset,
        "vmhwm_after_kib": hwm_after,
        "vmhwm_growth_kib": None if hwm_after is None else hwm_after - hwm_reset,
        "api_process_vanished_at": vanished,
        "scope_before": scope_before,
        "scope_after": scope_after,
        "scope_peak_sampled_bytes": sampler.last_cgroup_peak(),
        "last_sample": sampler.series()[-1:] if sampler.samples else None,
        "per_page": progress_summary(t0, t1),
        "stages": stages,
        "containers_mid_run": mid_stats,
        "containers_after": docker_stats(),
        "store_before": store_before,
        "store_after": store_bytes(),
        "rss_series": sampler.series(),
    })
    if vanished is not None:
        print(f"{phase}: THE API PROCESS VANISHED after {vanished - t0:.1f} s; last sample "
              f"{sampler.series()[-1:]}; scope peak sampled {sampler.last_cgroup_peak()} B")
    else:
        print(f"{phase}: run ended {terminal.get('state')} ({terminal.get('terminal_reason')}) after "
              f"{t1 - t0:.1f} s; VmHWM +{(hwm_after - hwm_reset) / 1024:.1f} MiB; scope memory.peak "
              f"{scope_after.get('memory_peak')} B")
    for entry in stages:
        memory = entry["memory"] or {}
        print(f"  {entry['stage_id']}: {entry['status']} {entry['error_code'] or ''} "
              f"{entry['wall_seconds']} s, duration_ms {entry['metrics'].get('duration_ms')}, "
              f"peak RSS {memory.get('peak_rss_kib')} KiB (+{(memory.get('peak_growth_kib') or 0) / 1024:.1f} MiB)")
    return 0 if vanished is None else 3


# ------------------------------------------------------------------ what the product does after a kill


def _run_rows(run_id: str) -> dict:
    run = db_rows("SELECT state FROM audit_run WHERE run_id = %s", (run_id,))
    jobs = db_rows("SELECT job_id, state FROM job WHERE run_id = %s", (run_id,))
    attempts = db_rows("SELECT a.state, count(*) FROM attempt a JOIN job j ON j.job_id = a.job_id "
                       "WHERE j.run_id = %s GROUP BY a.state ORDER BY a.state", (run_id,))
    stages = db_rows("SELECT stage_id, status FROM stage_result WHERE run_id = %s", (run_id,))
    return {"run": run[0][0] if run else None, "jobs": [state for _, state in jobs],
            "attempts": {state: count for state, count in attempts},
            "stage_results": {stage: status for stage, status in stages}}


def _alive(pid: int | None) -> bool:
    """A process that exists and is not a zombie; a child of ours is reaped once it has died."""
    if pid is None:
        return False
    try:
        if os.waitpid(pid, os.WNOHANG) != (0, 0):
            return False
    except ChildProcessError:
        pass
    try:
        state = next(line for line in Path(f"/proc/{pid}/status").read_text().splitlines()
                     if line.startswith("State:"))
    except (OSError, StopIteration):
        return False
    return "Z" not in state.split()[1]


def recovery(phase: str, run_id: str, restarts: int, window: int) -> int:
    """Restart the API whenever the cap has killed it, up to ``restarts`` times, and record what the
    product's own recovery does with the run it left behind. Nothing is reconciled by hand."""
    import stack

    started = time.time()
    events: list[dict] = [{"t": 0.0, "event": "observed", **_run_rows(run_id)}]
    done = 0
    pid = None
    last = None
    while time.time() - started < window:
        alive = _alive(pid)
        if not alive:
            if pid is not None:
                events.append({"t": round(time.time() - started, 1), "event": "api killed", "pid": pid,
                               **_run_rows(run_id)})
            if done >= restarts:
                break
            if common.listening_pid(common.API_PORT) is None:
                stack.api_start()
                done += 1
            pid = common.own_api_pid()
            events.append({"t": round(time.time() - started, 1), "event": f"api started ({done})",
                           "pid": pid, **_run_rows(run_id)})
        rows = _run_rows(run_id)
        snapshot = json.dumps(rows, sort_keys=True)
        if snapshot != last:
            events.append({"t": round(time.time() - started, 1), "event": "rows", **rows,
                           "rss_kib": common.vm_kib(pid, "VmRSS") if _alive(pid) else None})
            last = snapshot
        if rows["run"] in TERMINAL:
            break
        time.sleep(3)
    common.write_figures(phase, {"what": "the API restarted after each kill by the cap; the run's rows as the product leaves them",
                                 "run_id": run_id, "restarts": done, "events": events,
                                 "final": _run_rows(run_id)})
    print(json.dumps(events[-3:], indent=1))
    return 0


# ------------------------------------------------------------------ the portal blocks over the API


def _spread(values: list[int]) -> dict:
    if not values:
        return {}
    ordered = sorted(values)
    return {"n": len(ordered), "min": ordered[0], "p25": ordered[len(ordered) // 4],
            "median": ordered[len(ordered) // 2], "p75": ordered[(3 * len(ordered)) // 4], "max": ordered[-1]}


def blocks(phase: str, version_uid: str, redact: bool, limit: int) -> int:
    client = api()
    cursor, pages, seen, times = None, 0, [], []
    by_type: dict[str, int] = {}
    crops = geometry_ok = 0
    block_count = None
    pixels: list[int] = []
    while True:
        path = f"/versions/{version_uid}/portal-blocks?limit={limit}" + (f"&cursor={cursor}" if cursor else "")
        started = time.monotonic()
        status, body = client.json("GET", path)
        times.append(round(time.monotonic() - started, 3))
        if status != 200:
            raise SystemExit(f"listVersionPortalBlocks: {status} {_code(body)}")
        pages += 1
        block_count = body["block_count"]
        for item in body["items"]:
            seen.append(item["portal_block_id"])
            by_type[item["block_type"]] = by_type.get(item["block_type"], 0) + 1
            crops += "crop" in item
            if "crop" in item:
                pixels.append(item["crop"]["width_px"] * item["crop"]["height_px"])
            geometry_ok += item.get("geometry") == "ok"
        cursor = body["page"]["next_cursor"]
        if cursor is None:
            break
    unique = len(set(seen))
    common.write_figures(phase, {
        "what": f"listVersionPortalBlocks paged at limit {limit} to the end, loopback API",
        "status": body["status"], "block_count": block_count, "listed": len(seen), "unique": unique,
        "repeated": len(seen) - unique, "pages": pages, "by_type": by_type, "with_crop": crops,
        "geometry_ok": geometry_ok, "page_seconds": times,
        "crop_pixels": _spread(pixels),
        "crops_at_the_pixel_cap": sum(1 for n in pixels if n > 3_960_000),
    })
    print(f"{phase}: {len(seen)} listed of {block_count}, {unique} unique, {pages} pages, by type {by_type}, "
          f"crops {crops}, page times {min(times)}..{max(times)} s")
    return 0 if unique == len(seen) == block_count else 1


# ------------------------------------------------------------------ fetch (for the fidelity check)


def fetch(version_uid: str, into: Path) -> int:
    """The version's PDF and every crop, with the block geometry, into a git-ignored directory."""
    into = into.resolve()
    if common.OUT not in into.parents:
        raise SystemExit(f"refusing to write outside {common.OUT}")
    into.mkdir(parents=True, exist_ok=True)
    client = api()
    status, _, pdf = client.call("GET", f"/versions/{version_uid}/content")
    if status != 200:
        raise SystemExit(f"streamDocumentVersionContent: {status}")
    (into / "document.pdf").write_bytes(pdf)
    cursor, records = None, []
    while True:
        path = f"/versions/{version_uid}/portal-blocks?limit=200" + (f"&cursor={cursor}" if cursor else "")
        status, body = client.json("GET", path)
        if status != 200:
            raise SystemExit(f"listVersionPortalBlocks: {status}")
        for item in body["items"]:
            if item["block_type"] != "image":
                continue
            number = len(records) + 1
            record = {"n": number, "page_number": item["page_number"], "bbox_norm": item["bbox_norm"],
                      "polygon_points": item.get("polygon_points"), "geometry": item["geometry"],
                      "crop": item.get("crop"), "description": item.get("portal_description")}
            if "crop" in item:
                status, _, png = client.call(
                    "GET", f"/versions/{version_uid}/portal-blocks/{item['portal_block_id']}/crop")
                record["crop_status"] = status
                if status == 200:
                    (into / f"crop-{number:03d}.png").write_bytes(png)
            records.append(record)
        cursor = body["page"]["next_cursor"]
        if cursor is None:
            break
    (into / "image_blocks.json").write_text(json.dumps(records, ensure_ascii=False, indent=1))
    print(f"fetch: the PDF ({len(pdf)} bytes) and {sum(1 for r in records if r.get('crop_status') == 200)} "
          f"crops of {len(records)} IMAGE blocks into {into.relative_to(common.ROOT)}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("account")
    up = sub.add_parser("upload")
    up.add_argument("--bundle", type=Path, required=True)
    up.add_argument("--phase", required=True)
    up.add_argument("--project-name", default="W55B rehearsal")
    up.add_argument("--project-uid")
    up.add_argument("--redact", action="store_true")
    up.add_argument("--via-bff", action="store_true")
    refused = sub.add_parser("start-refused")
    refused.add_argument("--phase", required=True)
    refused.add_argument("--version-uid", required=True)
    one = sub.add_parser("run")
    one.add_argument("--phase", required=True)
    one.add_argument("--version-uid", required=True)
    one.add_argument("--timeout", type=int, default=3600)
    one.add_argument("--redact", action="store_true")
    listing = sub.add_parser("blocks")
    listing.add_argument("--phase", required=True)
    listing.add_argument("--version-uid", required=True)
    listing.add_argument("--limit", type=int, default=100)
    listing.add_argument("--redact", action="store_true")
    watch = sub.add_parser("recovery")
    watch.add_argument("--phase", required=True)
    watch.add_argument("--run-id", required=True)
    watch.add_argument("--restarts", type=int, default=3)
    watch.add_argument("--window", type=int, default=900)
    scope = sub.add_parser("scope")
    scope.add_argument("--phase", required=True)
    get = sub.add_parser("fetch")
    get.add_argument("--version-uid", required=True)
    get.add_argument("--into", type=Path, required=True)
    args = parser.parse_args(argv)
    common.ensure_out()
    if args.command == "account":
        return account()
    if args.command == "upload":
        return upload(args.bundle, args.phase, args.project_name, args.redact, args.project_uid, args.via_bff)
    if args.command == "start-refused":
        return start_refused(args.phase, args.version_uid)
    if args.command == "run":
        return run(args.phase, args.version_uid, args.timeout, args.redact)
    if args.command == "blocks":
        return blocks(args.phase, args.version_uid, args.redact, args.limit)
    if args.command == "fetch":
        return fetch(args.version_uid, args.into)
    if args.command == "recovery":
        return recovery(args.phase, args.run_id, args.restarts, args.window)
    if args.command == "scope":
        pid = common.own_api_pid()
        common.write_figures(args.phase, {"api_pid": pid, "vmrss_kib": common.vm_kib(pid, "VmRSS"),
                                          "vmhwm_kib": common.vm_kib(pid, "VmHWM"),
                                          "scope": common.cgroup_memory(pid)})
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main())
