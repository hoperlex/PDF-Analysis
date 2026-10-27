"""Fixtures of the comparison-upload suites. The database, the object store and the project come from
``tests/integration/ingest/conftest.py`` (a throwaway migrated database, a bucket per test, ``TRUNCATE`` between tests)."""

from __future__ import annotations

import pytest
from sqlalchemy.orm import Session, sessionmaker

from auditmanager.ingest.comparison_pdf.public import ComparisonUploadService, ComparisonVersionOrderService
from auditmanager.storage import S3BlobStore


@pytest.fixture
def comparison(store: S3BlobStore, session_factory: sessionmaker[Session]) -> ComparisonUploadService:
    return ComparisonUploadService(store, session_factory=session_factory)


@pytest.fixture
def orders(session_factory: sessionmaker[Session]) -> ComparisonVersionOrderService:
    return ComparisonVersionOrderService(session_factory=session_factory)


@pytest.fixture
def user(session_factory: sessionmaker[Session]) -> str:
    """An expert account that exists (a classification names its confirmer by a foreign key to ``app_user``)."""
    from tests.support.accounts import complete_expert_account

    with session_factory() as session:
        record = complete_expert_account(session, "comparison-ingest")
        session.commit()
        return str(record.user_uid)


class SpyStore:
    """The real store, with every call to the multipart port and to ``open_stream`` recorded (never faked)."""

    def __init__(self, inner: S3BlobStore) -> None:
        self._inner = inner
        self.calls: list[str] = []
        self.fail: dict[str, BaseException] = {}

    def __getattr__(self, name: str):
        target = getattr(self._inner, name)
        if not callable(target):
            return target

        def call(*args, **kwargs):
            self.calls.append(name)
            failure = self.fail.pop(name, None)
            if failure is not None:
                raise failure
            return target(*args, **kwargs)

        return call

    def count(self, name: str) -> int:
        return self.calls.count(name)


@pytest.fixture
def spy(store: S3BlobStore) -> SpyStore:
    return SpyStore(store)


@pytest.fixture
def watched(spy: SpyStore, session_factory: sessionmaker[Session]) -> ComparisonUploadService:
    """A service over the spying store, for the tests that assert on what the store was (not) asked."""
    return ComparisonUploadService(spy, session_factory=session_factory)  # type: ignore[arg-type]


@pytest.fixture
def open_uploads(raw_s3, s3_settings):
    """The multipart uploads the bucket still has open, read through a plain boto3 client."""

    def read() -> list[str]:
        return [item["Key"] for item in raw_s3.list_multipart_uploads(Bucket=s3_settings.bucket).get("Uploads", [])]

    return read
