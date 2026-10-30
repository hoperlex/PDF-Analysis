from __future__ import annotations

import hashlib
import io
import zipfile
from contextlib import contextmanager
from types import SimpleNamespace

import pytest

from auditmanager.ingest.comparison_pdf import zip_import as mod
from auditmanager.shared.errors import DomainError


def archive(entries):
    out = io.BytesIO()
    with zipfile.ZipFile(out, 'w', zipfile.ZIP_STORED) as target:
        for name, data in entries:
            target.writestr(name, data)
    return out.getvalue()


class Service:
    _factory = None

    def __init__(self):
        self.declarations = []
        self.parts = []
        self.completed = []
        self._read = lambda source: SimpleNamespace(facts=SimpleNamespace(page_count=1))

    def create_upload(self, **kwargs):
        self.declarations.append(kwargs)
        if not hasattr(self, 'upload'):
            files = tuple(SimpleNamespace(file_id=f'file-{i}', display_name=f.display_name, sha256=f.sha256,
                         size_bytes=f.size_bytes, state='declared') for i, f in enumerate(kwargs['files']))
            self.upload = SimpleNamespace(upload_id='upload-1', part_size_bytes=4, files=files)
        return self.upload

    def put_part(self, **kwargs):
        self.parts.append(kwargs)

    def complete_file(self, **kwargs):
        self.completed.append(kwargs)
        next(f for f in self.upload.files if f.file_id == kwargs['file_id']).state = 'verified'

    def get_upload(self, **kwargs):
        return self.upload


@pytest.fixture(autouse=True)
def admission(monkeypatch):
    @contextmanager
    def scope(_factory):
        yield SimpleNamespace(execute=lambda *args, **kwargs: None)
    monkeypatch.setattr(mod, 'session_scope', scope)
    monkeypatch.setattr('shutil.disk_usage', lambda _: SimpleNamespace(free=1024 ** 3))


def run(service, raw, key='request-1'):
    return mod.import_zip(service, project_uid='project', source=io.BytesIO(raw), user_uid='expert',
                          actor_label='Expert', idempotency_key=key, archive_name='source.zip')


def test_real_reader_imports_nested_members_and_replay_reuses_receipts():
    raw = archive([('docs/v1.pdf', b'first'), ('nested.zip', archive([('v2.pdf', b'second')]))])
    service = Service()
    uploaded = run(service, raw)
    assert len(uploaded.files) == 2
    assert [f.display_name for f in uploaded.files] == ['docs/v1.pdf', 'nested/v2.pdf']
    assert all(f.state == 'verified' for f in uploaded.files)
    assert service.declarations[0]['source_sha256'] == hashlib.sha256(raw).hexdigest()
    assert all('v1' not in item['idempotency_key'] and 'docs' not in item['idempotency_key'] for item in service.parts)
    first_parts = list(service.parts)
    run(service, raw)
    assert service.parts == first_parts
    assert service.declarations[0]['idempotency_key'] == service.declarations[1]['idempotency_key']


@pytest.mark.parametrize('name', ['__MACOSX/file.pdf', '../escape.pdf', 'document.txt'])
def test_unsafe_or_non_pdf_member_refuses_whole_archive_before_declaration(name):
    service = Service()
    with pytest.raises(DomainError):
        run(service, archive([('good.pdf', b'good'), (name, b'bad')]))
    assert service.declarations == []
    assert service.parts == []


def test_late_pdf_refusal_does_not_declare_or_publish_any_member():
    service = Service()
    def read(source):
        if source.read() == b'bad':
            from auditmanager.shared.errors import ErrorCode
            raise DomainError(ErrorCode.VALIDATION_FAILED, field='file', constraint='bad_pdf')
        return SimpleNamespace(facts=SimpleNamespace(page_count=1))
    service._read = read
    with pytest.raises(DomainError):
        run(service, archive([('good.pdf', b'good'), ('bad.pdf', b'bad')]))
    assert service.declarations == []


def test_raw_limit_refuses_before_declaration(monkeypatch):
    monkeypatch.setattr(mod, 'MAX_ARCHIVE_BYTES', 5)
    service = Service()
    with pytest.raises(DomainError):
        run(service, b'123456')
    assert service.declarations == []


def test_interrupted_import_resumes_verified_members_without_resending_them():
    service = Service()
    raw = archive([('one.pdf', b'1234'), ('two.pdf', b'5678')])
    original = service.put_part
    def interrupt(**kwargs):
        if kwargs['file_id'] == 'file-1':
            raise OSError('interrupted')
        original(**kwargs)
    service.put_part = interrupt
    with pytest.raises(OSError):
        run(service, raw)
    service.put_part = original
    run(service, raw)
    assert [part['file_id'] for part in service.parts] == ['file-0', 'file-1']
