"""Probe 1 -- upload to version, over HTTP to the running API (`W55B-QA-01`).

Crosses STREAM (the transport), INGEST (the bundle reader, the envelope, the publication)
and the documents read path, as a client meets them. Each test states its expected outcome
in its docstring; the expectation is the plan's or the contract's, never the code's.
"""

from __future__ import annotations

import json
import re

import pytest

from w55b_qa_support import (
    TEXTLESS_THRESHOLD,
    bundle_manifest,
    call,
    committed,
    create_project,
    manifest_entry,
    markdown_bodies,
    member_by_suffix,
    new_key,
    pdfium_page_characters,
    rebuild,
    rows,
    scalar,
    sha256_hex,
    upload,
    zip_members,
)

ACCEPTED = (
    "ar_baseline.zip",
    "ar_baseline_minimal.zip",
    "ar_baseline_ocr_defects.zip",
    "image_only_with_block.zip",
    "pages_31.zip",
)

#: Member role in ``bundle_manifest.json`` -> the manifest role the version must hold it under.
STORED_ROLE = {
    "pdf": "source.document",
    "blocks": "source.structured_companion",
    "results_md": "source.markdown",
    "stamp_audit": "source.stamp_audit",
}


def _documents_in(project_uid: str, token: str) -> list[dict]:
    answer = call("GET", f"/projects/{project_uid}/documents?limit=100", token=token)
    assert answer.status == 200, answer
    return answer.json()["items"]


@pytest.mark.parametrize("name", ACCEPTED)
def test_each_valid_bundle_becomes_a_version_holding_its_members_under_their_roles(
    api, engine, expert, name
) -> None:
    """Expected: ``201``; the version's ``input_manifest`` holds exactly one entry per stored
    member -- ``source.document``, ``source.structured_companion``, ``source.markdown`` and
    ``source.stamp_audit`` when the bundle has one -- each with the member's own digest and
    size; the HTML is in no entry and in no ``blob`` row; the version's digest, size and page
    count are the PDF member's; ``streamDocumentVersionContent`` serves the PDF's bytes."""
    entry = manifest_entry(bundle_manifest(), name)
    project = create_project(expert, f"QA P1 {name}")
    answer = upload(project, committed(name), expert)
    assert answer.status == 201, answer
    version = answer.json()

    members = {m["role"]: m for m in entry["members"]}
    expected = {
        STORED_ROLE[role]: (m["sha256"], m["size"]) for role, m in members.items() if role in STORED_ROLE
    }
    held = {e["role"]: (e["sha256"], e["size_bytes"]) for e in version["input_manifest"]}
    assert held == expected
    assert len(version["input_manifest"]) == len(expected)

    pdf = members["pdf"]
    assert (version["sha256"], version["byte_size"], version["page_count"]) == (
        pdf["sha256"], pdf["size"], entry["page_count"],
    )
    if "results_html" in members:
        html_sha = members["results_html"]["sha256"]
        assert html_sha not in {e["sha256"] for e in version["input_manifest"]}
        assert scalar(engine, "SELECT count(*) FROM blob WHERE sha256 = :s", s=html_sha) == 0

    content = call("GET", f"/versions/{version['version_uid']}/content", token=expert)
    assert content.status == 200, content
    assert sha256_hex(content.body) == pdf["sha256"]


@pytest.mark.parametrize("name", ACCEPTED)
def test_the_character_counts_and_textless_pages_are_stored_as_an_independent_count_gives_them(
    api, engine, expert, name
) -> None:
    """Expected: ``document_version.text_character_count`` equals the sum over pages of the
    length of pypdfium2's ``get_text_range()`` (counted here); ``textless_pages`` the
    ascending 1-based pages under 50 such characters (empty when none); and
    ``recognised_character_count`` the characters of the TEXT bodies of ``_results.md`` on
    those pages (read here by a reader of this module, not the product's)."""
    archive = committed(name)
    members = zip_members(archive)
    pdf = member_by_suffix(members, ".pdf")
    per_page = pdfium_page_characters(pdf)
    textless = [index + 1 for index, count in enumerate(per_page) if count < TEXTLESS_THRESHOLD]
    blocks = json.loads(member_by_suffix(members, "_blocks.json"))
    bodies = markdown_bodies(member_by_suffix(members, "_results.md").decode("utf-8"))
    on_textless = {
        b["block_id"] for b in blocks["blocks"]
        if b["block_type"] == "text" and b["page_index"] + 1 in textless
    }
    recognised = sum(len(bodies[i][1]) for i in on_textless)

    project = create_project(expert, f"QA P1 counts {name}")
    answer = upload(project, archive, expert)
    assert answer.status == 201, answer
    stored = rows(
        engine,
        "SELECT text_character_count, textless_pages, recognised_character_count "
        "FROM document_version WHERE version_uid = :v",
        v=answer.json()["version_uid"],
    )
    assert len(stored) == 1
    count, pages, recognised_count = stored[0]
    assert count == sum(per_page)
    assert list(pages) == textless
    assert recognised_count == recognised


def test_the_same_bundle_and_key_replay_the_same_version_and_create_nothing(api, engine, expert) -> None:
    """Expected: the second request with the same key and the same bundle answers ``201`` with
    the same ``version_uid``; the project still holds one document; no ``blob`` row and no
    ``document_version`` row was added."""
    project = create_project(expert, "QA P1 replay")
    key = new_key("replay")
    first = upload(project, committed("ar_baseline.zip"), expert, key=key)
    assert first.status == 201, first
    blobs = scalar(engine, "SELECT count(*) FROM blob")
    versions = scalar(engine, "SELECT count(*) FROM document_version")
    again = upload(project, committed("ar_baseline.zip"), expert, key=key)
    assert again.status == 201, again
    assert again.json()["version_uid"] == first.json()["version_uid"]
    assert len(_documents_in(project, expert)) == 1
    assert scalar(engine, "SELECT count(*) FROM blob") == blobs
    assert scalar(engine, "SELECT count(*) FROM document_version") == versions


def test_a_bundle_differing_only_in_its_html_is_another_command(api, engine, expert) -> None:
    """Expected: the HTML is in the command fingerprint although it is never stored. With the
    first request's key, a bundle whose only difference is ``_results.html`` is refused
    ``409 idempotency_key_reuse`` and creates nothing; with a fresh key it is a new version
    whose stored members are byte-identical to the first (so its manifest digests are
    equal), and still no blob of either HTML exists."""
    original = committed("ar_baseline.zip")
    html = member_by_suffix(zip_members(original), "_results.html")
    changed_html = html + b"\n<!-- W55B-QA-01: one byte more than the portal wrote -->\n"
    variant = rebuild(original, {"_results.html": changed_html})

    project = create_project(expert, "QA P1 html fingerprint")
    key = new_key("html")
    first = upload(project, original, expert, key=key)
    assert first.status == 201, first
    versions = scalar(engine, "SELECT count(*) FROM document_version")

    conflict = upload(project, variant, expert, key=key)
    assert conflict.status == 409, conflict
    assert conflict.json()["error_code"] == "idempotency_key_reuse"
    assert scalar(engine, "SELECT count(*) FROM document_version") == versions

    fresh = upload(project, variant, expert)
    assert fresh.status == 201, fresh
    assert fresh.json()["version_uid"] != first.json()["version_uid"]
    digests = lambda v: sorted((e["role"], e["sha256"]) for e in v["input_manifest"])  # noqa: E731
    assert digests(fresh.json()) == digests(first.json())
    for blob in (html, changed_html):
        assert scalar(engine, "SELECT count(*) FROM blob WHERE sha256 = :s", s=sha256_hex(blob)) == 0


@pytest.mark.parametrize("label", ["application/x-zip-compressed", "application/octet-stream", None])
def test_a_bundle_is_recognised_by_its_bytes_whatever_label_the_browser_sends(api, expert, label) -> None:
    """Expected: ``201`` -- the contract recognises the ZIP by its magic bytes whatever label
    the browser sends (or none)."""
    project = create_project(expert, f"QA P1 label {label}")
    answer = upload(project, committed("ar_baseline_minimal.zip"), expert, content_type=label)
    assert answer.status == 201, answer


@pytest.mark.parametrize("label", ["application/pdf", "application/zip"])
def test_a_bare_pdf_is_refused_with_the_bundle_sentence_and_nothing_is_created(api, engine, expert, label) -> None:
    """Expected: ``422 validation_failed`` with ``field: file`` and ``constraint:
    portal_bundle_required`` whether the PDF is labelled as a PDF or as a ZIP; the message is
    the Russian sentence telling the user to upload the recognition portal's ZIP; the
    project gains no document and the database no version or blob."""
    pdf = member_by_suffix(zip_members(committed("ar_baseline.zip")), ".pdf")
    project = create_project(expert, f"QA P1 bare pdf {label}")
    versions = scalar(engine, "SELECT count(*) FROM document_version")
    blobs = scalar(engine, "SELECT count(*) FROM blob")
    answer = upload(project, pdf, expert, filename="ar_baseline.pdf", content_type=label)
    assert answer.status == 422, answer
    body = answer.json()
    assert body["error_code"] == "validation_failed"
    assert body["details"] == {"field": "file", "constraint": "portal_bundle_required"}
    message = body["message"]
    assert re.search("[А-Яа-яЁё]", message), message
    assert "ZIP" in message and "портал" in message, message
    assert _documents_in(project, expert) == []
    assert scalar(engine, "SELECT count(*) FROM document_version") == versions
    assert scalar(engine, "SELECT count(*) FROM blob") == blobs


@pytest.mark.parametrize(
    ("name", "field", "constraint"),
    [
        ("encrypted.zip", "content", "not_encrypted"),
        ("image_only.zip", "page_text", "every_page_has_extractable_text"),
    ],
)
def test_the_committed_negative_bundles_are_refused_with_the_registered_codes(
    api, expert, name, field, constraint
) -> None:
    """Expected (``bundle_manifest.json`` and the error catalog): ``422 validation_failed``
    with exactly the manifest's ``field`` and ``constraint``, and no document created."""
    entry = manifest_entry(bundle_manifest(), name)
    assert entry["expected"] == "refused"
    assert entry["refusal"] == {"constraint": constraint, "field": field}
    project = create_project(expert, f"QA P1 negative {name}")
    answer = upload(project, committed(name), expert)
    assert answer.status == 422, answer
    body = answer.json()
    assert body["error_code"] == "validation_failed"
    assert body["details"] == {"field": field, "constraint": constraint}
    assert _documents_in(project, expert) == []


def test_the_page_ceiling_is_500_and_501_is_refused_with_the_page_count_constraint(api, expert) -> None:
    """Expected: a generated 500-page bundle is accepted (``201``, ``page_count: 500``); the same
    generator at 501 pages is ``422 validation_failed`` with ``field: page_count`` and
    ``constraint: 1 <= page_count <= 500``. ``pages_31.zip`` -- a negative under the old
    30-page ceiling -- is accepted above."""
    from portal_bundle import generated

    project = create_project(expert, "QA P1 page ceiling")
    at = upload(project, generated.bundle_with_pages(500), expert)
    assert at.status == 201, at
    assert at.json()["page_count"] == 500
    over = upload(project, generated.bundle_with_pages(501), expert)
    assert over.status == 422, over
    assert over.json()["details"] == {"field": "page_count", "constraint": "1 <= page_count <= 500"}
