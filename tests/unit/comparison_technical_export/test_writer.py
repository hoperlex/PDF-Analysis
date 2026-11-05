from __future__ import annotations

import hashlib
import io
import json
import zipfile
from xml.etree import ElementTree as ET

from auditmanager.comparison.report.technical_export import render_html, render_xlsx


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


def _sheet_cells(archive):
    """Every inline-string cell per sheet name, read back from the workbook XML."""
    ns = {'m': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main',
          'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'}
    workbook = ET.fromstring(archive.read('xl/workbook.xml'))
    sheets = {}
    for index, sheet in enumerate(workbook.find('m:sheets', ns), 1):
        root = ET.fromstring(archive.read(f'xl/worksheets/sheet{index}.xml'))
        sheets[sheet.get('name')] = [[''.join(cell.itertext()) for cell in row] for row in root.iter('{%s}row' % ns['m'])]
    return sheets


def test_excel_does_not_silently_truncate_overlong_cell():
    # a670f5d8 (BLOCK7, 2026-10-30) replaced the refusal of a 32768-unit cell by a lossless export:
    # the table cell is an explicit excerpt and the complete value lives in the RawJSON sheet.
    data = source(); data['series']['display_title'] = 'x' * 32768
    rendered = render_xlsx(data)
    with zipfile.ZipFile(io.BytesIO(rendered)) as archive:
        sheets = _sheet_cells(archive)
    marker = ' … [ОТРЫВОК; полное значение и источники в RawJSON]'
    # Sheet "Сводка" carries the title: the cell is cut under the 32767-unit Excel limit and says so.
    excerpts = [cell for row in sheets['Сводка'] for cell in row if cell.endswith(marker)]
    assert len(excerpts) == 1
    assert excerpts[0].startswith('x' * 30_000) and len(excerpts[0]) <= 32767
    assert all(len(cell) <= 32767 for rows in sheets.values() for row in rows for cell in row)
    # Nothing is lost: the RawJSON chunks, joined without a separator, are the complete record
    # and it still holds the whole 32768-character title.
    chunks = [row for row in sheets['RawJSON'][1:]]
    assert [row[0] for row in chunks] == [str(number) for number in range(1, len(chunks) + 1)]
    assert {row[1] for row in chunks} == {str(len(chunks))}
    full = ''.join(row[2] for row in chunks)
    assert json.loads(full) == data
    assert json.loads(full)['series']['display_title'] == 'x' * 32768
    assert all(len(row[2]) <= 30_000 for row in chunks)
    # The summary names the digest of exactly those bytes.
    digest = hashlib.sha256(full.encode()).hexdigest()
    assert ['SHA256 полного JSON UTF-8', digest] in sheets['Сводка']
    # A value under the limit is not marked as an excerpt.
    with zipfile.ZipFile(io.BytesIO(render_xlsx(source()))) as archive:
        assert not any(cell.endswith(marker) for rows in _sheet_cells(archive).values() for row in rows for cell in row)
