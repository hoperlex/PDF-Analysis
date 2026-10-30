from __future__ import annotations

import io
import json
import zipfile
from xml.etree import ElementTree as ET

import pytest

from auditmanager.comparison.report.technical_export import render_html, render_xlsx
from auditmanager.shared.errors import DomainError


def source():
    return {'series': {'series_id': 'series-1', 'state': 'running', 'display_title': '=SUM(1,2)<script>'},
            'versions': {'v1': {'sha256': 'a' * 64, 'size_bytes': 10, 'page_count': 1}},
            'transitions': [{'transition_id': 't1', 'transition_no': 1, 'source_version_uid': 'v1', 'target_version_uid': 'v2', 'state': 'running', 'verdict': {'code': 'needs_review'}, 'summary': {}}],
            'pairs': [{'transition_id': 't1', 'pair_id': 'p1', 'pair_no': 1, 'state': 'done', 'status': 'needs_review', 'ai_dependent': True,
                       'content_key': 'source-digest', 'channels': {'geometry': {'state': 'unchecked'}}, 'reasons': ['ALIGNMENT_UNRELIABLE'],
                       'result': {'how_compared': {'transform': [1, 0, 0, 1, 2, 3]}, 'differences': [{'region_class': 'text', 'before_text': '<unsafe>', 'after_text': '=formula', 'box': {'x': 1}}],
                                  'text_changes': [{'kind': 'changed', 'before': 'old', 'after': 'new'}], 'service_notes': []}}],
            'specifications': [{'transition_id': 't1', 'source': 'whole', 'state': 'incomplete', 'reason': 'SOURCE_PARTIAL', 'changes': []}],
            'limitations': ['Непроверенные каналы не означают отсутствие изменений.']}


def test_xlsx_is_valid_deterministic_multisheet_evidence_and_formula_safe():
    data = source()
    rendered = render_xlsx(data)
    assert rendered == render_xlsx(data)
    with zipfile.ZipFile(io.BytesIO(rendered)) as archive:
        for path in archive.namelist():
            ET.fromstring(archive.read(path))
        wb = archive.read('xl/workbook.xml').decode()
        assert 'Спецификации' in wb and 'Отличия' in wb and 'Служебное' in wb
        cells = ''.join(archive.read(name).decode() for name in archive.namelist() if 'worksheets/' in name)
        assert '<f>' not in cells
        assert '=SUM(1,2)&lt;script&gt;' in cells
        assert 'ALIGNMENT_UNRELIABLE' in cells and 'unchecked' in cells and 'source-digest' in cells
        assert '=formula' in cells and '&lt;unsafe&gt;' in cells


def test_html_zip_escapes_content_keeps_raw_provenance_and_preview_mapping():
    data = source()
    rendered = render_html(data, previews={'images/0001.png': b'PNG'}, preview_notes=['images/0001.png: профиль original-profile; сторона A'])
    with zipfile.ZipFile(io.BytesIO(rendered)) as archive:
        assert json.loads(archive.read('records.json')) == data
        page = archive.read('index.html').decode()
        assert '<script>' not in page and '&lt;script&gt;' in page
        assert 'изображения' in page and 'original-profile' in page and 'сторона A' in page
        assert archive.read('images/0001.png') == b'PNG'


def test_excel_does_not_silently_truncate_overlong_cell():
    data = source(); data['series']['display_title'] = 'x' * 32768
    with pytest.raises(DomainError):
        render_xlsx(data)
