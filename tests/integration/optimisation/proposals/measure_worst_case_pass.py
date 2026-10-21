"""`D-185` measurement harness: the wall time and peak memory of ``startOptimisationPass`` at the bounds.

**Not collected by a directory run** (the file name does not match ``test_*.py``); it is run by
name, on a lane's own stack, and it asserts only that the input it built is the one it meant to
build and that the request answered ``201``. What it *measures* is printed as one JSON line per
request and recorded in ``docs/program/API-FOLLOWUPS-01.md`` with the command that produced it::

    D185_SCENARIO=catalogue D185_RUNS=10 .venv/bin/python -m pytest -q -s \
        tests/integration/optimisation/proposals/measure_worst_case_pass.py

The request is the real one: the assembled application (``create_asgi_app``), the real seam and
credential exchange, the shipped :class:`~auditmanager.bootstrap.adapters.OptimisationProposalAdapter`
over a real PostgreSQL, a real price list uploaded through :class:`PriceListUploads` into a real
bucket, and an AR specification whose text layer is served from memory (the composition root's
reader fetches one blob of about a megabyte; that read is measured separately in the record).

**The largest input the bounds allow** is 20 000 price-list positions (``MAX_DATA_ROWS``) against
10 000 specification rows (``MAX_SPECIFICATION_ROWS``), 500 vendors on the list
(``MAX_VENDOR_LIST_ENTRIES``). The bounds do not say what the *shape* of that input is, and the
cost is a function of the shape, so four shapes are built (``D185_SCENARIO``):

``catalogue``
    200 head words of about 100 positions each, every row matching one position by name. What a
    real price list looks like, at the maximum size.
``one_head_similar``
    One head word, one unit, one currency; every name differs from every other by one word, so
    every pair is an analog. The candidate list of a row is the whole cheaper half.
``one_head_dissimilar``
    The same bucket, but no pair is similar enough: nothing is ever proposed.
``two_words``
    ``Профиль 17``: names that differ by one number each and share only the head word.
``common_code_token``
    Every code opens with the same token (``ПК``) and every row names it, so the matcher's code
    index holds the whole price list under one key.
``rich``
    Every field present and long (code, mark, a 300-character name): what the 10 MiB file cap
    allows at 20 000 rows, and the heaviest index the matcher builds.
``flat_price``
    Contrived: half the list at one price, all names alike, and the rows are the other half, so
    every row has one equal-price group of ten thousand analogs to order.
``overlap_dissimilar``
    Contrived: every name draws six words from slots of twenty, so nearly every pair shares a word
    and almost none reaches the threshold, and the rows are the dearest positions, whose cheaper
    prefix is the longest. The residual worst case of the search.

Each repetition changes the vendor list's notes, which changes the pass's pinned inputs and so
makes the server compute a fresh pass instead of answering the stored one.
"""

from __future__ import annotations

import json
import os
import random
import re
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker
from starlette.testclient import TestClient

from auditmanager.access.public import AccountRepository, UserRepository
from auditmanager.api.app import create_asgi_app
from auditmanager.api.routers import build_router
from auditmanager.api.security import API_TOKEN_VARIABLE, build_signer
from auditmanager.bootstrap.adapters import CredentialAdapter, OptimisationProposalAdapter
from auditmanager.optimisation.project_match import RunCandidate, SavedPageText
from auditmanager.optimisation.specification import MAX_SPECIFICATION_ROWS
from auditmanager.runs import InlineCarrier
from auditmanager.storage import S3BlobStore

from . import conftest as proposals
from ..conftest import PASSWORD
from .conftest import LAYER_SHA256, Reader, World, classify, global_vendors, upload

SECRET = "d-185-measurement-deployment-secret"
POSITIONS = int(os.environ.get("D185_POSITIONS", 20_000))
ROWS = int(os.environ.get("D185_ROWS", MAX_SPECIFICATION_ROWS))
RUNS = int(os.environ.get("D185_RUNS", 3))
SCENARIO = os.environ.get("D185_SCENARIO", "catalogue")
ROWS_PER_PAGE = 40
VENDORS = [f"Поставщик{n}" for n in range(500)]
HEADER = (
    "Поз. Наименование и техническая характеристика Тип, марка Код Завод- Ед. Кол. Масса Примечание\n"
    "изготовитель изм. 1 ед., кг\n"
)


def _names(scenario: str) -> tuple[list[str], list[str | None], list[str], list[str | None]]:
    """Position names, codes and marks, and the description each specification row carries."""
    nothing: list[str | None] = [None] * POSITIONS
    if scenario == "catalogue":
        names = [f"Материал{i % 200} тип {i}" for i in range(POSITIONS)]
        return names, nothing, [names[(2 * k) % POSITIONS] for k in range(ROWS)], nothing
    if scenario == "one_head_similar":
        names = [f"Профиль вариант {i}" for i in range(POSITIONS)]
        return names, nothing, [names[(2 * k) % POSITIONS] for k in range(ROWS)], nothing
    if scenario == "one_head_dissimilar":
        names = [f"Профиль {i}x{(i * 7919) % 10007} z{i % 977} q{(i * 31) % 4999}" for i in range(POSITIONS)]
        return names, nothing, [names[(2 * k) % POSITIONS] for k in range(ROWS)], nothing
    if scenario == "two_words":
        names = [f"Профиль {i}" for i in range(POSITIONS)]
        return names, nothing, [names[(2 * k) % POSITIONS] for k in range(ROWS)], nothing
    if scenario == "common_code_token":
        names = [f"Плита {i}" for i in range(POSITIONS)]
        codes: list[str | None] = [f"ПК {10000 + i}" for i in range(POSITIONS)]
        return names, codes, [f"Плита ПК {10000 + (2 * k) % POSITIONS}" for k in range(ROWS)], nothing
    if scenario == "rich":
        filler = " ".join(f"слово{w}" for w in range(30))
        names = [f"Изделие {i} {filler} типоразмер {i % 97}" for i in range(POSITIONS)]
        codes = [f"АБВ {20000 + i}" for i in range(POSITIONS)]
        marks: list[str | None] = [f"МК-{i}" for i in range(POSITIONS)]
        return names, codes, [names[(2 * k) % POSITIONS] for k in range(ROWS)], marks
    if scenario == "flat_price":
        names = [f"Профиль вариант {i}" for i in range(POSITIONS)]
        half = POSITIONS // 2
        return names, nothing, [names[half + (k % half)] for k in range(ROWS)], nothing
    if scenario == "overlap_dissimilar":
        rnd = random.Random(7)
        names = [
            f"Профиль {i}n " + " ".join(f"с{slot}в{rnd.randrange(20)}" for slot in range(6))
            for i in range(POSITIONS)
        ]
        return names, nothing, [names[POSITIONS - 1 - k] for k in range(ROWS)], nothing
    raise AssertionError(f"unknown D185_SCENARIO {scenario!r}")


def _price_list(scenario: str) -> bytes:
    names, codes, _, marks = _names(scenario)
    rnd = random.Random(20261021)
    lines = ["Код;Наименование;Марка;Ед. изм.;Цена;Валюта;Поставщик"]
    for index in range(POSITIONS):
        if scenario == "overlap_dissimilar":  # the dearest positions are the rows': the longest prefixes
            price = f"{index + 1}"
        elif scenario == "flat_price":  # half the list at one price; the rows are the other half
            price = "1" if index < POSITIONS // 2 else str(2 + index)
        else:
            price = f"{rnd.randint(1000, 900000) / 100:.2f}".replace(".", ",")
        lines.append(
            f"{codes[index] or ''};{names[index]};{marks[index] or ''};шт;{price};RUB;"
            f"{VENDORS[rnd.randrange(len(VENDORS))]}"
        )
    return ("\n".join(lines) + "\n").encode("utf-8")


def _pages(scenario: str) -> dict[int, str]:
    rows = _names(scenario)[2]
    pages: dict[int, str] = {}
    for start in range(0, len(rows), ROWS_PER_PAGE):
        body = [HEADER]
        for offset, name in enumerate(rows[start : start + ROWS_PER_PAGE], start=1):
            body.append(f"{offset} {name} шт {1 + (start + offset) % 50}\n")
        pages[start // ROWS_PER_PAGE + 1] = "".join(body)
    return pages


def _reset_peak_rss() -> None:
    """Zero the kernel's high-water mark of this process (Linux >= 4.0); a failure is reported."""
    try:
        Path("/proc/self/clear_refs").write_text("5")
    except OSError as exc:  # pragma: no cover - environment
        print(f"D185 could not reset VmHWM: {exc}")


def _rss_mib() -> tuple[float, float]:
    status = Path("/proc/self/status").read_text()
    now = int(re.search(r"VmRSS:\s+(\d+)", status).group(1)) / 1024  # type: ignore[union-attr]
    peak = int(re.search(r"VmHWM:\s+(\d+)", status).group(1)) / 1024  # type: ignore[union-attr]
    return now, peak


class _Built:
    def __init__(self, router: Any) -> None:
        self.router = router
        self.carrier = InlineCarrier()


@pytest.fixture
def big_world(
    session: Session, store: S3BlobStore, cast: Any, monkeypatch: pytest.MonkeyPatch
) -> tuple[World, dict[int, str]]:
    """The conftest's world, but a version whose page count is the specification's."""
    pages = _pages(SCENARIO)
    monkeypatch.setattr(proposals, "PAGES", pages)
    document, version = proposals._publish_version(session, store, cast.project, "13АВ-РД-АР-ТП1")
    built = World(
        project=cast.project, document=document, version=version,
        run=proposals._run_row(session, cast.project, version),
        foreign_document=document, other_document=document, other_version=version, other_run="",
    )
    session.commit()
    return built, pages


def test_measure_one_start_optimisation_pass_at_the_bounds(
    unit: Callable[..., Any],
    store: S3BlobStore,
    factory: sessionmaker[Session],
    cast: Any,
    big_world: tuple[World, dict[int, str]],
) -> None:
    world, pages = big_world
    classify(unit, cast, world)
    started = time.perf_counter()
    upload(store, factory, cast, _price_list(SCENARIO), "prices-d185")
    print(f"D185 setup: price list of {POSITIONS} positions uploaded in {time.perf_counter() - started:.1f} s")
    with factory() as check:
        assert check.execute(text("SELECT count(*) FROM price_list_position")).scalar_one() == POSITIONS
    assert len(pages) * ROWS_PER_PAGE >= ROWS

    reader = Reader(
        by_version={world.version: (RunCandidate(world.run, "published"),)},
        texts={world.run: SavedPageText(world.run, LAYER_SHA256, dict(pages))},
    )
    adapter = OptimisationProposalAdapter(factory, blob_store=store)
    adapter._reader = reader  # type: ignore[assignment]
    signer = build_signer({API_TOKEN_VARIABLE: SECRET})
    assert signer is not None
    router = build_router(
        projects=None, documents=None, runs=None, findings=None, decisions=None,  # type: ignore[arg-type]
        exports=None,  # type: ignore[arg-type]
        credentials=CredentialAdapter(
            factory, users=UserRepository(), accounts=AccountRepository(), signer=signer
        ),
        optimisation_proposals=adapter,
    )
    client = TestClient(
        create_asgi_app(environ={API_TOKEN_VARIABLE: SECRET}, application=_Built(router)),
        raise_server_exceptions=False,
    )
    exchanged = client.post(
        "/auth/token", json={"login": "anna@example.com", "password": PASSWORD}
    )
    assert exchanged.status_code == 200, exchanged.text
    headers = {"Authorization": f"Bearer {exchanged.json()['token']}"}
    url = f"/projects/{world.project}/documents/{world.document}/optimisation-passes"

    walls: list[float] = []
    for run in range(RUNS):
        # A new vendor-list revision (notes differ) pins a new input set: a fresh pass is computed.
        global_vendors(
            unit, cast, entries=[{"vendor": vendor, "note": f"run {run}"} for vendor in VENDORS]
        )
        _reset_peak_rss()
        before, _ = _rss_mib()
        cpu = time.process_time()
        clock = time.perf_counter()
        response = client.post(url, headers={**headers, "Idempotency-Key": f"d185-{run:04d}"})
        wall = time.perf_counter() - clock
        cpu = time.process_time() - cpu
        after, peak = _rss_mib()
        assert response.status_code == 201, response.text
        body = response.json()
        assert body["specification_row_count"] == ROWS
        walls.append(wall)
        print("D185 " + json.dumps({
            "scenario": SCENARIO, "run": run, "positions": POSITIONS, "rows": ROWS,
            "wall_s": round(wall, 2), "cpu_s": round(cpu, 2),
            "rss_before_mib": round(before, 0), "rss_peak_mib": round(peak, 0),
            "rss_after_mib": round(after, 0),
            "matched_rows": body["matched_row_count"], "proposed_rows": body["proposed_row_count"],
            "proposals": body["proposal_count"], "load1": os.getloadavg()[0],
        }))
    ordered = sorted(walls)
    print("D185 " + json.dumps({
        "scenario": SCENARIO, "runs": RUNS, "p50_s": round(ordered[len(ordered) // 2], 2),
        "p95_s": round(ordered[min(len(ordered) - 1, int(0.95 * len(ordered)))], 2),
        "max_s": round(ordered[-1], 2),
    }))
