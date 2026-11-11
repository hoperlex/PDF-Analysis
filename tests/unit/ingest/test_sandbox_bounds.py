"""The sandbox of the intake path: a reader's clock, the ZIP import's free disk, the proxy's body.

`REVIEW-FIX-BOUNDS-1102` (findings S8-01, S9-01, S6-01, S4-02). ``af581631`` set every one of
these to "no limit"; each test below fails against that, and the mutations are quoted next to
the test that catches them.
"""

from __future__ import annotations

import io
import os
import re
import time
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace

import pytest

from auditmanager.ingest import envelope
from auditmanager.ingest.comparison_pdf import child, zip_import
from auditmanager.shared.errors import DomainError

REPOSITORY = Path(__file__).resolve().parents[3]
PROXY = REPOSITORY / "infra" / "deploy" / "proxy"

#: A reader that says ``ready`` and then takes ``seconds`` to answer, as a document that loops would.
_SLOW_READER = """
import sys, time
print("ready", flush=True)
time.sleep({seconds})
print('{{"pages": []}}', flush=True)
"""


@pytest.fixture
def slow_reader(tmp_path: Path):
    program = tmp_path / "slow_reader.py"
    program.write_text(_SLOW_READER.format(seconds=20), encoding="utf-8")
    descriptor = os.open(os.devnull, os.O_RDONLY)
    yield program, descriptor
    os.close(descriptor)


class TestTheReaderClock:
    """Mutation: ``reader.communicate(timeout=None)`` -- the test waits the child's 20 s and fails."""

    def test_the_portal_reader_is_stopped_when_its_clock_runs_out(self, slow_reader, monkeypatch) -> None:
        program, descriptor = slow_reader
        monkeypatch.setattr(envelope, "READER_SECONDS", 1)
        started = time.monotonic()
        with pytest.raises(DomainError) as refused:
            envelope._run_reader(program, descriptor, {})  # noqa: SLF001
        assert refused.value.detail_fields["constraint"] == "pdf_reader_limits"
        assert time.monotonic() - started < 15

    def test_the_comparison_child_is_stopped_when_its_clock_runs_out(self, slow_reader) -> None:
        program, descriptor = slow_reader
        started = time.monotonic()
        with pytest.raises(DomainError) as refused:
            child.run_child(program, descriptor, {}, wall_seconds=1)
        assert refused.value.detail_fields["constraint"] == "pdf_reader_limits"
        assert time.monotonic() - started < 15

    def test_the_figures_are_the_measured_ones_and_far_from_the_integer_ceiling(self) -> None:
        assert (envelope.READER_ADDRESS_SPACE, envelope.READER_SECONDS) == (2 * 1024 * 1024 * 1024, 120)  # PDF-READER-ROOM-01
        assert envelope.READER_SECONDS < 3600 and envelope.READER_ADDRESS_SPACE < 2**40


class TestTheZipImportDisk:
    """Mutation: delete the ``shutil.disk_usage`` check in ``import_zip`` -- the first test fails."""

    @staticmethod
    def run(raw: bytes):
        service = SimpleNamespace(_factory=None)
        return zip_import.import_zip(service, project_uid="project", source=io.BytesIO(raw), user_uid="expert",
                                     actor_label="Expert", idempotency_key="key", archive_name="a.zip")

    @pytest.fixture(autouse=True)
    def admission(self, monkeypatch):
        @contextmanager
        def scope(_factory):
            yield SimpleNamespace(execute=lambda *args, **kwargs: None)

        monkeypatch.setattr(zip_import, "session_scope", scope)

    def test_too_little_free_disk_refuses_before_the_archive_is_read(self, monkeypatch) -> None:
        monkeypatch.setattr("shutil.disk_usage", lambda _: SimpleNamespace(free=zip_import.MAX_EXPANDED_BYTES * 2 - 1))
        with pytest.raises(DomainError) as refused:
            self.run(b"")
        assert refused.value.detail_fields["constraint"] == "comparison_zip_temporary_space"

    def test_exactly_enough_free_disk_goes_on_to_the_archive(self, monkeypatch) -> None:
        monkeypatch.setattr("shutil.disk_usage", lambda _: SimpleNamespace(free=zip_import.MAX_EXPANDED_BYTES * 2))
        with pytest.raises(DomainError) as refused:
            self.run(b"")
        assert refused.value.detail_fields["constraint"] == "comparison_zip_empty"

    def test_the_expansion_bound_is_the_sandbox_figure(self) -> None:
        assert zip_import.MAX_EXPANDED_BYTES == 256 * 1024 * 1024
        assert zip_import.ZIP_POLICY.total_bytes == zip_import.MAX_EXPANDED_BYTES
        assert zip_import.ZIP_POLICY.ratio == 100 and zip_import.ZIP_POLICY.member_bytes == 250 * 1024 * 1024


_BODY = re.compile(r"\bclient_max_body_size\s+(\S+?)\s*;")
_TIMEOUTS = re.compile(r"\b(client_body_timeout|proxy_read_timeout|proxy_send_timeout)\s+(\S+?)\s*;")


def unbounded(text: str) -> list[str]:
    """What in a proxy file lifts a body or timeout bound: a zero body size or a day-long timeout."""
    found = [f"client_max_body_size {value}" for value in _BODY.findall(text) if value in {"0", "0m"}]
    for name, value in _TIMEOUTS.findall(text):
        seconds = int(re.sub(r"\D", "", value) or 0) * (3600 if value.endswith("h") else 1)
        if seconds > 3600:
            found.append(f"{name} {value}")
    return found


@pytest.mark.parametrize("name", ["nginx.conf", "tls-server.conf"])
class TestTheProxy:
    """Mutation: write ``client_max_body_size 0;`` or ``proxy_read_timeout 86400s;`` back into either file."""

    def test_no_body_or_timeout_bound_is_lifted(self, name: str) -> None:
        assert unbounded((PROXY / name).read_text(encoding="utf-8")) == []

    def test_the_upload_locations_keep_their_finite_bounds(self, name: str) -> None:
        text = (PROXY / name).read_text(encoding="utf-8")
        uploads = re.findall(r"location ~ \^/(?:api|bff)/v1/projects/\[\^/\]\+/documents[^{]*\{(.*?)\n    \}",
                             text, flags=re.DOTALL)
        assert len(uploads) == 2
        for body in uploads:
            assert "client_max_body_size 260m;" in body
            assert "client_body_timeout 120s;" in body
            assert "proxy_read_timeout 300s;" in body

    def test_the_guard_can_fail(self, name: str) -> None:
        text = (PROXY / name).read_text(encoding="utf-8")
        lifted = text.replace("client_max_body_size 260m;", "client_max_body_size 0;", 1)
        slow = text.replace("proxy_read_timeout 300s;", "proxy_read_timeout 86400s;", 1)
        assert unbounded(lifted) == ["client_max_body_size 0"]
        assert unbounded(slow) == ["proxy_read_timeout 86400s"]
