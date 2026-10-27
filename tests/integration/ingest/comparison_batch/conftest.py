"""Fixtures of the batch-operation suites. The database, the object store and the project come from
``tests/integration/ingest/conftest.py`` (a throwaway migrated database, a bucket per test, ``TRUNCATE`` between tests;
``TRUNCATE ... project CASCADE`` empties the comparison tables too, queue included)."""

from __future__ import annotations

import pytest
from sqlalchemy.orm import Session, sessionmaker

from auditmanager.ingest.comparison_batch.public import BatchLifecycle, ComparisonBatchService
from auditmanager.ingest.comparison_pdf.public import ComparisonUploadService
from auditmanager.storage import S3BlobStore
from tests.integration.ingest.comparison_batch.support import Harness, Queue


@pytest.fixture
def user(session_factory: sessionmaker[Session]) -> str:
    """An expert account that exists (a classification names its confirmer by a foreign key to ``app_user``)."""
    from tests.support.accounts import complete_expert_account

    with session_factory() as session:
        record = complete_expert_account(session, "comparison-batch")
        session.commit()
        return str(record.user_uid)


@pytest.fixture
def lifecycle() -> BatchLifecycle:
    """The sweep is due at once here (the product waits five minutes for a part still on its way)."""
    return BatchLifecycle(sweep_delay_seconds=0.0)


@pytest.fixture
def h(store: S3BlobStore, session_factory: sessionmaker[Session], project, user: str, lifecycle: BatchLifecycle) -> Harness:
    comparison = ComparisonUploadService(store, session_factory=session_factory)
    batches = ComparisonBatchService(comparison, session_factory=session_factory, lifecycle=lifecycle)
    return Harness(comparison=comparison, batches=batches, sessions=session_factory, project_uid=str(project.project_uid), user=user)


@pytest.fixture
def queue(session_factory: sessionmaker[Session], engine, store: S3BlobStore, lifecycle: BatchLifecycle) -> Queue:
    return Queue(session_factory, engine, store, lifecycle=lifecycle)


@pytest.fixture
def open_uploads(raw_s3, s3_settings):
    """The multipart uploads the bucket still has open, read through a plain boto3 client (not the code under test)."""

    def read() -> list[str]:
        return sorted(item["Key"] for item in raw_s3.list_multipart_uploads(Bucket=s3_settings.bucket).get("Uploads", []))

    return read
