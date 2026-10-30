"""Technical version-comparison exports from stored evidence, without a model.

HOTFIX-VERSIONS-1030. Original report.py at PDF-proverka 3c994817 is the
functional reference (summary, sheets, differences, positions, HTML evidence),
not an imported runtime dependency. This implementation reads our immutable
identities and results; no original filesystem/PyMuPDF path is reproduced.
The XLSX package uses the stdlib XML/ZIP format already used by this project.
"""
from __future__ import annotations

import html
import io
import json
import re
import zipfile
from collections import Counter
from dataclasses import dataclass
from typing import Any
from xml.sax.saxutils import escape

from sqlalchemy import text

from auditmanager.shared.db import session_scope
from auditmanager.shared.errors import DomainError, ErrorCode

MAX_PAIRS = 2000
MAX_DETAIL_ROWS = 50_000
MAX_JSON_BYTES = 64 * 1024 * 1024
MAX_PREVIEWS = 200
MAX_PREVIEW_BYTES = 32 * 1024 * 1024
_XML_BAD = re.compile(r'[\x00-\x08\x0b\x0c\x0e-\x1f]')
_STATUS = {'same': 'Совпадает', 'same_zones_changed': 'Изменены служебные зоны', 'different': 'Отличается',
           'needs_review': 'Нужна проверка', 'added': 'Добавлено', 'removed': 'Удалено', 'unmatched': 'Не сопоставлено'}


@dataclass(frozen=True, slots=True)
class TechnicalReport:
    content: bytes
    media_type: str
    filename: str


def _refuse(constraint: str) -> DomainError:
    return DomainError(ErrorCode.VALIDATION_FAILED, field='format', constraint=constraint)


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str, separators=(',', ':'))


def _collect(sessions: Any, series_id: str) -> dict[str, Any]:
    from auditmanager.comparison.profile.source import load_source_version
    with session_scope(sessions) as session:
        session.execute(text('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY'))
        series = session.execute(text(
            'SELECT s.comparison_series_id AS series_id, s.project_uid, s.document_uid, s.state, '
            's.created_at, s.updated_at, d.display_title FROM comparison_series s '
            'JOIN document d ON d.document_uid=s.document_uid WHERE s.comparison_series_id=:id'
        ), {'id': series_id}).mappings().first()
        if series is None:
            raise DomainError(ErrorCode.NOT_FOUND, aggregate_type='ComparisonSeries')
        transitions = [dict(row) for row in session.execute(text(
            'SELECT comparison_transition_id AS transition_id, transition_no, source_version_uid, target_version_uid, '
            'state, summary, verdict, updated_at FROM comparison_transition WHERE comparison_series_id=:id ORDER BY transition_no'
        ), {'id': series_id}).mappings()]
        rows = session.execute(text(
            'SELECT p.comparison_sheet_pair_id AS pair_id, p.comparison_transition_id AS transition_id, p.pair_no, '
            'p.state, p.status, coalesce(r.reasons,p.flags) AS reasons, p.ai_dependent, p.page_a_profile_id, p.page_b_profile_id, p.result_id, '
            'pa.page_number AS a_page, pb.page_number AS b_page, pa.profile AS a_profile, pb.profile AS b_profile, '
            'r.content_key, r.algo_version, r.channels, r.result '
            'FROM comparison_sheet_pair p JOIN comparison_transition t ON t.comparison_transition_id=p.comparison_transition_id '
            'LEFT JOIN comparison_page_profile pa ON pa.comparison_page_profile_id=p.page_a_profile_id '
            'LEFT JOIN comparison_page_profile pb ON pb.comparison_page_profile_id=p.page_b_profile_id '
            'LEFT JOIN comparison_sheet_pair_result r ON r.comparison_sheet_pair_result_id=p.result_id '
            'WHERE t.comparison_series_id=:id ORDER BY t.transition_no,p.pair_no LIMIT :limit'
        ), {'id': series_id, 'limit': MAX_PAIRS + 1}).mappings()
        pairs = []
        details = 0
        for row in rows:
            if len(pairs) >= MAX_PAIRS:
                raise _refuse('comparison_technical_export_max_2000_pairs')
            item = dict(row)
            result = item.get('result') or {}
            details += sum(len(result.get(name) or []) for name in ('differences', 'text_changes', 'service_notes'))
            if details > MAX_DETAIL_ROWS:
                raise _refuse('comparison_technical_export_max_50000_details')
            pairs.append(item)
        specifications = [dict(row) for row in session.execute(text(
            'SELECT c.comparison_transition_id AS transition_id,c.state,c.source,c.reason,c.changes,c.coverage_a,c.coverage_b,c.totals '
            'FROM comparison_spec_comparison c JOIN comparison_transition t ON t.comparison_transition_id=c.comparison_transition_id '
            'WHERE t.comparison_series_id=:id ORDER BY t.transition_no,c.created_at'
        ), {'id': series_id}).mappings()]
        versions = {}
        for transition in transitions:
            for field in ('source_version_uid', 'target_version_uid'):
                version_id = transition[field]
                if version_id not in versions:
                    source = load_source_version(session, version_id)
                    versions[version_id] = {'sha256': source.sha256, 'size_bytes': source.size_bytes, 'page_count': source.page_count}
        data = {'format': 'comparison-technical/1', 'series': dict(series), 'versions': versions,
                'transitions': transitions, 'pairs': pairs, 'specifications': specifications,
                'limitations': ['Только сохранённые результаты; модель и повторное сравнение не запускались.',
                                'AI-сопоставление помечено отдельно; позиции whole-spec AI не подтверждены инженером.',
                                'Непроверенные каналы и незавершённые пары не означают отсутствие изменений.']}
        if len(_json(data).encode()) > MAX_JSON_BYTES:
            raise _refuse('comparison_technical_export_max_64_mib')
        return data


def _tables(data: dict[str, Any]) -> list[tuple[str, list[list[Any]]]]:
    counts = Counter(pair.get('status') or 'not_completed' for pair in data['pairs'])
    summary = [['Показатель', 'Значение'], ['Комплект', data['series'].get('display_title')],
               ['Серия ID', data['series']['series_id']], ['Состояние серии', data['series']['state']],
               ['Переходов', len(data['transitions'])], ['Пар/непарных листов', len(data['pairs'])]]
    summary += [[f'Статус: {_STATUS.get(key, key)}', value] for key, value in sorted(counts.items())]
    summary += [['Ограничение', value] for value in data['limitations']]
    versions = [['Версия ID', 'SHA-256 исходного PDF', 'Байт', 'Страниц']]
    versions += [[key, value['sha256'], value['size_bytes'], value['page_count']] for key, value in data.get('versions', {}).items()]
    transitions = [['Переход ID', '№', 'Версия A', 'Версия B', 'Состояние', 'Вердикт', 'Сводка']]
    transitions += [[t['transition_id'], t['transition_no'], t['source_version_uid'], t['target_version_uid'], t['state'], _json(t.get('verdict')), _json(t.get('summary'))] for t in data['transitions']]
    sheets = [['Переход ID', 'Пара ID', '№ пары', 'Страница A', 'Страница B', 'Статус', 'Состояние', 'Пару связал ИИ', 'Причины', 'Каналы', 'Алгоритм', 'Content key', 'Как сравнивали']]
    differences = [['Пара ID', '№', 'Класс', 'Слой', 'Координаты в pt страницы A', 'Было', 'Стало']]
    texts = [['Пара ID', '№', 'Тип', 'Было', 'Стало', 'Координаты', 'Числа']]
    notes = [['Пара ID', '№', 'Служебное свидетельство']]
    for pair in data['pairs']:
        result = pair.get('result') or {}
        sheets.append([pair['transition_id'], pair['pair_id'], pair['pair_no'], pair.get('a_page'), pair.get('b_page'),
                       _STATUS.get(pair.get('status'), pair.get('status') or 'Не завершено'), pair['state'],
                       'Да' if pair.get('ai_dependent') else 'Нет', _json(pair.get('reasons')), _json(pair.get('channels')),
                       pair.get('algo_version'), pair.get('content_key'), _json(result.get('how_compared'))])
        for number, diff in enumerate(result.get('differences') or [], 1):
            differences.append([pair['pair_id'], number, diff.get('region_class'), diff.get('layer'), _json(diff.get('box')), diff.get('before_text'), diff.get('after_text')])
        for number, change in enumerate(result.get('text_changes') or [], 1):
            texts.append([pair['pair_id'], number, change.get('kind'), change.get('before'), change.get('after'), _json(change.get('box')), _json(change.get('numbers'))])
        for number, note in enumerate(result.get('service_notes') or [], 1):
            notes.append([pair['pair_id'], number, _json(note)])
    specs = [['Переход ID', 'Источник', 'Состояние', 'Ограничение', '№', 'Изменение позиции (ИИ не подтверждён инженером)']]
    for spec in data.get('specifications', []):
        for number, change in enumerate(spec.get('changes') or [None], 1):
            specs.append([spec['transition_id'], spec.get('source'), spec['state'], spec.get('reason'), number, _json(change)])
    return [('Сводка', summary), ('Версии', versions), ('Переходы', transitions), ('Листы', sheets),
            ('Отличия', differences), ('Текст', texts), ('Служебное', notes), ('Спецификации', specs)]


def _archive(parts: dict[str, bytes]) -> bytes:
    output = io.BytesIO()
    with zipfile.ZipFile(output, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        for name, payload in sorted(parts.items()):
            info = zipfile.ZipInfo(name, (1980, 1, 1, 0, 0, 0)); info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, payload)
    return output.getvalue()


def render_xlsx(data: dict[str, Any]) -> bytes:
    tables = _tables(data)
    parts: dict[str, bytes] = {}
    sheets, relationships, overrides = [], [], []
    for index, (name, rows) in enumerate(tables, 1):
        sheets.append(f'<sheet name="{escape(name)}" sheetId="{index}" r:id="rId{index}"/>')
        relationships.append(f'<Relationship Id="rId{index}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet{index}.xml"/>')
        overrides.append(f'<Override PartName="/xl/worksheets/sheet{index}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>')
        xml_rows = []
        for number, row in enumerate(rows, 1):
            cells = []
            for value in row:
                if isinstance(value, (int, float)) and not isinstance(value, bool):
                    cells.append(f'<c><v>{value}</v></c>')
                else:
                    value = '' if value is None else _XML_BAD.sub('', str(value))
                    if len(value) > 32767:
                        raise _refuse('comparison_technical_export_excel_cell_max_32767')
                    cells.append(f'<c t="inlineStr"><is><t xml:space="preserve">{escape(value)}</t></is></c>')
            xml_rows.append(f'<row r="{number}">{"".join(cells)}</row>')
        parts[f'xl/worksheets/sheet{index}.xml'] = ('<?xml version="1.0" encoding="UTF-8"?>'
            '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetViews><sheetView workbookViewId="0">'
            '<pane ySplit="1" topLeftCell="A2" state="frozen"/></sheetView></sheetViews><sheetData>' + ''.join(xml_rows) + '</sheetData></worksheet>').encode()
    parts['[Content_Types].xml'] = ('<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>' + ''.join(overrides) + '</Types>').encode()
    parts['_rels/.rels'] = ('<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>').encode()
    parts['xl/workbook.xml'] = ('<?xml version="1.0" encoding="UTF-8"?><workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets>' + ''.join(sheets) + '</sheets></workbook>').encode()
    parts['xl/_rels/workbook.xml.rels'] = ('<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">' + ''.join(relationships) + '</Relationships>').encode()
    return _archive(parts)


def render_html(data: dict[str, Any], *, previews: dict[str, bytes] | None = None, preview_notes: list[str] | None = None) -> bytes:
    parts = dict(previews or {})
    chunks = ['<!doctype html><html lang="ru"><meta charset="utf-8"><title>Техническое сравнение версий</title>',
              '<style>body{font:14px sans-serif;margin:24px}table{border-collapse:collapse;width:100%}td,th{border:1px solid #bbb;padding:6px;vertical-align:top;white-space:pre-wrap;overflow-wrap:anywhere}img{max-width:48%;vertical-align:top}h2{margin-top:32px}</style>',
              '<h1>Техническое сравнение версий</h1><p>Сохранённые детерминированные свидетельства. AI-позиции не подтверждены инженером.</p>',
              '<p><a href="records.json">Полные данные и происхождение (JSON)</a></p>']
    for name, rows in _tables(data):
        chunks.append('<h2>' + html.escape(name) + '</h2><table>')
        for index, row in enumerate(rows):
            tag = 'th' if index == 0 else 'td'
            chunks.append('<tr>' + ''.join(f'<{tag}>{html.escape(str(value) if value is not None else "")}</{tag}>' for value in row) + '</tr>')
        chunks.append('</table>')
    chunks.append('<h2>Обзорные изображения исходных листов</h2><p>Это исходные страницы, без цветного наложения. Координаты отличий и сведения о регистрации приведены в таблицах и JSON.</p>')
    for filename in sorted(parts):
        chunks.append(f'<figure><img src="{html.escape(filename)}" alt="{html.escape(filename)}"><figcaption>{html.escape(filename)}</figcaption></figure>')
    for note in preview_notes or []:
        chunks.append('<p>' + html.escape(note) + '</p>')
    chunks.append('</html>')
    parts['index.html'] = ''.join(chunks).encode()
    parts['records.json'] = _json(data).encode()
    return _archive(parts)


def export_comparison_technical_report(
    session_factory: Any, *, series_id: str, format: str, blob_store: Any = None,
) -> TechnicalReport:
    if format not in ('xlsx', 'html'):
        raise _refuse('xlsx_or_html')
    data = _collect(session_factory, series_id)
    if format == 'xlsx':
        return TechnicalReport(render_xlsx(data), 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', 'comparison-technical.xlsx')
    previews, notes = {}, []
    profiles = {}
    for pair in data['pairs']:
        if pair.get('status') == 'same':
            continue
        for side in ('a', 'b'):
            profile_id = pair.get(f'page_{side}_profile_id')
            if profile_id:
                profiles.setdefault(profile_id, []).append((pair['pair_id'], side, pair.get(f'{side}_page')))
    if blob_store is None:
        notes.append('Изображения недоступны: хранилище не подключено. Все сохранённые данные включены в records.json.')
    else:
        from auditmanager.comparison.profile.reader import PageProfileReader
        reader = PageProfileReader(session_factory, blob_store)
        size = 0
        for number, (profile_id, subjects) in enumerate(profiles.items(), 1):
            if number > MAX_PREVIEWS:
                notes.append(f'Обзорные изображения ограничены первыми {MAX_PREVIEWS} профилями из {len(profiles)}; данные всех пар включены.')
                break
            try:
                image = reader.read_preview(profile_id)
            except DomainError as error:
                notes.append(f'Профиль {profile_id}: изображение недоступно ({error.code.value}).')
                continue
            if size + len(image) > MAX_PREVIEW_BYTES:
                notes.append('Лимит обзорных изображений 32 МиБ достигнут; данные всех пар включены.')
                break
            filename = f'images/{number:04d}.png'
            previews[filename] = image; size += len(image)
            notes.append(f'{filename}: профиль {profile_id}; ' + '; '.join(f'пара {p}, сторона {side.upper()}, страница {page}' for p, side, page in subjects))
    return TechnicalReport(render_html(data, previews=previews, preview_notes=notes), 'application/zip', 'comparison-technical-html.zip')
