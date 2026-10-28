# Comparison modules — evidence for the plan

Evidence gathered on 2026-10-27 for `COMPARE-MODULES-PLAN.md` (the plan of «Сравнение стадий» and
«Сравнение версий» to the original's functions and screens).

## Sources

- **The original's code**: GitHub `SU10KAZ/PDF-proverka`, branch `main` at
  `23f379fd2d5aeb7e7bddb735650e7393c68d4e42` (2026-10-27 08:03 UTC). Files were read from
  `raw.githubusercontent.com` at that commit; nothing was executed. In both inventories `ROOT`,
  `F:` (frontend) and `B:` (backend) paths are paths of that repository.
- **The original's live screens**: `https://auditmanager.app` (the owner's running instance), viewed
  read-only on 2026-10-27 between 15:20 and 16:10 +05 with an account the owner lent for the day. Only
  navigation and tab clicks were made; no upload, run, decision or setting was submitted.
- **This repository**: `integration/ar-close-1026` at `9e42c18a` (migration head `0035`, contract
  `1.8.0`, product `0.9.0`).

## Files

| File | What it is |
| --- | --- |
| `ORIGINAL-STAGE-COMPARISON-INVENTORY.md` | the original's «Сравнение стадий»: tabs, controls, endpoints, models, artifacts, what is live and what is dead code (737 lines, gathered by a read-only agent, spot-checked against the live screens below) |
| `ORIGINAL-VERSION-COMPARISON-INVENTORY.md` | the original's «Сравнение версий»: projects table with seven steps, sheet matrix across versions, overlay viewer, AI per-sheet description, specifications, MD/PDF report (520 lines, same method) |

## What the live screens showed (2026-10-27)

**«Сравнение стадий»** (menu title «Сравнение двух стадий проектной документации»). Four tabs: «1. Загрузка
документации», «2. Сопоставление листов», «3. Изменения проекта», «4. Отчёт»; a button «Загрузить проекты».
For object «256. Примавера К14 (Спартак)» tab 1 lists pairs with the columns «Проект / раздел», «OLD → NEW»
(for example «СТ26-01-14-ИОС2.1 → СТ26-01-14-ИОС2.1 · сборка из 9»), «Метод и модель» («Стандартный · Claude
Opus 5.5 → GPT-6 Astra (досборка) · xhigh»), «Дата», «Изменения», «Требуют проверки», «Статус» («Заморожен ·
прогон V3», «Ошибка анализа») and «Открыть» / «Запустить сравнение». An opened pair shows a seven-step strip
«01 Подготовка документов», «02 Смысловое сопоставление (7 из 7 частей)», «03 Поиск изменений (28 из 28
областей)», «04 Разбор несопоставленного», «05 Свод изменений», «06 Проверка по источникам (32 из 69
параметров, не проверено 37, требуют разбора 6)», «07 Подготовка результата». Tab 2 shows «Листы / Смысловые
блоки», filters «Все блоки / Блоки со связями / Блоки без связей», «Старый проект / Новый проект» page lists,
«Бирюзовый пунктир — конкретная связь · Оранжевый — общая тема», «Редактировать связи» and «Решения сохраняются
для этого результата. Анализ и отчёт автоматически не пересчитываются.» Tab 3 shows «Итоговые карточки»
(«Консолидатор (теневой режим, только просмотр)»), «Классический отчёт», «Отчёт с ИИ-разбором» («≈30–40 мин»),
and a table «ID / Изменение / Было / Стало / Источник (TABLE, GRAPHIC, TEXT) / Статус («Не оценено
Консолидатором») / +». Tab 4 shows «Итоговый журнал изменений», «Excel ↓ / PDF ↓ / HTML ↓» (disabled),
«Подтверждено изменений: N», «Группировка: По шифру / По разделу / По системе». The catalog entry of one run
records `gpt-6-astra`, 42 model calls, about 5.1 million input tokens and 50 minutes for a 8 + 38 page pair.
Object «213. Мосфильмовская 31А» has no stage pairs.

**«Сравнение версий»** (menu title «Наложение листов разных версий проекта»). Tab «Проекты и этапы» (68
projects, «478 версий · 410 переходов»): counters «Все / Ждут действия / Идут / Ошибки / Готовы», «Поиск по
шифру…», «Марка», «Порядок», «Очередь запуска», and a table whose columns are «Проект · следующий шаг»,
«Версии», «1 Загрузка», «2 Разбор версий», «3 Сопоставление листов», «4 ИИ-проверка сомнительных пар»,
«5 Сравнение соседних», «6 ИИ-описание изменений», «7 Сводка и отчёт»; each row has «Сводка изменений (MD)»
and per-step states and «↻ Заново». Tab «Сравнение листов» for project «133/23-ГК-ЭМ2» (12 versions):
«Сводка изменений (MD)», «Порядок версий», «Сформировать PDF-отчёт…»; «Сводка переходов» with one row per
adjacent transition («V2 30.05.2025 → V3 Изм.1 09.07.2025», progress «26 из 26», «Листов», «✓ ◐ ● ⚠»,
«Состав +10 / −0», verdict «есть отличия на 16 л.; изменён состав (+10 / −0 л.); нужна проверка: 9»,
«Открыть»); «ИИ-описание изменений» per transition with sheets, changes, questions, errors, «Проверить»,
calls, tokens and time; then a sheet matrix with one row per sheet («л.4 · Однолинейная расчетная схема ВРУ-1.
Начало») and one column per version, cells «стр.6 · л.6✎», «∅ нет в версии», markers ✎ ⇉ ◫.
