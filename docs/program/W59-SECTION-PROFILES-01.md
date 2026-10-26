# W59-SECTION-PROFILES-01 — draft text profiles for 13 non-AR sections

> Superseded in status on 2026-10-26: the 14 profiles are `reviewed` without any human review (`R-146ag`, `A-7`); the open questions below were answered by lanes, see `SECTION-REVIEW-LEDGER-01.md`; the text below is the state at its date.

**Base:** `a1a25ebc` on `integration/night-1020` (the task's frozen `origin/dev`
base is `9cf21cc0c111c819570927510ef40dec495df5e9`). **Branch:**
`agent/w59-section-profiles-01`. **Legacy source:** `PDF-proverka` at
`16ba8e5d23e4782550e79355002fde1365f682b7`, read only.

## Result

Thirteen `text-profile/1` data packages now exist under
`src/auditmanager/analysis/text/profiles/<code>/`. There is one for each non-AR section
that has legacy material: AI, PS, POS, TX, KJ, KM, OV, VK, PT, EOM, SS, ITP and GP. Each
package holds a `profile.json` and a `system_prompt.md`. PB has no legacy source and
gets no package. AR keeps its v1 constants and also gets no data package. The task
title says "14 non-AR sections", but its outcome list and deliverables name these
13; PB is the fourteenth and is excluded on purpose.

The packages are inert data, and nothing in this lane loads them. They become
executable only when the section-keyed registry of `W59-SECTION-SEAL-01` reads them.

**Every profile is `status: draft`, and all of them are debt.** None has had an
expert review, a field evaluation or a recorded response, so none may count towards
beta acceptance. At integration, register one debt row covering all 13 profiles.
Before any profile may become `reviewed`, it needs:

- an expert review, which answers that section's open questions below;
- independent positive and negative field cases;
- recorded responses;
- a decision on the cross-section questions in this report.

| Code | Title (S-3) | `analysis_profile_id` | `prompt_bundle_id` |
| --- | --- | --- | --- |
| AI | Архитектурные решения (интерьер) | `ap_01M5AXG1K03864N3KSY4AM9P10` | `pb_01M5AXG1K095VZEZ6BHYM6W9QV` |
| PS | Пояснительная записка | `ap_01M5AXG1K22R027A33VTKZ468P` | `pb_01M5AXG1K2JQQH7R4ACTBW8974` |
| POS | Проект организации строительства | `ap_01M5AXG1K4V1JCGK60TZRM9B96` | `pb_01M5AXG1K4QP84XW1DNYM72HN6` |
| TX | Технологические решения | `ap_01M5AXG1K6MGZGFCBG75M9ZR9D` | `pb_01M5AXG1K6E7TR87P0RGP6QBZM` |
| KJ | Конструкции железобетонные | `ap_01M5AXG1K82P9BCJ1NRYSTC2NY` | `pb_01M5AXG1K8EDTH597XY32Z696Y` |
| KM | Конструкции металлические | `ap_01M5AXG1KB71SHN23H775AP551` | `pb_01M5AXG1KB45S6A5TZ0ZTWRVHS` |
| OV | Отопление, вентиляция и кондиционирование | `ap_01M5AXG1KDVXRHH20N7KGBKPZ4` | `pb_01M5AXG1KDEVEZ88HR6KYX2YP9` |
| VK | Водоснабжение и канализация | `ap_01M5AXG1KF7NGNYMEFN97BW9ZN` | `pb_01M5AXG1KFMA8QCKP6YM1K5M5W` |
| PT | Противопожарный водопровод | `ap_01M5AXG1KHY5S7A1AFVND7FPS9` | `pb_01M5AXG1KH4JG7TMH93XACNF6H` |
| EOM | Электроснабжение и электрооборудование | `ap_01M5AXG1KKCKB70088QWAR8WD4` | `pb_01M5AXG1KKNVF7G99H0BB166TW` |
| SS | Слаботочные системы | `ap_01M5AXG1KN9C7BDD3CCHMFTMX3` | `pb_01M5AXG1KNQRT6DYJWYC5X0C5J` |
| ITP | Индивидуальный тепловой пункт | `ap_01M5AXG1KQSW41PC130SWCS8CD` | `pb_01M5AXG1KQR5A6ZPWDX4CC3CTS` |
| GP | Генеральный план | `ap_01M5AXG1KSSZM53N2CBV6XX83E` | `pb_01M5AXG1KSRDEWMP2WT3KNGWJ2` |

All 26 identities are fresh ULIDs from `AnalysisProfileId.new()` and
`PromptBundleId.new()`. They are generated once and pinned as literals, the same way
v1 pins AR's. They are unique, and none equals a literal anywhere else in
`src/auditmanager` (AR v1, AR v2/v3, code fixtures).

## How each system prompt is built

Each `system_prompt.md` is v1's served `SYSTEM_PROMPT` from
`src/auditmanager/analysis/text/prompt.py` with six anchored substitutions. Each
anchor had to occur exactly once in v1. Everything else is byte-for-byte v1's text:

- the single question;
- the two category definitions (`internal_contradiction`, `explicit_placeholder`);
- conditions 3 and 5 and the start of conditions 1, 2 and 4;
- the no-verdict sentence;
- the whole "Требования к ответу" block, which names `finding_text`,
  `recommendation_text`, `category`, `evidence`, `quote`, `page_number` and
  `observations`.

The unit test enforces this. The six changes:

1. **Opening sentence.** It names the section by its S-3 title and Cyrillic
   abbreviation instead of «Архитектурные решения» (АР).
2. **"Где в документе раздела … искать".** This new block sits before the five
   conditions and holds 10–11 section-specific places to cross-check. It is framed
   explicitly as a hint, not a third category or a list of required findings. Each
   bullet names one attribute of one kind of object, and the places in the same
   document where it is written. The last bullet names where explicit placeholders
   typically sit, worded as v1 defines them ("отметки о незаполненности"), not as
   empty cells.
3. **Condition 1 (different objects).** It lists this section's object kinds: for
   example panels, groups and lines for ЭОМ, or element marks and reinforcement
   zones for КЖ.
4. **Condition 2 (different attributes).** It gives two or three near-miss pairs
   typical for the section: for example design versus installed power, DN versus
   outside diameter, or normative versus design load.
5. **Condition 4 (decision given elsewhere).** It also accepts a reference to a
   specification or a sheet, alongside v1's table, schedule, section or volume. This
   is the same rule in engineering-document vocabulary.
6. **Exclusion sentence.** It adds the section's norm families where the legacy
   material leans on them:
   - ПУЭ (ЭОМ);
   - СанПиН (ТХ, ВК, ГП);
   - ПП РФ № 87 and federal laws (ПЗ);
   - the heat-metering rules (ИТП);
   - urban-planning standards (ГП).

   It also closes off engineering calculation and judging whether a decision is
   correct ("НЕ выполняешь и не перепроверяешь инженерные расчёты, НЕ оцениваешь,
   правильно ли принято техническое решение … Сравниваются только значения, прямо
   записанные в тексте").

The categories, response schema, user preamble, page banner and token limits are
not in the package. Under the seal's integration contract they stay v1's. Nothing
from the legacy text reaches the output contract:

- no legacy category, severity or triage;
- no JSON template;
- no instruction to cite norms;
- no instruction to give a verdict.

The section-specific bullets were drafted from the legacy material by four
parallel drafting subagents, using one brief and one worked example (ЭОМ, written by
the executor). The executor then reviewed every rendered prompt. One fix was
applied across all 13 sections: the placeholder bullet originally said
"незаполненные графы", which invites flagging empty table cells, and now uses v1's
"отметки о незаполненности («уточнить», «XX», «___»)".

## Legacy material: used and not used

Used, and hash-pinned in every `profile.json`, for each section:

- `role.md` — the subject only, as a list of objects;
- `checklist.md` — the items reframed as same-document cross-checks;
- `drawing_types.md` — the places in the document;
- `project_params.md` — the attributes that recur across places;
- `finding_categories.md` — read so that every legacy category can be recorded as
  dropped.

Each hash equals the value already catalogued in
`src/auditmanager/analysis/profiles/section_candidates/metadata.json`. It also equals
the blob at the pinned legacy commit, and the legacy working tree was clean.

Not used:

- `norms_reference.md` — norm compliance and actualness belong to W57;
- `triage_table.md` — page triage priority, not prompt content;
- `compact_strategy.md` — a token strategy;
- `config.json` — a file map;
- `prompts/disciplines/_registry.json` — titles come from the S-3 catalogue
  `src/auditmanager/sections/suggestion_patterns.json`, which pins the registry's
  digest;
- `backend/app/data/discipline_checklists/*.md` — the ЭОМ file was inspected. These
  files are a completeness lens: "mandatory section / calculation / parameter" items
  with severity tags and norm clauses. That is outside v1's question (condition 5),
  and seven of the 13 sections have no such file.

## Excluded in every section (W57 and out of v1 scope)

Each section's list below is item-by-item. Across all sections, these classes of
legacy items were excluded:

- **Norm compliance:** every СП, СНиП, ГОСТ, ПУЭ, СанПиН, ФЗ or ПП requirement, every
  normative limit or minimum, the actualness of norm references, "replaced or
  outdated standard" checks. This is W57's corpus-backed verification.
- **Engineering calculation:**
  - recomputing currents, sections, loads, heat losses, flows, strengths, anchorage
    lengths, crane reach, durations, balances or coefficients;
  - checking a stated value against a calculation;
  - arithmetic such as an «Итого» row against the sum of its rows (see the
    cross-section questions).
- **Judging the decision:** whether a solution is correct, sufficient, optimal, safe,
  realistic or selective.
- **Inference from drawing graphics:** colours, positions, routes, coverage zones and
  geometry that is not written as text.
- **Completeness:** "X must be present / is missing". This is v1 condition 5.
- **Other volumes:** comparison with other sections or volumes (АР, КР, ГП, ИГИ, ТУ,
  ТЗ). Only this document's text is available.
- **Legacy form:** the role's instructions to find nonconformities with Russian
  norms and to cite norm clauses; legacy finding categories, severities and
  `project_params` JSON templates.

## Cross-section questions for the expert reviewer

These questions apply to every profile, so they are asked once here:

1. **Site and contractor phrases.** «уточнить по месту», «уточнить при монтаже»,
   «уточняется в ППР», «по проекту оператора» and similar phrases. Under v1's
   wording each is an explicit placeholder. Are they placeholders, or accepted site
   or contractor instructions that should go into condition 4?
2. **«Итого» against the sum of rows.** An «Итого» line in a specification, a ТЭП
   table or a schedule that disagrees with the sum of its rows. Recomputation is
   excluded today. Should this one arithmetic case be an `internal_contradiction`?
3. **Text read from sheets.** Values read from the text layer of drawing sheets
   (labels, title blocks, leaders). These are text, but they are often detached from
   their objects. Do the bullets that name "подписи планов/схем" give systematic false
   findings?
4. **Missing items.** An item named in one place and absent from another (a panel on
   a scheme but not in the specification). This is an omission, not two
   incompatible values. Is a third kind of observation wanted? That would be a
   contract change, not a profile edit.

## Per-section record

Each entry gives the package and identities, the legacy files with their SHA-256,
the section adaptations, and then three lists in Russian, because they quote the
legacy text and are written for the Russian expert reviewer:

- kept: which legacy items were reframed as cross-checks;
- excluded: which items were dropped, and why;
- open questions for the expert reviewer.

### AI — Архитектурные решения (интерьер) (АИ)

Package `src/auditmanager/analysis/text/profiles/ai/`; `analysis_profile_id` `ap_01M5AXG1K03864N3KSY4AM9P10`, `prompt_bundle_id` `pb_01M5AXG1K095VZEZ6BHYM6W9QV`, status `draft`.

| Legacy source file | SHA-256 |
| --- | --- |
| `prompts/disciplines/AI/role.md` | `189b4d80aa2669e073b564323c77670b6116255ac9ca8741d5e885725f449f0d` |
| `prompts/disciplines/AI/checklist.md` | `3834f9d05d42d67b000fa97e9acaaed7fe312487bca74ef346f22f568a9db743` |
| `prompts/disciplines/AI/drawing_types.md` | `222a05aafc2a3f5eb6ec95afed033715daf12ca9dd760e6f8807a26b19b897de` |
| `prompts/disciplines/AI/project_params.md` | `4e793ef3c1ea30f97387d91ed584447542c9d2aeaa3411f11588bc6ffce2961e` |
| `prompts/disciplines/AI/finding_categories.md` | `70d3e0e5c4556583141dd41b9220a4c4917d8c12c541e810a802ac03f1f02946` |

Condition 1 objects: секциям, этажам, типам квартир, помещениям, зонам одного помещения, поверхностям (пол, стены, потолок), дверным блокам или изделиям. Condition 2 near-misses: высота помещения в чистоте и высота этажа, ширина дверного полотна и ширина дверного проёма, класс пожарной опасности материала (КМ) и его группа горючести (Г1–Г4).

Kept (reframed as same-document cross-checks):

- checklist.md «Ведомость отделки помещений»: классы пожарной опасности отделочных материалов (КМ), экологические показатели (Е1), класс истираемости — как сверка классов одного и того же материала между ведомостью отделки, общими указаниями и спецификацией, без нормативных требований к ним
- checklist.md «Планы полов»: типы покрытий по помещениям, гидроизоляция под покрытием (тип), уровни чистого пола, тип тёплого пола, уклоны в мокрых зонах — как сверка записанных значений одного помещения между ведомостью отделки, экспликацией полов, узлами и спецификацией, без нормативных пределов
- checklist.md «Планы потолков»: высоты помещений, конструкция подвесных и натяжных потолков, высота подвеса, класс пожарной опасности материала потолка, марка и количество встроенных светильников — как сверка значений одного помещения или изделия, без нормативных минимумов
- checklist.md «Развёртки стен» и «Кухни»: высота установки зеркал и полок, высота вытяжки и розеток над столешницей, материал и размеры фартука — как сверка записанной высоты и материала одного и того же элемента на развёртках, в узлах и в общих указаниях
- checklist.md «Санузлы»: гидроизоляция (высота заведения на стены), уклон пола душевой зоны к трапу, высота поручней — как сверка значений одного мокрого помещения, без нормативного минимума 200 мм и размеров МГН
- checklist.md «Двери»: типоразмеры, фурнитура, порог или беспороговое решение, предел огнестойкости противопожарных дверей — как сверка марки и исполнения одной и той же двери между ведомостью дверных заполнений, маркировкой на планах и спецификацией
- checklist.md «Общие проверки»: соответствие спецификации и чертежей (марки, количество, размеры) — как сверка прямо записанных значений одного и того же изделия
- project_params.md: типы отделки, классы КМ, экологические классы, классы истираемости, ведомость отделки, ведомость дверных заполнений, спецификация сантехприборов (марки, количество); «противоречия между ведомостью отделки и чертежами»
- drawing_types.md: перечень мест документа (ведомость отделки, план полов, план потолков, развёртки стен, планы санузлов и кухонь, расстановка мебели, план освещения, ведомость дверей, узлы, спецификация, общие указания)
- role.md: предмет раздела (отделка полов, стен и потолков, мокрые зоны, двери, встроенная мебель, сантехприборы, кухонное оборудование, интерьерное освещение) — только как перечень объектов

Excluded:

- checklist.md «Ведомость отделки помещений»: «соответствие материалов отделки назначению помещений», «влагостойкость материалов в мокрых зонах», «соответствие класса истираемости нагрузке помещения» — оценка правильности технического решения
- checklist.md: требуемый класс КМ на путях эвакуации; «Планы полов»: уклон не менее 0,01, перепад уровней не более 4 мм; «Планы потолков»: высота не менее 2,5 м в жилых помещениях и 2,1 м в коридорах и МОП; «Санузлы»: минимальные расстояния до приборов и между ними, размеры кабины и высота приборов для МГН, заведение гидроизоляции не менее 200 мм; «Кухни»: расстояние от плиты до окна, высота вытяжки 600–850 мм, количество и нормативная высота розеток; «Двери»: минимальные ширины, открывание из санузлов наружу, противопожарные двери «где требуется по ФЗ-123», звукоизоляция 26 и 32 дБ — нормативные требования и пределы (W57)
- checklist.md «Кухни»: «рабочий треугольник: периметр 3,5–6,5 м» — расчёт по геометрии планировки
- checklist.md «Развёртки стен»: раскладка плитки (привязки, подрезка, симметрия), ниши (глубина, высота, назначение), «отделка за сантехприборами (зоны влагозащиты)», «розетки и выключатели — соответствие раскладке плитки», «привязка фартука к мебели»; «Санузлы»: размещение сантехприборов, направление открывания двери; «Планы потолков»: разметка и привязки светильников; «Планы полов»: зоны тёплых полов; «Кухни»: размеры ниш встроенной техники — выводы из графики чертежа
- checklist.md «Ведомость отделки помещений»: «наличие всех помещений в ведомости отделки»; «Планы полов»: пороги и переходные профили, наличие гидроизоляции и звукоизоляционной подложки; «Планы потолков»: «вентиляционные решётки и ревизионные люки — наличие»; «Санузлы»: «вентиляция — наличие вытяжки, решётки», бортик, порог и трап душевой зоны; «Общие проверки»: «наличие узлов и деталей для нетиповых решений» — требование, чтобы указание было (v1, условие 5)
- checklist.md «Развёртки стен»: крепление зеркал и полок; «Кухни»: вентиляция встроенной техники, стык фартука со столешницей; «Планы полов»: совместимость тёплого пола с покрытием — оценка достаточности решения
- checklist.md «Общие проверки»: «соответствие интерьерных решений архитектурному разделу (АР)», «согласованность с разделами ОВ, ВК, ЭОМ»; «Планы потолков»: «совпадение с электропроектом» — сравнение с другими томами, которых нет в документе
- project_params.md: «нормативные ссылки → проверить актуальность» — нормоконтроль (W57); JSON-шаблон project_params и описание полей — формат вывода legacy
- finding_categories.md: двенадцать категорий (finishes, flooring, ceiling, walls, bathroom, kitchen, doors, furniture, lighting, accessibility, documentation, normative_refs) и формат поля category не переносятся — у v1 ровно две категории
- role.md: «находишь ошибки и несоответствия нормативной базе РФ», «рекомендации строго с привязкой к пунктам нормативных документов»; области «доступность для МГН», «пожарная безопасность отделочных материалов», «цветовые решения и декоративные элементы» как предмет оценки — противоречит v1 (без ссылок на нормы, без вердикта и без оценки решения)

Open questions for the expert reviewer:

- Формулировки «цвет — по выбору заказчика», «артикул согласовать с заказчиком», «по утверждённому образцу» — заполнитель или принятое решение оставить выбор до закупки и авторского надзора?
- Общая высота в общих указаниях («высота помещений в чистоте 2,70 м») и меньшая высота конкретного помещения с подвесным потолком в ведомости отделки — противоречие или общая величина, от которой отдельные помещения законно отступают?
- Общие указания задают класс для путей эвакуации («отделка стен и потолков — КМ1»), а в ведомости отделки коридора стоит материал КМ2: это внутреннее противоречие или скрытая проверка соответствия нормам, которую нужно оставить W57?
- Ведомость отделки и экспликации часто составляются на тип квартиры, а номера помещений повторяются на этажах и в разных типах: хватает ли условия 1, или сверка наименований и площадей по номеру помещения даст систематические ложные находки?

### PS — Пояснительная записка (ПЗ)

Package `src/auditmanager/analysis/text/profiles/ps/`; `analysis_profile_id` `ap_01M5AXG1K22R027A33VTKZ468P`, `prompt_bundle_id` `pb_01M5AXG1K2JQQH7R4ACTBW8974`, status `draft`.

| Legacy source file | SHA-256 |
| --- | --- |
| `prompts/disciplines/PS/role.md` | `9999c2e3398db818d1b85941473db785b8b132558c95661c016ad845a437b7fa` |
| `prompts/disciplines/PS/checklist.md` | `c3dd8f7b7f84ecd23de8e353071b0f400ef9be4863de1c6b3691083ffeee9a93` |
| `prompts/disciplines/PS/drawing_types.md` | `bfbf147ce3449ee293f194430d1aafa91898036f09f3cf9fe250c3c41cbee7d4` |
| `prompts/disciplines/PS/project_params.md` | `eb8dcb54b22371673195d0985d8bca6ca4a01d152d590567abdddb7313376a51` |
| `prompts/disciplines/PS/finding_categories.md` | `60dfdf036131121a97477e7cd0630f89fdf36a56d7c3e93dbb6123bfe204d907` |

Condition 1 objects: земельным участкам, этапам или очередям строительства, зданиям, корпусам, секциям, пожарным отсекам, надземной и подземной частям, этажам, группам помещений или вариантам проектного решения. Condition 2 near-misses: этажность и количество этажей, общая площадь здания и общая площадь квартир, расчётное и нормируемое значение удельной характеристики расхода тепловой энергии.
Extra norm families named in the exclusion sentence: ПП РФ № 87, федеральным законам.

Kept (reframed as same-document cross-checks):

- checklist.md «Технико-экономические показатели (ТЭП)»: площадь участка, площадь застройки, общая, жилая и нежилая площадь, строительный объём (надземный и подземный), этажность, количество квартир по типам, количество машиномест, расчётная численность жителей, коэффициенты застройки и плотности застройки — как сверка одних и тех же показателей между таблицей ТЭП, сводными таблицами и текстом записки, без пересчёта
- checklist.md «Описание конструктивных решений»: конструктивная система, тип и глубина заложения фундаментов, несущие стены, колонны и перекрытия и их материалы, класс сооружения, уровень ответственности — как сверка одних и тех же сведений в исходных данных, в описании решений и в ТЭП
- checklist.md «Описание инженерных систем»: водоснабжение (источник, схема, давление, расход), канализация (расходы стоков), теплоснабжение (источник, параметры теплоносителя), вентиляция (естественная или механическая), электроснабжение (категория надёжности, напряжение, мощность), лифтовое оборудование (количество, грузоподъёмность, типы) — как сверка значений одной системы в разных главах записки и в ТЭП
- checklist.md «Энергоэффективность»: класс энергоэффективности, расчётное удельное потребление энергии, приведённое сопротивление теплопередаче — как сверка между главой об энергоэффективности, энергетическим паспортом и ТЭП
- checklist.md «Мероприятия по обеспечению доступности для МГН»: лифты, квартиры и машиноместа для МГН — только как сверка количеств, записанных в разных местах
- checklist.md «Пожарная безопасность»: степень огнестойкости, классы конструктивной и функциональной пожарной опасности, категория по пожарной опасности, тип СОУЭ из перечня систем противопожарной защиты — как сверка значений одного здания, пожарного отсека или помещения между главами
- checklist.md «Состав пояснительной записки»: описание земельного участка (площадь), сведения о климатических и инженерно-геологических условиях, исходные данные — как сверка одних и тех же сведений, повторённых в разных главах, и как место незаполненных реквизитов документов
- checklist.md «Экология и охрана окружающей среды»: «благоустройство и озеленение» — только площади покрытий и озеленения в ТЭП и в тексте
- project_params.md: ТЭП, площади, этажность и высота здания, количество и типология квартир, строительный объём, класс энергоэффективности, степень огнестойкости и класс конструктивной пожарной опасности, описания конструктивных решений, инженерных систем и мероприятий для МГН — как перечень сверяемых признаков и мест
- drawing_types.md: перечень мест документа (текстовая часть, таблица ТЭП, сводные таблицы и квартирография, энергетический паспорт, общие и исходные данные, приложения); «Сравнительная таблица ТЭП» — значения разных вариантов проектного решения внесены в условие 1 как разные объекты
- role.md: предмет раздела (ТЭП, описания конструктивных и объёмно-планировочных решений, инженерных систем, пожарной безопасности, мероприятий для МГН, энергоэффективности) — только как перечень глав, между которыми ведётся сверка

Excluded:

- checklist.md «Состав пояснительной записки»: «наличие всех обязательных подразделов», наличие исходных данных, сведений о функциональном назначении объекта, топографических и геодезических данных — требование, чтобы указание было (v1, условие 5)
- checklist.md «Состав пояснительной записки»: границы и ограничения использования участка, «обоснование принятых объёмно-планировочных и архитектурных решений» — оценка достаточности и правильности решения
- checklist.md «ТЭП»: пересчёт коэффициентов застройки и плотности застройки, сумм площадей и квартир по типам — инженерный расчёт (сравниваются только прямо записанные значения)
- checklist.md «ТЭП»: «сверка ТЭП между ПЗ и другими разделами (АР, ГП)»; «Описание конструктивных решений»: «соответствие описания разделу КР»; «Описание инженерных систем»: «соответствие описания инженерных систем профильным разделам» — сравнение с другими томами, которых нет в документе
- checklist.md «Описание инженерных систем»: виды канализации и система очистки, наличие ИТП, состав слаботочных систем (связь, видеонаблюдение, домофон, АСКУЭ) — наличие и полнота описания (v1, условие 5)
- checklist.md «Энергоэффективность»: «мероприятия по повышению энергоэффективности» — оценка достаточности решения; «соответствие требованиям ФЗ-261» — нормативное требование (W57)
- checklist.md «Мероприятия по обеспечению доступности для МГН»: доступные входы и пути передвижения, доступность МОП — оценка достаточности решения; «соответствие требованиям СП 59.13330.2020» — нормоконтроль (W57)
- checklist.md «Пожарная безопасность»: эвакуационные пути и выходы, наличие АУПС, АУПТ и дымоудаления, противопожарные расстояния, проезды и площадки — нормативные требования, достаточность решения и выводы из графики ситуационного плана
- checklist.md «Экология и охрана окружающей среды»: охрана атмосферного воздуха и водных объектов, обращение с отходами строительства и эксплуатации, шумозащитные мероприятия — наличие и достаточность мероприятий
- checklist.md «Сметная документация»: наличие сводного сметного расчёта — требование, чтобы документ был; обоснование стоимости строительства и применение сметных нормативов — оценка правильности решения и нормоконтроль
- project_params.md: «нормативные ссылки (ПП РФ №87, СП 54, ФЗ-384, ФЗ-123 и др.)» — проверка ссылок, нормоконтроль (W57); JSON-шаблон project_params и описание полей — формат вывода legacy
- finding_categories.md: десять категорий (completeness, tep_consistency, structural_description, engineering_systems, fire_safety, accessibility, energy_efficiency, ecology, documentation, normative_refs) не переносятся — у v1 ровно две категории; суть «несоответствий между частями ПЗ» из documentation покрывает internal_contradiction
- role.md: «находишь ошибки, неполноту и несоответствия нормативной базе РФ», «рекомендации строго с привязкой к пунктам нормативных документов», «полнота состава по ПП РФ №87», «соответствие ТЭП между разделами проекта», «координация описаний с другими разделами», мероприятия по ГО и ЧС, сметная документация как предмет оценки — нормоконтроль, полнота, межтомная сверка и оценка решения противоречат v1

Open questions for the expert reviewer:

- Строка «Итого» в квартирографии и в ТЭП (всего квартир, общая площадь квартир) и сумма строк по типам квартир или секциям — считать ли их расхождение находкой (сейчас пересчёт исключён)?
- Значения из ГПЗУ и технических условий, приведённые в записке (предельная этажность, максимальный процент застройки, разрешённая мощность по ТУ), стоят рядом с проектными значениями; по условию 2 это разные признаки (предел и проектное значение) — верно ли, что такие пары не сравниваются, или эксперт ждёт этих находок?
- Формулировки «будет определено на стадии РД», «уточняется заданием на проектирование», «ТУ будут получены» — заполнитель или принятое решение отложить?
- Записка часто пересказывает значения других томов («по разделу АР общая площадь …»): расхождение такого пересказа с ТЭП самой записки — internal_contradiction (оба значения в одном документе) или по сути межтомная сверка, которую нужно исключить?
- Расчётные температуры наружного воздуха разной обеспеченности и для разных систем, архитектурная и пожарно-техническая высота здания — хватает ли условия 2, или пункты о климатических данных и высоте дадут систематические ложные находки?

### POS — Проект организации строительства (ПОС)

Package `src/auditmanager/analysis/text/profiles/pos/`; `analysis_profile_id` `ap_01M5AXG1K4V1JCGK60TZRM9B96`, `prompt_bundle_id` `pb_01M5AXG1K4QP84XW1DNYM72HN6`, status `draft`.

| Legacy source file | SHA-256 |
| --- | --- |
| `prompts/disciplines/POS/role.md` | `19e2951c15fe0cb0ae328eb8fdcb60861265df8a2749296b49c811116b89e8cb` |
| `prompts/disciplines/POS/checklist.md` | `a4c5bba5d83e46841e1182f714adb4b459ce646f49b511b3f05ebac215d6a722` |
| `prompts/disciplines/POS/drawing_types.md` | `cf608107fe49ba9fb0de02cd8522381e638e66563ce07f0b33fefd11bcb1ebb5` |
| `prompts/disciplines/POS/project_params.md` | `42f8346450816b49b00082f91a3b798e4714fe2264e0be6a1ecc499537939032` |
| `prompts/disciplines/POS/finding_categories.md` | `6c10f378c333711e58a00cabd2853ff1e4097723cb4550a079a4b8ddc920c816` |

Condition 1 objects: этапам и периодам строительства, строящимся зданиям и сооружениям, захваткам, видам работ, кранам и другим машинам, временным зданиям или временным сетям. Condition 2 near-misses: общая продолжительность строительства и продолжительность подготовительного периода, численность рабочих и общая численность работающих, максимальная грузоподъёмность крана и его грузоподъёмность на максимальном вылете.

Kept (reframed as same-document cross-checks):

- checklist.md «Стройгенплан»: радиусы рабочей зоны, зоны перемещения груза и опасной зоны кранов, тип и высота ограждения, ширина и покрытие временных дорог, состав бытового городка — как сверка прямо записанных значений одного и того же объекта между текстом записки, экспликацией и подписями стройгенплана, без нормативных минимумов
- checklist.md «Календарный план строительства»: продолжительность строительства — «соответствие … расчёту» — как сверка записанного итога расчёта продолжительности с календарным планом и текстом, без пересчёта
- checklist.md «Ведомость объёмов работ»: «корректность единиц измерения» — как сверка единиц и объёмов одного и того же вида работ в разных местах документа
- checklist.md «Потребность в кадрах»: графики потребности по периодам, максимальная численность — как сверка одной и той же численности в тексте, в графике и в расчёте временных зданий
- checklist.md «Потребность в механизмах»: количество кранов, марки и характеристики кранов и прочих механизмов (бетононасосы, автокраны, экскаваторы) — как сверка значений одной и той же машины в тексте, в ведомости и в подписях схем
- checklist.md «Временное электроснабжение»: расчёт нагрузок (только записанный итог), мощность трансформаторной подстанции — как сверка между расчётом, текстом и стройгенпланом
- checklist.md «Временное водоснабжение»: расчёт потребности в воде (только записанные итоги по нуждам), источник водоснабжения, диаметры временных сетей
- checklist.md «Экологические мероприятия»: вывоз строительных отходов (полигон), временное водоотведение из котлована — только как сверка места и дальности вывоза и способа водопонижения, записанных в разных местах
- project_params.md: площадь площадки, продолжительность строительства, количество, марка, грузоподъёмность и вылет кранов, ограждение, временные дороги, максимальная численность рабочих, мощность ТП, потребность в воде, глубина котлована и объём земляных работ, наличие сноса — как перечень сверяемых признаков
- drawing_types.md: перечень мест документа (стройгенплан, календарный план, схема организации площадки, схема монтажа, разрез котлована, схемы временных сетей, графики потребности в кадрах и механизмах, план демонтажа, ведомости, общие указания)
- role.md: предмет раздела (краны и механизмы, временные здания и сети, строительная площадка, кадры, снос и демонтаж, календарный план) — только как перечень объектов

Excluded:

- checklist.md «Стройгенплан»: привязка кранов к осям, пересечение опасных зон с застройкой, дорогами и ЛЭП, расположение въездов и выездов и схема движения, размеры и привязка зон складирования, размещение бытового городка, радиусы поворотов дорог; «Потребность в механизмах»: «вылет стрелы: покрытие всей зоны монтажа»; «Временное электроснабжение» и «Временное водоснабжение»: трассировка временных сетей, размещение ТП — выводы из графики чертежа
- checklist.md «Стройгенплан»: высота ограждения не менее 2,0 м, ширина дорог не менее 3,5 и 6,0 м, проходы не менее 1,0 м, пожарный проезд не менее 3,5 м, расстояние бытового городка от опасных зон, санитарные требования; «Календарный план»: соответствие продолжительности СНиП 1.04.03-85*; «Охрана труда и безопасность»: соответствие СНиП 12-03-2001 и СНиП 12-04-2002 — нормативные требования и пределы (W57)
- checklist.md «Стройгенплан»: защитный козырёк над тротуарами, знаки, пункт мойки колёс, пожарные гидранты, временное освещение; «Временное электроснабжение»: заземление, охранное, рабочее и аварийное освещение; «Временное водоснабжение»: пожарные гидранты; «Охрана труда и безопасность»: перечень мероприятий, ограждение опасных зон, сигнальное ограждение, предупредительные знаки, средства защиты, мероприятия при работе на высоте; «Экологические мероприятия»: пылеподавление, защита зелёных насаждений и почвенного слоя, шумозащита, наличие временного водоотведения; «Ведомость объёмов работ»: «полнота перечня видов работ» — требование, чтобы указание было (v1, условие 5)
- checklist.md «Календарный план»: последовательность выполнения работ, критический путь, допустимость совмещения работ, сезонность; «Потребность в механизмах»: обоснование количества кранов, подбор прочих механизмов; «Потребность в кадрах»: «соответствие количества рабочих объёмам работ и срокам»; «Экологические мероприятия»: периодичность вывоза отходов — оценка правильности и достаточности решения
- checklist.md «Потребность в механизмах»: грузоподъёмность на максимальном вылете не меньше массы самого тяжёлого элемента; «Временное электроснабжение»: расчёт нагрузок, сечения кабелей; «Временное водоснабжение»: расчёт потребности; «Потребность в кадрах»: «максимальная численность — соответствие размерам бытового городка» — инженерный расчёт и его перепроверка
- checklist.md «Календарный план»: «увязка с графиками поставки материалов и оборудования»; «Ведомость объёмов работ»: «соответствие объёмов работ проектным решениям (разделы КР, АР, ОВ, ВК, ЭОМ)» — сравнение с другими томами, которых нет в документе
- project_params.md: «нормативные ссылки (СП 48.13330, СП 49.13330, СНиП 12-03, СНиП 12-04 и др.)» — нормоконтроль (W57); JSON-шаблон project_params, поле winter_construction и описание полей — формат вывода legacy
- finding_categories.md: десять категорий (site_plan, schedule, crane_zones, safety, temporary_facilities, materials_logistics, environmental, demolition, documentation, normative_refs) не переносятся — у v1 ровно две категории
- role.md: «находишь ошибки и несоответствия нормативной базе РФ», «рекомендации строго с привязкой к пунктам нормативных документов», «увязка со смежниками», «критический путь», подбор кранов, безопасность и экологические мероприятия как предмет оценки — противоречит v1 (без ссылок на нормы, без вердикта и без оценки решения)

Open questions for the expert reviewer:

- Формулировки «марка крана уточняется в ППР», «решения уточняются при разработке ППР», «по выбору подрядной организации» — заполнитель (корень «уточн») или принятое в ПОС решение отложить выбор до проекта производства работ?
- Сумма продолжительностей этапов в календарном плане законно больше общей продолжительности из-за совмещения работ, а «Итого» распределения объёмов или капитальных вложений по периодам может не давать 100 %: считать ли находкой расхождение итоговой строки с суммой (сейчас пересчёт исключён)?
- Текстовый слой календарного плана и графиков потребности в кадрах и механизмах (диаграммы Ганта, гистограммы) обычно разорван: надёжна ли сверка продолжительностей и численности с ними, или этот пункт даст систематические ложные находки?
- Максимальная численность работающих и численность в наиболее многочисленную смену, принятая в расчёте временных зданий (часто долей от максимума), — хватает ли условия 2 и пояснения в перечне мест, чтобы эти значения не сравнивались как одно?

### TX — Технологические решения (ТХ)

Package `src/auditmanager/analysis/text/profiles/tx/`; `analysis_profile_id` `ap_01M5AXG1K6MGZGFCBG75M9ZR9D`, `prompt_bundle_id` `pb_01M5AXG1K6E7TR87P0RGP6QBZM`, status `draft`.

| Legacy source file | SHA-256 |
| --- | --- |
| `prompts/disciplines/TX/role.md` | `c7613a8b11f2cfef40eac29b68343d62dbfec3d8811c82445e0be49162bbc30d` |
| `prompts/disciplines/TX/checklist.md` | `1ac7f1cc6b994952f2fa74b56b72db010e4c7c6e0a05d54801940408d76f1bbf` |
| `prompts/disciplines/TX/drawing_types.md` | `25adf17e19e877514a047342bb4b40b79389a8b0f2f5fe974f7ccf896780dbb4` |
| `prompts/disciplines/TX/project_params.md` | `213459e8dd3bfd9b8a1c03969ef42b5d0edb1bb417f66637582289595262de02` |
| `prompts/disciplines/TX/finding_categories.md` | `345de86c9456996ea95858548929cfc09dd60c4e51cc3c95c7f7fc71589fbe55` |

Condition 1 objects: зданиям, этажам, уровням паркинга, предприятиям, помещениям, технологическим зонам или позициям оборудования. Condition 2 near-misses: установленная и потребляемая электрическая мощность оборудования, максимальный часовой и суточный расход воды, общая и торговая площадь помещения.
Extra norm families named in the exclusion sentence: СанПиН.

Kept (reframed as same-document cross-checks):

- checklist.md «Спецификации и ведомости»: соответствие марок оборудования спецификации и планам; технические характеристики (производительность, мощность, габариты) — как сверка одной и той же позиции между экспликацией, спецификацией и таблицами
- checklist.md «Расчётные параметры и нормативы для сверки»: нагрузки на перекрытия, расходы воды и стоков, электрические мощности, тепло- и холодовыделения — только как сверка одних и тех же значений внутри документа ТХ (спецификация, таблицы нагрузок и подключений, пояснительная записка)
- checklist.md «Планы расстановки оборудования»: «подключение к инженерным сетям» — как сверка записанных параметров подключения одной позиции между таблицей подключений и спецификацией
- checklist.md «Встроенные помещения общественного назначения»: складские помещения (площадь, температурный режим) — как сверка одного и того же помещения в экспликации, пояснительной записке и спецификации
- checklist.md «Предприятия общественного питания»: мощность теплового оборудования, количество моечных ванн и холодильного оборудования — только как сверка значений одной позиции между местами документа
- checklist.md «Медицинские помещения»: классы чистоты помещений — как сверка класса одного и того же помещения
- checklist.md «Паркинг»: размеры машиномест и количество машиномест для МГН — только как сверка прямо записанных чисел между общими данными, пояснительной запиской и таблицами
- checklist.md «Мусороудаление»: диаметр ствола мусоропровода, количество контейнеров — как сверка значений между пояснительной запиской, общими данными и спецификацией
- project_params.md: назначение, количество и площади встроенных помещений, характеристики оборудования (мощность, производительность), количество и размеры машиномест, нагрузки на перекрытия от оборудования, расходы воды, стоков и электроэнергии, тепло- и холодовыделения, мусороудаление; из JSON-шаблона — число посадочных мест, уровней паркинга и загрузочных — как перечень признаков для сверки
- drawing_types.md: перечень мест документа (план расстановки оборудования, технологический план этажа, план паркинга, загрузочная зона, мусорокамера, планы предприятия питания и медицинского помещения, схема подключений, спецификация, разрез, общие указания)
- role.md: предмет раздела (встроенные помещения, предприятия питания, медицинские помещения, паркинги, мусороудаление, погрузочно-разгрузочные зоны и грузовые лифты) — только как перечень объектов
- finding_categories.md: смысл категории documentation («несоответствие между чертежами и спецификациями») покрыт категорией internal_contradiction; сам код не переносится

Excluded:

- checklist.md «Расчётные параметры и нормативы для сверки»: сверка нагрузок с разделом КР, расходов воды и стоков с ВК, электрических мощностей с ЭОМ, тепло- и холодовыделений с ОВиК — сравнение с другими разделами (доступен только текст этого документа)
- checklist.md «Планы расстановки оборудования»: соответствие размеров оборудования каталожным данным — сверка с внешним источником, которого нет в документе
- checklist.md «Расчётные параметры»: нормативная площадь на единицу оборудования и рабочее место; «Планы»: проходы и зазоры не менее 0,7 и 1,2 м; «Встроенные помещения»: количество санитарных приборов по СП 118; «Паркинг»: размеры машиномест не менее 2,5×5,3 м (для МГН 3,6×6,0 м), ширина проездов не менее 6,0 и 3,5 м, доля машиномест для МГН не менее 10 %; «Предприятия общественного питания»: достаточность числа моечных ванн; «Мусороудаление»: размеры мусорокамер и контейнерных площадок, достаточность числа контейнеров — нормативные пределы и пересчёт (W57)
- checklist.md «Планы расстановки оборудования»: привязка оборудования к строительным осям, доступ для обслуживания и ремонта; «Паркинг»: радиусы поворотов на рампах и в проездах; «Мусороудаление»: размещение мусорокамер — выводы из графики чертежа
- checklist.md «Встроенные помещения»: функциональное зонирование (чистые и грязные зоны, потоки), раздельные входы для посетителей и персонала, загрузочные зоны (отдельный вход, тамбур, разворот тележек); «Предприятия общественного питания»: технологическая цепочка, раздельные потоки сырья и готовой продукции, соответствие холодильного оборудования объёму хранения; «Медицинские помещения»: раздельные потоки пациентов и персонала, отделка стен, полов и потолков — оценка правильности и достаточности технического решения
- checklist.md: наличие напольных трапов в мокрых зонах, подключение оборудования к инженерным сетям и теплового оборудования к вентзонтам, вентиляция складских помещений, подключение моечных к ГВС, ХВС и канализации, жироуловители на выпусках, бактерицидные облучатели и рециркуляторы, системы контроля CO и вентиляция по сигналу, отделка, вентиляция и водоснабжение мусорокамер, клапаны и прочистка мусоропровода, подъезд мусоровоза, раздельный сбор отходов, комплектность поставки — требование, чтобы указание было (v1, условие 5)
- checklist.md «Паркинг»: пожарные отсеки, дренчерные завесы, автоматическое пожаротушение — нормативные требования пожарной безопасности и предмет других разделов
- project_params.md: «нормативные ссылки (СП 118, СП 113, СП 154, СанПиН и др.)» — нормоконтроль (W57)
- project_params.md: JSON-шаблон параметров и таблица «Описание полей» — формат вывода legacy; признаки, которые он извлекал, перенесены в пункты сверки
- role.md: «находишь несоответствия нормативной базе РФ», «рекомендации строго с привязкой к пунктам нормативных документов» — противоречит v1 (без ссылок на нормы, без вердикта)
- role.md: технологические требования к помещениям (высота, нагрузки на перекрытия, вибрация), потоки людей, грузов и отходов, санитарно-гигиенические требования к пищевым производствам, технологическое оборудование паркингов (шлагбаумы, вентиляция, CO-датчики) — оценка решения и нормативные требования
- finding_categories.md: категории equipment_layout, process_flow, utility_connections, parking, food_technology, sanitary, waste, loading, capacity, documentation, normative_refs не переносятся — у v1 ровно две категории

Open questions for the expert reviewer:

- Формулировки «технологическое оборудование подбирается арендатором», «марка оборудования уточняется на стадии РД» — заполнитель (так по v1) или принятое разграничение объёма проектирования?
- Номера позиций оборудования часто повторяются в экспликациях разных помещений и предприятий: достаточно ли формулировки «одна и та же позиция», или одинаковый номер в разных помещениях будет давать систематические ложные находки (условие 1)?
- Считать ли находкой расхождение суммарной мощности или расхода воды в пояснительной записке с суммой строк спецификации или таблицы нагрузок (сейчас пересчёт исключён)?
- Позиция оборудования в экспликации плана без строки в спецификации (или наоборот) — нужна ли такая находка (в v1 это не категория)?
- Полон ли перечень мест сверки для типового комплекта ТХ жилого дома со встроенными помещениями и паркингом, и не стоит ли убрать пункты о паркинге, мусороудалении и грузовых лифтах, если эти значения обычно приводятся только в других разделах?

### KJ — Конструкции железобетонные (КЖ)

Package `src/auditmanager/analysis/text/profiles/kj/`; `analysis_profile_id` `ap_01M5AXG1K82P9BCJ1NRYSTC2NY`, `prompt_bundle_id` `pb_01M5AXG1K8EDTH597XY32Z696Y`, status `draft`.

| Legacy source file | SHA-256 |
| --- | --- |
| `prompts/disciplines/KJ/role.md` | `29004c6454798d53b5eb518b25990f39b223ce1b7b0b86c85aa723e85fe0f2af` |
| `prompts/disciplines/KJ/checklist.md` | `07ecdfce7696f16d004877117a58479edafca6f2fa8d81d530c6b20201b12801` |
| `prompts/disciplines/KJ/drawing_types.md` | `a50d6c11bcdd38e4678dbd380fda27869c27bfd718070600b15eed57b2761db8` |
| `prompts/disciplines/KJ/project_params.md` | `0a32c5a0eede3b3b69af0676a087220b30ad724a3dcfdee9b877e41fc7cdbafb` |
| `prompts/disciplines/KJ/finding_categories.md` | `9efdf059b322a51cbb5109e06190948cd30f6ea50e901c9d47d8a79ffbce48ee` |

Condition 1 objects: зданиям, секциям, этажам, захваткам, конструкциям, маркам элементов, сечениям, узлам или зонам армирования. Condition 2 near-misses: защитный слой бетона и расстояние от грани до оси стержня, длина анкеровки и длина нахлёста, отметка верха плиты и отметка чистого пола.

Kept (reframed as same-document cross-checks):

- checklist.md «Класс бетона и требования к нему»: класс по прочности на сжатие для каждого элемента, марки по морозостойкости F и водонепроницаемости W — как сверка значений одной и той же конструкции между общими данными, примечаниями к листам и ведомостью материалов
- checklist.md «Арматура — материалы и классы»: класс арматуры рабочего и конструктивного армирования — как сверка класса одной и той же позиции на листе армирования и в спецификации
- checklist.md «Армирование — геометрия»: диаметры основных и конструктивных стержней, шаг стержней и хомутов, количество стержней (сверка плана и спецификации)
- checklist.md «Анкеровка и стыки арматуры»: длины анкеровки и нахлёста («сверка с чертежами»), тип механических и сварных соединений — как сверка таблицы длин, общих указаний и примечаний к узлам
- checklist.md «Защитный слой бетона»: указание защитного слоя в примечаниях и общих указаниях — как сверка значений для одной и той же арматуры одной конструкции
- checklist.md «Конструктив — колонны, стены, пилоны», «Конструктив — плиты перекрытия и покрытия», «Конструктив — фундаменты», «Конструктив — лестницы и пандусы»: размеры сечений, толщина плит, диаметры, количество и шаг продольной, поперечной, верхней и нижней арматуры, тип и длина нахлёста стыков колонн по высоте, длина заделки арматуры колонн в фундамент, глубина заложения (отметка низа), класс и толщина бетонной подготовки, армирование ростверка, маршей и площадок — только как сверка записанных значений одного и того же элемента
- checklist.md «Сопряжения с другими разделами»: закладные детали, анкерные болты, отверстия для инженерных сетей — только как сверка ведомостей закладных изделий и отверстий с надписями на листах этого же документа
- checklist.md «Огнестойкость»: требуемый предел огнестойкости несущих конструкций; «Антикоррозийная защита»: класс агрессивности среды — как сверка записанных значений между общими данными, общими указаниями и примечаниями
- checklist.md «Производство работ»: распалубочная прочность — как сверка значения для одной и той же конструкции между общими указаниями и примечаниями к листам
- checklist.md «Спецификация и ведомости»: спецификация арматуры (диаметр, длина, количество, масса, класс), общая ведомость расхода стали по маркам, ведомость материалов, соответствие марок и количеств между чертежами и спецификацией
- checklist.md «Реестр отклонений РД от ПД»: «соответствие отклонений техническим решениям» — как сверка принятого значения из реестра со значением на листах этого же комплекта
- project_params.md: классы бетона по прочности, морозостойкости и водонепроницаемости, классы арматуры, защитный слой, требуемый предел огнестойкости, класс агрессивности среды, класс ответственности и коэффициент надёжности, сейсмичность, тип фундамента, толщины плит и стен, конструктивная схема, длины анкеровки и нахлёста, распалубочная прочность — как перечень признаков для сверки
- drawing_types.md: перечень мест документа (общие данные, реестр отклонений, опалубка вертикальных конструкций, плит и фундаментов, маркировочная схема, армирование колонн, стен, плит, фундаментов и лестниц, усиление отверстий, разрезы и сечения, спецификация и ведомости)
- role.md: предмет раздела (монолитные и сборные железобетонные конструкции, классы бетона и арматуры, защитный слой, анкеровка и стыки, закладные детали, спецификации и ведомости расхода стали) — только как перечень объектов и признаков

Excluded:

- checklist.md «Расчётная схема и нагрузки»: соответствие расчётной схемы конструктивной схеме здания, полнота учёта нагрузок, комбинации нагрузок по СП 20, назначение коэффициентов надёжности по нагрузке и по назначению; «Армирование — геометрия»: минимальный процент армирования; «Конструктив»: соответствие сечений расчёту, стойкость плоской формы пилонов, проверка толщины плиты на продавливание и прогиб; «Конструктив — фундаменты»: учёт глубины промерзания и уровня грунтовых вод; «Спецификация и ведомости»: удельный расход стали (кг/м³) в сравнении с расчётными показателями — инженерный расчёт
- checklist.md «Расчётная схема и нагрузки»: сверка нагрузок с разделами АР, ОВиК, ТХ, КМ; «Сопряжения с другими разделами»: КМ-КЖ, АР-КЖ, ОВиК/ВК/ЭОМ/СС-КЖ, ТХ-КЖ; «Конструктив — фундаменты»: сверка типа фундамента с инженерно-геологическими изысканиями; «Конструктив — лестницы и пандусы»: геометрия проступей и подступенков (пересечение с АР) — сравнение с другими разделами и томами (доступен только текст этого документа)
- checklist.md «Класс бетона»: соответствие ГОСТ 26633-2015 и ГОСТ 7473-2010; «Арматура»: запрет устаревших марок А-II, А-III, А-IV и ГОСТ 5781-82, проволочная арматура по ГОСТ 6727-80, соответствие диаметров нормативному сортаменту; «Анкеровка и стыки»: сертификация муфт по ГОСТ 32702, сварные соединения по ГОСТ 14098-2014; «Производство работ»: классы поверхности опалубки по СП 70, контроль прочности бетона по ГОСТ 18105, 22690, 17624, 10180 — нормоконтроль и актуальность ссылок (W57)
- checklist.md «Армирование — геометрия»: максимальные шаги арматуры по СП 63; «Анкеровка и стыки»: длины анкеровки и нахлёста по СП 63 (п. 10.3.25), не более 50 % стыкуемой арматуры в одном сечении, гибочные параметры (диаметр оправки, углы загиба); «Защитный слой»: величина по СП 63 (п. 10.3.2) в зависимости от класса среды, огнестойкости и контакта с грунтом, типовые значения 20–70 мм; «Сейсмика»: применение СП 14 при сейсмичности 7 баллов и более; «Огнестойкость»: назначение требуемого REI по ФЗ-123 и СП 2.13130, соответствие защитного слоя и толщины элемента требуемому REI по СП 468; «Антикоррозийная защита»: назначение класса среды по СП 28, требования к бетону (W, F) и арматуре в агрессивной среде — нормативные пределы и требования (W57)
- checklist.md «Класс бетона»: применимость марок F и W к конструкциям, подвижность смеси, водоцементное отношение и самоуплотнение «при необходимости», требования к цементу при агрессивных грунтовых водах; «Арматура»: выбор классов (А500С — рабочая, А240 — хомуты, B500C — сетки); «Конструктив»: косвенное армирование в местах повышенных напряжений, дополнительное армирование опорных зон, усиление отверстий и ростверка над сваями, обрамление балконных плит и огибающая арматура, температурно-усадочные швы, надёжность анкеровки маршей в опорной зоне, тип лестницы, совместимость гидроизоляции с классом W; «Сейсмика и прогрессирующее обрушение»: неразрывность и связность верхней и нижней арматуры в узлах и пролётах, особые требования к соединениям; «Огнестойкость»: учёт огнестойкости балконных плит и маршей на путях эвакуации; «Антикоррозийная защита»: дополнительные меры защиты, защита закладных деталей; «Производство работ»: тип опалубки, уход за бетоном; «Реестр отклонений»: обоснование отклонений и их согласование — оценка правильности и достаточности технического решения
- checklist.md «Защитный слой»: корректность защитного слоя в узлах сопряжения; «Конструктив — колонны»: размещение продольной арматуры, конфигурация хомутов и крюки 135°, положение стыков относительно перекрытия; «Конструктив — плиты»: разбивка армирования на зоны; «Конструктив — лестницы»: опирание марша на стены и плиты; «Производство работ»: положение и обработка рабочих швов бетонирования — выводы из графики чертежа
- checklist.md: «указание ГОСТ в спецификации арматуры и на чертежах», обеспечение защитного слоя фиксаторами, указание метода сварки, наличие реестра отклонений РД от ПД — требование, чтобы указание было (v1, условие 5)
- project_params.md: «нормативные ссылки (СП 63, СП 70, СП 20, СП 22, СП 28, ГОСТ 34028-2016, ГОСТ 26633-2015)», «устаревшие — А-II, А-III, ГОСТ 5781-82» — нормоконтроль (W57)
- project_params.md: категория требований к трещиностойкости — назначается по нормам и расчёту; рабочие швы бетонирования — выводы из графики чертежа; шифр комплекта и организация-разработчик — реквизиты документа, а не признак конструкции (нужна ли их сверка, вынесено в вопросы эксперту)
- project_params.md: JSON-шаблон параметров и таблица «Описание полей» (в том числе нагрузки, снеговой и ветровой районы, этажность) — формат вывода legacy; признаки из «Что искать в тексте» перенесены в пункты сверки
- role.md: «находишь несоответствия нормативной базе РФ», «рекомендации строго с привязкой к пунктам нормативных документов» — противоречит v1 (без ссылок на нормы, без вердикта)
- role.md: расчётные схемы и нагрузки, проверка прогибов и трещиностойкости по СП 63, сейсмика и прогрессирующее обрушение, порядок производства работ, сопряжения с разделами КМ, АР, ОВиК, ВК, ЭОМ, СС — инженерный расчёт, оценка решения и сравнение с другими разделами
- finding_categories.md: категории concrete_class, rebar_class, cover_thickness, anchorage, lap_length, rebar_geometry, stirrups, column_detail, slab_detail, foundation_detail, stairs_detail, opening_reinforcement, progressive_collapse, seismic_detail, fire_rating, corrosion_protection, km_kj_coordination, ar_kj_coordination, mep_coordination, construction_sequence, spec_mismatch, documentation, normative_refs не переносятся — у v1 ровно две категории

Open questions for the expert reviewer:

- Обозначения класса арматуры в старой и новой системе (А-III и А400, А-I и А240) или класса и марки бетона (В25 и М350) для одной и той же позиции — противоречие или одно значение в разных обозначениях?
- Формулировки «длину стержней уточнить по месту», «отверстия выполнять по заданию смежных разделов», «отметки уточнить по факту» — заполнитель (так по v1) или принятое указание производителю работ?
- Реестр отклонений РД от ПД по своей природе приводит два значения одного признака (по ПД и по РД) — не даёт ли пункт о реестре ложных находок, и стоит ли его оставить?
- Считать ли находкой расхождение строки «Итого» ведомости расхода стали или спецификации арматуры с суммой строк (сейчас пересчёт исключён)?
- Полон ли перечень мест сверки для КЖ стадий П и Р (на стадии П листов армирования обычно нет), нужна ли сверка шифра комплекта в основных надписях листов, и не дают ли пункты о защитном слое и длинах анкеровки систематических ложных находок из-за разных условий (верхняя и нижняя арматура, сжатие и растяжение, класс бетона)?

### KM — Конструкции металлические (КМ)

Package `src/auditmanager/analysis/text/profiles/km/`; `analysis_profile_id` `ap_01M5AXG1KB71SHN23H775AP551`, `prompt_bundle_id` `pb_01M5AXG1KB45S6A5TZ0ZTWRVHS`, status `draft`.

| Legacy source file | SHA-256 |
| --- | --- |
| `prompts/disciplines/KM/role.md` | `e07abb3b3a69300b01bf2e974ed1fa35c93c41068d96cabe83775291de071920` |
| `prompts/disciplines/KM/checklist.md` | `544487191d8d819081298ed15ef532be9c5db6196942b4e959eb79de4d7bf993` |
| `prompts/disciplines/KM/drawing_types.md` | `63e89356ed9e993d1872af34c92e96d974e5920cd08e5d5307f7615582509bb3` |
| `prompts/disciplines/KM/project_params.md` | `8ddfed0a615de7c59cc6d1c38f1de402a0a79ff859474ee65d8dbbe8bdb4e6af` |
| `prompts/disciplines/KM/finding_categories.md` | `c6002c08dfbf69b88a38b5127e25a8d016a57947dceff04a7a6deb0f179c29af` |

Condition 1 objects: зданиям, секциям, этажам, отметкам, конструкциям, маркам элементов, узлам или соединениям. Condition 2 near-misses: нормативное и расчётное значение нагрузки, класс прочности болтов и класс прочности гаек, масса одного элемента и общая масса всех элементов этой марки.

Kept (reframed as same-document cross-checks):

- checklist.md «Марки стали и материалы»: «указание класса прочности стали на чертежах и в спецификации», категории стали — как сверка марки и категории одного и того же элемента
- checklist.md «Спецификация и ведомости»: соответствие спецификации металла чертежам (марки, профили, массы), соответствие марок стали в спецификации и на чертежах, ведомость метизов, ведомость сварных швов, суммарный расход стали — как сверка одних и тех же записей между местами документа
- checklist.md «Узловые соединения — сварка»: тип соединения, катет и длина шва, марка электрода или проволоки, способ сварки — как сверка надписей узла с ведомостью сварных швов и общими указаниями
- checklist.md «Узловые соединения — болты»: класс прочности, диаметр и количество болтов, фрикционные соединения (обработка поверхностей, усилие натяжения) — как сверка надписей узла с ведомостью метизов и общими указаниями
- checklist.md «Огнезащита»: требуемый предел огнестойкости, тип огнезащиты, группа огнезащитной эффективности — как сверка значений одной и той же конструкции
- checklist.md «Антикоррозийная защита»: класс агрессивности среды, система покрытий (грунт, слои, толщина), степень очистки поверхности — как сверка значений одной и той же конструкции
- checklist.md «Монтажные схемы»: масса отправочных марок и масса элементов на схемах строповки — как сверка с массой той же марки в спецификации
- checklist.md «Расчётная схема и нагрузки»: коэффициент надёжности по ответственности и значения нагрузок — только как сверка одних и тех же записанных значений между таблицей нагрузок, пояснительной запиской и общими указаниями
- project_params.md: марки и категории стали, конструктивная схема, пролёты, шаг колонн, высоты этажей, нагрузки, класс ответственности и коэффициент надёжности, требуемый предел огнестойкости, класс агрессивности среды, способы сварки и марки электродов, класс прочности болтов; из JSON-шаблона — снеговой и ветровой районы, сейсмичность, тип и группа огнезащиты, система покрытия — как перечень признаков для сверки
- drawing_types.md: перечень мест документа (схемы расположения элементов и связей, монтажная схема, узлы, сечения, чертежи ферм, колонн и балок, спецификация, общие указания)
- role.md: предмет раздела (каркас, сечения, узлы, огнезащита, антикоррозионная защита, спецификация металлопроката и метизов) и усилия N, M, Q — только как перечень объектов и признаков; усилия сверяются как записанные значения, без пересчёта

Excluded:

- checklist.md «Расчётная схема и нагрузки»: соответствие расчётной схемы конструктивной схеме здания, полнота учёта нагрузок, комбинации нагрузок по СП 20, назначение коэффициентов надёжности по нагрузке — инженерный расчёт и нормативные требования
- checklist.md «Расчётная схема и нагрузки»: сверка нагрузок с разделами АР, ОВиК, ТХ — сравнение с другими разделами (доступен только текст этого документа)
- checklist.md «Сечения элементов»: соответствие сечений результатам расчёта, местная устойчивость стенок и полок, предельные гибкости; «Узловые соединения — болты»: количество болтов по расчёту; «Прочность и устойчивость»: все пять проверок (нормальные и касательные напряжения, общая и местная устойчивость, устойчивость при кручении, устойчивость рам); «Прогибы и деформации»: предельные прогибы балок, ферм и прогонов, горизонтальные перемещения, температурные деформации; «Огнезащита»: приведённая толщина металла для расчёта огнезащиты; «Спецификация и ведомости»: сравнение расхода стали с расчётом — инженерный расчёт
- checklist.md «Марки стали»: соответствие марки условиям эксплуатации, правила применения С245, С255, С345 и 09Г2С; «Сечения»: унификация сортамента, стыковка элементов разных сечений; «Монтажные схемы»: деление на отправочные марки по транспортабельности, порядок монтажа и временное раскрепление, выбор типа монтажных соединений — оценка правильности и оптимальности решения
- checklist.md «Марки стали»: категории по ударной вязкости по ГОСТ 27772-2015; «Сварка»: минимальный катет по ГОСТ 14771-76 и максимальный по толщине элемента, разделка кромок, зазоры, подварка корня; «Болты»: шаг и расстояния до края; «Антикоррозийная защита»: класс среды по СП 28 и степень очистки по ГОСТ 9.402 как требование; «Монтажные схемы»: допуски по ГОСТ 23118-2019 — нормативные пределы и требования (W57)
- checklist.md: наличие выводных планок, указание категории швов по ответственности, наличие шайб, контргаек и стопорения, защита в зонах контакта с бетоном и кладкой, защита метизов, сертификаты и технические свидетельства на огнезащитные составы, схемы строповки — требование, чтобы указание было (v1, условие 5)
- project_params.md: «нормативные ссылки (СП 16.13330, ГОСТ 27772, ГОСТ 23118 и др.)» — нормоконтроль (W57)
- project_params.md: JSON-шаблон параметров и таблица «Описание полей» — формат вывода legacy; признаки, которые он извлекал, перенесены в пункты сверки
- role.md: «находишь несоответствия нормативной базе РФ», «рекомендации строго с привязкой к пунктам нормативных документов» — противоречит v1 (без ссылок на нормы, без вердикта)
- role.md: «проверки прочности, устойчивости, предельных прогибов и деформаций», «марки стали и их применимость», «порядок монтажа» — инженерный расчёт и оценка решения
- finding_categories.md: категории steel_grades, sections, connections, welding, bolts, stability, fire_protection, corrosion_protection, assembly, documentation, normative_refs не переносятся — у v1 ровно две категории

Open questions for the expert reviewer:

- Разные обозначения стали для одного и того же элемента (С345 по ГОСТ 27772 в спецификации и 09Г2С по ГОСТ 19281 в общих указаниях) — противоречие или допустимая замена, которую решает эксперт?
- Формулировки «усилия в узлах — по расчёту», «катеты швов принимать по наименьшей толщине свариваемых элементов», «конструкцию узла уточнить в КМД» — заполнитель (так по v1) или принятое правило и передача решения в КМД?
- Считать ли находкой расхождение общей массы металлоконструкций в общих данных или строки «Итого» спецификации с суммой масс по маркам (сейчас пересчёт исключён), и как отличать массу по спецификации от массы с учётом наплавленного металла?
- Марки элементов (Б-1, К-1) нередко повторяются на схемах разных отметок для разных конструкций — не даёт ли пункт о профиле и отметках одной и той же марки систематических ложных находок (условие 1)?
- Полон ли перечень мест сверки для КМ стадий П и Р, и не даёт ли пункт о нагрузках ложных находок из-за смешения нормативных и расчётных значений?

### OV — Отопление, вентиляция и кондиционирование (ОВ)

Package `src/auditmanager/analysis/text/profiles/ov/`; `analysis_profile_id` `ap_01M5AXG1KDVXRHH20N7KGBKPZ4`, `prompt_bundle_id` `pb_01M5AXG1KDEVEZ88HR6KYX2YP9`, status `draft`.

| Legacy source file | SHA-256 |
| --- | --- |
| `prompts/disciplines/OV/role.md` | `7de3df5fd806e2e114e67993e2e9b8683a8a2d5a15fac46df185f3f780732858` |
| `prompts/disciplines/OV/checklist.md` | `bf246ffd2bea9f32f64105f4fc5425b54517554222483f635787d27cace09c2d` |
| `prompts/disciplines/OV/drawing_types.md` | `2d51c69768a68ba1da1f590358512a56b9404478fb9aa870967dc7b527c97eee` |
| `prompts/disciplines/OV/project_params.md` | `f62c496f6e7a301424284ded3735bad8d0067479c71ecdbeae0b35594c14bc88` |
| `prompts/disciplines/OV/finding_categories.md` | `87c0747badf050cf95ecc58e5f37307f5746e9c034a4d1dc11790ab795ca99b0` |

Condition 1 objects: зданиям, секциям, этажам, системам, установкам, стоякам, отопительным приборам, помещениям или участкам воздуховодов и трубопроводов. Condition 2 near-misses: расход воздуха в тёплый и в холодный период года, расчётный расход воздуха системы и производительность установки с учётом подсосов, температурный график теплоносителя в тепловой сети и во внутреннем контуре после ИТП.

Kept (reframed as same-document cross-checks):

- checklist.md «Планы вентиляции»: маркировка систем (П1, П2, В1, В2…) — соответствие спецификации — как сверка расхода воздуха и характеристик установки одной и той же системы между таблицей характеристик, схемой, планами и спецификацией
- checklist.md «Схемы систем вентиляции»: соответствие расходов воздуха на схеме и на плане — без изменений, как сверка значений одной и той же системы
- checklist.md «Системы противодымной вентиляции (ПДВ/ПД)»: огнестойкость воздуховодов дымоудаления — как сверка записанного предела огнестойкости и способа огнезащиты одной и той же системы между местами документа, без нормативного значения; алгоритм включения — как сверка отключения общеобменных систем и очерёдности включения противодымных между пояснительной запиской, общими указаниями и описанием автоматизации
- checklist.md «Планы вентиляции»: огнезадерживающие клапаны (КОЗ) — как сверка типа, размера, предела огнестойкости и исполнения одного и того же клапана, а не их наличия; материал воздуховодов — как сверка между общими указаниями и спецификацией
- checklist.md «Планы отопления»: тепловая мощность приборов, типы отопительных приборов, материал трубопроводов — как сверка типа, типоразмера и мощности одного и того же прибора и материала труб одной системы между планом, схемой, общими указаниями и спецификацией
- checklist.md «Схемы обвязки оборудования»: параметры теплоносителя (температурный график), напор и расход циркуляционных насосов — как сверка одних и тех же записей между общими данными, пояснительной запиской, схемой обвязки и спецификацией
- checklist.md «Спецификации, таблицы»: марки и типоразмеры оборудования, характеристики вентиляционного оборудования (расход, напор, мощность), соответствие позиций чертежей и таблиц, объёмы — только количество, прямо указанное в тексте
- project_params.md: расчётные параметры наружного воздуха, расходы приточного и вытяжного воздуха по помещениям, тепловые нагрузки на отопление и вентиляцию, параметры теплоносителя, характеристики вентиляционного оборудования, системы дымоудаления и подпора — как значения, которые сверяются между местами одного документа
- drawing_types.md: перечень мест документа (планы вентиляции, отопления, кондиционирования и противодымной вентиляции, схемы воздуховодов и трубопроводов, схемы приточных и вытяжных установок, обвязка ПУ и ИТП, спецификация, общие указания, узлы)
- role.md: предмет раздела (вентиляция, кондиционирование, отопление, противодымная вентиляция, воздуховоды, трубопроводы и их теплоизоляция, автоматизация) — только как перечень объектов

Excluded:

- checklist.md «Расчётные формулы для сверки»: расход теплоносителя G = Q / (c × ΔT), воздухообмен L = n × V, тепловая мощность Q = G × c × ΔT, скорость воздуха v = L / (3600 × F), потери давления и рабочая точка вентилятора — инженерный расчёт
- checklist.md: «соответствие расходов воздуха расчёту воздухообмена по СП 60.13330», «расход воздуха дымоудаления — по расчёту, не менее нормативного», нормативные значения EI 150 / EI 60, «отдельные системы для каждой зоны дымоудаления», «компенсация при работе ПДВ — подпор воздуха в лестничные клетки, лифтовые шахты» — нормативные требования (W57) и оценка достаточности решения
- checklist.md: «соответствие параметров оборудования расчётным нагрузкам», «трассы воздуховодов — сечения, соответствие расчёту», «теплопотери помещений» в сопоставлении с мощностью приборов, «трубопроводы — диаметры, уклоны», «расширительные баки — объём по расчёту» — инженерный расчёт; сечения и диаметры участков в тексте к участку не привязаны
- checklist.md: «типы отопительных приборов — соответствие назначению помещений», «резервирование (для систем дымоудаления — обязательно)», «циркуляционные насосы — резервирование» — оценка правильности технического решения
- checklist.md: «наличие всех элементов: фильтры, нагреватели, охладители, шумоглушители», «КОЗ в местах пересечения противопожарных преград», «обратные клапаны на вытяжных системах», «запорная и регулирующая арматура», «термостатические регуляторы на приборах отопления», «узлы учёта тепловой энергии (УУТЭ)», «предохранительные клапаны», «связь с пожарной сигнализацией» — требование, чтобы элемент или указание было (v1, условие 5)
- checklist.md «Планы вентиляции»: «расположение приточных/вытяжных решёток и диффузоров», трассы воздуховодов; «Спецификации, таблицы»: метражи воздуховодов и длины трубопроводов, снятые с планов, — выводы из графики чертежа
- checklist.md «Планы вентиляции»: «маркировка систем — уникальность» — одно обозначение у разных объектов по v1 (условие 1) не противоречие; оставлена сверка значений одной и той же системы
- checklist.md «Схемы систем вентиляции»: «электропитание приточных/вытяжных установок (по смежным — раздел ЭОМ)» — сравнение с другим разделом, которого нет в тексте документа
- project_params.md: «нормативные ссылки — проверить актуальность» — нормоконтроль (W57); JSON-шаблон project_params и описание его полей — формат вывода legacy
- finding_categories.md: категории airflow, duct_sizing, heating, piping, fire_dampers, smoke_exhaust, equipment, insulation, noise, documentation, normative_refs не переносятся — у v1 ровно две категории
- role.md: «находишь ошибки и несоответствия нормативной базе РФ», «рекомендации — строго с привязкой к конкретным пунктам нормативных документов» — противоречит v1 (без ссылок на нормы, без вердикта); теплопотери, гидравлический, аэродинамический и акустический расчёты, подбор оборудования, скорости, компенсаторы и уклоны — инженерный расчёт и оценка решения

Open questions for the expert reviewer:

- Формулировки «расход уточнить при наладке», «тип решёток уточнить при заказе оборудования» — заполнитель (так по v1) или принятое указание наладочной организации и поставщику?
- Производительность установки в таблице характеристик и в спецификации часто больше расчётного расхода системы на подсосы и потери; достаточно ли примера в условии 2, или сверка расходов всё равно даст систематические ложные находки?
- Пределы огнестойкости воздуховодов одной системы противодымной вентиляции законно различаются по участкам (в пределах обслуживаемого пожарного отсека, транзит, шахта); не даёт ли пункт об огнестойкости ложных находок, если участок в тексте не назван?
- Считать ли находкой расхождение расхода системы с суммой расходов по помещениям в таблице воздухообмена или строки «Итого» таблицы тепловых нагрузок с суммой строк (сейчас пересчёт исключён)?
- Полон ли перечень мест сверки для типового комплекта ОВ стадий П и Р, в частности для кондиционирования (марки и холодопроизводительность наружных и внутренних блоков) и для ИТП, если он входит в том ОВ?

### VK — Водоснабжение и канализация (ВК)

Package `src/auditmanager/analysis/text/profiles/vk/`; `analysis_profile_id` `ap_01M5AXG1KF7NGNYMEFN97BW9ZN`, `prompt_bundle_id` `pb_01M5AXG1KFMA8QCKP6YM1K5M5W`, status `draft`.

| Legacy source file | SHA-256 |
| --- | --- |
| `prompts/disciplines/VK/role.md` | `5140872cd9a8be7e6ca091fcc95a11e54c665b5a93ae5004f93e1377b5927781` |
| `prompts/disciplines/VK/checklist.md` | `5bcccef4fbe706983b1f125dbdcded15d97ba697677eb8b07998da72147eabd1` |
| `prompts/disciplines/VK/drawing_types.md` | `b6e1ed44f153d0e3e61f25c17da7aff5bd5bdd917356e48b6a0336302e802a20` |
| `prompts/disciplines/VK/project_params.md` | `45c73d4b95b95da870598020fc4f747d8201adab0dde1d5d9e13cfb1b6905724` |
| `prompts/disciplines/VK/finding_categories.md` | `84f8c7bb03f58c603ae42c8e9286872142922e5bbeef84a27e1f47b6feff5977` |

Condition 1 objects: зданиям, секциям, зонам водоснабжения, этажам, системам, вводам, выпускам, стоякам или помещениям. Condition 2 near-misses: суточный, часовой и секундный расход воды, гарантированный напор в наружной сети и требуемый напор на вводе, условный проход (DN) и наружный диаметр трубы.
Extra norm families named in the exclusion sentence: СанПиН.

Kept (reframed as same-document cross-checks):

- checklist.md «Водомерный узел»: тип водомера (счётчик, калибр, класс точности) — как сверка одного и того же водомерного узла между схемой, пояснительной запиской и спецификацией, а не требование наличия; «Спецификации, таблицы»: арматура (типы, DN) — в той же сверке для арматуры водомерного узла
- checklist.md «Насосные станции»: количество, характеристики (Q, H) и резерв повысительных насосов, характеристики циркуляционных насосов ГВС, расход и напор дренажных насосов — как сверка марки, подачи, напора и записанного числа рабочих и резервных насосов одной установки, а не требование резерва
- checklist.md «Стояковые схемы и аксонометрия»: диаметры стояков и магистралей, высотные отметки разводки; «Планы канализации»: выпуски из здания (уклон, диаметр, глубина) — как сверка записанных значений одного и того же стояка, ввода или выпуска между схемами, разрезами и планами
- checklist.md «Планы ХВС»: материал труб (ПП, ПЭ, сталь) — соответствие проектным решениям; «Спецификации, таблицы»: трубы (марки, диаметры), утеплитель для изоляции (тип, толщина); «Планы ХВС» и «Планы ГВС»: изоляция трубопроводов — как сверка материала и марки труб и изоляции одной и той же системы между общими указаниями, пояснительной запиской и спецификацией
- checklist.md «Планы ГВС»: система приготовления ГВС (ИТП/ЦТП, бойлер), температура ГВС — как сверка способа приготовления и записанной температуры между общими данными, пояснительной запиской и схемами, без нормативного значения
- checklist.md «Ливневая канализация (внутренние водостоки)»: количество и тип водоприёмных воронок, диаметры водосточных стояков, отвод в наружную ливнёвку или на рельеф — как сверка записанных значений одной и той же системы водостоков
- checklist.md «Спецификации, таблицы»: сантехприборы (тип, количество), насосное оборудование (марка, характеристики), соответствие позиций на чертежах и в спецификации; «Планы ГВС»: тип и количество полотенцесушителей — как сверка количества, прямо указанного в тексте
- project_params.md: источник водоснабжения, гарантированный напор, система ГВС, суточное водопотребление, типы канализации и водостоков, число насосов, материалы труб, калибр водомера, расчётные расходы, напоры, диаметры и уклоны, «противоречия между разделами ПЗ и чертежами» — как значения, которые сверяются между местами одного документа
- drawing_types.md: перечень мест документа (планы ХВС, ГВС, канализации и водостоков, водомерный узел, насосная станция, стояковые и аксонометрические схемы, разрезы, узлы, спецификация, общие указания)
- role.md: предмет раздела (ХВС, ГВС, бытовая и ливневая канализация, водомерные узлы, насосные станции) — только как перечень объектов и систем

Excluded:

- checklist.md «Расчётные формулы для сверки»: расход воды q = 5 × q₀ × α, потери напора ΔH = i × L + Σξ × v²/2g, сравнение гарантированного напора в наружной сети с требуемым, скорость и наполнение h/d в канализации — инженерный расчёт; свободный напор у прибора не менее 2 м и минимальные уклоны по диаметрам — нормативные пределы
- checklist.md: «соответствие калибра водомера расчётному расходу», «диаметры трубопроводов соответствуют расчёту расходов», «циркуляционная линия ГВС — диаметры», «диаметры отводных трубопроводов (Ø50 — мойки/умывальники, Ø100 — унитазы)» — инженерный расчёт и оценка правильности решения
- checklist.md: «температура ГВС не менее 60 °C (СанПиН 1.2.3685-21)», «уклоны самотёчных трубопроводов», «ревизии и прочистки на стояках через этаж, но не реже чем через 3 м», «вентиляция канализационных стояков выше кровли на 0,5 м», «материал труб — соответствие ГОСТ», «трубы, арматура (DN, PN) — соответствие ГОСТ» — нормативные требования и нормоконтроль (W57)
- checklist.md «Водомерный узел»: фильтр грубой очистки, обратный клапан, задвижки, манометры, обводная линия, дренаж; «Планы ХВС», «Планы ГВС»: запорная арматура на ответвлениях, поквартирные счётчики ХВС и ГВС, наличие циркуляционной линии, обязательная изоляция ГВС, изоляция ХВС «в необходимых случаях», компенсаторы на стояках; «Планы канализации»: гидрозатворы на всех приборах; «Стояковые схемы»: запорная арматура и компенсаторы; «Насосные станции»: резерв, виброизоляция и шумозащита, арматура, обратные клапаны, манометры, автоматика управления; «Ливневая канализация»: ревизии на стояках, обогрев воронок — требование, чтобы элемент или указание было (v1, условие 5)
- checklist.md: «поэтажная разводка (тупиковая/кольцевая)», подключение полотенцесушителей, «подключение стиральных/посудомоечных машин», размещение воронок, «отводы и тройники — соответствие условным обозначениям», длины труб, снятые с планов, — выводы из графики чертежа и оценка решения
- project_params.md: «нормативные ссылки — проверить актуальность», «марки труб и соответствие ГОСТ 32415-2013 (ПП), ГОСТ 18599-2001 (ПЭ)», «температурные параметры ГВС (не менее 60 °C)» — нормоконтроль (W57); JSON-шаблон project_params и описание его полей — формат вывода legacy
- finding_categories.md: категории cold_water, hot_water, sewerage, storm_drain, water_meter, pumps, pipe_sizing, insulation, materials, documentation, normative_refs не переносятся — у v1 ровно две категории
- role.md: «находишь ошибки и несоответствия нормативной базе РФ», «рекомендации — строго с привязкой к конкретным пунктам нормативных документов» — противоречит v1 (без ссылок на нормы, без вердикта); пожарные насосы и пожарный водопровод «в координации с ПТ» — сравнение с другим разделом; водоподготовка «при необходимости» — оценка необходимости решения

Open questions for the expert reviewer:

- Формулировки «напор в точке подключения уточнить по ТУ», «отметки выпусков уточнить по месту», «марку насосов уточнить при заказе» — заполнитель (так по v1) или ссылка на технические условия и принятое указание монтажной организации и поставщику?
- Диаметры полимерных труб в спецификации обычно заданы наружным диаметром и толщиной стенки, а на схемах — условным проходом; достаточно ли примера в условии 2, или сверка диаметров даст систематические ложные находки?
- Температура горячей воды законно различается в разных точках (на выходе из теплообменника, у водоразборных приборов, в циркуляционном трубопроводе); не даёт ли пункт о температуре ложных находок, если точка в тексте не названа?
- Считать ли находкой расхождение общего расхода здания с суммой расходов по системам или потребителям в таблице расчётных расходов (сейчас пересчёт исключён)?
- Полон ли перечень мест сверки для типового комплекта ВК стадий П и Р, и нужно ли отдельно учитывать внутренний противопожарный водопровод (В2), если он оформлен в том же томе ВК?

### PT — Противопожарный водопровод (ПТ)

Package `src/auditmanager/analysis/text/profiles/pt/`; `analysis_profile_id` `ap_01M5AXG1KHY5S7A1AFVND7FPS9`, `prompt_bundle_id` `pb_01M5AXG1KH4JG7TMH93XACNF6H`, status `draft`.

| Legacy source file | SHA-256 |
| --- | --- |
| `prompts/disciplines/PT/role.md` | `8d9136f0d6bcc1434ed0569106c4c9cd65e7658e72e13ba8fbe97964322bbbb3` |
| `prompts/disciplines/PT/checklist.md` | `64e1b131ba76fc6c86d0844728c8ed3ce21c02e69a325c244eb93b0155c39bc7` |
| `prompts/disciplines/PT/drawing_types.md` | `ddb28b04a734d033de15b72bfea23662b9362abe142f7b550abb80cf1588e9cc` |
| `prompts/disciplines/PT/project_params.md` | `97d008af80e8d984715ccadca0a0fc1bb0c228f584851ae1155c519e462e230a` |
| `prompts/disciplines/PT/finding_categories.md` | `03e4ca176804c587c489939913747b97fd51d8b36b9f1c12b73170ab018f913e` |

Condition 1 objects: зданиям, пожарным отсекам, этажам, зонам, системам, установкам, секциям, узлам управления, стоякам, пожарным кранам или помещениям. Condition 2 near-misses: расход одной пожарной струи и расчётный расход внутреннего противопожарного водопровода, свободный напор у пожарного крана и напор насоса, расчётная площадь орошения и площадь, защищаемая одним оросителем.

Kept (reframed as same-document cross-checks):

- checklist.md «Внутренний противопожарный водопровод (ВПВ)»: количество пожарных струй и расход каждой струи, высота компактной части струи, свободный напор у пожарного крана, время работы ВПВ — как сверка записанных значений между общими данными, пояснительной запиской и гидравлическим расчётом, без нормативных значений
- checklist.md «Пожарные краны (ПК)»: длина рукава, диаметр (DN50 или DN65), тип пожарного шкафа, высота размещения ПК — как сверка записанных значений пожарных кранов одного обозначения между общими указаниями, узлами и спецификацией, а не проверка нормативной высоты
- checklist.md «АУПТ спринклерная»: тип оросителей и положение розетки, температура срабатывания, интенсивность орошения по группе помещений, давление у диктующего оросителя, количество оросителей в секции, тип узла управления — как сверка записанных значений одних и тех же помещений, секций и узлов управления, без нормативных значений
- checklist.md «АУПТ дренчерная»: расход дренчерной завесы на погонный метр, время работы, вид побудительной системы, расход на дренчерное пожаротушение по площади — как сверка записанных значений одной и той же установки или завесы
- checklist.md «Пожарная насосная станция»: подача, напор и мощность двигателя основного насоса, резервный насос, жокей-насос — как сверка марки, характеристик и записанного числа рабочих и резервных насосов одной установки, а не требование резерва
- checklist.md «Пожарный резервуар»: объём неприкосновенного запаса воды, раздельные резервуары — как сверка записанного объёма и числа резервуаров, без пересчёта и нормативного порога
- checklist.md «Кольцевые и тупиковые сети»: диаметры трубопроводов, материал труб — как сверка материала и диаметра одного и того же расчётного участка или сети между таблицей гидравлического расчёта, расчётной схемой, общими указаниями и спецификацией
- checklist.md «Спецификации, таблицы»: соответствие оборудования проектным параметрам (насосы, арматура, оросители) — как сверка одной и той же позиции между схемами, пояснительной запиской и спецификацией; соответствие позиций чертежей и спецификации; объёмы — только количество оросителей в секции и число насосов, прямо указанные в тексте
- project_params.md: число струй, расход, напор и время работы ВПВ; группа помещений, интенсивность и площадь орошения; характеристики насосов; объём пожарного резервуара; диаметры трубопроводов из таблиц и схем; высота, этажность, класс функциональной пожарной опасности и степень огнестойкости здания; «противоречия между гидравлическим расчётом и принятыми решениями» — как сверка записанных значений без пересчёта
- drawing_types.md: перечень мест документа (планы ВПВ, спринклеров и дренчеров, пожарная насосная, стояковые и аксонометрические схемы, узлы управления, гидравлический расчёт, спецификация, общие указания, узлы)
- role.md: предмет раздела (ВПВ, спринклерные и дренчерные АУПТ, пожарные насосные станции, резервуары, узлы управления, кольцевые и тупиковые сети) — только как перечень объектов

Excluded:

- checklist.md «Расчётные формулы для сверки»: расход ВПВ Q = n × q, напор у пожарного крана Hсв = Hг + hпот + hнас, площадь орошения S = Q / i, объём резервуара V = Q × T × 60 / 1000, высота компактной части струи не менее высоты помещения (6 м для DN50, 8 м для DN65), интенсивность по СП 485 — инженерный расчёт и нормативные значения
- checklist.md «Внутренний противопожарный водопровод (ВПВ)»: необходимость ВПВ по высоте и этажности (СП 10.13130.2020, табл. 1), свободный напор не менее 4 м, время работы не менее 3 ч, давление у ПК не более 0,4 МПа (с диафрагмой до 0,6 МПа), соответствие высоты компактной части струи высоте помещения — нормативные требования пожарной безопасности (W57)
- checklist.md «Пожарные краны (ПК)»: высота 1,35 м ± 0,15 м как норматив, орошение каждой точки не менее чем двумя струями от разных ПК, длина рукава — соответствие расчётному радиусу действия, комплектация шкафов (рукав, ствол, вентиль), размещение ПК у входов, на лестничных площадках и в вестибюлях — нормативные требования, расчёт, требование наличия и выводы из графики
- checklist.md «АУПТ спринклерная»: температура срабатывания — соответствие температуре помещения, расстановка оросителей и расстояния до стен (СП 485, табл. 5.1–5.3), интенсивность по группе помещений как норматив, защищаемая площадь одним оросителем, давление у диктующего оросителя не менее 0,05 МПа, не более 800 оросителей в секции, сигнализация и дренаж узлов управления, кольцевая или тупиковая разводка и диаметры распределительных трубопроводов — нормативные требования, требование наличия и выводы из графики
- checklist.md «АУПТ дренчерная»: время работы не менее 60 мин, расстояние от дренчерной завесы до защищаемого проёма — нормативные требования и вывод из графики
- checklist.md «Пожарная насосная станция»: резервный насос — 100 % резерв основного, наличие жокей-насоса, автоматика пуска (от пожарной сигнализации, от падения давления, дистанционно), обвязка (обратные клапаны, задвижки, манометры, расходомеры), электроснабжение по I категории от двух независимых вводов, размещение в отдельном помещении, огнестойкость, доступ — нормативные требования и требование наличия (v1, условие 5); перечни способов пуска в разных местах обычно дополняют друг друга, а неполнота перечня — не противоречие
- checklist.md «Пожарный резервуар»: объём по расчёту, гарантированный забор воды при минимальном уровне, раздельные резервуары при объёме более 1000 м³, указатели уровня воды, переливная и сигнальная трубы — пересчёт, нормативный порог, оценка решения и требование наличия
- checklist.md «Кольцевые и тупиковые сети»: кольцевая сеть при числе ПК более 12, диаметры по гидравлическому расчёту, скорость не более 3 м/с в стояках и 5 м/с в магистралях, отключение участков не более 5 ПК, уклон не менее 0,001, сталь по ГОСТ 10704/10705 и ВГП по ГОСТ 3262 — нормативные требования, инженерный расчёт и нормоконтроль (W57)
- checklist.md «Спецификации, таблицы»: «марки труб — соответствие ГОСТ и требованиям огнестойкости» — нормоконтроль (W57); метражи и количество пожарных кранов и оросителей, снятые с планов, — выводы из графики чертежа
- project_params.md: «нормативные ссылки — проверить актуальность» — нормоконтроль (W57); поля vpv_required, sprinkler_required, drencher_required («требуется ли») — оценка необходимости решения по нормам; JSON-шаблон project_params и описание его полей — формат вывода legacy
- finding_categories.md: категории fire_hydrants, sprinkler, drencher, fire_pumps, reservoir, pipe_network, hydraulic, automation, documentation, normative_refs не переносятся — у v1 ровно две категории
- role.md: «находишь ошибки и несоответствия нормативной базе РФ», «рекомендации — строго с привязкой к конкретным пунктам нормативных документов» — противоречит v1 (без ссылок на нормы, без вердикта); гидравлические расчёты противопожарных систем — инженерный расчёт

Open questions for the expert reviewer:

- Формулировки «гарантированный напор уточнить по ТУ», «марку насосной установки уточнить при заказе», «длину рукава уточнить по месту» — заполнитель (так по v1) или ссылка на технические условия и принятое указание поставщику и монтажной организации?
- Подача насосов в пояснительной записке часто дана в л/с, а в спецификации — в м³/ч, напор — в метрах, а давление — в МПа; считать ли «10 л/с» и «36 м³/ч» одним значением (это уже перевод единиц, то есть счёт) или сравнивать только значения в одинаковых единицах?
- Напор и давление у пожарных кранов законно различаются по этажам и зонам (с диафрагмами и без); не даёт ли пункт о напоре у диктующего крана ложных находок, если зона или этаж в тексте не названы?
- Считать ли находкой расхождение расчётного расхода ВПВ с произведением числа струй на расход одной струи или итоговой строки гидравлического расчёта с суммой расходов ВПВ и АУПТ (сейчас пересчёт исключён)?
- Полон ли перечень мест сверки для комплекта ПТ, где ВПВ и АУПТ часто оформлены одним томом, и не путает ли модель системы с похожими параметрами (ВПВ жилой части и паркинга, спринклерные секции разных этажей)?

### EOM — Электроснабжение и электрооборудование (ЭОМ)

Package `src/auditmanager/analysis/text/profiles/eom/`; `analysis_profile_id` `ap_01M5AXG1KKCKB70088QWAR8WD4`, `prompt_bundle_id` `pb_01M5AXG1KKNVF7G99H0BB166TW`, status `draft`.

| Legacy source file | SHA-256 |
| --- | --- |
| `prompts/disciplines/EOM/role.md` | `949c503f0eca15b1fd99e29e3abcdaa801cbfd7481ed698e492f1cbcbaef53f0` |
| `prompts/disciplines/EOM/checklist.md` | `2835479eeb630d894349903ad601d3b6ce2cac1c05386f1a5601b58390d8664e` |
| `prompts/disciplines/EOM/drawing_types.md` | `4ccdc7c558465433e0f250114594fcb6b9b0a12dab0dc6f4a29fcf317a7574ed` |
| `prompts/disciplines/EOM/project_params.md` | `28506c8d3f9fc26addc6034f9529a5202229d49e0ec557f00c9832ca65a45c0b` |
| `prompts/disciplines/EOM/finding_categories.md` | `902fce3a4a4854dbb94bd86b042860d5ea2b0f8ad6d8ae8b85905498cf00475d` |

Condition 1 objects: зданиям, секциям, этажам, вводам, щитам, группам, линиям или помещениям. Condition 2 near-misses: установленная и расчётная мощность, номинальный ток аппарата и ток его уставки, сечение фазной жилы и сечение PE-проводника.
Extra norm families named in the exclusion sentence: ПУЭ.

Kept (reframed as same-document cross-checks):

- checklist.md «Однолинейные схемы»: соответствие кабелей на схеме спецификации; ТТ (номинал, класс точности); учёт электроэнергии — как сверка одних и тех же записей между схемой и спецификацией
- checklist.md «Схемы щитов»: совпадение групп со спецификацией; номиналы дифавтоматов и УЗО — как сверка значений одной группы
- checklist.md «Спецификации, таблицы»: объёмы (метражи, количество); соответствие позиций чертежей и таблиц
- checklist.md «Узлы ввода»: сечения вводных кабелей, способ прокладки — как сверка одного и того же ввода в разных местах
- project_params.md: категория надёжности, напряжение, расчётная мощность, cos φ, система заземления; «противоречия между разделами ПЗ»
- drawing_types.md: перечень мест документа (однолинейная схема, схема щита, план, кабельная трасса/журнал, узел ввода, спецификация, общие указания)
- role.md: предмет раздела (схемы электроснабжения, щиты, кабельные линии, учёт, огнестойкие кабели СПЗ) — только как перечень объектов

Excluded:

- checklist.md «Расчётные формулы для сверки»: пересчёт тока, выбор сечения по таблицам ПУЭ 1.3.4–1.3.8, проверка номинала и отключающей способности аппарата, потери напряжения не более 5 %, реалистичность cos φ — инженерный расчёт и нормативные пределы
- checklist.md: «номиналы автоматических выключателей — соответствие расчёту нагрузок», «сечения кабелей соответствуют нагрузкам и защитным аппаратам», «селективность защиты» — оценка правильности технического решения
- checklist.md: «наличие УЗО/УЗДП на нужных группах (розеточные 30 мА, ванные 10 мА)», «АВР для потребителей I категории и СПЗ» — нормативные требования ПУЭ/СП
- checklist.md: «наличие PE-шины», «наличие защиты от механических повреждений», «заземление, уравнивание потенциалов» — требование, чтобы указание было (v1, условие 5)
- checklist.md «Планы»: цвета кабелей по системам, трассы ОКЛ вне незащищённых зон, расположение оборудования — выводы из графики чертежа
- checklist.md: «марки кабелей по ГОСТ»; project_params.md: «нормативные ссылки — проверить актуальность», «соответствие ГОСТ 31996-2012» — нормоконтроль (W57)
- checklist.md: «все щиты с плана присутствуют в спецификации» без указанного количества — пропуск, а не два несовместимых значения
- checklist.md: «дубли групп (одинаковые обозначения)» — одно обозначение у разных объектов по v1 (условие 1) не противоречие; оставлена сверка параметров одного и того же обозначения
- finding_categories.md: категории calculation, phase_balance, fire_safety, normative_refs и остальные девять кодов не переносятся — у v1 ровно две категории
- role.md: «находишь несоответствия нормативной базе РФ», «рекомендации строго с привязкой к пунктам нормативных документов» — противоречит v1 (без ссылок на нормы, без вердикта)

Open questions for the expert reviewer:

- Формулировки «длины уточнить по месту», «уточнить при монтаже» — заполнитель (так по v1) или принятое указание монтажной организации?
- Считать ли находкой расхождение строки «Итого» таблицы нагрузок или спецификации с суммой строк (сейчас пересчёт исключён)?
- Щит или аппарат, названный на схеме, но отсутствующий в спецификации, — нужна ли такая находка (в v1 это не категория)?
- Полон ли перечень мест сверки для типового комплекта ЭОМ стадий П и Р, и не даёт ли какой-то пункт систематических ложных находок?

### SS — Слаботочные системы (СС)

Package `src/auditmanager/analysis/text/profiles/ss/`; `analysis_profile_id` `ap_01M5AXG1KN9C7BDD3CCHMFTMX3`, `prompt_bundle_id` `pb_01M5AXG1KNQRT6DYJWYC5X0C5J`, status `draft`.

| Legacy source file | SHA-256 |
| --- | --- |
| `prompts/disciplines/SS/role.md` | `bce9846d362a4994e82dd6fbc9c026c96de91c8eb27a4c654bb2b403cf48fc7f` |
| `prompts/disciplines/SS/checklist.md` | `4efe2296d18124aae441a05d01f8ea70ddace7ec4cd6608362796a0003b020f6` |
| `prompts/disciplines/SS/drawing_types.md` | `8a2e1c23105da4aca67eadf9e811e38508607c4b8e865b3844af0a1bbf6366e2` |
| `prompts/disciplines/SS/project_params.md` | `d36990b5b154eb3351939f5f1a6d4457db17c6da9caf475e7c84bbdc2ca03637` |
| `prompts/disciplines/SS/finding_categories.md` | `ff8193946f57ecfbc0e9c10f4be0f41f74c3decfe67257f16d9ebb398b0719c9` |

Condition 1 objects: зданиям, секциям, этажам, квартирам, помещениям, системам, шкафам, шлейфам, зонам оповещения или точкам доступа. Condition 2 near-misses: ёмкость прибора или контроллера и число фактически подключённых к нему устройств, время работы резервного источника питания в дежурном режиме и в режиме тревоги, количество абонентских розеток и количество портов СКС.

Kept (reframed as same-document cross-checks):

- checklist.md «Структурированная кабельная система (СКС)»: категория кабеля (Cat.5e / Cat.6 / Cat.6A); магистральные линии — тип и ёмкость; коммутационное оборудование — марка и количество; количество портов на квартиру или этаж — как сверка значений, прямо записанных в общих указаниях, на схемах, в кабельном журнале и в спецификации
- checklist.md «Видеонаблюдение (CCTV)»: количество и типы камер; кабельная инфраструктура (UTP, оптика, коаксиал) — как сверка количества, марки и типа кабеля, прямо указанных в тексте и в спецификации, а не подсчёт условных обозначений на плане
- checklist.md «СКУД»: типы считывателей, тип замков, количество контроллеров — как сверка одной и той же точки доступа и одного и того же прибора между таблицей, схемой и спецификацией; интеграция с домофоном и пожарной сигнализацией, разблокировка дверей при пожаре — как сверка условий формирования сигнала, записанных в разных местах; питание и ИБП контроллеров — как сверка ёмкости и времени работы одного источника
- checklist.md «Домофон / видеодомофон»: количество вызывных панелей, тип абонентских устройств, тип электрозамка, кабельная разводка — как сверка количества, марки и типа кабеля между текстом, схемами и спецификацией
- checklist.md «ОПС / АУПС»: тип системы (адресная / безадресная); марка ПКП; марка и исполнение кабелей шлейфов; интеграция с СОУЭ, СКУД, лифтами и вентиляцией — как сверка записанных условий формирования управляющих сигналов; резервное питание ПКП — как сверка указанных ёмкости АКБ и времени работы без проверки норматива
- checklist.md «СОУЭ»: тип СОУЭ — как сверка записанного типа между местами документа; зоны оповещения — как сверка границ одной и той же зоны; автоматический и ручной запуск — как сверка записанных условий запуска; кабели и резервное питание — как сверка марки одной линии и параметров одного источника
- checklist.md «Телевидение и радио»: способ приёма ТВ (коллективная антенна / кабельное ТВ / GPON); тип и количество усилителей; разводка по квартирам (коаксиал / оптика); количество ТВ-выводов на квартиру — как сверка записанных значений
- checklist.md «Диспетчеризация»: лифты, ИТП, пожарная автоматика, водомерный узел, АСКУЭ, каналы связи с диспетчерской — как сверка перечня выводимых сигналов и канала связи между пояснительной запиской, общими данными и структурной схемой
- project_params.md: категория СКС, количество камер, точек доступа и вызывных панелей, тип ОПС, тип СОУЭ, способ приёма ТВ, состав систем диспетчеризации; «противоречия между разделами проекта» — только между частями одного документа
- drawing_types.md: перечень мест документа (структурная и стояковая схемы, планы систем с подписями, схема серверной или слаботочного шкафа, спецификация, общие указания), дополненный кабельным журналом и таблицами адресов и подключений
- role.md: предмет раздела (СКС, видеонаблюдение, СКУД, домофон, ОПС / АУПС, СОУЭ, ТВ и радио, интернет и телефония, диспетчеризация, АСКУЭ) — только как перечень систем и объектов

Excluded:

- checklist.md «СКС»: «категория кабеля — соответствие ТЗ и нормативам», «длина горизонтальных линий ≤ 90 м (по ГОСТ Р 53246)» — сравнение с внешним ТЗ и нормоконтроль (W57)
- checklist.md «СКС»: «серверная / кроссовая: площадь, кондиционирование, электропитание, заземление», «маркировка кабелей и портов — наличие схемы маркировки» — требование, чтобы решение или указание было (v1, условие 5), и оценка достаточности
- checklist.md «СКС»: «кабельные трассы: совместная прокладка со слаботочными / силовыми» — вывод из графики трасс и нормативное требование
- checklist.md «Видеонаблюдение»: «зоны покрытия: входы, паркинг, дворовая территория, лифтовые холлы», «разрешение камер и углы обзора — достаточность для идентификации», «соответствие плану размещения» в части подсчёта камер по плану — оценка достаточности решения и вывод из графики чертежа
- checklist.md «Видеонаблюдение»: «глубина архива не менее 30 суток по СП 134» — нормативный предел (W57)
- checklist.md «Видеонаблюдение»: «питание камер: PoE / отдельное, наличие ИБП», «мониторы оператора — наличие поста охраны» — оценка технического решения и требование наличия
- checklist.md «СКУД»: «точки доступа: входные группы, паркинг, технические помещения», «кнопка экстренного открывания (Exit) — наличие на путях эвакуации» — полнота и нормативное требование
- checklist.md «СКУД»: «контроллеры доступа: ёмкость, резервирование» — оценка достаточности; ёмкость и число подключённых устройств — разные признаки (v1, условие 2)
- checklist.md «Домофон»: «расположение вызывных панелей» — вывод из графики; «совместимость абонентских устройств», «мощность и совместимость электрозамка с панелью», «количество абонентов — соответствие ёмкости» — оценка правильности решения и расчёт; «связь с постом консьержа / охраны» — требование наличия
- checklist.md «ОПС / АУПС»: «типы извещателей — соответствие помещениям», «размещение извещателей — нормативные расстояния (СП 484.1311500.2020, табл. А.1)», огнестойкость кабелей шлейфов и способ прокладки как требование — нормоконтроль (W57) и вывод из графики
- checklist.md «ОПС / АУПС»: «ПКП — ёмкость, расположение», «АКБ не менее 24 ч дежурный + 1 ч тревога», обязательность интеграции с СОУЭ, СКУД, лифтами и вентиляцией — расчёт ёмкости, нормативный предел, вывод из графики и требование наличия
- checklist.md «СОУЭ»: «тип СОУЭ — соответствие этажности и назначению здания», «разделение зон по пожарным отсекам / секциям», «приоритет сигналов», «прокладка в огнестойких коробах» — нормативные требования (W57)
- checklist.md «СОУЭ»: «речевые оповещатели: мощность, размещение, уровень звукового давления», «световые оповещатели «Выход» на путях эвакуации» — акустический расчёт, вывод из графики и требование наличия
- checklist.md «Телевидение и радио»: «расположение усилителей», «головная станция / оптический узел — расположение» — вывод из графики; «радиофикация — при наличии требования» — нормативное требование
- checklist.md «Диспетчеризация»: аварийные сигналы лифтов, датчики ИТП, импульсные счётчики, вывод сигналов на пожарную часть как обязательный состав; «резервирование каналов связи» — требование наличия и оценка достаточности
- project_params.md: «нормативные ссылки → проверить актуальность по нормативной базе дисциплины» — нормоконтроль (W57)
- project_params.md: JSON-шаблон project_params и поля server_room_count, total_apartments — формат вывода legacy, у v1 свой контракт ответа
- finding_categories.md: категории scs, cctv, access_control, intercom, fire_alarm, pa_system, tv_radio, dispatch, cable_routing, documentation, normative_refs не переносятся — у v1 ровно две категории
- role.md: «эксперт-проектировщик», «находишь ошибки и несоответствия нормативной базе РФ», «рекомендации строго с привязкой к конкретным пунктам нормативных документов» — противоречит v1 (инструмент без ссылок на нормы и без вердикта)

Open questions for the expert reviewer:

- Формулировки «тип оборудования уточнить по ТУ оператора связи», «по проекту оператора», «по согласованию с управляющей компанией» — заполнитель (так по v1, если значения в документе нет) или принятая ссылка на внешний документ?
- Пожарная сигнализация и СОУЭ нередко выпускаются отдельным томом (АПС, СОУЭ) вне раздела СС: оставить их в этом профиле или вынести в отдельный?
- Если перечень сигналов, выводимых на диспетчерский пункт, или состав оборудования точки доступа в одном месте короче, чем в другом, — это противоречие или неполнота, о которой по условию 5 не сообщают?
- Количество портов СКС и ТВ-выводов «на квартиру» часто различается для разных типов квартир: достаточно ли условия 1, или этот пункт будет давать систематические ложные находки?
- Строка «Итого» спецификации или кабельного журнала против суммы строк, ёмкость ППКП против числа адресных устройств — сейчас пересчёт и такое сравнение исключены; нужна ли какая-либо из этих находок?

### ITP — Индивидуальный тепловой пункт (ИТП)

Package `src/auditmanager/analysis/text/profiles/itp/`; `analysis_profile_id` `ap_01M5AXG1KQSW41PC130SWCS8CD`, `prompt_bundle_id` `pb_01M5AXG1KQR5A6ZPWDX4CC3CTS`, status `draft`.

| Legacy source file | SHA-256 |
| --- | --- |
| `prompts/disciplines/ITP/role.md` | `18cb5f3e4f321b3f9eb526e0702d3f7bc49e972c4555bd0ab02b0f86d1bc2ca1` |
| `prompts/disciplines/ITP/checklist.md` | `22aa3697b2557feb65e2e25f1478e81ec2d48ba815818f62eef40a8059f0dbb1` |
| `prompts/disciplines/ITP/drawing_types.md` | `5ba8823dd2d2a8291dd9c17dc4a9d9a480af8dc3ade9b8a48efa652d0858b1ee` |
| `prompts/disciplines/ITP/project_params.md` | `0fbb238e3fe676e744610e4af63caed85014e30a4b3eb9b0652bc1f4fba19796` |
| `prompts/disciplines/ITP/finding_categories.md` | `113fe584e10e12b5c28ec4bb4342b58bd8277e1724cbfb8a712ac53fbdbe7e13` |

Condition 1 objects: зданиям, частям здания, контурам, ступеням подогрева ГВС, теплообменникам, насосам, клапанам, узлам учёта или участкам трубопроводов. Condition 2 near-misses: максимальная и среднечасовая тепловая нагрузка на ГВС, расчётная тепловая нагрузка контура и номинальная мощность теплообменника, условная пропускная способность клапана Kvs и расчётная пропускная способность Kv.
Extra norm families named in the exclusion sentence: Правилам коммерческого учёта тепловой энергии.

Kept (reframed as same-document cross-checks):

- checklist.md «Принципиальная схема ИТП»: тип присоединения к тепловой сети, схема приготовления ГВС — как сверка записанного типа схемы между общими данными, пояснительной запиской и принципиальной схемой
- checklist.md «Теплообменники»: температурный график первичного и вторичного контуров, потери давления по первичной и вторичной стороне, количество пластин или площадь теплообмена — как сверка значений одного и того же теплообменника и контура между схемой, опросным листом и спецификацией
- checklist.md «Насосы»: тип насоса (с частотным регулированием или без), электрическая мощность — как сверка значений одного и того же насоса на принципиальной схеме, на схеме электроснабжения и в спецификации; расход и напор — только как сверка записей одного и того же насоса, а не сравнение с расчётом
- checklist.md «Регулирующие клапаны»: тип клапана (двух- / трёхходовой) и соответствие схеме, Kvs, тип привода и время полного хода — как сверка значений одного и того же клапана на схемах и в спецификации
- checklist.md «КИПиА и автоматика»: алгоритмы регулирования, аварийные защиты, датчики температуры и давления — как сверка уставок и условий срабатывания, записанных в разных местах документа
- checklist.md «Узел учёта тепловой энергии (УУТЭ)»: тип теплосчётчика и класс точности; расходомеры (тип, диаметр, диапазон измерений); термопреобразователи и датчики давления (класс точности) — как сверка одного и того же узла учёта между пояснительной запиской, схемой и спецификацией
- checklist.md «Трубопроводы»: диаметры, материал труб, теплоизоляция — как сверка одного и того же участка между схемами, общими указаниями и спецификацией
- checklist.md «Запорная арматура»: тип арматуры, номинальное давление PN — как сверка одной и той же позиции между схемой и спецификацией
- checklist.md «Спецификации и ведомости»: соответствие марок оборудования между схемой, планом и спецификацией; технические характеристики (мощность, расход, напор, Kvs); количество оборудования (основное + резервное) — как прямая сверка записанных значений
- project_params.md: тепловые нагрузки по контурам, температурные графики, давление теплоносителя, тип присоединения, схема ГВС, характеристики теплообменников и насосов, параметры УУТЭ, параметры технических условий в том виде, в каком они приведены в самом документе, — как сверка между местами одного документа
- drawing_types.md: перечень мест документа (принципиальная схема, аксонометрическая схема, функциональная схема автоматизации, схема узла учёта, схема электроснабжения ИТП, спецификация, общие указания), дополненный опросными листами и таблицами нагрузок и уставок
- role.md: предмет раздела (теплообменники, насосные группы, регулирующие клапаны, КИПиА, УУТЭ, трубопроводы и арматура) — только как перечень объектов

Excluded:

- checklist.md «Принципиальная схема ИТП»: «наличие всех контуров (отопление, ГВС, вентиляция, тёплые полы)», «наличие обратных клапанов на подключениях контуров», «наличие грязевиков и фильтров», «предохранительные клапаны на контурах с закрытыми системами» — требование, чтобы элемент или указание было (v1, условие 5)
- checklist.md «Принципиальная схема ИТП»: «соответствие схемы техническим условиям теплоснабжающей организации» — сравнение с внешним документом, которого нет в тексте; сверка параметров ТУ, приведённых в самом документе, оставлена
- checklist.md «Теплообменники»: «соответствие мощности расчётным тепловым нагрузкам», «запас мощности 10–15 % для отопления, до 25 % для ГВС», «резервирование для ГВС», «материал пластин и уплотнений (коррозионная стойкость)» — инженерный расчёт и оценка правильности технического решения
- checklist.md «Насосы»: «соответствие расхода и напора расчётным значениям», «рабочая точка на характеристике насоса» — гидравлический расчёт и вывод из графика характеристики
- checklist.md «Насосы»: «резервирование (100 % резерв для циркуляционных насосов отопления)», «наличие подпиточного насоса с обратным клапаном», «наличие обратных клапанов и запорной арматуры на обвязке», «виброизолирующие вставки», «категория электроприёмника» — нормативное требование и требование наличия
- checklist.md «Регулирующие клапаны»: «Kvs — соответствие расчётному расходу», «авторитет клапана ≥ 0,5», «перепад давления на клапане», «наличие обводной линии (байпаса) при необходимости» — гидравлический расчёт и оценка технического решения
- checklist.md «КИПиА и автоматика»: наличие контроллера погодозависимого регулирования, датчиков, частотных преобразователей и функциональной схемы автоматизации — требование наличия
- checklist.md «УУТЭ»: «прямые участки до и после расходомеров (по паспорту прибора)», длина погружной части и гильзы термопреобразователей — подбор по внешнему паспорту, вывод из графики и требование наличия; «соответствие Правилам коммерческого учёта (Постановление № 1034)» — нормоконтроль (W57); «наличие пломбируемых участков» — требование наличия
- checklist.md «Трубопроводы»: «диаметры — соответствие расчётным скоростям (≤ 3 м/с)», «материал в зависимости от параметров», толщина теплоизоляции по нормам — расчёт и оценка решения; «компенсация температурных удлинений», «уклоны ≥ 0,002», «опоры и подвесы (шаг, тип)», «дренажные штуцеры и воздушники» — расчёт, нормативный предел, вывод из графики и требование наличия
- checklist.md «Запорная арматура»: «наличие запорной арматуры на вводе, отводах контуров, обвязке оборудования», «наличие спускных и дренажных кранов», «PN — соответствие рабочим параметрам» — требование наличия и оценка технического решения
- checklist.md «Дренаж и водоотведение»: приямок, дренажный насос, уклон пола ≥ 0,005, гидроизоляция пола, порог на входе — требование наличия, нормативный предел и вывод из графики
- checklist.md «Электроснабжение ИТП»: «категория электроснабжения не ниже II», «щит управления: комплектация, защитные аппараты», «заземление и молниезащита», «освещение рабочее и аварийное», «сечения кабелей питания насосов и приводов» — нормативное требование, требование наличия и электротехнический расчёт
- checklist.md «Спецификации и ведомости»: «комплектность спецификации (все позиции схемы учтены)» — отсутствие позиции не два несовместимых значения (v1, условие 5)
- project_params.md: «нормативные ссылки (СП 124.13330, СП 60.13330, ГОСТ 34011, Постановление № 1034)» — нормоконтроль (W57); JSON-шаблон project_params — формат вывода legacy, у v1 свой контракт ответа
- drawing_types.md: «гидравлическая схема» не названа местом сверки расхода и напора насосов — там расчётные (требуемые) значения, а не характеристики выбранного насоса (v1, условие 2); «план помещения ИТП» — компоновка и проходы читаются из графики
- role.md: «находишь несоответствия нормативной базе РФ», «рекомендации строго с привязкой к конкретным пунктам нормативных документов» — противоречит v1; «подбор по мощности, запас», «гидравлический расчёт, увязка контуров», «компоновка оборудования, монтажные зазоры, доступ для обслуживания» — расчёт, оценка решения и вывод из графики
- finding_categories.md: категории heat_exchangers, pumps, valves, automation, metering, piping, electrical, layout, documentation, normative_refs не переносятся — у v1 ровно две категории

Open questions for the expert reviewer:

- Тепловые нагрузки в одних местах записаны в Гкал/ч, в других — в кВт или МВт: считать ли значения, совпадающие после перевода единиц, согласованными, и не даст ли округление при переводе ложных находок?
- Температурный график, записанный в одном месте как «150/70 со срезкой на 130 °C», а в другом как «130/70», — противоречие или один и тот же график в разной записи?
- Параметры насоса или теплообменника в спецификации (выбранное изделие) и в опросном листе или таблице расчёта (требуемые значения) сейчас считаются разными признаками (условие 2); нужна ли когда-нибудь находка о таком расхождении?
- Формулировки «подбор оборудования уточнить после получения ТУ», «марку теплосчётчика согласовать с теплоснабжающей организацией», «уставки уточнить при пусконаладке» — заполнитель (так по v1) или принятое указание?
- Строка «Итого» тепловых нагрузок против суммы нагрузок по контурам — сейчас пересчёт исключён; нужна ли такая находка?

### GP — Генеральный план (ГП)

Package `src/auditmanager/analysis/text/profiles/gp/`; `analysis_profile_id` `ap_01M5AXG1KSSZM53N2CBV6XX83E`, `prompt_bundle_id` `pb_01M5AXG1KSRDEWMP2WT3KNGWJ2`, status `draft`.

| Legacy source file | SHA-256 |
| --- | --- |
| `prompts/disciplines/GP/role.md` | `3a5fdbafcca2b0ada0ad50d53145599b45c771bd3bfa95d1c157469d1b44bd0a` |
| `prompts/disciplines/GP/checklist.md` | `c6d42f648e73bde0e434efe54e6c544d3eaf181c594b27d76eb6041b7e1fc247` |
| `prompts/disciplines/GP/drawing_types.md` | `e382963ebbe0ce8b14e27e51fa9b914b8a6aa07ed643f1404f82c88ec08bf799` |
| `prompts/disciplines/GP/project_params.md` | `fe02d212adddc7dba97962328862428051951b1e2e32fc2d0b4ecf6d3e6caa93` |
| `prompts/disciplines/GP/finding_categories.md` | `0568f133ba2cc85e85078f6f2c949b1839dc0a015b674ce26a0d988704d2107d` |

Condition 1 objects: земельным участкам, этапам или очередям строительства, зданиям, проездам, площадкам, парковкам, участкам инженерных сетей или зонам благоустройства. Condition 2 near-misses: площадь земельного участка и площадь в границах благоустройства, площадь озеленения и площадь газонов, требуемое по расчёту и фактически размещённое количество машино-мест.
Extra norm families named in the exclusion sentence: СанПиН, нормативам градостроительного проектирования.

Kept (reframed as same-document cross-checks):

- checklist.md «Расчётные формулы и нормативы для сверки»: баланс территории, площадь озеленения — только как сверка одних и тех же записанных площадей и процентов между таблицей баланса, технико-экономическими показателями и пояснительной запиской, без проверки суммы 100 % и нормативных долей
- checklist.md «Проезды и дороги»: ширина пожарного проезда, расстояние от края проезда до стены здания, проезд вдоль фасада с двух продольных сторон, ширина тротуаров, продольный уклон проездов — как сверка значений одного и того же проезда, записанных в разных местах, без сравнения с нормативами
- checklist.md «Парковки»: общее количество машино-мест и мест для МГН — как сверка записанных количеств одной и той же парковки между пояснительной запиской, таблицей машино-мест, технико-экономическими показателями и подписями плана
- checklist.md «Благоустройство — детские площадки»: покрытие детских площадок — как сверка типа и конструкции покрытия одной и той же площадки между ведомостью покрытий и пояснительной запиской
- checklist.md «Благоустройство — прочие площадки»: площадки для отдыха, хозяйственные, контейнерные, для выгула собак, твёрдое покрытие контейнерных площадок — только как перечень объектов для сверки номера, назначения, площади, покрытия и оборудования одной и той же площадки
- checklist.md «Озеленение»: сохранение существующих деревьев — как сверка числа сохраняемых и вырубаемых деревьев между перечётной ведомостью и пояснительной запиской; площадь озеленения — как сверка записанной площади
- checklist.md «Вертикальная планировка»: уклоны дорожек, тротуаров и проездов — как сверка записанных уклонов и отметок одного и того же элемента на профиле, в подписях плана и в пояснительной записке
- checklist.md «Доступность для МГН»: продольный и поперечный уклон и ширина пешеходных путей — как сверка записанных значений одного и того же пути без нормативных пределов
- project_params.md: площадь участка, баланс территории, площадь и процент застройки, площадь и процент озеленения, площадь твёрдых покрытий, количество машино-мест (в том числе для МГН), количество и типы площадок, ширина пожарных проездов и число сторон здания с проездом, перечень наружных сетей, тип водоотведения поверхностных вод — как сверка между местами одного документа
- drawing_types.md: перечень мест документа (разбивочный план, план благоустройства, план организации рельефа, сводный план сетей, продольные и поперечные профили, план озеленения, план водоотведения, ведомости и спецификации, узлы покрытий, общие данные)
- role.md: предмет раздела (проезды, парковки, площадки, озеленение, малые архитектурные формы, наружные сети, вертикальная планировка, водоотведение) — только как перечень объектов

Excluded:

- checklist.md «Расчётные формулы и нормативы для сверки»: «застройка + озеленение + покрытия + прочее = 100 %» — арифметический пересчёт; «озеленение не менее 25 % (СП 42.13330.2016, п. 7.5)», «обеспеченность парковочными местами по региональным нормативам», «детские площадки 0,7 м² на жителя», «спортивные площадки 0,2 м² на жителя» — нормативный расчёт (W57)
- checklist.md «Проезды и дороги»: «ширина пожарного проезда не менее 3,5 м», «5–8 м / 8–10 м от края проезда до стены», «по всей длине фасада с двух продольных сторон», «разворотные площадки 15×15 м», «радиусы поворотов ≥ 10 м», «тротуары ≥ 1,5 / 1,0 м», «высота проезда под аркой ≥ 4,25 м», «продольный уклон ≤ 10 %» — нормативные пределы (W57); сами записанные значения сверяются между местами документа
- checklist.md «Парковки»: размеры машино-мест 2,5×5,3 и 3,5×5,3 м, ширина проездов на парковке ≥ 6,0 м, места для МГН не менее 10 %, расстояния от парковок 10 / 15 / 25 м до жилых домов по СанПиН 2.1.3684-21 — нормативные пределы, расчёт доли и вывод расстояний из графики
- checklist.md «Благоустройство — детские площадки»: расстояния 12 и 25 м от окон, «ударопоглощающее покрытие (ГОСТ Р 52169-2012)», «ограждение обязательно вблизи проездов», «инсоляция не менее 3 часов на 50 % площади», «зоны безопасности оборудования» — нормативные требования, расчёт инсоляции, требование наличия и вывод из графики
- checklist.md «Благоустройство — прочие площадки»: расстояния от окон 10 / 20 / 40 м, «контейнерные площадки не более 100 м от входа», «ограждение с трёх сторон высотой ≥ 1,5 м» — нормативные пределы, вывод расстояний из графики и требование наличия
- checklist.md «Озеленение»: «нормативная площадь озеленения ≥ 25 %», расстояния от деревьев и кустарников до стен зданий, трубопроводов, бортового камня и опор освещения, «обязательная дендрологическая экспертиза» — нормативные пределы, вывод из графики и требование наличия
- checklist.md «Инженерные сети (трассировка)»: расстояния между параллельными сетями и до зданий (СП 42.13330.2016, табл. 12.5), глубина заложения водопровода и канализации, охранные зоны, пересечения под углом 90° — нормативные пределы, расчёт и вывод из графики трасс
- checklist.md «Вертикальная планировка»: уклон отмостки ≥ 1 %, диапазоны уклонов территории, площадок, дорожек и поперечного уклона проездов, «обеспечить понижение рельефа от здания во все стороны», высота цоколя ≥ 0,15 м — нормативные пределы и вывод направления стока из графики
- checklist.md «Доступность для МГН»: продольный уклон ≤ 5 %, поперечный ≤ 2 %, ширина ≥ 1,8 / 1,2 м, тактильные указатели, пандусы у перепадов > 14 мм, бордюрные пандусы, высота бортового камня ≤ 40 мм, площадки отдыха через каждые 300 м — нормативные требования (W57) и требование наличия
- project_params.md: «нормативные ссылки (СП 42.13330, СП 476.1325800, СП 82.13330, СП 4.13130, СП 59.13330 и др.)» — нормоконтроль (W57); «наличие разворотных площадок» — требование наличия
- project_params.md: «высота здания — для определения требований к пожарным проездам», «расчётное количество жителей» — исходные данные нормативных расчётов, которые исключены; JSON-шаблон project_params — формат вывода legacy, у v1 свой контракт ответа
- role.md: «находишь несоответствия нормативной базе РФ», «рекомендации строго с привязкой к конкретным пунктам нормативных документов» — противоречит v1; «функциональное зонирование», «нормативная площадь», «расстояния от зданий и сетей», «доступность для МГН» как экспертиза — нормоконтроль и оценка решения
- finding_categories.md: категории roads_access, parking, playgrounds, landscaping, utilities, grading, drainage, accessibility, fire_access, documentation, normative_refs не переносятся — у v1 ровно две категории

Open questions for the expert reviewer:

- Если сумма позиций баланса территории не равна 100 % или площади участка, считать ли это находкой (сейчас арифметический пересчёт исключён)?
- Площадь участка по ГПЗУ, площадь в границах благоустройства (включая благоустройство за границей участка) и площадь в границах проектирования часто приводятся рядом: не даёт ли пункт о балансе территории систематических ложных находок?
- Технико-экономические показатели часто приводят значения и по этапам (очередям) строительства, и на весь комплекс: достаточно ли условия 1, чтобы такие значения не сопоставлялись?
- Отметки и уклоны в текстовом слое планов и профилей оторваны от того, к чему относятся: надёжна ли сверка «в подписях плана организации рельефа», или её лучше ограничить пояснительной запиской, профилями и ведомостями?
- Формулировки «уточнить по результатам инженерных изысканий», «по согласованию с владельцами сетей», «ассортимент растений уточнить на стадии Р», «отметки уточнить по месту» — заполнитель (так по v1) или принятое указание?

## Checks

Run from the worktree with
`PY=/root/projects/PDF-Analysis/.local/worktrees/w55b-main-candidate/.venv/bin/python`.
No container, no provider call, no full gate (`R-135`).

- `$PY -m pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider
  tests/unit/analysis/text_profiles tests/contract/program`: **36 passed**. That is 8
  new tests and the 28 existing program governance tests.
- The same unit suite with `AUDITMANAGER_LEGACY_PROMPTS_REPO=/nonexistent`:
  **7 passed, 1 skipped**. The skip is explicit: "legacy repository /nonexistent is
  not on this host; hash-at-commit check skipped". The hashes are still checked
  against the in-repository candidate metadata.
- `git diff --cached --check` over the staged change: clean (exit 0).
- One extra guard, because the new files are tracked text under `src/` and `docs/`:
  `tests/contract/api_v1/test_surface_counts_in_prose.py` together with
  `tests/contract/domain_p02/test_project_section_catalog.py` gave **38 passed**.
- **Mutation 1 (duplicate code).** In `km/profile.json`,
  `sed -i 's/"section_code": "KM"/"section_code": "KJ"/'` gave **4 failed, 4
  passed**. The first failure reads "duplicate section_code across packages: ['AI',
  'EOM', 'GP', 'ITP', 'KJ', 'KJ', 'OV', …]". The file was restored from a copy and
  its SHA-256 re-checked (`d0b73794…`).
- **Mutation 2 (output contract).** In `gp/system_prompt.md`, the line `- category —
  строго одно из двух значений выше.` was changed to `… выше или normative_refs.`.
  This gave **1 failed, 7 passed**: the v1 output-contract tail no longer matches.
  The file was restored and its SHA-256 re-checked (`b7a3ea14…`).
- Every rendered prompt was diffed against v1's `SYSTEM_PROMPT`. Only the six
  anchored places differ.

The unit test reads the packages with `json` and `pathlib`, and imports only v1's
`prompt` module and `auditmanager.shared.identity`. It does not import a registry.
It checks:

- **Package set:** exactly the 13 expected codes, with no duplicate. Codes come from
  the 15-code S-3 catalogue, with no AR or PB package. The directory name equals the
  code in lower case.
- **Manifest:** exactly the `text-profile/1` keys; `profile_version` `1.0.0`;
  `status` `draft`; the S-3 `title_ru`; one legacy commit across all packages.
- **Identities:** `ap_`/`pb_` identities parse and are unique; none equals any
  identity literal elsewhere in `src/auditmanager`.
- **Hashes:** they match the catalogued candidate metadata, and the blob at the
  recorded commit (skipped if the legacy repository is absent).
- **Prompts:** v1's question, its two-category block, its five-condition skeleton
  and its output-contract tail appear verbatim. Every schema field name appears.
  No other snake_case token appears, so no legacy category can leak in. There are no
  braces and no code fences. The file ends with exactly one newline.

## Contracts, risks and limitations

- **Contracts.** No contract, migration, registry, run-start code or served
  behaviour changes. The new data format is the seal's `text-profile/1`, consumed
  as specified.
- **Trailing newline.** `system_prompt.md` ends with one trailing newline; v1's
  constant has none. Whether the registry strips that newline before hashing is the
  seal's decision. Either way it is deterministic, but it changes
  `content_sha256`.
- **AR data package.** The unit test asserts that there is no `profiles/ar/` or
  `profiles/pb/` package. If the seal adds an AR *data* package, the merge will
  redden this test. That would conflict with "AR from the existing v1 constants"
  and should be resolved at integration, not by loosening the test silently.
- **Draft quality.** All prompts are drafts derived from legacy checklists by
  reframing. They have no field evaluation, so false-positive behaviour on real
  documents is unknown. The riskiest bullets are named in each section's questions.
- **Legacy repository location.** The legacy repository is at a host path. On a
  host without it, the hash-at-commit sub-check skips explicitly, and the metadata
  cross-check still runs.

## Integration

1. Merge `W59-SECTION-SEAL-01` first, then this lane.
2. Run the seal's registry test over the merged tree. It should find these 13
   packages and register AR from v1.
3. Re-run `tests/unit/analysis/text_profiles`.
4. Register the expert-review debt row for all 13 draft profiles.
5. **Rollback:** delete a section's package directory. That section then returns to
   `section_profile_unavailable`.

## Changed files and hotspots

Added only:

- `src/auditmanager/analysis/text/profiles/{ai,ps,pos,tx,kj,km,ov,vk,pt,eom,ss,itp,gp}/profile.json`;
- the matching `system_prompt.md` in each of those 13 directories;
- `tests/unit/analysis/text_profiles/test_text_profile_packages.py`;
- this report.

Untouched (see `git diff --name-only` at hand-back):

- `contracts/**` and migrations;
- `profile.py`, `profile_registry.py` and `profiles/ar/**`;
- the composition root;
- dependency files;
- `CURRENT_STATE.md`;
- every ref and tag.
