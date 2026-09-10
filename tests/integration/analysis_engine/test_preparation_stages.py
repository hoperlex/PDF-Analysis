"""The three deterministic preparation stages, over the real baseline corpus.

Read ``P02_SEAMS`` section 4.1 alongside this file. The strongest evidence this
session can produce is here:
:func:`test_manifest_quotations_resolve_at_their_declared_pages` resolves all twelve
manifest quotations through the published ``prepared.text_layer``, and
:func:`test_offsets_are_code_points_and_not_bytes` is the assertion a byte-offset
implementation cannot pass.
"""

from __future__ import annotations

import json
import unicodedata
from typing import Any

import pytest
from sqlalchemy import text as sql_text

from auditmanager.analysis.public import (
    ARTIFACT_VERSION,
    NORMALIZATION_ID,
    ROLE_BLOCK_INDEX,
    ROLE_DOCUMENT_GRAPH,
    ROLE_PAGE_CROPS,
    ROLE_PAGE_INVENTORY,
    ROLE_SOURCE_DOCUMENT,
    ROLE_TEXT_LAYER,
    StageStatus,
    document_text,
    run_stage,
)
from auditmanager.shared.db import session_scope
from auditmanager.storage import sha256_of

#: A well-formed ``DocumentVersion`` identity. The stages take it as a parameter;
#: they never allocate one, because identity allocation is not this seam's business.
VERSION_UID = "ver_01M2545JSD15ETSNNV904X991J"

# --- the pipeline, run once per session --------------------------------------


@pytest.fixture(scope="session")
def prepared(store: Any, source_blob: Any) -> dict[str, Any]:
    """Run all three stages in dependency order and return every result and document."""
    first = run_stage(
        "source_preparation",
        version_uid=VERSION_UID,
        inputs={ROLE_SOURCE_DOCUMENT: source_blob},
        blob_store=store,
    )
    assert first.status is StageStatus.SUCCEEDED, first.error

    second = run_stage(
        "page_geometry_extraction",
        version_uid=VERSION_UID,
        inputs={
            ROLE_PAGE_INVENTORY: first.artifact(ROLE_PAGE_INVENTORY).blob_id,
            ROLE_TEXT_LAYER: first.artifact(ROLE_TEXT_LAYER).blob_id,
        },
        blob_store=store,
    )
    assert second.status is StageStatus.SUCCEEDED, second.error

    third = run_stage(
        "document_context_build",
        version_uid=VERSION_UID,
        inputs={
            ROLE_BLOCK_INDEX: second.artifact(ROLE_BLOCK_INDEX).blob_id,
            ROLE_TEXT_LAYER: first.artifact(ROLE_TEXT_LAYER).blob_id,
        },
        blob_store=store,
    )
    assert third.status is StageStatus.SUCCEEDED, third.error

    def read(result: Any, role: str) -> dict[str, Any]:
        return json.loads(store.read(result.artifact(role).blob_id))

    return {
        "results": (first, second, third),
        "page_inventory": read(first, ROLE_PAGE_INVENTORY),
        "text_layer": read(first, ROLE_TEXT_LAYER),
        "block_index": read(second, ROLE_BLOCK_INDEX),
        "page_crops": read(second, ROLE_PAGE_CROPS),
        "document_graph": read(third, ROLE_DOCUMENT_GRAPH),
    }


@pytest.fixture(scope="session")
def whole_text(prepared: dict[str, Any]) -> str:
    """The one document-global character sequence every offset indexes."""
    return document_text(prepared["text_layer"])


# --- THE offset evidence -----------------------------------------------------


def test_manifest_quotations_resolve_at_their_declared_pages(
    prepared: dict[str, Any], whole_text: str, manifest_anchors: tuple[dict[str, Any], ...]
) -> None:
    """All twelve manifest quotations resolve through the published text layer.

    The manifest declares each quotation by ``page`` and by an offset *within that
    page's text*. This test converts that to a document-global offset the only way
    section 4.1 allows - the page's ``char_start`` plus the page-local offset - and
    slices the concatenated sequence.

    **This is the test that fails under a byte-offset implementation.** Every
    quotation here is Russian, so each Cyrillic character occupies two bytes in UTF-8.
    If ``char_start`` were a byte count, the page offsets would run ahead of the code
    point positions by roughly the number of Cyrillic characters on every preceding
    page, and the slice would land in the middle of an unrelated sentence - while a
    test written against an English fixture would still pass.
    """
    assert len(manifest_anchors) == 12, (
        "the manifest is expected to declare twelve anchored quotations; "
        f"found {len(manifest_anchors)}"
    )
    starts = {
        page["page_number"]: page["char_start"] for page in prepared["text_layer"]["pages"]
    }

    resolved = 0
    misses: list[str] = []
    for anchor in manifest_anchors:
        quotation = unicodedata.normalize("NFC", anchor["quotation"])
        start = starts[anchor["page"]] + anchor["char_offset_in_page_text"]
        end = start + len(quotation)
        if whole_text[start:end] == quotation:
            resolved += 1
        else:
            misses.append(
                f"page {anchor['page']} offset {anchor['char_offset_in_page_text']}: "
                f"expected {quotation[:40]!r}, found {whole_text[start:end][:40]!r}"
            )

    assert resolved == 12, "\n".join(misses)


def test_offsets_are_code_points_and_not_bytes(
    prepared: dict[str, Any], whole_text: str
) -> None:
    """``total_char_count`` counts code points. On this corpus that is provable.

    The Russian text is strictly longer in UTF-8 bytes than in code points, so a
    declared count equal to the byte length would be a byte count and this assertion
    is what catches it. The ``.encode`` here is *deliberate and confined to the test*:
    it exists to construct the wrong answer and show the implementation did not give
    it.
    """
    text_layer = prepared["text_layer"]
    byte_length = len(whole_text.encode("utf-8"))

    assert text_layer["total_char_count"] == len(whole_text)
    assert text_layer["total_char_count"] < byte_length, (
        "the corpus must contain non-ASCII text for this discrimination to be "
        "meaningful"
    )

    for page in text_layer["pages"]:
        assert page["char_end"] - page["char_start"] == len(page["text"])
        assert page["char_end"] - page["char_start"] != len(page["text"].encode("utf-8"))


def test_quotations_land_wholly_within_their_declared_line(
    prepared: dict[str, Any], manifest_anchors: tuple[dict[str, Any], ...]
) -> None:
    """The resolution contract ``expected_issues.json`` declares, preserved."""
    pages = {page["page_number"]: page["text"] for page in prepared["text_layer"]["pages"]}
    for anchor in manifest_anchors:
        line_index = anchor.get("line_index_in_page_text")
        if line_index is None:
            continue
        lines = pages[anchor["page"]].split("\n")
        assert line_index < len(lines)
        assert unicodedata.normalize("NFC", anchor["quotation"]) in lines[line_index]


# --- prepared.text_layer, section 4.3 ----------------------------------------


def test_text_layer_pages_are_contiguous_and_gapless(prepared: dict[str, Any]) -> None:
    pages = prepared["text_layer"]["pages"]
    assert [page["page_number"] for page in pages] == list(range(1, len(pages) + 1))
    assert pages[0]["char_start"] == 0
    for previous, current in zip(pages, pages[1:]):
        assert current["char_start"] == previous["char_end"]
    assert pages[-1]["char_end"] == prepared["text_layer"]["total_char_count"]


def test_pages_are_concatenated_with_no_separator(
    prepared: dict[str, Any], whole_text: str
) -> None:
    """Section 4.1: no separator is inserted between pages.

    Asserted positively: the slice of the whole sequence at each page's declared
    interval is exactly that page's text, which cannot hold if anything - a newline,
    a form feed, a space - were inserted between them.
    """
    for page in prepared["text_layer"]["pages"]:
        assert whole_text[page["char_start"] : page["char_end"]] == page["text"]
    assert len(whole_text) == sum(
        len(page["text"]) for page in prepared["text_layer"]["pages"]
    )


def test_text_layer_declares_its_extractor_and_normalization(
    prepared: dict[str, Any],
) -> None:
    text_layer = prepared["text_layer"]
    assert text_layer["artifact_role"] == ROLE_TEXT_LAYER
    assert text_layer["artifact_version"] == ARTIFACT_VERSION
    assert text_layer["version_uid"] == VERSION_UID
    assert text_layer["normalization"]["id"] == NORMALIZATION_ID
    assert text_layer["extractor"]["name"] == "pdfplumber"
    assert text_layer["extractor"]["version"]
    assert len(text_layer["extractor"]["options_sha256"]) == 64


def test_the_published_text_is_already_normalized(whole_text: str) -> None:
    """Normalization is applied once, by this stage. ``B4`` normalizes nothing again.

    If the published text were not already in NFC, the grounding gate - which compares
    exactly, after this one normalization and nothing else - would reject quotations
    that differ from it only by composition.
    """
    assert unicodedata.normalize("NFC", whole_text) == whole_text


# --- prepared.page_inventory, section 4.2 ------------------------------------


def test_page_inventory_shape(prepared: dict[str, Any], source_blob: Any, baseline_pdf: bytes) -> None:
    inventory = prepared["page_inventory"]
    assert inventory["artifact_role"] == ROLE_PAGE_INVENTORY
    assert inventory["artifact_version"] == ARTIFACT_VERSION
    assert inventory["source_blob_id"] == str(source_blob)
    assert inventory["source_sha256"] == sha256_of(baseline_pdf)
    assert inventory["page_count"] == len(inventory["pages"])
    assert [page["page_number"] for page in inventory["pages"]] == list(
        range(1, inventory["page_count"] + 1)
    )
    for page in inventory["pages"]:
        assert page["has_text_layer"] is True
        assert page["rotation_deg"] in (0, 90, 180, 270)
        assert page["width_pt"] > 0 and page["height_pt"] > 0


def test_page_inventory_char_counts_match_the_text_layer(
    prepared: dict[str, Any],
) -> None:
    layer = {page["page_number"]: page for page in prepared["text_layer"]["pages"]}
    for page in prepared["page_inventory"]["pages"]:
        span = layer[page["page_number"]]
        assert page["char_count"] == span["char_end"] - span["char_start"]


# --- geometry.block_index, section 4.4 ---------------------------------------


def test_block_ids_are_contract_shaped_and_sequential(prepared: dict[str, Any]) -> None:
    blocks = prepared["block_index"]["blocks"]
    assert blocks
    ordered = sorted(blocks, key=lambda b: (b["page_number"], b["block_ordinal"]))
    assert ordered == blocks, "blocks are stored in (page_number, block_ordinal) order"
    for position, block in enumerate(ordered, start=1):
        assert block["block_id"] == f"b_{position:06d}"


def test_block_spans_resolve_and_stay_inside_their_page(
    prepared: dict[str, Any], whole_text: str
) -> None:
    pages = {
        page["page_number"]: (page["char_start"], page["char_end"])
        for page in prepared["text_layer"]["pages"]
    }
    for block in prepared["block_index"]["blocks"]:
        start, end = block["char_start"], block["char_end"]
        page_start, page_end = pages[block["page_number"]]
        assert page_start <= start <= end <= page_end
        assert whole_text[start:end]


def test_block_text_reassembles_its_page(prepared: dict[str, Any], whole_text: str) -> None:
    """Every page's blocks, joined by the line separator, reproduce the page text.

    This is what makes the block index and the text layer one artifact pair rather
    than two independent derivations that happen to agree today.
    """
    by_page: dict[int, list[str]] = {}
    for block in prepared["block_index"]["blocks"]:
        by_page.setdefault(block["page_number"], []).append(
            whole_text[block["char_start"] : block["char_end"]]
        )
    for page in prepared["text_layer"]["pages"]:
        assert "\n".join(by_page[page["page_number"]]) == page["text"]


def test_block_index_binds_itself_to_the_text_layer_it_used(
    prepared: dict[str, Any], store: Any
) -> None:
    published = prepared["results"][0].artifact(ROLE_TEXT_LAYER)
    assert prepared["block_index"]["text_layer_sha256"] == published.sha256
    assert sha256_of(store.read(published.blob_id)) == published.sha256


def test_block_boxes_are_top_left_points_after_rotation(prepared: dict[str, Any]) -> None:
    for block in prepared["block_index"]["blocks"]:
        assert block["bbox_unit"] == "pt"
        assert block["bbox_origin"] == "top_left"
        bbox = block["bbox"]
        assert bbox["x0"] <= bbox["x1"]
        # y increases downwards, so y0 is the top edge and y1 the bottom.
        assert bbox["y0"] <= bbox["y1"]


def test_block_boxes_lie_within_their_page(prepared: dict[str, Any]) -> None:
    pages = {
        page["page_number"]: (page["width_pt"], page["height_pt"])
        for page in prepared["page_inventory"]["pages"]
    }
    for block in prepared["block_index"]["blocks"]:
        width, height = pages[block["page_number"]]
        bbox = block["bbox"]
        assert 0 <= bbox["x0"] and bbox["x1"] <= width + 1
        assert 0 <= bbox["y0"] and bbox["y1"] <= height + 1


# --- geometry.page_crops, section 4.5 and OD-04 ------------------------------


def test_page_crops_is_present_and_explicitly_empty(prepared: dict[str, Any]) -> None:
    """``OD-04``: the role is present, schema-valid and explicitly empty."""
    crops = prepared["page_crops"]
    assert crops["artifact_role"] == ROLE_PAGE_CROPS
    assert crops["artifact_version"] == ARTIFACT_VERSION
    assert crops["crop_policy"] == "none"
    assert crops["crops"] == []


def test_the_crop_policy_is_echoed_in_the_stage_metrics(prepared: dict[str, Any]) -> None:
    """``OD-04`` requires the policy to be visible on the result, not only in the artifact."""
    metrics = prepared["results"][1].metrics
    assert metrics["crop_policy"] == "none"
    assert metrics["crop_count"] == 0


# --- context.document_graph, section 4.6 -------------------------------------


def test_document_graph_anchors_all_resolve(prepared: dict[str, Any]) -> None:
    graph = prepared["document_graph"]
    block_ids = {block["block_id"] for block in prepared["block_index"]["blocks"]}
    section_ids = {section["section_id"] for section in graph["sections"]}

    for section in graph["sections"]:
        assert section["section_id"].startswith("s_") and len(section["section_id"]) == 6
        assert set(section["block_ids"]) <= block_ids
        parent = section["parent_section_id"]
        assert parent is None or parent in section_ids

    for reference in graph["references"]:
        assert reference["from_block_id"] in block_ids
        assert reference["to_section_id"] in section_ids
        assert reference["kind"] in {
            "cross_reference",
            "continuation",
            "table_caption",
            "figure_caption",
        }

    for entry in graph["neighbourhood"]:
        assert entry["block_id"] in block_ids
        for key in ("previous_block_id", "next_block_id"):
            assert entry[key] is None or entry[key] in block_ids


def test_every_block_belongs_to_exactly_one_section(prepared: dict[str, Any]) -> None:
    """Assignment is total, which is why the front-matter section exists."""
    graph = prepared["document_graph"]
    block_ids = [block["block_id"] for block in prepared["block_index"]["blocks"]]
    assigned = [
        block_id for section in graph["sections"] for block_id in section["block_ids"]
    ]
    assert sorted(assigned) == sorted(block_ids)
    assert len(assigned) == len(set(assigned))


def test_the_section_hierarchy_is_a_tree(prepared: dict[str, Any]) -> None:
    parents = {
        section["section_id"]: section["parent_section_id"]
        for section in prepared["document_graph"]["sections"]
    }
    for section_id in parents:
        seen = {section_id}
        cursor = parents[section_id]
        while cursor is not None:
            assert cursor not in seen, "the section hierarchy contains a cycle"
            seen.add(cursor)
            cursor = parents.get(cursor)


def test_the_graph_binds_itself_to_the_block_index(prepared: dict[str, Any]) -> None:
    published = prepared["results"][1].artifact(ROLE_BLOCK_INDEX)
    assert prepared["document_graph"]["block_index_sha256"] == published.sha256


def test_neighbourhood_is_the_document_order_chain(prepared: dict[str, Any]) -> None:
    graph = prepared["document_graph"]
    blocks = [block["block_id"] for block in prepared["block_index"]["blocks"]]
    entries = {entry["block_id"]: entry for entry in graph["neighbourhood"]}
    assert set(entries) == set(blocks)
    for index, block_id in enumerate(blocks):
        entry = entries[block_id]
        assert entry["previous_block_id"] == (blocks[index - 1] if index else None)
        assert entry["next_block_id"] == (
            blocks[index + 1] if index + 1 < len(blocks) else None
        )


def test_the_document_graph_recovers_the_corpus_sections(prepared: dict[str, Any]) -> None:
    """The seven numbered sections of the corpus, plus its front matter."""
    titles = [section["title"] for section in prepared["document_graph"]["sections"]]
    numbered = [title for title in titles if title[:1].isdigit()]
    assert len(numbered) == 7
    assert numbered[0].startswith("1. ")
    assert numbered[-1].startswith("7. ")


# --- every required output role is present, with identity and checksum -------


@pytest.mark.parametrize(
    ("index", "stage_id"),
    [
        (0, "source_preparation"),
        (1, "page_geometry_extraction"),
        (2, "document_context_build"),
    ],
)
def test_every_required_output_role_is_published(
    prepared: dict[str, Any], index: int, stage_id: str
) -> None:
    from auditmanager.analysis.public import default_registry

    result = prepared["results"][index]
    definition = default_registry().stage(stage_id)
    assert result.stage_id == stage_id
    assert result.stage_version == definition.stage_version
    assert result.status is StageStatus.SUCCEEDED
    assert result.error is None
    assert set(definition.required_output_roles) <= result.roles


def test_every_artifact_reference_carries_identity_and_checksum(
    prepared: dict[str, Any], store: Any
) -> None:
    for result in prepared["results"]:
        for reference in result.artifacts:
            assert reference.blob_id.startswith("blob_")
            assert len(reference.sha256) == 64
            assert reference.size_bytes > 0
            assert reference.media_type == "application/json"
            payload = store.read(reference.blob_id)
            assert sha256_of(payload) == reference.sha256
            assert len(payload) == reference.size_bytes


def test_no_artifact_reference_contains_a_key_url_or_credential(
    prepared: dict[str, Any],
) -> None:
    """A reference is content-addressed and nothing else.

    Checked over the serialized result document rather than the dataclass fields, so
    a value smuggled into an existing field is caught as well as a new field.
    """
    forbidden_keys = {
        "bucket",
        "key",
        "object_key",
        "uri",
        "url",
        "path",
        "endpoint",
        "credential",
        "access_key",
        "secret",
        "token",
    }
    forbidden_fragments = ("://", "s3://", "/", "\\")

    for result in prepared["results"]:
        for reference in result.to_document()["artifacts"]:
            assert not forbidden_keys & reference.keys()
            for name, value in reference.items():
                if name in ("role", "media_type"):
                    continue  # a media type legitimately contains "/"
                assert isinstance(value, (str, int))
                if isinstance(value, str):
                    for fragment in forbidden_fragments:
                        assert fragment not in value, (name, value)


# --- determinism -------------------------------------------------------------


def test_two_runs_publish_byte_identical_text_layer_and_block_index(
    store: Any, source_blob: Any
) -> None:
    """Deterministic re-execution over identical inputs gives identical checksums."""
    digests = []
    for _ in range(2):
        first = run_stage(
            "source_preparation",
            version_uid=VERSION_UID,
            inputs={ROLE_SOURCE_DOCUMENT: source_blob},
            blob_store=store,
        )
        assert first.status is StageStatus.SUCCEEDED, first.error
        second = run_stage(
            "page_geometry_extraction",
            version_uid=VERSION_UID,
            inputs={
                ROLE_PAGE_INVENTORY: first.artifact(ROLE_PAGE_INVENTORY).blob_id,
                ROLE_TEXT_LAYER: first.artifact(ROLE_TEXT_LAYER).blob_id,
            },
            blob_store=store,
        )
        assert second.status is StageStatus.SUCCEEDED, second.error
        digests.append(
            (
                first.artifact(ROLE_TEXT_LAYER).sha256,
                first.artifact(ROLE_PAGE_INVENTORY).sha256,
                second.artifact(ROLE_BLOCK_INDEX).sha256,
                store.read(first.artifact(ROLE_TEXT_LAYER).blob_id),
                store.read(second.artifact(ROLE_BLOCK_INDEX).blob_id),
            )
        )
    assert digests[0] == digests[1]


def test_a_blob_id_is_derived_from_content_so_a_rerun_reuses_it(
    prepared: dict[str, Any], store: Any, source_blob: Any
) -> None:
    """The same artifact bytes resolve to the same ``blob_id`` on a second run."""
    rerun = run_stage(
        "source_preparation",
        version_uid=VERSION_UID,
        inputs={ROLE_SOURCE_DOCUMENT: source_blob},
        blob_store=store,
    )
    assert (
        rerun.artifact(ROLE_TEXT_LAYER).blob_id
        == prepared["results"][0].artifact(ROLE_TEXT_LAYER).blob_id
    )


# --- the engine touches no canonical row -------------------------------------


def test_the_engine_writes_no_canonical_metadata_row(
    database_url: str, store: Any, source_blob: Any
) -> None:
    """The stage engine persists nothing. ``P2-RUN-01`` owns persistence.

    Run against real PostgreSQL: the row count of every table in the public schema is
    taken before and after a full stage run, and must be unchanged.
    """

    def snapshot() -> dict[str, int]:
        with session_scope() as session:
            tables = [
                row[0]
                for row in session.execute(
                    sql_text(
                        "SELECT tablename FROM pg_tables "
                        "WHERE schemaname = 'public' ORDER BY tablename"
                    )
                )
            ]
            return {
                table: session.execute(
                    sql_text(f'SELECT count(*) FROM "{table}"')  # noqa: S608 - pg_tables
                ).scalar_one()
                for table in tables
            }

    before = snapshot()
    assert before, "the migrated database is expected to declare tables"

    result = run_stage(
        "source_preparation",
        version_uid=VERSION_UID,
        inputs={ROLE_SOURCE_DOCUMENT: source_blob},
        blob_store=store,
    )
    assert result.status is StageStatus.SUCCEEDED, result.error

    assert snapshot() == before
