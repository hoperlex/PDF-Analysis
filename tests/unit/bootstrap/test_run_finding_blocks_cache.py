"""`D-353` (5), judge J3 F4: ``listRunFindingBlocks`` does not read and parse the run's three documents on every call.

Each call of the read used to fetch and SHA-256 the run's block index and page inventory and the version's portal blocks, parse
them whole, and build a ``TextLine`` for every line of every page, though only the pages that carry evidence matter. The review
screen asks for it again for each finding a reader opens, so the cost was one whole-document parse per click.

The derived inputs are now kept per adapter, keyed by the version and the SHA-256 and size each ``stage_result`` recorded for the
three artifacts. The cases are aimed at: a hit that is not the same answer as a miss (the answer must not depend on the cache); a
key that ignores one of the three documents; a cache that grows without bound; a hit that hides what a miss would refuse; and a
cache that serves one version's documents to another. The object store is a counting double, the runs and findings are stubbed at
the seams the adapter reads them through (as ``test_run_finding_blocks_adapter`` does), and the documents are real bytes verified
through the adapter's own ``_verified_bytes``.

``build`` is also what the measurement in ``D-353`` ran (calls and time of K successive reads, with and without the cache).
"""

from __future__ import annotations

import hashlib
import json
from types import SimpleNamespace
from typing import Any

import pytest
from sqlalchemy.orm import sessionmaker

import auditmanager.findings as findings_module
from auditmanager.analysis.public import (
    ARTIFACT_VERSION,
    KIND_RECOGNISED_TEXT,
    ROLE_BLOCK_INDEX,
    ROLE_PAGE_INVENTORY,
    ROLE_PORTAL_BLOCKS,
    ROLE_RECOGNISED_TEXT,
)
from auditmanager.bootstrap.adapters import BlockAdapter
from auditmanager.runs import RunRepository
from auditmanager.shared.errors import DomainError, ErrorCode
from auditmanager.storage.public import BlobNotFoundError, derive_blob_id

VERSION = "ver_01ARZ3NDEKTSV4RRFFQ69G5FAV"
OTHER_VERSION = "ver_01ARZ3NDEKTSV4RRFFQ69G5FAW"
RUN = "run_01ARZ3NDEKTSV4RRFFQ69G5FAV"
OTHER_RUN = "run_01ARZ3NDEKTSV4RRFFQ69G5FAW"


class CountingStore:
    """An object store that holds content-addressed blobs and counts how often it is asked for one."""

    def __init__(self) -> None:
        self.blobs: dict[str, bytes] = {}
        self.reads = 0

    def put(self, payload: bytes) -> dict[str, Any]:
        sha256 = hashlib.sha256(payload).hexdigest()
        blob_id = str(derive_blob_id(sha256=sha256, size=len(payload)))
        self.blobs[blob_id] = payload
        return {"blob_id": blob_id, "sha256": sha256, "size_bytes": len(payload)}

    def open_stream(self, blob_id: Any, *, expected_sha256: str, expected_size: int) -> Any:
        self.reads += 1
        payload = self.blobs.get(str(blob_id))
        if payload is None:
            raise BlobNotFoundError(str(blob_id))
        assert hashlib.sha256(payload).hexdigest() == expected_sha256 and len(payload) == expected_size
        return iter((payload,))


def documents(pages: int, lines_per_page: int, *, version: str = VERSION, shift: float = 0.0) -> dict[str, dict[str, Any]]:
    """A document set of ``pages`` pages, ``lines_per_page`` evenly stacked lines each; ``shift`` moves every line sideways."""
    blocks, cursor = [], 0
    for page in range(1, pages + 1):
        for line in range(lines_per_page):
            blocks.append({
                "block_id": f"b_{len(blocks) + 1:06d}", "page_number": page, "block_ordinal": line,
                "bbox": {"x0": 50.0 + shift, "y0": 20.0 + 6.0 * line, "x1": 250.0 + shift, "y1": 24.0 + 6.0 * line},
                "bbox_unit": "pt", "bbox_origin": "top_left", "char_start": cursor, "char_end": cursor + 40,
            })
            cursor += 41
    # `shift` also stands for "another document": it is in every document, so changing it changes each one's digest.
    head = {"artifact_version": ARTIFACT_VERSION, "version_uid": version, "generation": shift}
    return {
        ROLE_BLOCK_INDEX: {**head, "artifact_role": ROLE_BLOCK_INDEX, "blocks": blocks},
        ROLE_PAGE_INVENTORY: {**head, "artifact_role": ROLE_PAGE_INVENTORY, "pages": [
            {"page_number": page, "width_pt": 600.0, "height_pt": 800.0, "rotation_deg": 0} for page in range(1, pages + 1)]},
        ROLE_PORTAL_BLOCKS: {**head, "artifact_role": ROLE_PORTAL_BLOCKS,
            "pages": [{"page_number": page, "width_px": 1200, "height_px": 1600, "rotation_deg": 0, "geometry": "ok"}
                      for page in range(1, pages + 1)],
            "blocks": [{"portal_block_id": f"blk_{page:016x}{block:016x}", "page_number": page, "bbox_norm": [0.0, 0.02 + 0.2 * block, 1.0, 0.2 + 0.2 * block]}
                       for page in range(1, pages + 1) for block in range(4)]},
    }


class Adapter(BlockAdapter):
    """The adapter over a counting store; the run's rows and its stages are answered from memory."""

    def __init__(self, store: CountingStore) -> None:
        super().__init__(sessionmaker(), blob_store=store)
        self.store = store
        self.references: dict[str, dict[str, Any]] = {}

    def _read(self, work: Any) -> Any:
        return work(None)

    def _portal_source(self, version_uid: str) -> Any:
        return SimpleNamespace(
            portal_blocks=self.references[ROLE_PORTAL_BLOCKS], recognised_text=self.references.get(ROLE_RECOGNISED_TEXT),
        )


def build(pages: int = 6, lines_per_page: int = 10, *, store: CountingStore | None = None, version: str = VERSION,
          shift: float = 0.0) -> tuple[Adapter, dict[str, dict[str, Any]]]:
    store = store or CountingStore()
    adapter = Adapter(store)
    for role, document in documents(pages, lines_per_page, version=version, shift=shift).items():
        adapter.references[role] = {"role": role, **store.put(json.dumps(document).encode("utf-8"))}
    return adapter, adapter.references


def stub_run(
    monkeypatch: pytest.MonkeyPatch, adapter: Adapter, *, run: str = RUN, version: str = VERSION, evidence: tuple[Any, ...] | None = None,
) -> None:
    stages = {
        "page_geometry_extraction": SimpleNamespace(stage_id="page_geometry_extraction", status="succeeded",
                                                    artifacts=(adapter.references[ROLE_BLOCK_INDEX],)),
        "source_preparation": SimpleNamespace(stage_id="source_preparation", status="succeeded",
                                              artifacts=(adapter.references[ROLE_PAGE_INVENTORY],)),
    }
    monkeypatch.setattr(RunRepository, "find", lambda self, session, run_id: SimpleNamespace(version_uid=version))
    monkeypatch.setattr(RunRepository, "stage_results", lambda self, session, run_id: tuple(stages.values()))
    finding = SimpleNamespace(canonical=SimpleNamespace(finding_uid="fnd_01ARZ3NDEKTSV4RRFFQ69G5FAV", finding_observation_id="obs_1"), merged=())
    monkeypatch.setattr(findings_module, "published_findings", lambda session, run_id: ())
    monkeypatch.setattr(findings_module, "group_published_findings", lambda rows: (finding,))
    monkeypatch.setattr(findings_module, "published_finding_evidence", lambda session, run_id: evidence if evidence is not None else (
        SimpleNamespace(finding_observation_id="obs_1", page_number=2, char_start=10 * 41 + 3, char_end=10 * 41 + 20, quote="x"),))


@pytest.fixture
def run(monkeypatch: pytest.MonkeyPatch) -> Any:
    def start(adapter: Adapter, **kwargs: Any) -> None:
        stub_run(monkeypatch, adapter, **kwargs)
    return start


def test_successive_reads_of_one_run_read_the_object_store_once_and_answer_the_same(run: Any) -> None:
    adapter, _ = build()
    run(adapter)
    first = adapter.list_run_finding_blocks(run_id=RUN)
    assert adapter.store.reads == 3                        # the index, the inventory, the portal blocks
    assert first.status == "produced" and first.items[0].portal_block_ids != []
    for _ in range(5):
        assert adapter.list_run_finding_blocks(run_id=RUN) == first
    assert adapter.store.reads == 3                        # nothing further was fetched, verified or parsed


def test_the_answer_does_not_depend_on_the_cache(run: Any) -> None:
    """A miss is the whole truth: an adapter that never kept anything answers what the caching one answers."""
    caching, _ = build()
    run(caching)
    answer = caching.list_run_finding_blocks(run_id=RUN)
    never_keeping, _ = build()
    never_keeping._GEOMETRY_CACHE_BYTES = 0
    run(never_keeping)
    for _ in range(3):
        assert never_keeping.list_run_finding_blocks(run_id=RUN) == answer
    assert never_keeping.store.reads == 9                  # the bound disables the cache: every call reads all three again


def test_another_document_is_another_key_whichever_of_the_three_it_is(run: Any) -> None:
    adapter, references = build()
    run(adapter)
    adapter.list_run_finding_blocks(run_id=RUN)
    before = adapter.store.reads
    for role, document in documents(6, 10, shift=5.0).items():
        references_before = dict(references[role])
        references[role] = {"role": role, **adapter.store.put(json.dumps(document).encode("utf-8"))}
        run(adapter)
        adapter.list_run_finding_blocks(run_id=RUN)
        assert adapter.store.reads == before + 3, f"changing only the {role} did not make a miss"
        before = adapter.store.reads
        assert references[role]["sha256"] != references_before["sha256"]


def test_a_cached_derivation_is_not_served_to_another_version(run: Any) -> None:
    adapter, _ = build()
    run(adapter)
    adapter.list_run_finding_blocks(run_id=RUN)
    other, _ = build(store=adapter.store, version=OTHER_VERSION)
    other._geometry_cache = adapter._geometry_cache        # the very cache, with the first version's entry in it
    run(other, version=OTHER_VERSION)
    reads = adapter.store.reads
    other.list_run_finding_blocks(run_id=OTHER_RUN)
    assert adapter.store.reads == reads + 3


def test_the_cache_is_bounded_by_entries_and_by_bytes(run: Any) -> None:
    adapter, references = build(pages=2, lines_per_page=3)
    for number in range(adapter._GEOMETRY_CACHE_ENTRIES + 4):
        for role, document in documents(2, 3, shift=float(number)).items():
            references[role] = {"role": role, **adapter.store.put(json.dumps(document).encode("utf-8"))}
        run(adapter)
        adapter.list_run_finding_blocks(run_id=RUN)
    assert len(adapter._geometry_cache) == adapter._GEOMETRY_CACHE_ENTRIES
    assert adapter._geometry_cache_bytes == sum(weight for _, weight in adapter._geometry_cache.values())

    small = build(pages=2, lines_per_page=3)[0]
    small._GEOMETRY_CACHE_BYTES = 1
    run(small)
    small.list_run_finding_blocks(run_id=RUN)
    assert len(small._geometry_cache) == 0 and small._geometry_cache_bytes == 0     # larger than the budget: derived, never kept


def test_a_hit_does_not_hide_what_a_miss_refuses(run: Any) -> None:
    """The cache keeps what a verified read produced; a read that cannot be verified is still the integrity error it was."""
    adapter, references = build()
    run(adapter)
    adapter.list_run_finding_blocks(run_id=RUN)
    adapter.store.blobs.pop(references[ROLE_PORTAL_BLOCKS]["blob_id"])
    adapter.list_run_finding_blocks(run_id=RUN)            # a hit: the object is not asked for (documented in `_run_geometry`)
    adapter._geometry_cache.clear()
    adapter._geometry_cache_bytes = 0
    with pytest.raises(DomainError) as refused:
        adapter.list_run_finding_blocks(run_id=RUN)        # a miss: the object is asked for, and its absence is not an empty answer
    assert refused.value.code == ErrorCode.STORAGE_INTEGRITY_ERROR


def test_a_reference_without_a_recorded_digest_is_never_kept(run: Any) -> None:
    adapter, references = build()
    references[ROLE_BLOCK_INDEX]["sha256"] = None
    run(adapter)
    adapter._verified_bytes = lambda reference: json.dumps(documents(6, 10)[reference["role"]]).encode("utf-8")   # type: ignore[method-assign]
    adapter.list_run_finding_blocks(run_id=RUN)
    assert len(adapter._geometry_cache) == 0


# --- D-590: the recognised text is the fourth document of the key ------------------------------------------------------------
#
# One page, one line across two portal blocks (the left and the right cell of a row): the geometry alone links the evidence to
# neither, and the recognised text names the right one. So the answer is a function of the recognised text, and a cache that
# did not key on it would serve the answer of the text it first read.

LEFT_CELL, RIGHT_CELL = "blk_" + "e" * 32, "blk_" + "f" * 32
QUOTE = "Степень огнестойкости здания — II."
ROW_EVIDENCE = (SimpleNamespace(finding_observation_id="obs_1", page_number=1, char_start=3, char_end=40, quote=QUOTE),)


def row_documents(left: str, right: str, *, version: str = VERSION) -> dict[str, dict[str, Any]]:
    head = {"artifact_version": ARTIFACT_VERSION, "version_uid": version}
    line = {"block_id": "b_000001", "page_number": 1, "bbox": {"x0": 100.0, "y0": 250.0, "x1": 500.0, "y1": 262.0},
            "char_start": 0, "char_end": 40, "block_ordinal": 0, "bbox_unit": "pt", "bbox_origin": "top_left"}

    def cell(identifier: str, x0: float, x1: float) -> dict[str, Any]:
        return {"portal_block_id": identifier, "page_number": 1, "block_type": "text", "bbox_norm": [x0, 0.3, x1, 0.35]}

    return {
        ROLE_BLOCK_INDEX: {**head, "artifact_role": ROLE_BLOCK_INDEX, "blocks": [line]},
        ROLE_PAGE_INVENTORY: {**head, "artifact_role": ROLE_PAGE_INVENTORY,
                              "pages": [{"page_number": 1, "width_pt": 600.0, "height_pt": 800.0, "rotation_deg": 0}]},
        ROLE_PORTAL_BLOCKS: {**head, "artifact_role": ROLE_PORTAL_BLOCKS,
                             "pages": [{"page_number": 1, "width_px": 1200, "height_px": 1600, "rotation_deg": 0, "geometry": "ok"}],
                             "blocks": [cell(LEFT_CELL, 0.1, 0.5), cell(RIGHT_CELL, 0.5, 0.9)]},
        ROLE_RECOGNISED_TEXT: {**head, "artifact_role": ROLE_RECOGNISED_TEXT, "results_sha256": "0" * 64, "entries": [
            {"portal_block_id": identifier, "page_number": 1, "kind": KIND_RECOGNISED_TEXT, "quote_source": "recognised",
             "text": text, "flags": []}
            for identifier, text in ((LEFT_CELL, left), (RIGHT_CELL, right))
        ]},
    }


def build_row(left: str, right: str, *, store: CountingStore | None = None, with_text: bool = True) -> tuple[Adapter, dict[str, dict[str, Any]]]:
    store = store or CountingStore()
    adapter = Adapter(store)
    for role, document in row_documents(left, right).items():
        if role != ROLE_RECOGNISED_TEXT or with_text:
            adapter.references[role] = {"role": role, **store.put(json.dumps(document).encode("utf-8"))}
    return adapter, adapter.references


def blocks_of_the_row(adapter: Adapter) -> list[str]:
    return adapter.list_run_finding_blocks(run_id=RUN).items[0].portal_block_ids


HOLDS, ELSEWHERE = f"1.3. {QUOTE} Класс конструктивной пожарной опасности — С0.", "Другой пункт, в нём этой строки нет."


def test_a_changed_recognised_text_is_another_key_and_the_cache_does_not_serve_the_answer_of_the_old_one(run: Any) -> None:
    adapter, references = build_row("Пункт 1.3", HOLDS)
    run(adapter, evidence=ROW_EVIDENCE)
    assert blocks_of_the_row(adapter) == [RIGHT_CELL]
    assert adapter.store.reads == 4                         # the index, the inventory, the portal blocks, the recognised text
    assert blocks_of_the_row(adapter) == [RIGHT_CELL] and adapter.store.reads == 4          # a hit asks the store for nothing
    before = references[ROLE_RECOGNISED_TEXT]["sha256"]

    document = row_documents("Пункт 1.3", ELSEWHERE)[ROLE_RECOGNISED_TEXT]
    references[ROLE_RECOGNISED_TEXT] = {"role": ROLE_RECOGNISED_TEXT, **adapter.store.put(json.dumps(document).encode("utf-8"))}
    run(adapter, evidence=ROW_EVIDENCE)
    assert references[ROLE_RECOGNISED_TEXT]["sha256"] != before
    assert blocks_of_the_row(adapter) == []                 # the new text does not hold the quotation: a miss, and the link is gone
    assert adapter.store.reads == 8                         # all four were read again, and the two entries of the cache are kept
    assert len(adapter._geometry_cache) == 2


def test_a_version_without_recognised_text_reads_three_documents_and_keeps_its_own_key(run: Any) -> None:
    adapter, _ = build_row("Пункт 1.3", HOLDS, with_text=False)
    run(adapter, evidence=ROW_EVIDENCE)
    assert blocks_of_the_row(adapter) == [] and adapter.store.reads == 3       # no witness: the geometry alone links nothing here
    assert blocks_of_the_row(adapter) == [] and adapter.store.reads == 3
    (key,) = adapter._geometry_cache
    assert [entry[0] for entry in key[1:]] == [ROLE_BLOCK_INDEX, ROLE_PAGE_INVENTORY, ROLE_PORTAL_BLOCKS]
    # The same three documents with a recognised text are another entry, not the first one served with the text missing.
    with_text, _ = build_row("Пункт 1.3", HOLDS, store=adapter.store)
    with_text._geometry_cache = adapter._geometry_cache
    run(with_text, evidence=ROW_EVIDENCE)
    assert blocks_of_the_row(with_text) == [RIGHT_CELL] and adapter.store.reads == 3 + 4
    assert len(adapter._geometry_cache) == 2


def test_the_answer_with_the_witness_does_not_depend_on_the_cache(run: Any) -> None:
    caching, _ = build_row("Пункт 1.3", HOLDS)
    run(caching, evidence=ROW_EVIDENCE)
    assert blocks_of_the_row(caching) == [RIGHT_CELL]       # the answer is one the witness gave
    never_keeping, _ = build_row("Пункт 1.3", HOLDS)
    never_keeping._GEOMETRY_CACHE_BYTES = 0
    run(never_keeping, evidence=ROW_EVIDENCE)
    for _ in range(3):
        assert never_keeping.list_run_finding_blocks(run_id=RUN) == caching.list_run_finding_blocks(run_id=RUN)
    assert never_keeping.store.reads == 12 and caching.store.reads == 4          # three more reads each


def test_the_recognised_text_counts_in_the_weight_the_cache_is_bounded_by(run: Any) -> None:
    adapter, references = build_row("Пункт 1.3", HOLDS)
    run(adapter, evidence=ROW_EVIDENCE)
    blocks_of_the_row(adapter)
    (_, weight), = adapter._geometry_cache.values()
    assert weight == sum(references[role]["size_bytes"] for role in references)
    assert adapter._geometry_cache_bytes == weight


def test_a_recognised_text_that_cannot_be_verified_is_the_integrity_error_a_geometry_document_is(run: Any) -> None:
    adapter, references = build_row("Пункт 1.3", HOLDS)
    run(adapter, evidence=ROW_EVIDENCE)
    adapter.store.blobs.pop(references[ROLE_RECOGNISED_TEXT]["blob_id"])
    with pytest.raises(DomainError) as refused:
        adapter.list_run_finding_blocks(run_id=RUN)
    assert refused.value.code == ErrorCode.STORAGE_INTEGRITY_ERROR
    assert len(adapter._geometry_cache) == 0                # nothing was kept
