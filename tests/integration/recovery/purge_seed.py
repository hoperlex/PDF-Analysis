"""A stand in miniature, for the product-purge tests: product data, accounts and a norm corpus.

`STAND-PURGE-TOOL-01`. The purge has to be shown on a database that looks like the deployed
stand will look: the product tables full (everything `synthetic_drill_seed` writes through the
owning contexts' public surfaces -- projects, versions, a published run with findings and
decisions, classification and its correction, work assignments, price and vendor lists, an
optimisation pass with decisions, and five-plus real Blobs in a real bucket), the accounts side
populated (the administrator's password changed, a pending registration request, an approval's
command receipt), and the corpus present (a snapshot with documents, paragraphs, chunks, an
embedding, a verified retrieval set, confirmed custody admissions and bindings, `norm_custody.*`
journal events, a designated current snapshot, and the corpus' objects in the same bucket).

One product graph (`_seed_finding` of the migration suite) cites the corpus, so the purge meets a
product row with a foreign key INTO a keep table. A temporary object a product row names, and a
stray object nothing names, are put in the bucket too: the first must go, the second must stay.

`digest_of` is deliberately NOT the tool's digest: it is the test's own, over `row_to_json`, so a
comparison with it does not share a bug with what it checks.
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from typing import Any

import boto3
from botocore.client import Config
from sqlalchemy import Engine, text
from sqlalchemy.orm import Session

from auditmanager.access.public import UserRepository
from auditmanager.access.registrations import RegistrationRepository
from auditmanager.shared.db.config import DatabaseSettings, parse_database_url
from auditmanager.shared.db.engine import create_database_engine
from auditmanager.shared.identity import AuditEventId, NormsSnapshotId
from auditmanager.storage.public import canonical_object_key_for_recovery
from scripts.recovery import synthetic_drill_seed as seed
from tests.integration.db.test_norm_citations_migration import QUOTE, _seed_finding

NEW_ADMIN_PASSWORD = "A-changed-administrator-password-2026"  # noqa: S105 - a lane's literal
STRAY_KEY = "blobs/ZZ/ZZ/ZZZZZZZZZZZZZZZZZZZZZZZZZZ"
STRAY_BYTES = b"nothing names me, so nothing deletes me"


def s3(values: Mapping[str, str]) -> Any:
    return boto3.client(
        "s3", endpoint_url=values["S3_ENDPOINT_URL"], region_name=values["S3_REGION"],
        aws_access_key_id=values["S3_ACCESS_KEY_ID"], aws_secret_access_key=values["S3_SECRET_ACCESS_KEY"],
        config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
    )


def bucket_profile(client: Any, bucket: str) -> dict[str, tuple[int, str]]:
    """``key -> (size, sha256 of the bytes actually read)`` for every object."""
    profile = {}
    for page in client.get_paginator("list_objects_v2").paginate(Bucket=bucket):
        for item in page.get("Contents", []):
            data = client.get_object(Bucket=bucket, Key=item["Key"])["Body"].read()
            profile[item["Key"]] = (len(data), hashlib.sha256(data).hexdigest())
    return profile


def digest_of(engine: Engine, table: str, where: str = "true") -> tuple[int, str]:
    """The test's own fingerprint: sorted ``row_to_json`` texts, hashed in Python."""
    with engine.connect() as connection:
        rows = sorted(r[0] for r in connection.execute(
            text(f'SELECT row_to_json(t)::text FROM public."{table}" t WHERE {where}')))
    return len(rows), hashlib.sha256("\n".join(rows).encode()).hexdigest()


def seed_stand(values: Mapping[str, str], settings: DatabaseSettings) -> dict[str, Any]:
    """Fill a migrated, empty lane. Returns identities and the keys the tests assert on."""
    summary = seed.seed_source_lane(values)
    engine = create_database_engine(settings)
    client = s3(values)
    bucket = values["S3_BUCKET"]
    try:
        # --- accounts: the administrator's password CHANGED, a pending request, an approval receipt
        with Session(engine) as session:
            admin = session.execute(text("SELECT user_uid FROM app_user WHERE login = 'admin'")).scalar_one()
            changed = UserRepository().change_password(
                session, user_uid=admin, current_password="password", new_password=NEW_ADMIN_PASSWORD)
            assert changed is not None
            RegistrationRepository().submit(
                session, login="pending.person@example.com", password="a-long-enough-password-1",
                last_name="Иванов", first_name="Пётр")
            session.commit()
        with engine.begin() as connection:
            command = "cmd_" + str(AuditEventId.new()).removeprefix("evt_")
            connection.execute(text(
                "INSERT INTO command_record (command_id, command_type, idempotency_key, payload_fingerprint, state) "
                "VALUES (:c, 'approve_registration', 'approve-seed-1', :f, 'in_progress')"),
                {"c": command, "f": "a" * 64})
            connection.execute(text(
                "UPDATE command_record SET state = 'succeeded', outcome = CAST('{}' AS jsonb) WHERE command_id = :c"),
                {"c": command})

        # --- the corpus: a verified retrieval set, custody, and one product graph that cites it
        with engine.begin() as connection:
            finding, observation = _seed_finding(
                connection, citation_count=1, with_0023=True, category="evacuation")
            citation = connection.execute(text(
                "SELECT o.run_id, r.norms_snapshot_id, r.norm_retrieval_set_id, "
                "d.norm_document_id, p.norm_paragraph_id "
                "FROM finding_observation o JOIN audit_run r ON r.run_id = o.run_id "
                "JOIN norm_paragraph p ON p.norms_snapshot_id = r.norms_snapshot_id "
                "JOIN norm_document d ON d.norm_document_pk = p.norm_document_pk "
                "WHERE o.finding_observation_id = :o"), {"o": observation}).mappings().one()
            connection.execute(text(
                "INSERT INTO finding_observation_norm_citation "
                "(finding_observation_id, citation_ordinal, run_id, norms_snapshot_id, "
                "norm_retrieval_set_id, norm_document_id, norm_paragraph_id, quote, "
                "char_start, char_length, state) "
                "VALUES (:observation, 1, :run_id, :norms_snapshot_id, :norm_retrieval_set_id, "
                ":norm_document_id, :norm_paragraph_id, :quote, 0, :length, 'verified')"),
                {**citation, "observation": observation, "quote": QUOTE, "length": len(QUOTE)})
            snapshot = connection.execute(text("SELECT norms_snapshot_id FROM norm_retrieval_set")).scalar_one()
            event = str(AuditEventId.new())
            connection.execute(text(
                "INSERT INTO norm_current_snapshot_event (event_id, from_snapshot_id, to_snapshot_id, actor_user_uid) "
                "VALUES (:e, NULL, :s, :a)"), {"e": event, "s": snapshot, "a": admin})
            connection.execute(text(
                "INSERT INTO norm_current_snapshot (norms_snapshot_id, event_id) VALUES (:s, :e)"),
                {"s": snapshot, "e": event})
            for number, kind in enumerate(("admitted", "confirmed", "bound"), start=1):
                connection.execute(text(
                    "INSERT INTO audit_event (audit_event_id, event_type, aggregate_type, aggregate_id, payload) "
                    "VALUES (:e, :t, 'NormCustody', :a, CAST('{}' AS jsonb))"),
                    {"e": str(AuditEventId.new()), "t": f"norm_custody.{kind}",
                     "a": "nad_" + str(NormsSnapshotId.new()).removeprefix("ns_")})
            keep_blobs = connection.execute(text(
                "SELECT b.blob_id, b.sha256, b.size_bytes, b.media_type FROM blob b WHERE b.blob_id IN "
                "(SELECT blob_id FROM norm_custody_binding UNION SELECT set_blob_id FROM norm_retrieval_set "
                "UNION SELECT catalogue_blob_id FROM norm_retrieval_set)")).all()
        norm_keys = []
        for blob_id, sha, size, media in keep_blobs:
            key = canonical_object_key_for_recovery(blob_id)
            client.put_object(Bucket=bucket, Key=key, Body=b"N" * size, ContentType=media, Metadata={
                "blob-id": blob_id, "blob-role": "norm_source", "content-sha256": sha, "content-size": str(size)})
            norm_keys.append(key)

        # --- a temporary object a product row names (must go) and a stray one nothing names (must stay)
        with engine.connect() as connection:
            token = connection.execute(text(
                "SELECT upload_token FROM analysis_artifact_publication ORDER BY upload_token LIMIT 1")).scalar_one()
        client.put_object(Bucket=bucket, Key=f"temporary/{token}", Body=b"a staged upload a crash left behind")
        client.put_object(Bucket=bucket, Key=STRAY_KEY, Body=STRAY_BYTES)
        summary.update(admin=admin, norm_keys=sorted(norm_keys), temporary_key=f"temporary/{token}",
                       citing_finding=finding, snapshot=snapshot)
        return summary
    finally:
        engine.dispose()


def settings_of(url: str) -> DatabaseSettings:
    return DatabaseSettings(url=parse_database_url(url))
