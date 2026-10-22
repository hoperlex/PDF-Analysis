"""The extraction stage's per-page collection costs what the document built, not what the process holds (`D-200`).

`analysis/stages/extraction.py::_release` runs a full ``gc.collect()`` after every page (`W55B-FIX`,
X-2: the per-page reference cycle that pdfminer's content parser leaves, which owns the page's
decoded streams, must not live on to the next page). A full collection walks every object the
process tracks, so its cost is the *process's* heap, not the page's: measured by `GATE-REPAIR-02`
at 0.08 s on a worker-sized heap, 0.32 s on 2.1 M simple objects and 2.5 to 3.6 s in the complete
battery's process, and it holds the GIL for that long. A heartbeat thread beside the stage then
gets one beat per five collections (the gap is ``wait + 5 x collection``), which is how a lease
heartbeat starved in a large process (`D-190`, `D-200`).

The cases here run ``extract_document`` -- the stage's own path form, over a temporary file -- in a
child process of their own, so that the heap is the one the case builds and no other test's
objects, natural collections or frozen state reach the measurement. The child holds a ballast
heap of tracked objects, times a plain full collection of it (``t_full``), then reads a document
of tiny pages with

* a ``gc.callbacks`` observer that adds up the duration of every full collection that runs while
  the document is read (the stage's own and the interpreter's natural ones alike), and
* a heartbeat-shaped thread (a 0.05 s wait, then ten steps that each need the GIL back, as a
  database round trip with its commit does) whose longest gap between beats is read.

Both numbers are read against ``t_full`` of the same process in the same minute, so a loaded host
inflates the bound together with the measurement. The bounds are far from both measured sides.
Measured on this host with the numbers below (2.1 M ballast objects, ``t_full`` 0.2 s, 16 pages),
before the repair: 16 full collections adding up to 3.8 s (one ``t_full`` and more per page) and a
longest beat gap of 1.0 s (6 beats in 4 s); the bounds are 3 ``t_full`` and ``0.05 s + t_full +
0.25 s``.
"""

from __future__ import annotations

import gc
import io
import json
import subprocess
import sys
import threading
import zlib
from pathlib import Path

import pytest

import auditmanager
from auditmanager.analysis.stages import extraction
from auditmanager.shared.errors import DomainError, ErrorCode

SOURCE_ROOT = Path(auditmanager.__file__).resolve().parents[1]

#: Tracked objects the child holds beside the stage: enough that one full collection costs a
#: measurable fraction of a second (0.2 s on this host; `D-200` measured 0.32 s on the same
#: 2.1 M), small enough for a shared host (about 200 MB of address space).
BALLAST_OBJECTS = 2_100_000
#: Pages of the measured document. Before the repair this many full collections run.
PAGES = 16
#: A hard stop for a regression on a shared host.
CHILD_ADDRESS_SPACE = 1500 << 20

#: How many ``t_full`` the full collections of the whole document may add up to. A natural
#: full collection is the interpreter's own and may happen once or twice; one per page is
#: ``PAGES`` (16).
MAX_FULL_COLLECTIONS_IN_T_FULL = 3
#: The heartbeat's wait, plus how many ``t_full`` one beat may be late, plus scheduling noise.
BEAT_WAIT = 0.05
BEAT_SLACK_IN_T_FULL = 1
BEAT_NOISE = 0.25
#: Steps of one beat that each need the GIL back (a statement, its commit, the reply).
BEAT_STEPS = 10


def _text_pages(pages: int) -> bytes:
    """A PDF of ``pages`` pages, each with one text line of its own and nothing else."""
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids ["
        + b" ".join(b"%d 0 R" % (4 + i) for i in range(pages))
        + b"] /Count %d >>" % pages,
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    first_stream = 4 + pages
    for index in range(pages):
        objects.append(
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
            b"/Resources << /Font << /F1 3 0 R >> >> /Contents %d 0 R >>" % (first_stream + index)
        )
    for index in range(pages):
        content = b"BT /F1 9 Tf 10 10 Td (page %d: a line of text for the layer) Tj ET\n" % index
        packed = zlib.compress(content, 9)
        objects.append(
            b"<< /Length %d /Filter /FlateDecode >>\nstream\n" % len(packed)
            + packed
            + b"\nendstream"
        )
    out = io.BytesIO()
    out.write(b"%PDF-1.7\n")
    offsets = []
    for number, body in enumerate(objects, 1):
        offsets.append(out.tell())
        out.write(b"%d 0 obj\n" % number + body + b"\nendobj\n")
    xref = out.tell()
    out.write(b"xref\n0 %d\n0000000000 65535 f \n" % (len(objects) + 1))
    for offset in offsets:
        out.write(b"%010d 00000 n \n" % offset)
    out.write(
        b"trailer << /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (len(objects) + 1, xref)
    )
    return out.getvalue()


_CHILD = r"""
import gc, json, resource, sys, threading, time
resource.setrlimit(resource.RLIMIT_AS, (int(sys.argv[1]), int(sys.argv[1])))
sys.path.insert(0, sys.argv[2])
from auditmanager.analysis.stages.extraction import extract_document

path, ballast_objects, beat_wait, beat_steps = (
    sys.argv[3], int(sys.argv[4]), float(sys.argv[5]), int(sys.argv[6]))
heap = [[i] for i in range(ballast_objects)]   # each list is one tracked object
gc.collect()
timings = []
for _ in range(3):
    started = time.perf_counter()
    gc.collect()
    timings.append(time.perf_counter() - started)
t_full = min(timings)

full = {"seconds": 0.0, "count": 0}
began = [0.0]
def watch(phase, info):
    if phase == "start":
        began[0] = time.perf_counter()
    elif info["generation"] == 2:
        full["seconds"] += time.perf_counter() - began[0]
        full["count"] += 1
gc.callbacks.append(watch)

beats = []
stop = threading.Event()
def heartbeat():
    while not stop.wait(beat_wait):
        for _ in range(beat_steps):
            time.sleep(0.0001)
        beats.append(time.perf_counter())
thread = threading.Thread(target=heartbeat, daemon=True)
thread.start()
time.sleep(4 * beat_wait)

first = time.perf_counter()
document = extract_document(path)
last = time.perf_counter()
stop.set()
thread.join()
gc.callbacks.remove(watch)

inside = [b for b in beats if first <= b <= last]
edges = [first] + inside + [last]
print(json.dumps({
    "pages": document.page_count,
    "tracked_ballast": len(heap),
    "t_full": t_full,
    "full_collections": full["count"],
    "full_seconds": full["seconds"],
    "extraction_seconds": last - first,
    "max_beat_gap": max(b - a for a, b in zip(edges, edges[1:])),
    "beats": len(inside),
}))
"""


@pytest.fixture(scope="module")
def measured(tmp_path_factory: pytest.TempPathFactory) -> dict[str, float]:
    """One child run: the ballast heap, the document, the observers. Shared by the cases below."""
    source = tmp_path_factory.mktemp("gc-scope") / "document.pdf"
    source.write_bytes(_text_pages(PAGES))
    completed = subprocess.run(
        [
            sys.executable,
            "-I",
            "-c",
            _CHILD,
            str(CHILD_ADDRESS_SPACE),
            str(SOURCE_ROOT),
            str(source),
            str(BALLAST_OBJECTS),
            str(BEAT_WAIT),
            str(BEAT_STEPS),
        ],
        capture_output=True,
        text=True,
        timeout=300,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr[-2000:]
    answer = json.loads(completed.stdout)
    assert answer["pages"] == PAGES
    return answer


def test_the_pages_of_a_document_add_up_to_no_more_than_a_few_full_heap_scans(measured) -> None:
    t_full = measured["t_full"]
    bound = MAX_FULL_COLLECTIONS_IN_T_FULL * t_full
    assert measured["full_seconds"] <= bound, (
        f"{measured['full_collections']} full collections ran while {PAGES} pages were read and "
        f"took {measured['full_seconds']:.3f} s in all; one full collection of the process's "
        f"{measured['tracked_ballast']} ballast objects takes {t_full:.3f} s, so the stage "
        f"scans the whole heap per page instead of what the document built"
    )


def test_a_heartbeat_thread_keeps_its_pace_while_the_pages_are_released(measured) -> None:
    t_full = measured["t_full"]
    limit = BEAT_WAIT + BEAT_SLACK_IN_T_FULL * t_full + BEAT_NOISE
    assert measured["max_beat_gap"] <= limit, (
        f"the longest gap between two heartbeats while {PAGES} pages were read was "
        f"{measured['max_beat_gap']:.3f} s (limit {limit:.3f} s; a full collection of this "
        f"process's heap takes {t_full:.3f} s and holds the GIL): the page release starves "
        f"the thread that keeps the lease"
    )


# --- The freeze that makes the collection cheap is scoped, counted and given back ------------------


def test_the_heap_is_frozen_while_the_pages_are_read_and_given_back_after(monkeypatch) -> None:
    frozen_at_each_page: list[int] = []
    read_page = extraction._extract_page

    def watch(page, number):
        frozen_at_each_page.append(gc.get_freeze_count())
        return read_page(page, number)

    monkeypatch.setattr(extraction, "_extract_page", watch)
    before = gc.get_freeze_count()

    document = extraction.extract_document(_text_pages(3))

    assert document.page_count == 3
    assert len(frozen_at_each_page) == 3
    assert all(count > before for count in frozen_at_each_page), (before, frozen_at_each_page)
    assert gc.get_freeze_count() <= before, "the heap was not given back when the document ended"


def test_a_page_that_fails_midway_is_still_released_and_the_heap_is_given_back(monkeypatch) -> None:
    released: list[int] = []
    release_page = extraction._release
    read_page = extraction._extract_page

    def watch_release(page):
        released.append(page.page_number)
        release_page(page)

    def fail_on_the_second(page, number):
        if number == 2:
            raise ValueError("a page that cannot be read")
        return read_page(page, number)

    monkeypatch.setattr(extraction, "_release", watch_release)
    monkeypatch.setattr(extraction, "_extract_page", fail_on_the_second)
    before = gc.get_freeze_count()

    with pytest.raises(DomainError) as refused:
        extraction.extract_document(_text_pages(4))

    assert refused.value.code is ErrorCode.ANALYSIS_INPUT_INVALID
    assert refused.value.detail_fields["reason"] == "source_unreadable"
    assert released == [1, 2], "the failing page must be released, and no page after it read"
    assert gc.get_freeze_count() <= before, "a failed document left the heap frozen"


def test_two_documents_read_at_once_keep_one_freeze_until_the_last_one_ends(monkeypatch) -> None:
    first_is_inside = threading.Event()
    let_the_first_go = threading.Event()
    first: list[threading.Thread] = []
    read_page = extraction._extract_page

    def hold_the_first(page, number):
        if threading.current_thread() is first[0] and number == 1:
            first_is_inside.set()
            assert let_the_first_go.wait(60)
        return read_page(page, number)

    monkeypatch.setattr(extraction, "_extract_page", hold_the_first)
    before = gc.get_freeze_count()
    reader = threading.Thread(target=lambda: extraction.extract_document(_text_pages(2)))
    first.append(reader)
    reader.start()
    try:
        assert first_is_inside.wait(60)
        extraction.extract_document(_text_pages(2))  # a whole second document, start to end
        assert gc.get_freeze_count() > before, (
            "the second document to end lifted the freeze the first one is still reading under"
        )
    finally:
        let_the_first_go.set()
        reader.join(60)

    assert not reader.is_alive()
    assert gc.get_freeze_count() <= before, "the last document to end did not give the heap back"


def test_a_freeze_made_by_other_code_is_left_in_force() -> None:
    gc.freeze()
    try:
        frozen = gc.get_freeze_count()
        extraction.extract_document(_text_pages(2))
        assert gc.get_freeze_count() > 0.9 * frozen, (
            f"{frozen} objects were frozen by the caller and {gc.get_freeze_count()} are left: "
            "the stage lifted a freeze that was not its own"
        )
    finally:
        gc.unfreeze()
