"""The measurement helpers every driver of this directory shares: the cold/warm bench, ``EXPLAIN (ANALYZE, BUFFERS)`` of the exact statement the
code sent, and the result file. Nothing here changes the repository.

Environment (read at import; ``perf_stand.sh`` sets all of it):

* ``DATABASE_URL`` -- the throwaway PostgreSQL, at migration head;
* ``PERF_OUT`` -- the directory for ``result.json`` and ``explain/`` (created on first use);
* ``PERF_RUNS`` -- warm runs per figure (default 5).

Method, per figure. *Cold*: write back and drop every shared buffer (``pg_buffercache_evict`` after a ``CHECKPOINT``) and forget the pooled
connections, so the first run is a fresh backend with cold caches. The tmpfs data directory stays in the kernel's page cache, so *cold* here
is a lower bound of a disk-cold read. *Warm*: ``PERF_RUNS`` consecutive runs after that, the median reported with the minimum and maximum.
``explain`` runs the statement the code sent (captured through ``before_cursor_execute``) under ``EXPLAIN (ANALYZE, BUFFERS, SETTINGS)`` and
stores the plan per figure.
"""
from __future__ import annotations

import json
import os
import re
import statistics
import sys
import time
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker

OUT = Path(os.environ["PERF_OUT"])
RESULT = OUT / "result.json"
RUNS = int(os.environ.get("PERF_RUNS", "5"))
results: dict[str, Any] = {}

engine = create_engine(os.environ["DATABASE_URL"], pool_size=2, max_overflow=0)
factory = sessionmaker(engine, expire_on_commit=False)


def log(message: str) -> None:
    print(f"[perf {time.strftime('%H:%M:%S')}] {message}", file=sys.stderr, flush=True)


def save() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    RESULT.write_text(json.dumps(results, indent=2, ensure_ascii=False, default=str), encoding="utf-8")


def admin(sql: str) -> Any:
    with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
        result = conn.execute(text(sql))
        return result.all() if result.returns_rows else []


def evict() -> int | None:
    """Cold: write back and drop every shared buffer, then forget the pooled connections (fresh backend, cold caches)."""
    try:
        admin("CREATE EXTENSION IF NOT EXISTS pg_buffercache")
        admin("CHECKPOINT")
        rows = admin("SELECT count(*) FILTER (WHERE pg_buffercache_evict(bufferid)) FROM pg_buffercache WHERE relfilenode IS NOT NULL")
        engine.dispose()
        return int(rows[0][0])
    except Exception as error:  # the figure then says it was not cold
        engine.dispose()
        log(f"evict failed: {error}")
        return None


def ms(seconds: float) -> float:
    return round(seconds * 1000, 1)


def bench(label: str, fn, *, runs: int | None = None) -> dict[str, Any]:
    """One cold run and ``runs`` warm runs of ``fn``; milliseconds."""
    runs = RUNS if runs is None else runs
    evicted = evict()
    started = time.perf_counter()
    fn()
    cold = ms(time.perf_counter() - started)
    warm = []
    for _ in range(runs):
        started = time.perf_counter()
        fn()
        warm.append(ms(time.perf_counter() - started))
    figure = {
        "cold_ms": cold, "warm_ms": warm, "warm_median_ms": statistics.median(warm), "warm_min_ms": min(warm),
        "warm_max_ms": max(warm), "evicted_buffers": evicted,
    }
    log(f"{label}: cold {cold} ms, warm median {figure['warm_median_ms']} ms {warm}")
    return figure


def capture(fn) -> list[tuple[str, Any]]:
    """The statements ``fn`` sends, in order, as (text, parameters)."""
    seen: list[tuple[str, Any]] = []

    def hook(conn, cursor, statement, parameters, context, executemany):  # noqa: ANN001
        seen.append((statement, parameters))

    event.listen(engine, "before_cursor_execute", hook)
    try:
        fn()
    finally:
        event.remove(engine, "before_cursor_execute", hook)
    return seen


def explain(label: str, statement: str, parameters: Any, *, cold: bool = False) -> dict[str, Any]:
    """EXPLAIN (ANALYZE, BUFFERS, SETTINGS) of the exact statement; the plan goes to a file, the headline numbers to the result."""
    if cold:
        evict()
    raw = engine.raw_connection()
    try:
        cursor = raw.cursor()
        cursor.execute("EXPLAIN (ANALYZE, BUFFERS, SETTINGS) " + statement, parameters)
        lines = [row[0] for row in cursor.fetchall()]
    finally:
        raw.rollback()
        raw.close()
    plan = "\n".join(lines)
    (OUT / "explain").mkdir(parents=True, exist_ok=True)
    (OUT / "explain" / f"{label}{'-cold' if cold else ''}.txt").write_text(plan, encoding="utf-8")
    execution = re.search(r"Execution Time: ([\d.]+) ms", plan)
    planning = re.search(r"Planning Time: ([\d.]+) ms", plan)
    jit = re.search(r"JIT:.*?Timing: (.*?Total ([\d.]+) ms)", plan, re.S)
    buffers = re.search(r"Buffers: (shared[^\n]*)", plan)
    return {
        "execution_ms": float(execution.group(1)) if execution else None,
        "planning_ms": float(planning.group(1)) if planning else None,
        "jit_total_ms": float(jit.group(2)) if jit else None,
        "top_buffers": buffers.group(1).strip() if buffers else None,
    }


def explain_of(label: str, fn, *, which: int = -1, cold: bool = False) -> dict[str, Any]:
    """Capture what ``fn`` sends and EXPLAIN the ``which``-th statement (the longest one when ``which`` is -1)."""
    statements = capture(fn)
    if which == -1:
        statement, parameters = max(statements, key=lambda pair: len(pair[0]))
    else:
        statement, parameters = statements[which]
    return explain(label, statement, parameters, cold=cold)


def norm(rows) -> list[tuple]:
    """Rows in a total order that tolerates NULLs, for comparing two statements' answers."""
    return sorted((tuple(r) for r in rows), key=lambda r: tuple("" if x is None else str(x) for x in r))
