#!/usr/bin/env python3
"""The whole deterministic comparison chain on a version set: admission, page profiles, matrix, series, tile cost
(`CMP-MEASURE-01`, ADR-0025 decisions 8 and 9, wave brief `CMP-WAVE-C1` section 5 item 4).

    comparison_chain.py run    --results DIR [--set DIR] [--files v1.pdf,v2.pdf,...] [--label NAME]
    comparison_chain.py tiles  --results DIR [--tiles 20]
    comparison_chain.py report --results DIR
    comparison_chain.py worker                 (internal: the real worker with a recording wrapper)

Run it from the lane worktree with the lane's stack up (``make up`` and ``make migrate``), the lane's interpreter and
``PYTHONPATH=$PWD/src``; the variables of the lane's ``.env`` are read from the file in the working directory.

What ``run`` does, through the product's own path, on the lane's own PostgreSQL and MinIO
------------------------------------------------------------------------------------------
1. creates an expert account and a project and signs a credential (the way the suites do), builds the composed application
   in this process (``create_app``; **this process is the API process**, and ``TestClient`` drives its routers);
2. starts the **real worker** (``python -m auditmanager.workers serve``, ``EXECUTION_ROLE=worker``,
   ``AUDITMANAGER_COMPARISON_MODULES=versions``) as a child of this process, through a thin recording wrapper (``worker``):
   a class-level wrapper of ``SubprocessChildRunner.run`` and of three functions that adds a record to a JSON-lines file and
   changes nothing else;
3. **admission** over HTTP: ``createComparisonUpload``, one ``uploadComparisonUploadPart`` per 16 MiB, ``completeComparisonUploadFile``
   (the product reads the PDF there, in two ceilinged children), ``getComparisonUploadProposal``, ``confirmComparisonUploadSet``
   in the order of the files, ``listComparisonVersionOrders``;
4. **page profiles**: the worker's ``page_profile`` items, released by the confirmation (the batch lifecycle); waits for them;
5. **matrix**: ``prepareComparisonMatrix`` → the worker's ``matrix_build`` item; waits for ``ready``;
6. **series**: ``startComparisonSeries`` → ``series_drive`` and ``series_pair`` items; waits for a terminal state;
7. reads the outcome (matrix counts, series, transitions, every sheet pair) and the censuses (bytes per kind, rows per table).

Figures
-------
* Memory of a child is the child's **own** ``VmHWM`` (peak resident set) and ``VmPeak`` (peak address space, the quantity
  ``RLIMIT_AS`` limits), read by the child from ``/proc/self/status`` and reported in its last JSON line (``facts``); the
  kernel's ``ru_maxrss`` from ``wait4`` is **not** used (it includes the resident set of the parent at ``fork``:
  ``CMP-ENGINE-01`` section 6).
* Memory of the worker is, per work item, ``VmHWM`` read after the item with the high-water mark reset (``clear_refs`` 5) before
  it, ``VmPeak`` (cumulative) and ``VmRSS``; the orchestrator's sampler adds a time series of the worker, of its children and of
  this process every ``--interval`` seconds (``samples.jsonl``), from which the **largest sum of the worker and its children at one
  instant** (the footprint the host must hold) is taken.
* CPU of a stage is the worker's ``utime + stime`` (and, apart, that of the children it waited for) from ``/proc/<pid>/stat``.
* Every timing is recorded with the one-minute load average of the host: the host is shared, times are upper bounds.

The real set is client-like data. Nothing of a page, word, text or raster is read, printed or written by this program: records
hold numbers, the file's base name, opaque identities and words that name a state or a typed reason. Nothing is committed.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import math
import os
import shutil
import signal
import subprocess
import sys
import threading
import time
import zipfile
from collections import defaultdict
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from comparison_engine import STOP_FREE_BYTES, _free_bytes  # noqa: E402  (the engine tool's disk guard, reused)

ROOT = Path(__file__).resolve().parents[2]
REAL_SET = Path("/root/projects/PDF-Analysis/.local/comparison-measure/13AV-RD-EM2-PA")
RESULTS = Path("/root/projects/PDF-Analysis/.local/comparison-measure/results-final/chain-01")
MIB = 1024 * 1024
KIB = 1024
CLK_TCK = os.sysconf("SC_CLK_TCK")
SECRET = "comparison-chain-measure-01"  # the deployment secret of this lane's disposable application
LOGIN_LABEL = "chain-measure"
GUARD_RSS_KIB = int(3.5 * 1024 * MIB // KIB)  # the worker tree is ended (by PID) above this resident size ...
GUARD_AVAILABLE_KIB = 600 * MIB // KIB  # ... or when the host has less than this available
RECORD_FILES = ("children", "pages", "pairs", "items")
_NAMES = (
    "DATABASE_URL", "S3_ENDPOINT_URL", "S3_API_PORT", "S3_REGION", "S3_ACCESS_KEY_ID", "S3_SECRET_ACCESS_KEY", "S3_BUCKET",
)


# ---------------------------------------------------------------------------------------------------------------------
# /proc
# ---------------------------------------------------------------------------------------------------------------------


def proc_status(pid: int | str = "self") -> dict[str, int]:
    wanted = {"VmPeak": "vm_peak_kib", "VmHWM": "vm_hwm_kib", "VmRSS": "vm_rss_kib", "VmSwap": "vm_swap_kib", "Threads": "threads"}
    found: dict[str, int] = {}
    try:
        with open(f"/proc/{pid}/status", encoding="ascii") as handle:
            for line in handle:
                key, _, rest = line.partition(":")
                if key in wanted:
                    found[wanted[key]] = int(rest.split()[0])
    except OSError:
        return {}
    return found


def proc_ticks(pid: int | str = "self") -> tuple[int, int, int, int] | None:
    """``(utime, stime, cutime, cstime)`` in clock ticks: the process, then the children it has waited for."""
    try:
        with open(f"/proc/{pid}/stat", encoding="ascii") as handle:
            text = handle.read()
    except OSError:
        return None
    fields = text[text.rindex(")") + 2 :].split()
    return int(fields[11]), int(fields[12]), int(fields[13]), int(fields[14])


def reset_hwm(pid: int | str = "self") -> bool:
    """Reset the peak resident set of a process to its present resident set (Linux 4.0 ``clear_refs`` 5)."""
    try:
        with open(f"/proc/{pid}/clear_refs", "w", encoding="ascii") as handle:
            handle.write("5")
        return True
    except OSError:
        return False


def loadavg() -> list[float]:
    with open("/proc/loadavg", encoding="ascii") as handle:
        return [float(x) for x in handle.read().split()[:3]]


def meminfo() -> dict[str, int]:
    found: dict[str, int] = {}
    with open("/proc/meminfo", encoding="ascii") as handle:
        for line in handle:
            key, _, rest = line.partition(":")
            if key in ("MemTotal", "MemAvailable", "SwapTotal", "SwapFree"):
                found[key] = int(rest.split()[0])
    return found


def direct_children(pid: int) -> list[int]:
    found: list[int] = []
    try:
        for tid in os.listdir(f"/proc/{pid}/task"):
            try:
                with open(f"/proc/{pid}/task/{tid}/children", encoding="ascii") as handle:
                    found.extend(int(x) for x in handle.read().split())
            except OSError:
                continue
    except OSError:
        pass
    return found


def descendants(pid: int, depth: int = 3) -> list[int]:
    out: list[int] = []
    frontier = [pid]
    for _ in range(depth):
        nxt: list[int] = []
        for item in frontier:
            nxt.extend(direct_children(item))
        out.extend(nxt)
        frontier = nxt
        if not frontier:
            break
    return out


def label_of(pid: int) -> str:
    """What a child is, from its command line: a page-profile mode and page, the engine, or an upload reader. Numbers and words only."""
    try:
        with open(f"/proc/{pid}/cmdline", "rb") as handle:
            parts = handle.read().split(b"\0")
    except OSError:
        return "gone"
    text = [p.decode("utf-8", "replace") for p in parts if p]
    program = next((Path(p).name for p in text if p.endswith(".py")), "?")
    parent = next((Path(p).parent.parent.name for p in text if p.endswith("program.py")), "")
    settings: dict[str, Any] = {}
    for item in text:
        if item.startswith("{"):
            try:
                settings = json.loads(item)
            except ValueError:
                settings = {}
    if program == "program.py" and parent == "engine":
        return "engine"
    if program == "program.py":
        return f"profile.{settings.get('mode', '?')}.p{settings.get('page', '?')}"
    return program.removesuffix(".py")


# ---------------------------------------------------------------------------------------------------------------------
# the sampler
# ---------------------------------------------------------------------------------------------------------------------


class Sampler(threading.Thread):
    """Samples the trees of the named roots every ``interval`` seconds into ``samples.jsonl`` and guards the host."""

    def __init__(self, path: Path, roots: dict[str, int], interval: float) -> None:
        super().__init__(daemon=True, name="chain-sampler")
        self.path, self.roots, self.interval = path, roots, interval
        self.stop_event = threading.Event()
        self.tripped: str | None = None
        self.on_trip: Any = None
        self.peak_tree_kib = 0
        self._last_system = 0.0

    def sample(self) -> None:
        now = time.time()
        record: dict[str, Any] = {"t": round(now, 3)}
        tree_total = 0
        # the worker is a child of the process that hosts the API: its tree is the worker's, not the API's
        worker_pid = self.roots.get("worker")
        apart = {worker_pid, *descendants(worker_pid)} if worker_pid else set()
        for name, pid in sorted(self.roots.items(), key=lambda kv: kv[0] != "worker"):
            status = proc_status(pid)
            if not status:
                continue
            item: dict[str, Any] = {"rss": status.get("vm_rss_kib", 0), "hwm": status.get("vm_hwm_kib", 0), "peak": status.get("vm_peak_kib", 0)}
            ticks = proc_ticks(pid)
            if ticks is not None:
                item["cpu"] = ticks[0] + ticks[1]
                item["ccpu"] = ticks[2] + ticks[3]
            kids = []
            for kid in descendants(pid):
                if name != "worker" and kid in apart:
                    continue
                kstat = proc_status(kid)
                if kstat:
                    kticks = proc_ticks(kid)
                    kids.append([kid, label_of(kid), kstat.get("vm_rss_kib", 0), kstat.get("vm_hwm_kib", 0), kstat.get("vm_peak_kib", 0),
                                 (kticks[0] + kticks[1]) if kticks else 0])
            item["kids"] = kids
            record[name] = item
            tree_total += item["rss"] + sum(k[2] for k in kids)
            if name == "worker":
                self.peak_tree_kib = max(self.peak_tree_kib, item["rss"] + sum(k[2] for k in kids))
        if now - self._last_system >= 1.0:
            self._last_system = now
            mem = meminfo()
            record["sys"] = {"avail": mem.get("MemAvailable", 0), "swap_free": mem.get("SwapFree", 0), "load1": loadavg()[0]}
            if self.on_trip is not None and self.tripped is None:
                worker = record.get("worker")
                worker_tree = (worker["rss"] + sum(k[2] for k in worker["kids"])) if worker else 0
                if worker_tree > GUARD_RSS_KIB:
                    self.tripped = f"worker tree resident {worker_tree // KIB} MiB over {GUARD_RSS_KIB // KIB} MiB"
                elif mem.get("MemAvailable", GUARD_AVAILABLE_KIB + 1) < GUARD_AVAILABLE_KIB:
                    self.tripped = f"host MemAvailable {mem.get('MemAvailable', 0) // KIB} MiB"
                if self.tripped:
                    self.on_trip(self.tripped)
        with open(self.path, "a", encoding="ascii") as sink:
            sink.write(json.dumps(record, separators=(",", ":")) + "\n")

    def run(self) -> None:
        while not self.stop_event.wait(self.interval):
            try:
                self.sample()
            except Exception as failure:  # noqa: BLE001 - a sampling slip must not end the run
                print(f"sampler: {type(failure).__name__}: {failure}", file=sys.stderr)

    def stop(self) -> None:
        self.stop_event.set()
        self.join(timeout=5)


# ---------------------------------------------------------------------------------------------------------------------
# the recording wrapper (worker side, and the tile process)
# ---------------------------------------------------------------------------------------------------------------------

_ctx = threading.local()
_emit_lock = threading.Lock()
_SAFE_STRINGS = frozenset({"status", "reason", "stage", "end", "method", "kind", "mode"})


def numbers_only(value: Any, depth: int = 0) -> Any:
    """Keep the numbers (and a few words that name a state) of a mapping; drop everything else (never page content)."""
    if isinstance(value, dict):
        out = {}
        for key, item in value.items():
            kept = numbers_only(item, depth + 1) if depth < 3 else None
            if isinstance(item, str):
                kept = item if str(key) in _SAFE_STRINGS and len(item) <= 48 else None
            if kept not in (None, {}, []):
                out[str(key)] = kept
        return out
    if isinstance(value, bool) or isinstance(value, (int, float)):
        return value
    if isinstance(value, (list, tuple)) and value and len(value) <= 12 and all(isinstance(x, (int, float)) and not isinstance(x, bool) for x in value):
        return list(value)
    return None


def install_recording(records: Path, label: str) -> None:
    """Wrap, at class and module level, the points the measurement reads. The wrappers add a record and call the original."""
    records.mkdir(parents=True, exist_ok=True)

    def emit(name: str, record: dict[str, Any]) -> None:
        record["proc"] = label
        line = json.dumps(record, ensure_ascii=True, separators=(",", ":"))
        with _emit_lock, open(records / f"{name}.jsonl", "a", encoding="ascii") as sink:
            sink.write(line + "\n")

    from auditmanager.comparison.profile import runner as runner_module

    original_run = runner_module.SubprocessChildRunner.run

    def run(self: Any, settings: Any, limits: Any) -> Any:
        context = dict(getattr(_ctx, "value", None) or {})
        kind = "engine" if "inputs" in settings else str(settings.get("mode", "?"))
        started = time.time()
        load = loadavg()[0]
        try:
            result = original_run(self, settings, limits)
        except BaseException as failure:
            emit("children", {"t0": started, "t1": time.time(), "kind": kind, "ctx": context, "raised": type(failure).__name__, "load1": load})
            raise
        emit("children", {
            "t0": started, "t1": time.time(), "kind": kind, "ctx": context, "status": result.status, "stage": result.stage,
            "wall_s": result.wall_s, "cpu_s": result.cpu_s, "ru_maxrss_kib": result.max_rss_kib, "load1": load,
            "ceiling_mib": limits.address_space // MIB, "cpu_limit_s": limits.cpu_seconds, "wall_limit_s": limits.wall_seconds,
            "facts": numbers_only(dict(result.facts)), "settings": numbers_only(dict(settings)),
        })
        return result

    runner_module.SubprocessChildRunner.run = run  # type: ignore[method-assign]

    try:
        from auditmanager.comparison.profile import builder as builder_module
    except ImportError:  # pragma: no cover
        builder_module = None
    if builder_module is not None:
        original_profile_page = builder_module.profile_page

        def profile_page(runner: Any, *, pdf_path: str, page_index: int, version_sha256: str, **more: Any) -> Any:
            _ctx.value = {"stage": "profile", "version": version_sha256[:12], "page": page_index + 1}
            started, cpu0 = time.time(), time.thread_time()
            try:
                outcome = original_profile_page(runner, pdf_path=pdf_path, page_index=page_index, version_sha256=version_sha256, **more)
            finally:
                _ctx.value = None
            members: dict[str, Any] = {}
            if outcome.pack:
                with zipfile.ZipFile(io.BytesIO(outcome.pack)) as archive:
                    infos = archive.infolist()
                tiles = [i for i in infos if i.filename.startswith("tiles/")]
                members = {
                    "archive_bytes": len(outcome.pack),
                    "profile_json_bytes": sum(i.file_size for i in infos if i.filename == "profile.json"),
                    "profile_json_stored": sum(i.compress_size for i in infos if i.filename == "profile.json"),
                    "mask_bytes": sum(i.file_size for i in infos if i.filename == "mask.bin"),
                    "mask_stored": sum(i.compress_size for i in infos if i.filename == "mask.bin"),
                    "tiles_count": len(tiles),
                    "tiles_bytes": sum(i.compress_size for i in tiles),
                }
            summary = outcome.summary or {}
            emit("pages", {
                "t0": started, "t1": time.time(), "version": version_sha256[:12], "page": page_index + 1, "status": outcome.status,
                "reason": outcome.reason, "thread_cpu_s": round(time.thread_time() - cpu0, 3),
                "preview_bytes": len(outcome.preview or b""), "thumbnail_bytes": len(outcome.thumbnail or b""), **members,
                "width_pt": summary.get("width_pt"), "height_pt": summary.get("height_pt"), "rotation": summary.get("rotation"),
                "raster": numbers_only(summary.get("raster")), "counts": numbers_only(summary.get("counts")),
                "scan": summary.get("scan"), "text_layer": summary.get("text_layer"),
                "failure": numbers_only(summary.get("failure")) or summary.get("failure"),
            })
            return outcome

        builder_module.profile_page = profile_page

    try:
        from auditmanager.comparison.engine import service as engine_service
    except ImportError:  # pragma: no cover
        engine_service = None
    if engine_service is not None:
        original_compute = engine_service._compute

        def describe(page: Any) -> dict[str, Any]:
            return {
                "id": page.row.page_profile_id, "version": page.row.version_uid, "page": page.row.page_number,
                "width_pt": round(page.width_pt, 1), "height_pt": round(page.height_pt, 1),
                "raster": list(page.raster) if page.raster else None, "words": len(page.words), "lines": len(page.lines),
                "annotations": len(page.annotations), "scan": page.scan, "text_layer": page.has_text_layer,
            }

        def _compute(session_factory: Any, blob_store: Any, a: Any, b: Any, link_reasons: Any, part: Any, runner: Any,
                     child_limits: Any, work_dir: Any) -> Any:
            _ctx.value = {"stage": "pair", "a": a.row.page_profile_id, "b": b.row.page_profile_id}
            started, cpu0 = time.time(), time.thread_time()
            try:
                computed = original_compute(session_factory, blob_store, a, b, link_reasons, part, runner, child_limits, work_dir)
            except BaseException as failure:
                emit("pairs", {"t0": started, "t1": time.time(), "a": describe(a), "b": describe(b), "raised": type(failure).__name__})
                raise
            finally:
                _ctx.value = None
            outcome = computed.outcome
            emit("pairs", {
                "t0": started, "t1": time.time(), "a": describe(a), "b": describe(b), "end": computed.end,
                "status": outcome["status"], "reasons": [r for r in outcome["reasons"] if isinstance(r, str) and len(r) <= 64],
                "differences": len(outcome["result"]["differences"]), "text_changes": len(outcome["result"]["text_changes"]),
                "mask_bytes": len(computed.mask) if computed.mask else 0, "thread_cpu_s": round(time.thread_time() - cpu0, 3),
                "link_reasons": list(link_reasons), "part": part,
            })
            return computed

        engine_service._compute = _compute

    try:
        from auditmanager.comparison.work.runner import ComparisonWorkRunner
    except ImportError:  # pragma: no cover
        ComparisonWorkRunner = None  # type: ignore[assignment]
    if ComparisonWorkRunner is not None:
        original_execute = ComparisonWorkRunner.execute

        def execute(self: Any, item: Any) -> Any:
            reset_hwm()
            before = proc_status()
            t0, c0, wall0 = time.time(), os.times(), time.perf_counter()
            state: Any = None
            try:
                state = original_execute(self, item)
                return state
            finally:
                c1, after = os.times(), proc_status()
                payload = {k: v for k, v in (item.payload or {}).items() if k in ("sheet_pair_id", "version_uid", "document_uid", "series_id", "retry_failed")}
                emit("items", {
                    "t0": t0, "t1": time.time(), "kind": item.kind, "work_id": item.work_id, "attempt_no": item.attempt_no,
                    "payload": payload, "state": state, "wall_s": round(time.perf_counter() - wall0, 3),
                    "cpu_user_s": round(c1.user - c0.user, 3), "cpu_sys_s": round(c1.system - c0.system, 3),
                    "child_user_s": round(c1.children_user - c0.children_user, 3), "child_sys_s": round(c1.children_system - c0.children_system, 3),
                    "rss_before_kib": before.get("vm_rss_kib"), "hwm_kib": after.get("vm_hwm_kib"), "rss_after_kib": after.get("vm_rss_kib"),
                    "vm_peak_kib": after.get("vm_peak_kib"), "load1": loadavg()[0],
                })

        ComparisonWorkRunner.execute = execute  # type: ignore[method-assign]


def install_source_role_shim() -> None:
    """**Shim S-1, a finding of this run and not a product behaviour.** ``comparison/profile/source.py::load_source_version``
    reads the manifest entry of role ``source.document`` only, while the plain-PDF upload (``CMP-INGEST-01``) writes the distinct
    role ``comparison.source_pdf`` (so that a run refuses the version, ADR-0025 decision 11): a version admitted through the
    product's upload is therefore unreadable by the page-profile builder, the engine and the tile path
    (``page_profile_source_unreadable``). The suites of the lanes seed ``source.document`` and never met it. This wrapper widens
    that one condition (it is the product's function with ``item.role in (source.document, comparison.source_pdf)``), in the
    processes this tool starts only, so that the stages behind the defect can be measured. Without ``--shim`` the chain runs as
    shipped and stops at the profiles with the typed reason."""
    from auditmanager.comparison.engine import service as engine_service
    from auditmanager.comparison.profile import builder, reader
    from auditmanager.comparison.profile import source as source_module
    from auditmanager.documents.public import MANIFEST_ROLE_COMPARISON_PDF, MANIFEST_ROLE_SOURCE_DOCUMENT, DocumentRepository
    from auditmanager.shared.errors import DomainError, ErrorCode
    from auditmanager.shared.identity import VersionUid

    def load_source_version(session: Any, version_uid: str) -> Any:
        record = DocumentRepository().get_version(session, VersionUid(version_uid))
        entry = next((item for item in record.manifest if item.role in (MANIFEST_ROLE_SOURCE_DOCUMENT, MANIFEST_ROLE_COMPARISON_PDF)), None)
        if entry is None or entry.media_type != "application/pdf":
            raise DomainError(ErrorCode.ANALYSIS_INPUT_INVALID, message="the version has no source document the page profile can read",
                              stage_id="comparison_page_profile", reason="source_unreadable")
        return source_module.SourceVersion(
            version_uid=str(record.version_uid), project_uid=str(record.project_uid), page_count=int(record.page_count),
            sha256=entry.sha256, size_bytes=int(entry.size_bytes), blob_id=str(entry.blob_id))

    for module in (source_module, builder, reader, engine_service):
        module.load_source_version = load_source_version


def cmd_worker(_args: argparse.Namespace) -> int:
    records = Path(os.environ["CMP_MEASURE_RECORDS"])
    install_recording(records, "worker")
    if os.environ.get("CMP_MEASURE_SHIM") == "source_role":
        install_source_role_shim()
    start = proc_status()
    with open(records / "worker_start.json", "w", encoding="ascii") as sink:
        json.dump({"t": time.time(), **start}, sink)
    from auditmanager.workers.__main__ import main as worker_main

    return worker_main(["serve"])


# ---------------------------------------------------------------------------------------------------------------------
# the environment, the account, the application
# ---------------------------------------------------------------------------------------------------------------------


def load_dotenv() -> dict[str, str]:
    values: dict[str, str] = {}
    path = Path.cwd() / ".env"
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        name, separator, value = line.partition("=")
        if separator and name.strip():
            values[name.strip()] = value.strip().strip("\"'")
    return values


def application_environment(dotenv: dict[str, str], role: str) -> dict[str, str]:
    env = {**os.environ, **{k: v for k, v in dotenv.items() if k in _NAMES}}
    env.update({
        "EXECUTION_ROLE": role,
        "AUDITMANAGER_COMPARISON_MODULES": "versions",
        "AUDITMANAGER_LEGACY_PROMPTS_REPO": "/nonexistent",
        "PYTHONPATH": str(ROOT / "src"),
        "PYTHONUNBUFFERED": "1",
    })
    if role == "worker":
        env.pop("AUDITMANAGER_API_TOKEN", None)  # the worker holds the API's environment without that secret
    else:
        env["AUDITMANAGER_API_TOKEN"] = SECRET
    return env


def provision_account(session_factory: Any) -> tuple[str, str]:
    """The complete expert account of this measurement (created when absent) and a signed credential for it."""
    from auditmanager.access.accounts import AccountRepository
    from auditmanager.access.repository import UserRepository
    from auditmanager.api.security import API_TOKEN_VARIABLE, Subject, build_signer

    users = UserRepository()
    login = f"{LOGIN_LABEL}@suite.invalid"
    with session_factory() as session:
        record = users.find_by_login(session, login)
        if record is None:
            created = users.create_user(session, login, "comparison-chain-measure-password")
            accounts = AccountRepository()
            accounts.complete_profile(session, user_uid=str(created.user_uid), email=None, last_name="Измерение", first_name="Цепочки")
            accounts.grant_role(session, user_uid=str(created.user_uid), role="expert", granted_by=None)
            record = users.find_by_login(session, login)
            session.commit()
        signer = build_signer({API_TOKEN_VARIABLE: SECRET})
        token = signer.issue(
            Subject(user_uid=str(record.user_uid), login=record.login, token_epoch=record.token_epoch, display_label=record.display_label),
            is_default_credential=False,
        ).token
        return str(record.user_uid), token


class Api:
    """HTTP into the composed application of this process; every call is timed and kept as a record of numbers."""

    def __init__(self, client: Any, token: str, calls_path: Path) -> None:
        self.client, self.token, self.calls_path = client, token, calls_path
        self.counter = 0

    def call(self, method: str, path: str, *, expect: int | tuple[int, ...], label: str, key: bool = False, **kwargs: Any) -> Any:
        self.counter += 1
        headers = {"Authorization": f"Bearer {self.token}"}
        if key:
            headers["Idempotency-Key"] = f"chain-{self.counter}-{hashlib.sha1(label.encode()).hexdigest()[:12]}"
        if "content" in kwargs:
            headers["content-type"] = "application/octet-stream"
        expected = (expect,) if isinstance(expect, int) else expect
        started, wall0 = time.time(), time.perf_counter()
        response = self.client.request(method, path, headers=headers, **kwargs)
        elapsed = time.perf_counter() - wall0
        body: Any = None
        content_type = response.headers.get("content-type", "")
        if content_type.startswith("application/json"):
            body = response.json()
        record = {
            "label": label, "method": method, "path_kind": path.split("?")[0].rsplit("/", 1)[-1] if "/" in path else path,
            "status": response.status_code, "t0": started, "wall_s": round(elapsed, 3), "bytes_out": len(response.content),
            "load1": loadavg()[0], "api_rss_kib": proc_status().get("vm_rss_kib"), "api_hwm_kib": proc_status().get("vm_hwm_kib"),
        }
        if response.status_code not in expected and isinstance(body, dict):
            record["error"] = {k: body.get(k) for k in ("error_code",)} | {"details": numbers_only(body.get("details")) or body.get("details")}
        with open(self.calls_path, "a", encoding="ascii") as sink:
            sink.write(json.dumps(record, ensure_ascii=True, separators=(",", ":")) + "\n")
        if response.status_code not in expected:
            raise ChainStop(f"{label}: HTTP {response.status_code} {json.dumps(record.get('error'), ensure_ascii=True)}")
        return body if body is not None else response.content


class ChainStop(RuntimeError):
    """A stage cannot go on; the typed reason is in the message and in ``outcome.json`` (a FIX item, never a patch)."""


# ---------------------------------------------------------------------------------------------------------------------
# the run
# ---------------------------------------------------------------------------------------------------------------------


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def host_facts() -> dict[str, Any]:
    def run(*cmd: str) -> str:
        return subprocess.run(cmd, capture_output=True, text=True, check=False).stdout.strip()

    return {
        "at": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "uptime": run("uptime"), "free_m": run("free", "-m"), "nproc": run("nproc"),
        "df": run("df", "-h", "/"), "uname": run("uname", "-r"), "loadavg": loadavg(),
        "cpu_model": next((line.split(":", 1)[1].strip() for line in open("/proc/cpuinfo", encoding="utf-8") if line.startswith("model name")), "?"),
    }


def tree_facts() -> dict[str, Any]:
    def run(*cmd: str) -> str:
        return subprocess.run(cmd, capture_output=True, text=True, check=False, cwd=ROOT).stdout.strip()

    import importlib.metadata as md

    libs = {}
    for name in ("numpy", "opencv-python-headless", "pypdfium2", "pdfplumber", "pypdf", "Pillow", "psycopg", "SQLAlchemy"):
        try:
            libs[name] = md.version(name)
        except md.PackageNotFoundError:
            libs[name] = None
    return {"commit": run("git", "rev-parse", "HEAD"), "status": run("git", "status", "--short"), "python": sys.version.split()[0], "libs": libs}


class Run:
    def __init__(self, args: argparse.Namespace) -> None:
        self.args = args
        self.results = Path(args.results)
        self.records = self.results / "records"
        self.stages: list[dict[str, Any]] = []
        self.outcome: dict[str, Any] = {"stopped": None, "stages": {}}
        self.dotenv = load_dotenv()
        self.worker: subprocess.Popen[bytes] | None = None
        self.sampler: Sampler | None = None

    # -- bookkeeping -------------------------------------------------------------------------------------------------

    def snapshot(self) -> dict[str, Any]:
        worker = self.worker.pid if self.worker is not None and self.worker.poll() is None else None
        snap: dict[str, Any] = {"t": time.time(), "load": loadavg(), "free_bytes": _free_bytes(str(ROOT)),
                                "avail_kib": meminfo().get("MemAvailable"), "api": proc_status(), "api_ticks": proc_ticks()}
        if worker is not None:
            snap["worker"] = proc_status(worker)
            snap["worker_ticks"] = proc_ticks(worker)
        query = getattr(self, "query", None)
        if query is not None:
            snap["db_bytes"] = int(query("SELECT pg_database_size(current_database())")[0][0])
            snap["blob_bytes"] = int(query("SELECT coalesce(sum(size_bytes), 0) FROM blob")[0][0])
            snap["blob_rows"] = int(query("SELECT count(*) FROM blob")[0][0])
        return snap

    def stage_begin(self, name: str) -> None:
        self.current = {"name": name, "begin": self.snapshot()}
        print(f"== stage {name} begins", flush=True)

    def stage_end(self, name: str, **more: Any) -> None:
        end = self.snapshot()
        entry = {**self.current, "end": end, "wall_s": round(end["t"] - self.current["begin"]["t"], 3), **more}
        self.stages.append(entry)
        self.write_json("stages.json", self.stages)
        print(f"== stage {name} ends in {entry['wall_s']} s (load {end['load'][0]})", flush=True)

    def write_json(self, name: str, value: Any) -> None:
        with open(self.results / name, "w", encoding="ascii") as sink:
            json.dump(value, sink, ensure_ascii=True, indent=1, default=str)

    def check_disk(self) -> None:
        free = _free_bytes(str(ROOT))
        if free < STOP_FREE_BYTES:
            raise ChainStop(f"STOP: under 1.5 GiB free ({free // MIB} MiB)")

    def worker_alive(self) -> None:
        if self.worker is None or self.worker.poll() is not None:
            raise ChainStop("the worker is not running")
        if self.sampler is not None and self.sampler.tripped:
            raise ChainStop(f"the guard ended the worker: {self.sampler.tripped}")

    def poll(self, what: str, done: Any, timeout_s: float, every: float = 1.0) -> Any:
        deadline = time.time() + timeout_s
        last = time.time()
        while True:
            self.worker_alive()
            self.check_disk()
            value = done()
            if value:
                return value
            if time.time() > deadline:
                raise ChainStop(f"timeout waiting for {what} after {timeout_s:.0f} s")
            if time.time() - last > 60:
                last = time.time()
                print(f"   ... waiting for {what} (load {loadavg()[0]}, worker tree {self.sampler.peak_tree_kib // KIB if self.sampler else 0} MiB peak)", flush=True)
            time.sleep(every)

    # -- the chain ---------------------------------------------------------------------------------------------------

    def execute(self) -> int:
        from sqlalchemy import create_engine, text
        from starlette.testclient import TestClient

        from auditmanager.api.app import create_app, create_asgi_app
        from auditmanager.shared.db import create_database_engine, create_session_factory
        from auditmanager.shared.db.config import DatabaseSettings, parse_database_url

        args = self.args
        names = [n.strip() for n in args.files.split(",") if n.strip()]
        paths = [Path(args.set) / n for n in names]
        self.results.mkdir(parents=True, exist_ok=True)
        self.records.mkdir(parents=True, exist_ok=True)
        for old in list(self.results.glob("*.jsonl")) + list(self.records.glob("*.jsonl")):
            old.unlink()
        self.check_disk()

        digests = {p.name: sha256_of(p) for p in paths}
        sizes = {p.name: p.stat().st_size for p in paths}
        self.write_json("meta.json", {"label": args.label, "set": str(args.set), "files": names, "sha256": digests, "bytes": sizes,
                                      "host": host_facts(), "tree": tree_facts(), "argv": sys.argv, "interval": args.interval})
        print("host:", json.dumps(host_facts()["uptime"]), flush=True)

        env = application_environment(self.dotenv, "api")
        os.environ.update({k: env[k] for k in env if k in _NAMES or k.startswith("AUDITMANAGER_") or k == "EXECUTION_ROLE"})
        engine = create_engine(self.dotenv["DATABASE_URL"], pool_size=3, max_overflow=2)
        sessions = create_session_factory(create_database_engine(DatabaseSettings(url=parse_database_url(self.dotenv["DATABASE_URL"]))))
        self.engine, self.text = engine, text

        def query(sql: str, **params: Any) -> list[tuple[Any, ...]]:
            with engine.connect() as connection:
                return [tuple(row) for row in connection.execute(text(sql), params).all()]

        self.query = query
        user_uid, token = provision_account(sessions)
        application = create_app(environ=env)
        client = TestClient(create_asgi_app(environ=env, application=application), raise_server_exceptions=False)
        api = Api(client, token, self.results / "calls.jsonl")
        self.api = api

        # the sampler and the worker
        roots = {"api": os.getpid()}
        self.sampler = Sampler(self.results / "samples.jsonl", roots, args.interval)
        self.sampler.on_trip = self.trip
        self.sampler.start()
        worker_env = application_environment(self.dotenv, "worker") | {"CMP_MEASURE_RECORDS": str(self.records)}
        if args.shim:
            worker_env["CMP_MEASURE_SHIM"] = "source_role"
        self.outcome["shim"] = "source_role" if args.shim else None
        log = open(self.results / "worker.log", "wb")
        self.worker = subprocess.Popen(
            [sys.executable, str(Path(__file__).resolve()), "worker"], env=worker_env, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT,
        )
        roots["worker"] = self.worker.pid
        print(f"worker pid {self.worker.pid}", flush=True)
        time.sleep(4.0)
        self.worker_alive()
        self.write_json("worker_ready.json", {"pid": self.worker.pid, "status": proc_status(self.worker.pid), "t": time.time()})

        try:
            project = api.call("POST", "/projects", json={"name": "Измерение цепочки сравнения"}, expect=201, label="create_project", key=True)
            project_uid = project["project_uid"]
            self.ids = {"project_uid": project_uid, "user_uid": user_uid, "login": f"{LOGIN_LABEL}@suite.invalid"}
            self.write_json("ids.json", self.ids)
            self.stage_admission(api, paths, digests, sizes, query)
            self.stage_profiles(api, query)
            self.stage_matrix(api, query)
            self.stage_series(api, query)
        except ChainStop as stop:
            self.outcome["stopped"] = str(stop)
            print(f"STOPPED: {stop}", flush=True)
        finally:
            self.finish(query)
        return 0 if self.outcome["stopped"] is None else 3

    def trip(self, why: str) -> None:
        print(f"GUARD: {why}: ending the worker by its PID", flush=True)
        if self.worker is not None and self.worker.poll() is None:
            os.kill(self.worker.pid, signal.SIGTERM)

    # -- stage 0: admission ------------------------------------------------------------------------------------------

    def stage_admission(self, api: Api, paths: list[Path], digests: dict[str, str], sizes: dict[str, int], query: Any) -> None:
        self.stage_begin("admission")
        project_uid = self.ids["project_uid"]
        declared = [{"display_name": p.name, "size_bytes": sizes[p.name], "sha256": digests[p.name]} for p in paths]
        created = api.call("POST", f"/projects/{project_uid}/comparison-uploads", json={"files": declared, "compare_after_preparation": False},
                           expect=201, label="create_upload", key=True)
        upload_id, part_size = created["upload_id"], int(created["part_size_bytes"])
        ids = {item["display_name"]: item["file_id"] for item in created["files"]}
        self.ids["upload_id"] = upload_id
        for index, path in enumerate(paths):
            data = path.read_bytes()
            number = 0
            for offset in range(0, len(data), part_size):
                number += 1
                api.call("PUT", f"/comparison-uploads/{upload_id}/files/{ids[path.name]}/parts?part_number={number}",
                         content=data[offset : offset + part_size], expect=200, label=f"part_{path.name}_{number}", key=True)
            del data
            done = api.call("POST", f"/comparison-uploads/{upload_id}/files/{ids[path.name]}/completion", expect=200,
                            label=f"completion_{path.name}", key=True)
            self.outcome.setdefault("files", {})[path.name] = {"state": done.get("state"), "failure_reason": done.get("failure_reason")}
            if done.get("state") != "verified":
                raise ChainStop(f"completion of {path.name} ended {done.get('state')}, reason {done.get('failure_reason')}")
        upload = api.call("GET", f"/comparison-uploads/{upload_id}", expect=200, label="get_upload")
        self.outcome["upload_state_after_files"] = upload["state"]
        proposal = api.call("GET", f"/comparison-uploads/{upload_id}/proposal", expect=200, label="get_proposal")
        sets = proposal["sets"]
        names_by_file = {v: k for k, v in ids.items()}
        intended_names = [p.name for p in paths]
        detail = []
        for item in sets:
            ordered = sorted(item["files"], key=lambda f: f["position"])
            designation = item.get("designation")
            detail.append({
                "set_id": item["set_id"], "state": item["state"], "files": [names_by_file.get(f["file_id"], "?") for f in ordered],
                "warnings": [w if isinstance(w, str) else w.get("code") for w in (item.get("warnings") or [])],
                "designation_present": bool(designation), "designation_sha256_8": hashlib.sha256(designation.encode()).hexdigest()[:8] if designation else None,
                "stage_proposed": item.get("project_stage"), "section_proposed": item.get("section_code"),
                "labels_present": sum(1 for f in ordered if f.get("version_label")),
                "existing_document_offered": bool(item.get("existing_document_uid")),
            })
        self.outcome["proposal"] = {"sets": len(sets), "detail": detail}
        # one set is confirmed as it is; several (the stamps of the files disagree) are confirmed one after another, each later one
        # joining the document the first made (``existing_document_uid``), and the order of the versions is then confirmed as
        # an expert's act: what a person does when the proposal is not one set
        ordered_sets = sorted(zip(sets, detail), key=lambda pair: min(intended_names.index(n) for n in pair[1]["files"] if n in intended_names))
        first_set, first_detail = ordered_sets[0]
        confirmed = api.call("POST", f"/comparison-uploads/{upload_id}/sets/{first_set['set_id']}/confirmation",
                             json={"files": [{"file_id": ids[n]} for n in first_detail["files"]]}, expect=200, label="confirm_set_1", key=True)
        self.confirmed_at = time.time()
        document_uid = confirmed.get("document_uid")
        if not document_uid:
            raise ChainStop(f"the confirmation made no document: set state {confirmed.get('state')}, {confirmed.get('failure_reason')}")
        self.ids["document_uid"] = document_uid
        self.write_json("ids.json", self.ids)
        self.stage_end("admission", upload_id=upload_id, confirmed_at=self.confirmed_at)
        # the first confirmation released the first set to the worker: the page-profile stage begins here, and the few small
        # requests that remain (the other sets, the order) are made inside it
        self.stage_begin("page_profiles")
        for number, (extra, extra_detail) in enumerate(ordered_sets[1:], start=2):
            joined = api.call("POST", f"/comparison-uploads/{upload_id}/sets/{extra['set_id']}/confirmation",
                              json={"files": [{"file_id": ids[n]} for n in extra_detail["files"]], "existing_document_uid": document_uid},
                              expect=200, label=f"confirm_set_{number}", key=True)
            if joined.get("document_uid") != document_uid:
                raise ChainStop(f"set {number} did not join the document: state {joined.get('state')}, {joined.get('failure_reason')}")
        orders = api.call("GET", f"/projects/{project_uid}/documents/{document_uid}/comparison-version-orders", expect=200, label="list_orders")
        rows = query("SELECT version_uid, version_ordinal, source_filename, sha256, page_count, byte_size, upload_kind FROM document_version "
                     "WHERE document_uid = :d ORDER BY version_ordinal", d=document_uid)
        names_by_version = {r[0]: r[2] for r in rows}
        version_by_name = {r[2]: r[0] for r in rows}
        self.versions = [r[0] for r in rows]
        self.outcome["versions"] = dict(names_by_version)
        self.pages_total = sum(int(r[4]) for r in rows)
        latest = orders["items"][0] if orders.get("items") else None
        order_names = [names_by_version[v] for v in latest["version_uids"]] if latest else None
        record = {
            "revisions_before": len(orders.get("items") or []), "revision_no": latest and latest["revision_no"], "source": latest and latest["source"],
            "names": order_names, "equals_intended": order_names == intended_names, "document_ordinals": [r[2] for r in rows],
            "pages_per_version": {r[2]: int(r[4]) for r in rows}, "upload_kind": sorted({r[6] for r in rows}), "bytes_per_version": {r[2]: int(r[5]) for r in rows},
        }
        self.outcome["version_order"] = record
        if order_names != intended_names:
            appended = api.call("POST", f"/projects/{project_uid}/documents/{document_uid}/comparison-version-orders",
                                json={"version_uids": [version_by_name[n] for n in intended_names], "base_revision_no": latest["revision_no"] if latest else 0},
                                expect=(200, 201), label="append_order", key=True)
            record["appended"] = {"revision_no": appended.get("revision_no"), "source": appended.get("source")}
            orders = api.call("GET", f"/projects/{project_uid}/documents/{document_uid}/comparison-version-orders", expect=200, label="list_orders_after")
            latest = orders["items"][0]
            order_names = [names_by_version[v] for v in latest["version_uids"]]
            record.update(names_after=order_names, equals_intended_after=order_names == intended_names, revision_no_after=latest["revision_no"], source_after=latest["source"])
        if (record.get("names_after") or order_names) != intended_names:
            raise ChainStop(f"the version order {record.get('names_after') or order_names} is not the file order")

    # -- stage 1: page profiles --------------------------------------------------------------------------------------

    def stage_profiles(self, api: Api, query: Any) -> None:
        project_uid = self.ids["project_uid"]

        def finished() -> Any:
            rows = query("SELECT kind, state, count(*) FROM comparison_work WHERE project_uid = :p AND kind = 'page_profile' GROUP BY kind, state", p=project_uid)
            if not rows:
                return False
            live = [r for r in rows if r[1] in ("queued", "running", "paused")]
            return not live and sum(r[2] for r in rows) >= len(self.versions)

        self.poll("the page_profile items", finished, 3600, every=1.0)
        counts = query("SELECT status, count(*) FROM comparison_page_profile WHERE version_uid = ANY(:v) GROUP BY status", v=self.versions)
        by_status = {r[0]: int(r[1]) for r in counts}
        work = query("SELECT state, count(*), max(attempt_count), max(failure_reason) FROM comparison_work WHERE project_uid = :p AND kind = 'page_profile' GROUP BY state", p=project_uid)
        self.outcome["profiles"] = {"pages_expected": self.pages_total, "by_status": by_status, "work": [list(map(str, r)) for r in work]}
        self.stage_end("page_profiles")
        if sum(by_status.values()) != self.pages_total:
            failed = [r for r in work if r[0] == "failed"]
            why = f"; {sum(int(r[1]) for r in failed)} page_profile items failed with {sorted({r[3] for r in failed})} after {max((int(r[2]) for r in failed), default=0)} attempts" if failed else ""
            raise ChainStop(f"{sum(by_status.values())} profiles for {self.pages_total} pages{why}")

    # -- stage 2: matrix ---------------------------------------------------------------------------------------------

    def stage_matrix(self, api: Api, query: Any) -> None:
        project_uid, document_uid = self.ids["project_uid"], self.ids["document_uid"]
        self.stage_begin("matrix")
        prepared = api.call("POST", f"/projects/{project_uid}/documents/{document_uid}/comparison-matrix/preparation", expect=(200, 202), label="prepare_matrix", key=True)
        self.outcome["matrix_prepare_state"] = prepared.get("state")
        box: dict[str, Any] = {}

        def ready() -> Any:
            matrix = api.call("GET", f"/projects/{project_uid}/documents/{document_uid}/comparison-matrix", expect=200, label="get_matrix_poll")
            box["matrix"] = matrix
            return matrix["state"] in ("ready", "failed", "stale")

        self.poll("the matrix", ready, 3600, every=1.0)
        matrix = box["matrix"]
        self.stage_end("matrix")
        self.outcome["matrix"] = self.matrix_summary(matrix)
        if matrix["state"] != "ready":
            raise ChainStop(f"the matrix is {matrix['state']} ({matrix.get('failure_reason')})")

    @staticmethod
    def matrix_summary(matrix: dict[str, Any]) -> dict[str, Any]:
        cells = defaultdict(int)
        flags = defaultdict(int)
        confidences = defaultdict(int)
        reasons = defaultdict(int)
        rows_by_width = defaultdict(int)
        for row in matrix.get("rows") or []:
            matched_cells = [c for c in row["cells"] if c["state"] == "matched"]
            rows_by_width[len(matched_cells)] += 1
            for cell in row["cells"]:
                cells[cell["state"]] += 1
                for flag in cell.get("flags") or []:
                    flags[flag] += 1
                if cell.get("confidence"):
                    confidences[cell["confidence"]] += 1
                if cell.get("reason"):
                    reasons[cell["reason"]] += 1
        return {
            "state": matrix["state"], "revision": matrix.get("revision"), "counts": matrix.get("counts"), "progress": matrix.get("progress"),
            "stale_reasons": matrix.get("stale_reasons"), "columns": [c["page_count"] for c in matrix.get("columns") or []],
            "unassigned_pages": len(matrix.get("unassigned_pages") or []), "cells_by_state": dict(cells), "cell_flags": dict(flags),
            "cell_confidence": dict(confidences), "cell_reasons": dict(reasons), "rows_by_matched_cells": dict(sorted(rows_by_width.items())),
            "orphaned_edits": len(matrix.get("orphaned_edit_ids") or []),
        }

    # -- stage 3: series ---------------------------------------------------------------------------------------------

    def stage_series(self, api: Api, query: Any) -> None:
        project_uid, document_uid = self.ids["project_uid"], self.ids["document_uid"]
        self.stage_begin("series")
        series = api.call("POST", f"/projects/{project_uid}/documents/{document_uid}/comparison-series", json={}, expect=201, label="start_series", key=True)
        series_id = series["series_id"]
        self.ids["series_id"] = series_id
        self.write_json("ids.json", self.ids)
        self.outcome["series_start"] = {"state": series["state"], "transitions_total": series["transitions_total"]}
        box: dict[str, Any] = {}

        def terminal() -> Any:
            current = api.call("GET", f"/comparison-series/{series_id}", expect=200, label="get_series_poll")
            box["series"] = current
            return current["state"] in ("completed", "failed", "cancelled")

        self.poll("the series", terminal, 7200, every=1.0)
        self.stage_end("series")
        series_final = api.call("GET", f"/comparison-series/{series_id}", expect=200, label="get_series")
        pairs = []
        for transition in series_final["transitions"]:
            cursor = None
            while True:
                path = f"/comparison-transitions/{transition['transition_id']}/sheet-pairs" + (f"?cursor={cursor}" if cursor else "")
                page = api.call("GET", path, expect=200, label="list_sheet_pairs")
                for pair in page["items"]:
                    pairs.append({"transition": transition["transition_id"], **self.pair_record(pair)})
                cursor = (page.get("page") or {}).get("next_cursor")
                if not cursor:
                    break
        self.outcome["series"] = {
            "state": series_final["state"], "failure_reason": series_final.get("failure_reason"), "stale_reasons": series_final.get("stale_reasons"),
            "transitions": [{
                "transition_id": t["transition_id"], "source_version_uid": t["source_version_uid"], "target_version_uid": t["target_version_uid"],
                "state": t["state"], "verdict": t.get("verdict"), "summary": t["summary"], "items_total": t["items_total"],
                "items_done": t["items_done"], "failure_reason": t.get("failure_reason"),
            } for t in series_final["transitions"]],
        }
        self.outcome["pairs"] = pairs
        if series_final["state"] != "completed":
            raise ChainStop(f"the series ended {series_final['state']} ({series_final.get('failure_reason')})")

    @staticmethod
    def pair_record(pair: dict[str, Any]) -> dict[str, Any]:
        def ref(side: Any) -> Any:
            if not side:
                return None
            page = side.get("page") or {}
            return {"version_uid": page.get("version_uid"), "page_number": page.get("page_number"), "page_profile_id": page.get("page_profile_id") or page.get("id"),
                    "scan": side.get("scan")}

        channels = pair.get("channels") or {}
        return {
            "sheet_pair_id": pair["sheet_pair_id"], "state": pair["state"], "status": pair.get("status"), "confidence": pair.get("confidence"),
            "flags": pair.get("flags"), "reasons": pair.get("reasons"), "failure_reason": pair.get("failure_reason"), "result_id": pair.get("result_id"),
            "a": ref(pair.get("page_a")), "b": ref(pair.get("page_b")), "ai_dependent": pair.get("ai_dependent"),
            "channels": {k: [v.get("state"), v.get("diffs")] for k, v in channels.items() if isinstance(v, dict)},
            "permit_state": (pair.get("permit") or {}).get("state"), "parts": numbers_only(pair.get("parts")),
        }

    # -- the end -----------------------------------------------------------------------------------------------------

    def finish(self, query: Any) -> None:
        stopped_worker = None
        try:
            if self.worker is not None and self.worker.poll() is None:
                final = proc_status(self.worker.pid)
                ticks = proc_ticks(self.worker.pid)
                stopped_worker = {"status": final, "ticks": ticks}
                os.kill(self.worker.pid, signal.SIGTERM)  # the worker this run started, by its PID
                try:
                    self.worker.wait(timeout=60)
                except subprocess.TimeoutExpired:
                    os.kill(self.worker.pid, signal.SIGKILL)
                    self.worker.wait(timeout=20)
        finally:
            if self.sampler is not None:
                self.sampler.stop()
        self.outcome["worker_at_stop"] = stopped_worker
        self.outcome["worker_exit_code"] = self.worker.returncode if self.worker is not None else None
        self.outcome["guard"] = self.sampler.tripped if self.sampler else None
        try:
            self.outcome["census"] = census(self.dotenv, query, self.ids)
        except Exception as failure:  # noqa: BLE001 - the census must not hide the run
            self.outcome["census_error"] = f"{type(failure).__name__}: {failure}"
        self.write_json("outcome.json", self.outcome)
        print("outcome written", flush=True)


# ---------------------------------------------------------------------------------------------------------------------
# the census: rows per table, bytes per kind
# ---------------------------------------------------------------------------------------------------------------------


def census(dotenv: dict[str, str], query: Any, ids: dict[str, Any]) -> dict[str, Any]:
    import boto3
    from botocore.client import Config

    result: dict[str, Any] = {}
    tables = [r[0] for r in query("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' AND table_type = 'BASE TABLE' ORDER BY 1")]
    rows = {}
    for table in tables:
        count = query(f'SELECT count(*) FROM "{table}"')[0][0]
        if count:
            size = query("SELECT pg_total_relation_size(CAST(:t AS regclass))", t=f'public."{table}"')[0][0]
            rows[table] = {"rows": int(count), "total_bytes": int(size)}
    result["tables"] = rows
    result["database_bytes"] = int(query("SELECT pg_database_size(current_database())")[0][0])
    result["jsonb_bytes"] = {
        "comparison_page_profile.profile": int(query("SELECT coalesce(sum(pg_column_size(profile)), 0) FROM comparison_page_profile")[0][0]),
        "comparison_sheet_pair_result.result": int(query("SELECT coalesce(sum(pg_column_size(result)), 0) FROM comparison_sheet_pair_result")[0][0]),
        "comparison_sheet_pair_result.channels": int(query("SELECT coalesce(sum(pg_column_size(channels)), 0) FROM comparison_sheet_pair_result")[0][0]),
        "comparison_matrix.rows": int(query("SELECT coalesce(sum(pg_column_size(rows)), 0) FROM comparison_matrix")[0][0]),
    }

    def sized(sql: str, **params: Any) -> dict[str, int]:
        row = query(sql, **params)[0]
        return {"blobs": int(row[0]), "bytes": int(row[1])}

    result["blobs"] = {
        "sources": sized("SELECT count(DISTINCT b.blob_id), coalesce(sum(DISTINCT b.size_bytes), 0) FROM blob b JOIN input_manifest_entry m ON m.blob_id = b.blob_id WHERE m.role LIKE 'comparison%'"),
        "sources_per_version_row": sized("SELECT count(*), coalesce(sum(m.size_bytes), 0) FROM input_manifest_entry m WHERE m.role LIKE 'comparison%'"),
        "previews": sized("SELECT count(b.blob_id), coalesce(sum(b.size_bytes), 0) FROM comparison_page_profile p JOIN blob b ON b.blob_id = p.preview_blob_id"),
        "thumbnails": sized("SELECT count(b.blob_id), coalesce(sum(b.size_bytes), 0) FROM comparison_page_profile p JOIN blob b ON b.blob_id = p.thumbnail_blob_id"),
        "archives": sized("SELECT count(b.blob_id), coalesce(sum(b.size_bytes), 0) FROM comparison_page_profile p JOIN blob b ON b.blob_id = p.profile_blob_id"),
        "masks": sized("SELECT count(b.blob_id), coalesce(sum(b.size_bytes), 0) FROM comparison_sheet_pair_result r JOIN blob b ON b.blob_id = r.mask_blob_id"),
        "all_blob_rows": sized("SELECT count(*), coalesce(sum(size_bytes), 0) FROM blob"),
        "by_state": {r[0]: [int(r[1]), int(r[2])] for r in query("SELECT state, count(*), coalesce(sum(size_bytes), 0) FROM blob GROUP BY state")},
    }
    result["pairs_without_mask_by_status"] = {r[0]: int(r[1]) for r in query("SELECT status, count(*) FROM comparison_sheet_pair_result WHERE mask_blob_id IS NULL GROUP BY status")}
    result["pairs_with_mask_by_status"] = {r[0]: int(r[1]) for r in query("SELECT status, count(*) FROM comparison_sheet_pair_result WHERE mask_blob_id IS NOT NULL GROUP BY status")}
    client = boto3.client("s3", endpoint_url=dotenv["S3_ENDPOINT_URL"], region_name=dotenv["S3_REGION"], aws_access_key_id=dotenv["S3_ACCESS_KEY_ID"],
                          aws_secret_access_key=dotenv["S3_SECRET_ACCESS_KEY"], config=Config(s3={"addressing_style": "path"}))
    total = count = 0
    prefixes: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    token = None
    while True:
        page = client.list_objects_v2(Bucket=dotenv["S3_BUCKET"], **({"ContinuationToken": token} if token else {}))
        for item in page.get("Contents", []):
            total += item["Size"]
            count += 1
            head = item["Key"].split("/", 1)[0]
            prefixes[head][0] += 1
            prefixes[head][1] += item["Size"]
        if not page.get("IsTruncated"):
            break
        token = page.get("NextContinuationToken")
    result["bucket"] = {"objects": count, "bytes": total, "by_prefix": {k: v for k, v in prefixes.items()}}
    volumes = {}
    for suffix in ("postgres-data", "s3-data"):
        name = f"{dotenv['FOUNDATION_INSTANCE']}-{suffix}"
        inspected = subprocess.run(["docker", "volume", "inspect", name, "--format", "{{.Mountpoint}}"], capture_output=True, text=True, check=False).stdout.strip()
        if inspected:
            used = subprocess.run(["du", "-sb", inspected], capture_output=True, text=True, check=False).stdout.split()
            volumes[name] = int(used[0]) if used else None
    result["volumes_bytes"] = volumes
    work = query("SELECT kind, state, count(*), max(attempt_count), coalesce(max(failure_reason), '') FROM comparison_work WHERE project_uid = :p GROUP BY kind, state ORDER BY 1, 2", p=ids["project_uid"])
    result["work_items"] = [{"kind": r[0], "state": r[1], "count": int(r[2]), "max_attempts_used": int(r[3]), "failure_reason": r[4]} for r in work]
    attempts = query("SELECT w.kind, a.state, count(*), coalesce(max(a.failure_reason), '') FROM comparison_work_attempt a JOIN comparison_work w ON w.comparison_work_id = a.comparison_work_id WHERE w.project_uid = :p GROUP BY 1, 2 ORDER BY 1, 2", p=ids["project_uid"])
    result["work_attempts"] = [{"kind": r[0], "state": r[1], "count": int(r[2]), "failure_reason": r[3]} for r in attempts]
    return result


def cmd_run(args: argparse.Namespace) -> int:
    return Run(args).execute()


# ---------------------------------------------------------------------------------------------------------------------
# tiles: the cost of single pair tiles through streamComparisonPairTile
# ---------------------------------------------------------------------------------------------------------------------

DEFAULT_LAYERS = "main,light_elements,color_change,line_style,service_zones"  # the viewer's five default layers


def tiles_per_level(width_px: int, height_px: int, level: int) -> tuple[int, int]:
    scale = 2 ** level
    return max(1, math.ceil(width_px / scale / 512)), max(1, math.ceil(height_px / scale / 512))


def pick_tiles(width_px: int, height_px: int, wanted: dict[int, int]) -> list[tuple[int, int, int]]:
    chosen: list[tuple[int, int, int]] = []
    for level, count in wanted.items():
        columns, rows = tiles_per_level(width_px, height_px, level)
        candidates = [(columns // 2, rows // 2), (0, 0), (columns - 1, rows - 1), (columns // 2 + 1, rows // 2), (columns // 2, rows // 2 + 1), (0, rows - 1), (columns - 1, 0)]
        seen: list[tuple[int, int]] = []
        for column, row in candidates:
            if 0 <= column < columns and 0 <= row < rows and (column, row) not in seen:
                seen.append((column, row))
        chosen.extend((level, c, r) for c, r in seen[:count])
    return chosen


def cmd_tiles(args: argparse.Namespace) -> int:
    results = Path(args.results)
    records = results / "records_tiles"
    records.mkdir(parents=True, exist_ok=True)
    for old in records.glob("*.jsonl"):
        old.unlink()
    out_path = results / "tiles.jsonl"
    out_path.write_text("", encoding="ascii")
    dotenv = load_dotenv()
    env = application_environment(dotenv, "api")
    os.environ.update({k: env[k] for k in env if k in _NAMES or k.startswith("AUDITMANAGER_") or k == "EXECUTION_ROLE"})
    ids = json.loads((results / "ids.json").read_text(encoding="ascii"))
    outcome = json.loads((results / "outcome.json").read_text(encoding="ascii"))

    started_import = time.perf_counter()
    from sqlalchemy import create_engine, text
    from starlette.testclient import TestClient

    from auditmanager.api.app import create_app, create_asgi_app
    from auditmanager.shared.db import create_database_engine, create_session_factory
    from auditmanager.shared.db.config import DatabaseSettings, parse_database_url

    import_rss = proc_status()
    install_recording(records, "api-tiles")
    if outcome.get("shim") == "source_role":
        install_source_role_shim()
    sessions = create_session_factory(create_database_engine(DatabaseSettings(url=parse_database_url(dotenv["DATABASE_URL"]))))
    _user, token = provision_account(sessions)
    application = create_app(environ=env)
    client = TestClient(create_asgi_app(environ=env, application=application), raise_server_exceptions=False)
    api = Api(client, token, results / "calls_tiles.jsonl")
    api.call("GET", "/system/version", expect=200, label="warm_version")
    baseline = {"t": time.time(), **proc_status(), "import_s": round(time.perf_counter() - started_import, 3), "import_rss_kib": import_rss.get("vm_rss_kib"), "load1": loadavg()[0]}
    sampler = Sampler(results / "samples_tiles.jsonl", {"api": os.getpid()}, args.interval)
    sampler.start()

    # the two pairs: the largest canvas among the compared pairs with a mask, and the median one
    engine = create_engine(dotenv["DATABASE_URL"])
    with engine.connect() as connection:
        rows = connection.execute(text(
            "SELECT sp.comparison_sheet_pair_id, r.status, (r.result->'canvas'->>'width_pt')::float, (r.result->'canvas'->>'height_pt')::float, "
            "(r.result->'how_compared'->>'dpi')::int, r.mask_blob_id, sp.page_a_profile_id, sp.page_b_profile_id "
            "FROM comparison_sheet_pair sp JOIN comparison_sheet_pair_result r ON r.comparison_sheet_pair_result_id = sp.result_id "
            "WHERE r.mask_blob_id IS NOT NULL ORDER BY (r.result->'canvas'->>'width_pt')::float * (r.result->'canvas'->>'height_pt')::float DESC, sp.comparison_sheet_pair_id")).all()
    if len(rows) < 2:
        raise SystemExit("fewer than two compared pairs with a mask")
    picks = [("largest", rows[0]), ("median", rows[len(rows) // 2])]
    records_out: list[dict[str, Any]] = []
    plan: list[dict[str, Any]] = []
    wanted = {0: 3, 1: 3, 2: 2, 3: 2}
    for name, row in picks:
        pair_id, status, width_pt, height_pt, dpi, _mask, page_a, _page_b = row
        profile = api.call("GET", f"/page-profiles/{page_a}", expect=200, label=f"profile_{name}")
        width_px, height_px = int(profile["raster_width_px"]), int(profile["raster_height_px"])
        chosen = pick_tiles(width_px, height_px, wanted)
        plan.append({"pair": name, "sheet_pair_id": pair_id, "status": status, "width_mm": round(width_pt / 72 * 25.4), "height_mm": round(height_pt / 72 * 25.4),
                     "dpi": dpi, "raster_px": [width_px, height_px], "megapixels": round(width_px * height_px / 1e6, 2), "tiles": len(chosen)})
        for level, column, row_index in chosen:
            path = f"/comparison-sheet-pairs/{pair_id}/tile?mode=overlay&level={level}&column={column}&row={row_index}&layers={DEFAULT_LAYERS}"
            records_out.append({"pair": name, "sheet_pair_id": pair_id, "level": level, "column": column, "row": row_index, "path": path, "cold": True})
    # top up to the requested number from the largest pair's level 0 and 1 grids when a grid was too small
    while len(records_out) < args.tiles:
        pair_id = picks[0][1][0]
        width_px, height_px = plan[0]["raster_px"]
        for level in (0, 1):
            columns, rows_n = tiles_per_level(width_px, height_px, level)
            for c in range(columns):
                for r in range(rows_n):
                    p = f"/comparison-sheet-pairs/{pair_id}/tile?mode=overlay&level={level}&column={c}&row={r}&layers={DEFAULT_LAYERS}"
                    if all(x["path"] != p for x in records_out) and len(records_out) < args.tiles:
                        records_out.append({"pair": "largest", "sheet_pair_id": pair_id, "level": level, "column": c, "row": r, "path": p, "cold": True})
    records_out = records_out[: args.tiles]
    done: list[dict[str, Any]] = []
    for item in records_out + [dict(x, cold=False) for x in (records_out[0], records_out[-1])]:
        before = proc_status()
        started = time.time()
        wall0 = time.perf_counter()
        response = client.get(item["path"], headers={"Authorization": f"Bearer {token}"})
        elapsed = time.perf_counter() - wall0
        after = proc_status()
        item = {k: v for k, v in item.items() if k != "path"} | {
            "http": response.status_code, "wall_ms": round(elapsed * 1000, 1), "bytes": len(response.content), "t0": started,
            "rss_before_kib": before.get("vm_rss_kib"), "rss_after_kib": after.get("vm_rss_kib"), "hwm_after_kib": after.get("vm_hwm_kib"),
            "peak_after_kib": after.get("vm_peak_kib"), "load1": loadavg()[0], "cache_control": response.headers.get("cache-control"),
        }
        done.append(item)
        with open(out_path, "a", encoding="ascii") as sink:
            sink.write(json.dumps(item, separators=(",", ":")) + "\n")
    sampler.stop()
    summary = {"baseline": baseline, "plan": plan, "final": proc_status(), "requests": len(done), "cold": sum(1 for d in done if d["cold"]),
               "series_id": ids.get("series_id"), "pairs_with_mask": len(rows)}
    (results / "tiles_summary.json").write_text(json.dumps(summary, indent=1), encoding="ascii")
    print(json.dumps(summary))
    for item in done:
        print(json.dumps({k: item[k] for k in ("pair", "level", "column", "row", "cold", "http", "wall_ms", "bytes", "rss_after_kib")}))
    del outcome
    return 0


# ---------------------------------------------------------------------------------------------------------------------
# report: tables from the records
# ---------------------------------------------------------------------------------------------------------------------


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="ascii").splitlines() if line.strip()]


def mib(kib: float | int | None) -> str:
    return "-" if kib is None else f"{kib / KIB:.1f}"


def mb(count: float | int | None) -> str:
    return "-" if count is None else f"{count / MIB:.2f}"


def size_class(width_pt: float, height_pt: float) -> str:
    """The displayed page size in mm, long side first, to the nearest mm (the way the earlier report names it)."""
    long_side, short_side = sorted((width_pt, height_pt), reverse=True)
    return f"{round(long_side / 72 * 25.4)}x{round(short_side / 72 * 25.4)}"


def percentile(values: list[float], share: float) -> float:
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, int(share * len(ordered)))] if ordered else 0.0


def cmd_report(args: argparse.Namespace) -> int:
    results = Path(args.results)
    stages = json.loads((results / "stages.json").read_text(encoding="ascii"))
    samples = load_jsonl(results / "samples.jsonl")
    children = load_jsonl(results / "records" / "children.jsonl")
    items = load_jsonl(results / "records" / "items.jsonl")
    pages = load_jsonl(results / "records" / "pages.jsonl")
    pairs = load_jsonl(results / "records" / "pairs.jsonl")
    outcome = json.loads((results / "outcome.json").read_text(encoding="ascii"))
    meta = json.loads((results / "meta.json").read_text(encoding="ascii"))
    versions: dict[str, str] = outcome.get("versions", {})

    print(f"## run `{meta['label']}` tree {meta['tree']['commit'][:8]} at {meta['host']['at']}; host before: {meta['host']['uptime'].strip()}")
    print(f"stopped: {outcome.get('stopped')}; guard: {outcome.get('guard')}; shim: {outcome.get('shim')}; worker exit {outcome.get('worker_exit_code')}\n")

    print("## stages")
    print("| stage | wall s | load1 start/end | API cpu s | worker cpu s (self) | worker cpu s (children waited) | worker VmHWM MiB (item max) | worker VmPeak MiB | worker RSS max MiB (samples) | worker+children RSS max MiB | API VmHWM MiB at end | blobs added MiB | database added MiB |")
    print("| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |")
    for stage in stages:
        t0, t1 = stage["begin"]["t"], stage["end"]["t"]
        inside = [s for s in samples if t0 <= s["t"] <= t1 and "worker" in s]
        worker_rss = max((s["worker"]["rss"] for s in inside), default=None)
        tree = max((s["worker"]["rss"] + sum(k[2] for k in s["worker"]["kids"]) for s in inside), default=None)
        item_hwm = max((i["hwm_kib"] or 0 for i in items if t0 <= i["t0"] <= t1), default=None)

        def dcpu(key: str, idx: tuple[int, ...]) -> float:
            a, b = stage["begin"].get(key), stage["end"].get(key)
            return sum(b[i] - a[i] for i in idx) / CLK_TCK if a and b else 0.0

        print(f"| {stage['name']} | {stage['wall_s']:.1f} | {stage['begin']['load'][0]}/{stage['end']['load'][0]} | {dcpu('api_ticks', (0, 1)):.1f} | "
              f"{dcpu('worker_ticks', (0, 1)):.1f} | {dcpu('worker_ticks', (2, 3)):.1f} | {mib(item_hwm)} | {mib(stage['end'].get('worker', {}).get('vm_peak_kib'))} | "
              f"{mib(worker_rss)} | {mib(tree)} | {mib(stage['end'].get('api', {}).get('vm_hwm_kib'))} | "
              f"{mb(stage['end'].get('blob_bytes', 0) - stage['begin'].get('blob_bytes', 0))} | {mb(stage['end'].get('db_bytes', 0) - stage['begin'].get('db_bytes', 0))} |")

    print("\n## API process: children seen by the sampler (admission reads the PDFs in two children each)")
    seen: dict[str, dict[str, Any]] = {}
    for sample in samples:
        for kid in (sample.get("api") or {}).get("kids", []):
            if kid[1] == "gone":
                continue
            entry = seen.setdefault(f"{kid[1]}:{kid[0]}", {"label": kid[1], "n": 0, "rss": 0, "hwm": 0, "peak": 0, "first": sample["t"], "last": sample["t"]})
            entry["n"] += 1
            entry["rss"], entry["hwm"], entry["peak"] = max(entry["rss"], kid[2]), max(entry["hwm"], kid[3]), max(entry["peak"], kid[4])
            entry["last"] = sample["t"]
    by_label: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for entry in seen.values():
        by_label[entry["label"]].append(entry)
    for label, group in sorted(by_label.items()):
        print(f"| {label} | processes {len(group)} | VmHWM max {mib(max(e['hwm'] for e in group))} | VmPeak max {mib(max(e['peak'] for e in group))} | seen up to {max(e['last'] - e['first'] for e in group):.1f} s |")
    api_status = [(s["name"], s["end"].get("api", {})) for s in stages]
    print("API process at each stage end: " + "; ".join(f"{n}: VmRSS {mib(a.get('vm_rss_kib'))} VmHWM {mib(a.get('vm_hwm_kib'))} VmPeak {mib(a.get('vm_peak_kib'))}" for n, a in api_status))

    print("\n## HTTP calls (admission): label, wall s, API VmHWM MiB")
    for call in load_jsonl(results / "calls.jsonl"):
        if call["label"].startswith(("create_", "part_", "completion_", "get_proposal", "confirm_", "list_orders", "append_", "prepare_", "start_", "get_series")) and not call["label"].endswith("poll"):
            print(f"| {call['label']} | {call['status']} | {call['wall_s']} | {mib(call['api_hwm_kib'])} | load {call['load1']} |")

    print("\n## worker work items by kind (count, wall sum/max s, cpu self sum s, cpu children sum s, worker VmHWM max MiB, VmPeak max MiB)")
    by_kind: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in items:
        by_kind[item["kind"]].append(item)
    for kind, group in sorted(by_kind.items()):
        print(f"| {kind} | {len(group)} | {sum(i['wall_s'] for i in group):.1f}/{max(i['wall_s'] for i in group):.1f} | {sum(i['cpu_user_s'] + i['cpu_sys_s'] for i in group):.1f} | "
              f"{sum(i['child_user_s'] + i['child_sys_s'] for i in group):.1f} | {mib(max(i['hwm_kib'] or 0 for i in group))} | {mib(max(i['vm_peak_kib'] or 0 for i in group))} |")

    print("\n## children by kind (count, wall sum/max s, cpu sum/max s, VmHWM max MiB, VmPeak max MiB, ended without a result)")
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for child in children:
        groups[child["kind"]].append(child)
    for kind, group in sorted(groups.items()):
        good = [c for c in group if "facts" in c]
        notok = [c for c in group if c.get("status") != "ok"]
        print(f"| {kind} | {len(group)} | {sum(c.get('wall_s', 0) for c in good):.1f}/{max((c.get('wall_s', 0) for c in good), default=0):.1f} | "
              f"{sum(c.get('cpu_s', 0) for c in good):.1f}/{max((c.get('cpu_s', 0) for c in good), default=0):.1f} | "
              f"{mib(max((c['facts'].get('vm_hwm_kib') or 0 for c in good), default=0))} | {mib(max((c['facts'].get('vm_peak_kib') or 0 for c in good), default=0))} | {len(notok)} |")

    # pages: attribute a page record to the version of the page_profile item that was running
    windows = [(i["t0"], i["t1"], versions.get(i["payload"].get("version_uid"), "?")) for i in items if i["kind"] == "page_profile"]

    def version_of(t: float) -> str:
        return next((name for a, b, name in windows if a <= t <= b), "?")

    page_children: dict[tuple[str, int, str], dict[str, Any]] = {}
    for child in children:
        ctx = child.get("ctx") or {}
        if ctx.get("stage") == "profile" and child["kind"] in ("render", "extract"):
            page_children[(version_of(child["t0"]), int(ctx["page"]), child["kind"])] = child
    rows = []
    for page in pages:
        name = version_of(page["t0"])
        render, extract = page_children.get((name, page["page"], "render")), page_children.get((name, page["page"], "extract"))
        rows.append((name, page, render, extract))
    print("\n## page profiles by size class (pages; render wall sum/max s; extract wall sum/max s; render VmHWM/VmPeak max MiB; extract VmHWM/VmPeak max MiB; archive+preview+thumbnail bytes sum/max MiB)")
    by_class: dict[str, list[Any]] = defaultdict(list)
    for row in rows:
        by_class[size_class(row[1]["width_pt"] or 0, row[1]["height_pt"] or 0)].append(row)

    def fact(child: dict[str, Any] | None, key: str) -> float:
        return float((child or {}).get("facts", {}).get(key) or 0)

    for name, group in sorted(by_class.items(), key=lambda kv: -int(kv[0].split("x")[0])):
        stored = [(r[1].get("archive_bytes") or 0) + r[1]["preview_bytes"] + r[1]["thumbnail_bytes"] for r in group]
        print(f"| {name} | {len(group)} | {sum((r[2] or {}).get('wall_s', 0) for r in group):.1f}/{max(((r[2] or {}).get('wall_s', 0) for r in group), default=0):.1f} | "
              f"{sum((r[3] or {}).get('wall_s', 0) for r in group):.1f}/{max(((r[3] or {}).get('wall_s', 0) for r in group), default=0):.1f} | "
              f"{mib(max(fact(r[2], 'vm_hwm_kib') for r in group))}/{mib(max(fact(r[2], 'vm_peak_kib') for r in group))} | "
              f"{mib(max(fact(r[3], 'vm_hwm_kib') for r in group))}/{mib(max(fact(r[3], 'vm_peak_kib') for r in group))} | {mb(sum(stored))}/{mb(max(stored))} |")
    print("\n## page profiles by version (pages, ready, render wall s, extract wall s, bytes archive/preview/thumbnail MiB, archive parts: profile.json/mask/tiles MiB, tiles count)")
    for name in sorted({r[0] for r in rows}):
        group = [r for r in rows if r[0] == name]
        print(f"| {name} | {len(group)} | {sum(1 for r in group if r[1]['status'] == 'ready')} | {sum((r[2] or {}).get('wall_s', 0) for r in group):.1f} | "
              f"{sum((r[3] or {}).get('wall_s', 0) for r in group):.1f} | {mb(sum(r[1].get('archive_bytes') or 0 for r in group))}/{mb(sum(r[1]['preview_bytes'] for r in group))}/{mb(sum(r[1]['thumbnail_bytes'] for r in group))} | "
              f"{mb(sum(r[1].get('profile_json_stored') or 0 for r in group))}/{mb(sum(r[1].get('mask_stored') or 0 for r in group))}/{mb(sum(r[1].get('tiles_bytes') or 0 for r in group))} | {sum(r[1].get('tiles_count') or 0 for r in group)} |")

    print("\n## worst pages")
    def worst(key: Any, count: int = 4) -> list[Any]:
        return sorted(rows, key=key, reverse=True)[:count]

    for title, key in (("by extraction VmPeak", lambda r: fact(r[3], "vm_peak_kib")), ("by render VmPeak", lambda r: fact(r[2], "vm_peak_kib")),
                       ("by page wall (render+extract)", lambda r: (r[2] or {}).get("wall_s", 0) + (r[3] or {}).get("wall_s", 0))):
        print(f"{title}")
        for name, page, render, extract in worst(key):
            counts = page.get("counts") or {}
            print(f"| {name} p{page['page']} | {size_class(page['width_pt'] or 0, page['height_pt'] or 0)} mm | raster {page.get('raster')} | lines {counts.get('lines')} drawn {counts.get('drawn_lines')} rects {counts.get('rects')} curves {counts.get('curves')} words {counts.get('words')} | "
                  f"render wall {(render or {}).get('wall_s')} cpu {(render or {}).get('cpu_s')} hwm {mib(fact(render, 'vm_hwm_kib'))} peak {mib(fact(render, 'vm_peak_kib'))} | "
                  f"extract wall {(extract or {}).get('wall_s')} cpu {(extract or {}).get('cpu_s')} hwm {mib(fact(extract, 'vm_hwm_kib'))} peak {mib(fact(extract, 'vm_peak_kib'))} | status {page['status']} {page.get('reason') or ''} |")

    print("\n## sheet pairs computed (one row per pair: transition, pages, size mm, dpi, end, status, child wall/cpu s, child VmHWM/VmPeak MiB, worker item VmHWM MiB, mask bytes, differences)")
    pair_items = {i["payload"].get("sheet_pair_id"): i for i in items if i["kind"] == "series_pair"}
    engine_by_ids: dict[tuple[str, str], dict[str, Any]] = {}
    for child in children:
        ctx = child.get("ctx") or {}
        if child["kind"] == "engine" and ctx.get("stage") == "pair":
            engine_by_ids[(ctx["a"], ctx["b"])] = child
    sheet_pair_by_profiles = {(p["a"]["page_profile_id"], p["b"]["page_profile_id"]): p for p in outcome.get("pairs", []) if p.get("a") and p.get("b")}
    pair_rows = []
    for pair in pairs:
        if "raised" in pair:
            continue
        child = engine_by_ids.get((pair["a"]["id"], pair["b"]["id"]))
        sheet = sheet_pair_by_profiles.get((pair["a"]["id"], pair["b"]["id"]))
        item = pair_items.get((sheet or {}).get("sheet_pair_id"))
        pair_rows.append((pair, child, item))
    for pair, child, item in sorted(pair_rows, key=lambda r: (versions.get(r[0]["a"]["version"], ""), r[0]["a"]["page"])):
        a, b = pair["a"], pair["b"]
        print(f"| {versions.get(a['version'], '?')}p{a['page']}->{versions.get(b['version'], '?')}p{b['page']} | {size_class(a['width_pt'], a['height_pt'])} | {a['raster'][0] if a['raster'] else '-'} dpi | "
              f"{pair['end']} | {pair['status']} | {(child or {}).get('wall_s', '-')} / {(child or {}).get('cpu_s', '-')} | {mib(fact(child, 'vm_hwm_kib'))}/{mib(fact(child, 'vm_peak_kib'))} | "
              f"{mib((item or {}).get('hwm_kib'))} | {pair['mask_bytes']} | {pair['differences']} | {','.join(pair['reasons'])} |")
    print("\n## worst pairs")
    for title, key in (("by engine child VmPeak", lambda r: fact(r[1], "vm_peak_kib")), ("by engine child wall", lambda r: (r[1] or {}).get("wall_s", 0)),
                       ("by worker VmHWM during the pair item", lambda r: (r[2] or {}).get("hwm_kib") or 0)):
        print(f"{title}")
        for pair, child, item in sorted(pair_rows, key=key, reverse=True)[:3]:
            a, b = pair["a"], pair["b"]
            print(f"| {versions.get(a['version'], '?')}p{a['page']}->{versions.get(b['version'], '?')}p{b['page']} | {size_class(a['width_pt'], a['height_pt'])} mm | {pair['status']} | child wall {(child or {}).get('wall_s')} cpu {(child or {}).get('cpu_s')} hwm {mib(fact(child, 'vm_hwm_kib'))} peak {mib(fact(child, 'vm_peak_kib'))} | item wall {(item or {}).get('wall_s')} worker hwm {mib((item or {}).get('hwm_kib'))} | mask {pair['mask_bytes']} B |")

    print("\n## ended without a result")
    notok = [c for c in children if c.get("status") != "ok" or "raised" in c]
    print(f"children: {len(notok)} " + json.dumps([{k: c.get(k) for k in ('kind', 'status', 'raised')} for c in notok][:10]))
    bad_pages = [p for p in pages if p["status"] != "ready"]
    print(f"pages not ready: {len(bad_pages)} " + json.dumps([{k: p.get(k) for k in ('version', 'page', 'status', 'reason')} for p in bad_pages][:10]))
    failed_items = [i for i in items if i["state"] not in ("succeeded", "completed", "queued")]
    print(f"items ended otherwise: {len(failed_items)} " + json.dumps(sorted({(i['kind'], str(i['state'])) for i in items})))
    print("work items in the database: " + json.dumps((outcome.get("census") or {}).get("work_items")))

    census_ = outcome.get("census") or {}
    print("\n## bytes per kind (census)")
    print(json.dumps(census_.get("blobs"), indent=0))
    print("bucket:", json.dumps(census_.get("bucket")), "volumes:", json.dumps(census_.get("volumes_bytes")), "database bytes:", census_.get("database_bytes"))
    print("jsonb:", json.dumps(census_.get("jsonb_bytes")))
    print("\n## rows per table (rows, total bytes)")
    for name, value in sorted((census_.get("tables") or {}).items()):
        print(f"| {name} | {value['rows']} | {value['total_bytes']} |")
    print("\n## matrix")
    print(json.dumps(outcome.get("matrix")))
    print("\n## series")
    versions_name = versions
    series = outcome.get("series") or {}
    print(json.dumps({k: series.get(k) for k in ("state", "failure_reason", "stale_reasons")}))
    for transition in series.get("transitions", []):
        print(f"| {versions_name.get(transition['source_version_uid'])} -> {versions_name.get(transition['target_version_uid'])} | {transition['state']} | {transition['verdict']} | {json.dumps(transition['summary'])} |")
    by_transition: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for pair in outcome.get("pairs", []):
        by_transition[pair["transition"]][f"{pair['state']}/{pair['status']}"] += 1
    for transition in series.get("transitions", []):
        print(f"pairs of {versions_name.get(transition['source_version_uid'])} -> {versions_name.get(transition['target_version_uid'])}: {dict(by_transition[transition['transition_id']])}")

    tiles_path = results / "tiles.jsonl"
    if tiles_path.exists():
        print("\n## tiles")
        summary = json.loads((results / "tiles_summary.json").read_text(encoding="ascii"))
        print(json.dumps(summary["plan"]), "baseline", json.dumps(summary["baseline"]), "final", json.dumps(summary["final"]))
        tile_rows = load_jsonl(tiles_path)
        cold = [t for t in tile_rows if t["cold"]]
        by_level: dict[int, list[float]] = defaultdict(list)
        for tile in cold:
            by_level[tile["level"]].append(tile["wall_ms"])
        for level, values in sorted(by_level.items()):
            print(f"| level {level} | {len(values)} tiles | median {percentile(values, 0.5):.0f} ms | max {max(values):.0f} ms | mean {sum(values) / len(values):.0f} ms |")
        print(f"all cold: {len(cold)} tiles, total {sum(t['wall_ms'] for t in cold) / 1000:.2f} s, mean {sum(t['wall_ms'] for t in cold) / len(cold):.0f} ms, max {max(t['wall_ms'] for t in cold):.0f} ms; "
              f"API VmRSS {mib(cold[0]['rss_before_kib'])} -> {mib(cold[-1]['rss_after_kib'])} MiB, VmHWM {mib(cold[-1]['hwm_after_kib'])} MiB, VmPeak {mib(cold[-1]['peak_after_kib'])} MiB; bytes per tile {min(t['bytes'] for t in cold)}..{max(t['bytes'] for t in cold)}")
        warm = [t for t in tile_rows if not t["cold"]]
        print("warm repeats: " + ", ".join(f"{t['wall_ms']:.0f} ms" for t in warm))
        tile_children = load_jsonl(results / "records_tiles" / "children.jsonl")
        tile_children = [c for c in tile_children if c["kind"] == "tile"]
        if tile_children:
            print(f"tile children: {len(tile_children)}; wall sum {sum(c['wall_s'] for c in tile_children if 'facts' in c):.2f} s max {max(c['wall_s'] for c in tile_children if 'facts' in c):.2f} s; "
                  f"VmHWM max {mib(max(fact(c, 'vm_hwm_kib') for c in tile_children))} MiB VmPeak max {mib(max(fact(c, 'vm_peak_kib') for c in tile_children))} MiB; not ok {sum(1 for c in tile_children if c.get('status') != 'ok')}")
    return 0


# ---------------------------------------------------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    commands = parser.add_subparsers(dest="command", required=True)
    run = commands.add_parser("run", help="the whole chain on a version set")
    run.add_argument("--set", default=str(REAL_SET))
    run.add_argument("--files", default="v1.pdf,v2.pdf,v3.pdf,v4.pdf")
    run.add_argument("--results", default=str(RESULTS))
    run.add_argument("--label", default="chain-01")
    run.add_argument("--interval", type=float, default=0.05)
    run.add_argument("--shim", action="store_true", help="shim S-1: the worker reads the role comparison.source_pdf as a source (see install_source_role_shim)")
    tiles = commands.add_parser("tiles", help="the cost of pair tiles through streamComparisonPairTile")
    tiles.add_argument("--results", default=str(RESULTS))
    tiles.add_argument("--tiles", type=int, default=20)
    tiles.add_argument("--interval", type=float, default=0.05)
    report = commands.add_parser("report", help="tables from the records")
    report.add_argument("--results", default=str(RESULTS))
    commands.add_parser("worker", help="internal: the real worker with a recording wrapper")
    args = parser.parse_args(argv)
    return {"run": cmd_run, "tiles": cmd_tiles, "report": cmd_report, "worker": cmd_worker}[args.command](args)


if __name__ == "__main__":
    raise SystemExit(main())
