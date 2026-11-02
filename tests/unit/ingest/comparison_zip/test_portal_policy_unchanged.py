"""The portal bundle's reader is what it was: the policy parameter changed nothing for it.

`CMP-INGEST-ZIP-01` (ADR-0025 decision 12: «the policy parameter is the only edit of
``bundle_archive.py``», and the portal bundle's behaviour stays byte for byte). The proof is in
three layers, and this module is the cheapest of them:

1. **the existing suite, unmodified**: ``tests/integration/ingest/test_bundle_archive.py`` (269
   tests: 67 small negatives, the size-driven families, the ZIP64 and descriptor positives, the
   name decoding, the memory test) and the other ingest tests that read the portal reader. They
   need no container and are run, unedited, in the report;
2. **a differential over a corpus**, run against the base commit and the edited tree, with the
   outcomes compared as JSON (558 archives, 400 of them seeded fuzz of a committed bundle): in
   the report, because its second tree is another commit;
3. **this module**: the default is the portal policy and nothing else, the portal refuses with
   its own names and sentences and keeps its bounds, and the two policies are different -- an
   archive one accepts the other refuses.
"""

from __future__ import annotations

import inspect
import io
from typing import Any

import pytest

from auditmanager.ingest import bundle_archive as ba
from auditmanager.ingest.bundle_archive import PORTAL_POLICY, ArchivePolicy, extract_bundle
from auditmanager.shared.errors import DomainError
from tests.unit.ingest.comparison_zip import zip_builders as z
from tests.unit.ingest.comparison_zip.zip_builders import (  # noqa: F401  (the autouse fixture)
    MiB,
    PDF_HEADER,
    REPOSITORY_ROOT,
    accept,
    build,
    entry,
    pdf,
    private_temporary_directory,
    refusal,
    zw,
)

BUNDLES = REPOSITORY_ROOT / "fixtures" / "synthetic" / "ar" / "bundles"


def _outcome(data: bytes, **options: Any) -> list[Any]:
    """What the reader did with ``data``: the members it kept, or the refusal's whole text."""
    try:
        with extract_bundle(io.BytesIO(data), **options) as bundle:
            return ["ok", {
                role: [m.display_name, m.size, m.sha256, m.path.read_bytes().hex()[:64] if m.path else None]
                for role, m in bundle.members.items()
            }]
    except DomainError as refused:
        return ["refused", dict(refused.detail_fields), str(refused)]


def test_the_default_policy_is_the_portal_policy_and_it_is_nothing_but_the_portal_rules() -> None:
    assert inspect.signature(extract_bundle).parameters["policy"].default is PORTAL_POLICY
    assert isinstance(PORTAL_POLICY, ArchivePolicy)
    assert PORTAL_POLICY.judge is ba._judge_entries
    assert PORTAL_POLICY.translate is None, "the portal's refusals are never renamed"
    assert PORTAL_POLICY.max_directory_bytes is None, "the portal reads the directory it always did"


def test_the_portal_bounds_are_the_ruled_ones() -> None:
    assert ba.MAX_ENTRIES == 8
    assert ba.TOTAL_BYTES == 300 * MiB
    assert ba.MAX_RATIO == 100
    assert ba.MEMBER_BYTES == 250 * MiB
    assert ba.TEXT_MEMBER_BYTES == 16 * MiB
    assert ba.BLOCKS_MEMBER_BYTES == 4 * MiB
    assert ba.STAMP_AUDIT_BYTES == 4 * MiB
    assert ba.DEFAULT_LIMITS == ba.BundleLimits(
        member_bytes=250 * MiB, text_member_bytes=16 * MiB, blocks_member_bytes=4 * MiB,
        stamp_audit_bytes=4 * MiB, total_bytes=300 * MiB, ratio=100, entries=8,
    )


@pytest.mark.parametrize("name", sorted(p.name for p in BUNDLES.glob("*.zip")))
def test_a_committed_bundle_is_read_the_same_with_the_default_and_with_the_portal_policy_named(
    name: str,
) -> None:
    data = (BUNDLES / name).read_bytes()
    default = _outcome(data)
    assert default == _outcome(data, policy=PORTAL_POLICY)
    assert default[0] == "ok", name
    assert set(default[1]) >= {"pdf", "blocks", "results_md"}


@pytest.mark.parametrize(
    ("archive", "constraint", "sentence"),
    [
        (build(*[pdf(f"m{i}.pdf") for i in range(9)]), "bundle_entry_count",
         "The archive holds more entries than a portal bundle can."),
        (build(pdf("../a.pdf")), "bundle_member_name",
         "A member of the archive has a name that is not a plain file name."),
        (build(entry("a.pdf", b"x", external_attr=zw.SYMLINK)), "bundle_symlink",
         "A member of the archive is a symbolic link."),
        (build(entry("a.pdf", b"x", flags=1)), "bundle_encrypted_member",
         "A member of the archive is encrypted."),
        (build(pdf("a.pdf"), pdf("A.pdf")), "bundle_duplicate_member",
         "Two members of the archive have the same name."),
        (build(pdf("a.pdf")), "bundle_member_set", None),
        (build(entry("a.pdf", PDF_HEADER, declared_size=300 * MiB), entry("a_blocks.json", b"{}"),
               entry("a_results.md", b"x")), "bundle_member_size",
         "A member of the archive is larger than a portal bundle allows."),
        (build(z.directory("a/"), pdf("a/b.pdf")), "bundle_directory_entry",
         "The archive holds a directory entry, which a portal bundle never does."),
        (b"%PDF-1.7 a bare pdf", "portal_bundle_required", None),
    ],
    ids=["entry-count", "name", "symlink", "encrypted", "duplicate", "member-set", "member-size",
         "directory", "bare-pdf"],
)
def test_the_portal_still_refuses_in_its_own_words(
    archive: bytes, constraint: str, sentence: str | None
) -> None:
    refused = _outcome(archive)
    assert refused[0] == "refused"
    assert refused[1] == {"field": "file", "constraint": constraint}
    if sentence is not None:
        assert refused[2] == sentence
    assert refused == _outcome(archive, policy=PORTAL_POLICY)


def test_a_set_the_portal_refuses_is_accepted_by_the_set_policy_and_the_other_way_round() -> None:
    """The two policies are two different rules: three PDFs are a set and not a bundle, and a
    bundle -- a PDF with its block list and recognised text -- is a bundle and not a set."""
    three_pdfs = build(pdf("a.pdf", b"1"), pdf("b.pdf", b"2"), pdf("c.pdf", b"3"))
    assert _outcome(three_pdfs)[1:2] == [{"field": "file", "constraint": "bundle_member_set"}]
    with accept(three_pdfs) as found:
        assert len(found.members) == 3

    bundle = (BUNDLES / "ar_baseline_minimal.zip").read_bytes()
    assert _outcome(bundle)[0] == "ok"
    assert refusal(bundle) == "comparison_zip_member_kind"


def test_a_portal_refusal_is_never_renamed_even_where_the_set_policy_would_rename_it() -> None:
    hostile = [
        build(pdf("../a.pdf")), build(pdf("a.pdf"), pdf("A.pdf")), b"not a zip",
        build(entry("a.pdf", zw.Fill(8 * MiB, 0, PDF_HEADER), method=8, deflate="zlib")),
    ]
    for archive in hostile:
        outcome = _outcome(archive)
        assert outcome[0] == "refused"
        constraint = outcome[1]["constraint"]
        assert not constraint.startswith("comparison_zip_"), constraint


def test_the_portal_has_no_central_directory_bound_and_reads_the_directory_it_always_did() -> None:
    """Three members with 60 000-byte comments make a directory of 180 KB. The portal reads it,
    as it did before the parameter existed; the set policy's bound (``directory_bytes``) is the
    set's and is not applied to it."""
    commented = build(
        *[entry(n, PDF_HEADER, comment=b"c" * 60_000) for n in
          ("a.pdf", "a_blocks.json", "a_results.md")]
    )
    assert _outcome(commented)[0] == "ok"
    assert refusal(commented, policy=z.SetPolicy(directory_bytes=4096)) == "comparison_zip_unreadable"


def test_the_set_policy_is_not_wired_into_the_portal_path() -> None:
    """Nothing the portal upload runs imports the set package: the portal's own modules do not
    mention it, so a defect of the set reader cannot be reached from an upload of a bundle."""
    ingest = REPOSITORY_ROOT / "src" / "auditmanager" / "ingest"
    for name in ("bundle_members.py", "bundle_envelope.py", "service.py", "__init__.py", "public.py"):
        assert "comparison_zip" not in (ingest / name).read_text(encoding="utf-8"), name
    assert sorted(ba.__all__) == sorted(set(ba.__all__))
