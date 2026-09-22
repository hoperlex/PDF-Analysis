"""A `results.md` in the corpus's exact shape, small enough to reason about by hand.

Every structural feature here was taken from the real drop rather than invented: the
`# Document:`/`Path:`/`Generated:` preamble, the `## Page N` / `### BLOCK #n [TEXT]:` pair,
the two `> **...:**` metadata lines, the ConsultantPlus header and footer stamps, the
ellipsis-truncated title reprinted per page, a numbered clause, a markdown heading, a table,
and a body paragraph that legitimately ends in an ellipsis and occurs once.
"""

from __future__ import annotations

import pytest

CONSULTANT_PLUS_MARKDOWN = """# Document: ГОСТ_00000-2026__Пример.pdf

Path: ГОСТы и НОРМЫ Узун 08.26 / ГОСТ_00000-2026__Пример.pdf

Generated: 2026-08-25 09:47:54 UTC

## Page 1

### BLOCK #1 [TEXT]: blk_aaaa0000

> **Created:** 2026-08-25 09:22:54 UTC
> **Crop:** [Crop](https://vibe.cloud-ip.cc/api/crops/AAAA)

КонсультантПлюс

"ГОСТ 00000-2026. Пример межгосударственного стандарта для проверки сегментации..."

Документ предоставлен **КонсультантПлюс**

www.consultant.ru

Дата сохранения: 23.07.2026

## Page 2

### BLOCK #2 [TEXT]: blk_bbbb0000

> **Created:** 2026-08-25 09:22:54 UTC
> **Crop:** [Crop](https://vibe.cloud-ip.cc/api/crops/BBBB)

"ГОСТ 00000-2026. Пример межгосударственного стандарта для проверки сегментации..."

Документ предоставлен **КонсультантПлюс**
Дата сохранения: 23.07.2026

##### 1. ОБЩИЕ ПОЛОЖЕНИЯ

1.1. Настоящий стандарт распространяется на изделия, применяемые в строительстве, и устанавливает требования к их приёмке.

Рисунок Л.6 - Схема расположения колонн, ригелей и балок перекрытия на отм. ...

| N | Наименование | Значение |
|---|---|---|
| 1 | Предел прочности | 25 МПа |

**КонсультантПлюс**
надежная правовая поддержка

www.consultant.ru

Страница 2 из 2
"""

#: A document with no ConsultantPlus marker of any kind, carrying its own publisher's line.
#: Modelled on `ГОСТ_Р_72509-2026`, which prints `Страница документа - https://GostExpert.ru/`
#: 49 times and states no `Дата сохранения` at all.
UNATTRIBUTED_MARKDOWN = """# Document: ГОСТ_Р_00001-2026__Пример.pdf

Path: ГОСТы и НОРМЫ Узун 08.26 / ГОСТ_Р_00001-2026__Пример.pdf

Generated: 2026-08-25 09:47:54 UTC

## Page 1

### BLOCK #1 [TEXT]: blk_cccc0000

> **Created:** 2026-08-25 09:22:54 UTC
> **Crop:** [Crop](https://vibe.cloud-ip.cc/api/crops/CCCC)

4.2. Испытания проводят при температуре окружающего воздуха от 15 до 25 градусов Цельсия.

Страница документа - https://GostExpert.ru/gost/gost-00001-2026
"""

#: A document whose block bodies carry no `## Page` heading for one page, as
#: `ГОСТ_Р_50030_2-2010` does for pages 22 and 210: the label jumps and does not renumber.
GAPPED_PAGES_MARKDOWN = """# Document: ГОСТ_Р_00002-2010__Пример.pdf

Path: ГОСТы и НОРМЫ Узун 08.26 / ГОСТ_Р_00002-2010__Пример.pdf

Generated: 2026-08-25 09:47:54 UTC

## Page 1

### BLOCK #1 [TEXT]: blk_dddd0000

> **Created:** 2026-08-25 09:22:54 UTC
> **Crop:** [Crop](https://vibe.cloud-ip.cc/api/crops/DDDD)

5.1. Первая страница несёт блок.

## Page 3

### BLOCK #2 [TEXT]: blk_eeee0000

> **Created:** 2026-08-25 09:22:54 UTC
> **Crop:** [Crop](https://vibe.cloud-ip.cc/api/crops/EEEE)

5.2. Третья страница тоже, а вторая не упомянута вовсе.
"""


@pytest.fixture
def consultant_plus_markdown() -> str:
    return CONSULTANT_PLUS_MARKDOWN


@pytest.fixture
def unattributed_markdown() -> str:
    return UNATTRIBUTED_MARKDOWN


@pytest.fixture
def gapped_pages_markdown() -> str:
    return GAPPED_PAGES_MARKDOWN
