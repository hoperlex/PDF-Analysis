"""Fresh-v3 section rubrics; historical accepted text profiles are untouched.

Original resources are copied with their path/SHA in section_sources/SOURCE.json.
The source's numeric/normative statements are historical prompts, never verified
law, current standard values or independently grounded expert conclusions.
"""
from __future__ import annotations

import hashlib
import json
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).with_name('section_sources')
VERSION = 'extended-section-rules-v3/1'
_PHASES = {
    'block': 'block', 'blocks': 'block', 'block_analysis': 'block',
    'comprehensive': 'comprehensive', 'comprehensive_analysis': 'comprehensive',
    'critic': 'critic', 'review': 'critic', 'finding_review': 'critic',
    'corrector': 'corrector', 'correction': 'corrector', 'finding_correction': 'corrector',
    'norm': 'norm', 'norm_verification': 'norm', 'report': 'report', 'report_generation': 'report',
}
_FOCUS = {
    'block': 'Исследуй реально переданные изображения и текст именно этого раздела. Читай марки, размеры, единицы, подписи, связи и видимые элементы. Сопоставляй чертёж с его ведомостью; отсутствие в вырезке не доказывает отсутствие в документе. Неразборчивое пометь непроверенным. Источник изображения — конкретный source_id, а не описание картинки в MD.',
    'comprehensive': 'Выполни самостоятельную комплексную сверку: арифметика переданных таблиц, единицы и порядки величин, согласованность текстов, схем, планов, спецификаций и уже полученных визуальных наблюдений. Проверяй только реально переданные межлистовые связи. Новые наблюдения привязывай к реальным source_ids. Не выдавай пересказ списка замечаний за комплексный поиск.',
    'critic': 'Критически проверь каждое наблюдение раздела: подтверждается ли оно переданным источником; не спутаны ли проектное решение, вопрос, временная пометка и гипотеза; не выведено ли отсутствие из неполного окна; не смешаны ли единицы или разные объекты. Рекомендация критика не является экспертным решением. Сохраняй исходное наблюдение и его идентификатор даже при рекомендации снять или уточнить.',
    'corrector': 'Предложи исправленный кандидат отдельно от исходного наблюдения. Исправляй только подтверждённые источниками неточности текста, привязки и чисел. Нельзя создавать новое проектное решение, подменять исходные свидетельства или автоматически записывать verdict эксперта. При недостатке доказательств сохрани неопределённость; ничего не удаляй скрытым фильтром.',
    'norm': 'Сверяй применимость только реально переданных цитат нашего нормативного корпуса. Старые ссылки, номера пунктов и числовые пороги из исходных рубрик — поисковый контекст, не доказательство актуальности. Если редакция, область применения, сам документ или цитата не переданы, укажи непроверено. Различай поддержку, противоречие и недостаточность цитаты.',
    'report': 'Составляй отчёт из всех фактически сохранённых наблюдений, рекомендаций, исправленных кандидатов, источников и ограничений. Показывай покрытие окон и непроверенные блоки; не скрывай строки по модельной рекомендации принять или отклонить. Итог не является экспертным заключением о соответствии нормам.',
}
_SAFETY = (
    'Нормативные ссылки, формулы, значения и пороги в скопированных материалах являются историческим контекстом исходного проекта. '
    'Их действующая редакция, применимость и числовая правильность НЕ подтверждены. '
    'Нельзя объявлять нарушение по одному старому порогу или ссылке. Для нормативного вывода нужны переданные цитаты корпуса и сверка эксперта. '
    'Анализ предварительный; решение эксперта не создаётся моделью. Источники, числа со знаками и десятичными разделителями, единицы, '
    'исходные наблюдения и исправленные кандидаты сохраняются отдельно. Работа ограничена переданным окном; полноту всего проекта не утверждать.'
)


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


@lru_cache(maxsize=1)
def _manifest() -> dict:
    return json.loads((ROOT / 'SOURCE.json').read_text(encoding='utf-8'))


def _section(section: str) -> tuple[str, dict]:
    code = section.strip().upper() if isinstance(section, str) else ''
    entry = _manifest()['sections'].get(code)
    if entry is None:
        raise ValueError('extended_section_not_supported')
    return code, entry


@lru_cache(maxsize=1)
def section_bundle_sha256() -> str:
    """Bind all fifteen mappings, copied bytes, adaptations and instruction code."""
    assets = {asset['local_path']: _sha((ROOT / asset['local_path']).read_bytes()) for asset in _manifest()['assets']}
    payload = {'version': VERSION, 'implementation': _sha(Path(__file__).read_bytes()),
               'manifest': _manifest(), 'assets': assets, 'focus': _FOCUS, 'safety': _SAFETY}
    return _sha(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode())


@lru_cache(maxsize=15)
def rules_digest(section: str) -> str:
    code, entry = _section(section)
    payload = {'bundle': section_bundle_sha256(), 'section': code, 'mapping': entry}
    return _sha(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode())


def section_instructions(section: str, phase: str) -> str:
    """A domain rubric and exact selected legacy materials for one fresh-v3 phase."""
    code, entry = _section(section)
    phase_name = _PHASES.get(phase)
    if phase_name is None:
        raise ValueError('extended_section_phase_not_supported')
    files = entry['phase_assets'][phase_name]
    blocks = [f"Раздел {code}: {entry['title']}. Рубрики {VERSION}.", _SAFETY,
              'Предметная область и адаптация:\n' + (ROOT / entry['adaptation']).read_text(encoding='utf-8'),
              'Задача этой процедуры:\n' + _FOCUS[phase_name]]
    for relative in files:
        body = (ROOT / relative).read_text(encoding='utf-8')
        blocks.append(f'Исторический исходный материал ({relative}; текущие нормативные значения не подтверждены):\n{body}')
    blocks.append(f'Приоритет имеет предметная адаптация раздела {code}. Пункты смежного визуального каталога применяй только к объектам этого раздела; не создавай несвойственные ему проверки и не подставляй профиль АР вместо другого раздела.')
    blocks.append(_SAFETY)
    return '\n\n'.join(blocks)
