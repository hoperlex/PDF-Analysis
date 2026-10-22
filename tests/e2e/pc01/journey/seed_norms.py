#!/usr/bin/env python3
"""Put a small, synthetic normative snapshot into a LANE's own database.

    PYTHONPATH=src .venv/bin/python tests/e2e/pc01/journey/seed_norms.py          # reads .env
    PYTHONPATH=src .venv/bin/python tests/e2e/pc01/journey/seed_norms.py --check   # read-only

`BETA-LIVE-JOURNEY-01`. The journey's «Нормы» steps (search, catalogue, the administrator's
designation of the current snapshot) need two things a fresh lane database does not have: a
snapshot that qualifies for designation, and one that does not. The real corpus (674
documents, 5.4 GB of bundle) cannot be loaded on a lane, so this writes the smallest rows the
screens read -- by plain SQL, the way `tests/integration/norms/search/conftest.py` (`Corpus`)
writes them for the search suites, so the seed shares no code with what it feeds:

* snapshot A, three documents with a few paragraphs each, the chunk and embedding completion
  rows and a confirmed PDF binding for every document: **qualified**, not yet current, so the
  administrator can designate it from the screen. `PC01-JOURNEY-GAPS-01`: the bound bytes are also
  put into the lane's own object store (the `S3_*` names of its `.env`), so the document view's
  `streamNormDocumentContent` has an object to serve and the journey can open the PDF at a page. The
  bytes are a stand-in, not a PDF: the endpoint serves what the binding names, and the viewer inside
  the browser is not what the journey asserts;
* snapshot B, one document and nothing else: **not qualified**, so the screen must say why
  and offer no button.

Nothing is made current here -- designating is what a step of the journey does, through the
screen. Every run adds one more pair, so a lane that already designated a snapshot can be
given another to designate.

**It refuses to run against anything but a database whose name says it is a lane's** (the
name must contain `journey` or `lane`), and it prints the database it wrote to. The
synthetic text is Russian prose about fire-safety and architectural clauses, invented for the
journey; none of it is from a real norm.

Exit status: 0 written (or checked), 1 refused, 2 a usage or environment error (a database, or an
object store, the environment does not name -- the seed never falls back to writing rows without
the objects they claim).
"""

from __future__ import annotations

import argparse
import hashlib
import os
import sys
from pathlib import Path

from sqlalchemy import text

REPOSITORY_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPOSITORY_ROOT / "src"))

#: Real slugs of the W54 snapshot (as the catalogue suite uses them), so the designation
#: derivation the screen shows is the one the real corpus gets.
SP_54 = "СП_54_13330_2022__Свод_правил__Здания_жилые_многоквартирные"
SP_1 = "СП_1_13130_2020__Свод_правил__Системы_противопожарной_защиты"
ORDER_288 = "Приказ_МЧС_России_от_24_04_2013_N_288_(ред__от_27_06_2023)"
SP_104 = "СП_104_13330_2016__Свод_правил__Инженерная_защита_территори"

PARAGRAPHS = {
    SP_54: [
        ("5.1", "Высота жилых помещений от пола до потолка должна быть не менее 2,5 м."),
        ("5.2", "Эвакуационные выходы из квартир должны быть обозначены и свободны от предметов."),
    ],
    SP_1: [
        ("4.2", "Эвакуационные выходы должны быть обозначены знаками пожарной безопасности."),
        ("4.3", "Ширина эвакуационного выхода в свету должна быть не менее 0,8 м."),
    ],
    ORDER_288: [
        (None, "Настоящий приказ устанавливает порядок обозначения эвакуационных путей."),
    ],
}


#: The names the seed needs from the lane's environment: the database, and the object store
#: the bound PDFs are put into.
ENVIRONMENT_NAMES = (
    "DATABASE_URL",
    "S3_ENDPOINT_URL",
    "S3_REGION",
    "S3_ACCESS_KEY_ID",
    "S3_SECRET_ACCESS_KEY",
    "S3_BUCKET",
)


def load_environment() -> None:
    """Fill the lane's names from its `.env` when the environment lacks them; never override.

    A missing `DATABASE_URL` ends the run here. A missing `S3_*` name ends it in `main`, with the
    object store's own typed error naming the variable.
    """
    missing = [name for name in ENVIRONMENT_NAMES if not os.environ.get(name)]
    if not missing:
        return
    dotenv = REPOSITORY_ROOT / ".env"
    if dotenv.is_file():
        for raw in dotenv.read_text(encoding="utf-8").splitlines():
            line = raw.strip().removeprefix("export ").strip()
            name, _, value = line.partition("=")
            name = name.strip()
            if name not in missing:
                continue
            value = value.strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
                value = value[1:-1]
            os.environ[name] = value
    if not os.environ.get("DATABASE_URL"):
        raise SystemExit("no DATABASE_URL in the environment and none in .env: run from a lane worktree")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("--check", action="store_true", help="read the snapshots and write nothing")
    args = parser.parse_args(argv)
    load_environment()

    from auditmanager.shared.db.config import DatabaseSettings, parse_database_url
    from auditmanager.shared.db.engine import create_database_engine
    from auditmanager.shared.db.session import create_session_factory
    from auditmanager.shared.identity import NormDocumentId, NormParagraphId, NormsSnapshotId
    from auditmanager.shared.identity.ulid import new_ulid
    from auditmanager.storage import derive_blob_id
    from auditmanager.storage.public import (
        BlobMetadataRepository,
        S3BlobStore,
        S3StorageSettings,
        StorageError,
        VerifiedBlob,
        parse_blob_id,
        parse_blob_role,
    )

    settings = DatabaseSettings(url=parse_database_url(os.environ["DATABASE_URL"]))
    database = settings.url.database or ""
    if not any(word in database for word in ("journey", "lane")):
        print(
            f"seed_norms: refusing to write to database {database!r}: its name does not say it "
            "is a lane's (it must contain 'journey' or 'lane').",
            file=sys.stderr,
        )
        return 1
    engine = create_database_engine(settings)
    session_factory = create_session_factory(engine)
    try:
        store = S3BlobStore(S3StorageSettings.from_env())
        store.check_access()
    except StorageError as error:
        print(
            f"seed_norms: the object store the bound PDFs are put into cannot be used ({error!r}). "
            "Set the S3_* names of the lane's .env; the seed writes no row that claims an object it "
            "did not store.",
            file=sys.stderr,
        )
        return 2

    if args.check:
        with engine.connect() as connection:
            rows = connection.execute(text(
                "SELECT s.norms_snapshot_id, s.document_count, "
                "(SELECT count(*) FROM norm_chunk_build b WHERE b.norms_snapshot_id = s.norms_snapshot_id), "
                "(SELECT norms_snapshot_id FROM norm_current_snapshot) = s.norms_snapshot_id "
                "FROM norms_snapshot s ORDER BY s.norms_snapshot_id"
            )).all()
        for row in rows:
            print(f"snapshot {row[0]} documents={row[1]} built={row[2]} current={row[3]}")
        with engine.connect() as connection:
            bound = [
                row[0]
                for row in connection.execute(text(
                    "SELECT DISTINCT blob_id FROM norm_custody_binding WHERE role = 'norm_source'"
                ))
            ]
        absent = 0
        for blob_id in bound:
            try:
                store.inspect(parse_blob_id(blob_id))
            except StorageError:
                absent += 1
        print(f"seed_norms: {len(rows)} snapshot(s) in {database}; {len(bound)} bound PDF(s), {absent} without an object")
        return 0

    def run(sql: str, **parameters) -> None:
        with engine.begin() as connection:
            connection.execute(text(sql), parameters)

    def scalar(sql: str, **parameters):
        with engine.connect() as connection:
            return connection.execute(text(sql), parameters).scalar()

    def snapshot(documents: int) -> str:
        identity = str(NormsSnapshotId.new())
        tail = identity[-12:].lower()
        base = f"2026-07-23+{documents}d.{tail}"
        run(
            "INSERT INTO norms_snapshot (norms_snapshot_id, content_key, base_content_key, "
            "content_digest, undated_documents, document_count, repair_count, "
            "unreliable_count, segmentation_profile) VALUES (:s, :content, :base, :digest, "
            "0, :documents, 0, 0, 'markdown-v1')",
            s=identity, content=base, base=base, digest="d" * 64, documents=documents,
        )
        return identity

    def document(snapshot_id: str, slug: str) -> str:
        identity = str(NormDocumentId.new())
        run(
            "INSERT INTO norm_document (norm_document_id, norms_snapshot_id, source_document_ref, "
            "slug, title, doc_type, source_attribution, pdf_page_count, block_count, "
            "page_heading_count, recognised_characters, paragraph_count) VALUES (:d, :s, :ref, "
            ":slug, :title, :doc_type, 'consultant_plus', 12, 1, 0, 10, 0)",
            d=identity, s=snapshot_id, ref=f"ref-{identity[-8:]}", slug=slug,
            title=slug.split("__", 1)[-1].replace("_", " ") or slug,
            doc_type=slug.split("_", 1)[0],
        )
        return identity

    def paragraph(document_id: str, body: str, ordinal: int, clause: str | None) -> None:
        run(
            "INSERT INTO norm_paragraph (norm_paragraph_id, norms_snapshot_id, norm_document_pk, "
            "ordinal, page_label, block_ref, char_offset, char_length, kind, clause_number, "
            "text, text_reliability) SELECT :p, d.norms_snapshot_id, d.norm_document_pk, "
            ":ordinal, '1', :block, 0, char_length(:body), 'body', :clause, :body, 'reliable' "
            "FROM norm_document d WHERE d.norm_document_id = :d",
            p=str(NormParagraphId.new()), d=document_id, ordinal=ordinal,
            block=f"blk_{ordinal:06d}", clause=clause, body=body,
        )

    def build(snapshot_id: str) -> None:
        run(
            "INSERT INTO norm_chunk_build (norms_snapshot_id, chunking_profile, "
            "target_characters, chunk_count) VALUES (:s, 'characters-v2:1200', 1200, 0) "
            "ON CONFLICT DO NOTHING", s=snapshot_id,
        )
        run(
            "INSERT INTO norm_embedding_build (norms_snapshot_id, chunking_profile, "
            "embedding_profile, chunk_count, window_count, embedding_set_sha256) "
            "VALUES (:s, 'characters-v2:1200', 'bge-m3-dense-v1', 0, 0, :sha)",
            s=snapshot_id, sha="e" * 64,
        )

    def bind_pdf(document_id: str) -> None:
        data = f"%PDF-1.7 synthetic journey norm {document_id}".encode()
        sha256 = hashlib.sha256(data).hexdigest()
        blob_id = derive_blob_id(sha256=sha256, size=len(data))
        # The object first, then the rows that claim it: a binding with no object is the state the
        # document view used to meet (a store error), and the one this seed must not leave.
        published = store.put_blob(
            data,
            declared_sha256=sha256,
            declared_size=len(data),
            role=parse_blob_role("norm_source"),
            media_type="application/pdf",
        )
        if str(published.blob_id) != str(blob_id):
            raise SystemExit(f"seed_norms: the store published {published.blob_id}, the seed derived {blob_id}")
        repository = BlobMetadataRepository()
        with session_factory() as session:
            repository.record_verified(
                session,
                VerifiedBlob(
                    blob_id=blob_id, upload_token="journey-norm-seed", sha256=sha256,
                    size=len(data), role=parse_blob_role("norm_source"),
                    media_type="application/pdf",
                ),
            )
            repository.mark_available(session, blob_id)
            session.commit()
        ref = scalar(
            "SELECT source_document_ref FROM norm_document WHERE norm_document_id = :d",
            d=document_id,
        )
        admission = f"nad_{new_ulid()}"
        slot = {
            "role": "norm_source", "target_kind": "norm_document", "target_id": document_id,
            "anchor_kind": "pdf", "anchor": ref,
        }
        run(
            "INSERT INTO norm_custody_admission (norm_custody_admission_id, role, target_kind, "
            "target_id, anchor_kind, anchor, blob_id, declared_size_bytes, declared_sha256, "
            "media_type) VALUES (:a, :role, :target_kind, :target_id, :anchor_kind, :anchor, "
            ":blob, :size, :sha, 'application/pdf')",
            a=admission, blob=str(blob_id), size=len(data), sha=sha256, **slot,
        )
        run(
            "UPDATE norm_custody_admission SET state = 'confirmed', "
            "confirmed_at = clock_timestamp() WHERE norm_custody_admission_id = :a",
            a=admission,
        )
        run(
            "INSERT INTO norm_custody_binding (norm_custody_binding_id, "
            "norm_custody_admission_id, role, target_kind, target_id, anchor_kind, anchor, "
            "blob_id) VALUES (:b, :a, :role, :target_kind, :target_id, :anchor_kind, :anchor, "
            ":blob)",
            b=f"nbd_{new_ulid()}", a=admission, blob=str(blob_id), **slot,
        )

    qualified = snapshot(len(PARAGRAPHS))
    for slug, entries in PARAGRAPHS.items():
        identity = document(qualified, slug)
        for ordinal, (clause, body) in enumerate(entries, start=1):
            paragraph(identity, body, ordinal, clause)
        bind_pdf(identity)
    build(qualified)

    unqualified = snapshot(1)
    document(unqualified, SP_104)

    print(f"seed_norms: wrote to {database}")
    print(f"  qualified snapshot   {qualified} ({len(PARAGRAPHS)} documents, built, PDFs bound and stored)")
    print(f"  unqualified snapshot {unqualified} (1 document, no build)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
