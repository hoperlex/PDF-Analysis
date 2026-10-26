# SECTION-WIDEN-G2-01 — KM OV VK PT: the total-against-its-rows checks added to four prompts, every topic decided

Task: `docs/program/tasks/SECTION-WIDEN-G2-01.md`. Branch `agent/section-widen-g2-01`, base `6075df88` (`integration/ar-close-1026`). Plan item `PROD-14`; owner rulings `R-146an`, `R-146ag`; accepted risks `A-5`, `A-7`; brief `docs/program/dispatch/PRODUCTION-WAVE-PW4.md` section 6. Format follows `SECTION-WIDEN-G1-01.md`, `SECTION-PT-FULL-01.md` and `SECTION-PROMPT-TOKEN-GUARD-01.md`.

## Result

The gap report (`ROADMAP-GAP-2026-10-27.md` section 2.3) marks five groups of topics in these four sections as «reinstatable now»: a mass total against the marks (КМ), a system flow against its rooms and a heat-load total against its rows (ОВ), the building's total flow against the systems (ВК), and for ПТ the same flow in two units, the jets times single-jet flow, and the ВПВ + АУПТ total. This lane decided each (17 rows below, because some topics split in two and rule 5 adds one notation row): **W 8, K 2, N 1, X 6**. By section: КМ W 1, K 1, X 2; ОВ W 3, K 1, X 2; ВК W 1, X 1; ПТ W 3, N 1, X 1.

- **Widened (W), one exception paragraph per prompt.** After the exclusion paragraph each of the four prompts now carries «Единственное исключение из запрета на расчёты», which lets the model add the rows of a table whose total the text itself writes (КМ, ОВ, ВК) or make the three ПТ comparisons, and report `internal_contradiction` when the difference exceeds the tolerance the paragraph states in words. A hint bullet in the «where to look» block points to the paragraph. The five conditions, the two categories and the output contract are untouched; the evidence is the total and every row.
- **Conservative where the record names an overlap or a basis.** КМ compares a mass total only when the text names the basis of the masses (with or without weld metal and the like) and the same basis stands for the total and for every row. ОВ compares a system flow with its rooms only when the text itself calls it their sum. ВК adds the daily consumption only, from parts the text itself names as parts. ПТ multiplies jets by single-jet flow only when all three figures are written for one system and the text does not say the design flow came from another method, and compares the ВПВ + АУПТ total only when the text calls it the sum.
- **Refused (X) or kept (K).** Hourly and secondly flows of a building are not summed (VK-2). The mass of one element times its count is named as refused (KM-3). `С345` against `09Г2С` stays excluded (KM-4, rule 5). Supply against exhaust air and the building total of supply air are not compared (OV-5, OV-6). No other conversion of units is allowed (PT-5). **N:** a head in metres and a pressure in МПа are not compared (PT-2).
- `profile_version` is `1.2.0` for all four, `status` stays `reviewed`; the four routing recordings are rebuilt, the four expectations lines moved, one allowlist entry appended (`PT`, `3,6`, the factor of 1 л/с = 3,6 м³/ч). The response schema, `prompt.py`, `response.py`, `stage.py`, every contract and every other section are untouched. No omission topic («named in one place, absent from another») was decided W: the group has none, and no added sentence speaks of a missing item.

**`reviewed` carries no human review** (`R-146ag`, `A-7`). Nobody, neither an expert nor the owner, checked any sentence below, and nothing was measured on real text or with a model. The new sentences are the lane's reading of the record, the gap report and the brief's rules.

## Premise and deviations from the brief

Premise: **match, with the differences below** (task file P-01 to P-10). The packages, the pinned legacy sources, the gap report's rows and the record's questions are as the brief describes.

| # | Difference | What the lane did |
| --- | --- | --- |
| D1 | The brief asks for a positive and a negative recording per section through `build_fixtures.py`. `test_section_recordings.py` pins exactly one file per section directory (line 97) and 14 planned entries (line 156), and neither it nor the builder is in the lane's allowed paths (P-06). | The lane rebuilt the four existing recordings and kept the positive and negative specimens in this report, replayed through the real stage (section «Specimens»), on the coordinator's instruction after `SECTION-WIDEN-G1-01`. It had first built a sibling directory with its own builder and a 46-test file (commit `b91e2022`) and removed both from the tip in `0690d6d5`; an integrator lane that files the specimens can restore them with `git checkout b91e2022 -- fixtures/recorded/sections_widen_g2 tests/integration/sections/test_section_widen_g2_recordings.py` (the builder rebuilds them after any prompt change). |
| D2 | The allowlist wants `disclosed_by` to match `SECTION-[A-Z]+-FULL-01.md`, which refuses this report (P-07). | The one line of `test_prompt_token_guard.py` is changed to the integration branch's own line (`fa7f2ae6`): `SECTION-(?:[A-Z]+-FULL\|WIDEN-G[0-9]+)-01`. No other edit to that test. |
| D3 | Rule 4 of the brief writes the unit factor as «1 м³/ч = 3.6 · 1 л/с ⇒ 1 л/с = 3.6 м³/ч». The first half is inverted (1 м³/ч is 0,2778 л/с, P-09). | The prompt uses only the correct form, «1 л/с = 3,6 м³/ч». |
| D4 | Rule 1 says the difference must exceed «the rounding of the less precise figure». For a sum of several rows that is not the exact bound. | The tolerance is the sum of the half-units of the last written digit of all compared figures (with the multiplier or the conversion for a product or a unit change). That is never smaller than the brief's single rounding, so it flags less; it is the exact condition under which no choice of unrounded values makes the written figures consistent. |
| D5 | The brief says «КМ mass total only when the text states its basis». | Read literally: the prompt requires the table or its note to name the basis and the basis to be the same for the total and the rows. Most real specifications name none, so the КМ check will be quiet on them; that is the conservative end of the brief and an expert may loosen it (assumption 1). |
| D6 | The gap report lists «metres and MPa» under ПТ and «the building's total flow against the sum over systems» under ВК as reinstatable. | Metres against МПа is decided N: the conversion needs a water density and is not one of the definitional factors of rule 4. The ВК check is restricted to the daily consumption and the hourly and secondly flows are X (assumption 4). |

## Decisions

Vocabulary: **W** widen (the brief's rule), **K** keep the 1.1.0 behaviour, **N** narrow, **X** exclude. «Sentence» is the exact text added to the prompt, quoted from the fragment table below (id in brackets); a K or X row without a sentence says why none is needed. Source columns: GAP is `ROADMAP-GAP-2026-10-27.md` section 2.3 («Reinstatable now»), REC is the topic's question in `W59-SECTION-PROFILES-01.md`, SRC the pinned legacy file.

| # | Section, topic | D | Reason and source | Exact sentence |
| --- | --- | --- | --- | --- |
| KM-1 | КМ: «Итого» of the mass column of the metalwork specification against the sum of the masses of its rows | **W** | GAP: «a total mass against the sum of marks (q3), conditional on a stated basis». REC: «Считать ли находкой расхождение общей массы … или строки «Итого» спецификации с суммой масс по маркам … и как отличать массу по спецификации от массы с учётом наплавленного металла?». SRC: masses of marks and «Суммарный расход стали» (`checklist.md` lines 72, 75). Rule 3: the text must state the basis. | [KM-SCOPE] «Для КМ это строка «Итого» («Всего», «Сумма») столбца масс в спецификации металлопроката или в ведомости элементов и сумма масс строк этого же столбца.» [KM-BASIS] «у самой таблицы или в её примечании текст называет основу массы: включены ли в неё наплавленный металл, метизы, огнезащита, запас; основа одна и та же у итога и у всех строк, а между строками и итогом нет подытогов и строк-добавок». Also KM-HINT, W-HEAD, W-VISIBLE, W-NONUM, W-TOL, KM-CLOSE. |
| KM-2 | КМ: the total mass of the general data against the итог of the specification | **K** | Two written totals: bullet 5 of 1.1.0 already compares them and condition 2 keeps a different basis apart. Not a total against its rows. | none |
| KM-3 | КМ: mass of one element times its count against the mass of the mark | **X** | Not marked reinstatable by GAP; a second recomputation the record does not ask for. | [KM-CLOSE] «Других вычислений (например, массу одного элемента, умноженную на количество) не выполняй.» |
| KM-4 | КМ: `С345` and `09Г2С` as one value | **X** | Rule 5. No pinned file states the equivalence (`checklist.md` line 10 names С345 and 09Г2С as different grades); GAP puts it under «norms or experts». Unchanged: two different grades named for one element are two values, as in 1.1.0 (question 1, K). | none |
| OV-1 | ОВ: «Итого по системе» of the air-exchange table against the sum of the room flows of that system (supply with supply, exhaust with exhaust) | **W** | GAP: «a system's flow against the sum of its room flows». REC: «Считать ли находкой расхождение расхода системы с суммой расходов по помещениям в таблице воздухообмена …». SRC: «Расходы приточного/вытяжного воздуха по помещениям» (`project_params.md` line 5). | [OV-SCOPE] «Для ОВ это строка «Итого» («Всего») таблицы воздухообмена по системе и сумма расходов помещений этой системы того же вида (приток с притоком, вытяжка с вытяжкой) …». Also OV-HINT, W-HEAD, W-VISIBLE, W-NONUM, OV-PART, W-TOL, W-CLOSE. |
| OV-2 | ОВ: the flow of a system in the table of system characteristics or the specification against the sum of its rooms, when the text calls it that sum | **W** | Rule 3: the basis is stated by the text. The same sentence keeps OV-3. | [OV-SYSFLOW] «Расход системы из таблицы характеристик систем или из спецификации с суммой расходов помещений сопоставляй, только если текст прямо называет его суммой расходов этих помещений …» |
| OV-3 | ОВ: the same, when the text does not call it the sum | **K** | The system flow legitimately exceeds the room sum by leaks and losses; `SECTION-OV-FULL-01` question 2 (N) stands. | [OV-SYSFLOW] «… : разница на подсосы и потери допустима.» |
| OV-4 | ОВ: «Итого» of the heat-load table against the sum of its rows (one kind of load) | **W** | GAP: «a heat-load total against its rows (q4)». SRC: «Тепловые нагрузки на отопление и вентиляцию» (`project_params.md` line 6). The record names no basis; the prompt still requires that a stated included or excluded part be in the rows too. | [OV-SCOPE] «… а также строка «Итого» таблицы тепловых нагрузок и сумма её строк того же вида нагрузки.» [OV-PART] «между строками и итогом нет подытогов и строк-добавок, а текст не говорит, что итог включает или не включает какую-то часть либо получен иначе (с учётом потерь, коэффициента, резерва) …» |
| OV-5 | ОВ: supply air against exhaust air; loads of different kinds against each other | **X** | Different attributes; an imbalance of supply and exhaust is legal and no source rule asks for it. | [OV-NOCROSS] «Приток с вытяжкой и нагрузки разных видов друг с другом не сопоставляй.» |
| OV-6 | ОВ: the building totals of supply and exhaust air (`total_supply_air_m3h`) against the sum over systems | **X** | Not marked reinstatable by GAP; the source names the building totals but no text states that systems add up to them (smoke-exhaust and standby systems, modes). The scope sentence is a closed list. | none (the scope sentence OV-SCOPE names what is added) |
| VK-1 | ВК: the daily consumption of the building against the sum of its parts that the text itself names as parts | **W** | GAP: «the building's total flow against the sum over systems (q4)». REC: «Считать ли находкой расхождение общего расхода здания с суммой расходов по системам или потребителям …». SRC: «Суточное водопотребление здания, м³/сут» (`project_params.md` line 36). | [VK-SCOPE] «Для ВК это только суточное водопотребление: итог по зданию («Итого», «Всего») и строки по системам или потребителям, которые текст сам называет частями этого итога («в том числе», «из них»).» [VK-NODOUBLE] «Строку, которая сама является итогом или повторяет другую строку (например, расход канализации, равный общему расходу воды), в сумму не включай.» Also VK-HINT, W-HEAD, VK-VISIBLE, W-NONUM, VK-PART, W-TOL, W-CLOSE. |
| VK-2 | ВК: hourly and secondly flows of the building against the sum over systems | **X** | The text does not state that peak flows add up, and in the usual method the peak flow of a building is set from all fixtures together, so a sum of system flows would flag consistent documents. This is the lane's engineering reasoning, not in any pinned file (assumption 4). | [VK-PEAKS] «Часовые и секундные расходы здания не суммируй: расходы отдельных систем в сумме не обязаны давать расход здания.» |
| PT-1 | ПТ: the same flow written in л/с in one place and in м³/ч in another | **W** | GAP: «the same quantity in different units (л/с and м³/ч …; q2)». REC: «считать ли «10 л/с» и «36 м³/ч» одним значением …?». SRC: the pump flow in м³/ч (`checklist.md` line 44) and in л/с (`project_params.md` line 53). Rule 4: the factor is a definition (P-09). | [PT-UNITS] «один и тот же расход (подача одного и того же насоса, расход одной и той же системы), записанный в одном месте в л/с, а в другом в м³/ч: приведи к одним единицам по равенству 1 л/с = 3,6 м³/ч.» Also PT-HINT, PT-HEAD, PT-GATE, PT-VISIBLE, W-NONUM, PT-PART, PT-TOL, PT-CLOSE. |
| PT-2 | ПТ: a head in metres against a pressure in МПа | **N** | GAP lists «metres and MPa», but the conversion needs a water density and is not a rule-4 factor (D6). With one conversion now allowed, the model must not improvise a second; 1.1.0 left this to the model (question 2, K). The cost: a real conflict written in the two units is not reported (assumption 7). | [PT-UNITS-LIMIT] «… а напор, записанный в метрах, и давление, записанное в МПа, между собой не сопоставляй;» |
| PT-3 | ПТ: the design flow of the ВПВ against jets times single-jet flow | **W** | GAP: «design flow as jets times single-jet flow». REC: «… расхождение расчётного расхода ВПВ с произведением числа струй на расход одной струи …». SRC: `Q = n × q`, n the number of jets, q the flow of one jet (`checklist.md` line 2), so no number is added. Rule 3: not when the text says the design flow came another way. | [PT-PRODUCT] «расчётный расход ВПВ и произведение числа струй на расход одной струи — только если число струй, расход одной струи и расчётный расход записаны в тексте для одной и той же системы, а текст не говорит, что расчётный расход определён иначе (например, по гидравлическому расчёту при другом числе или расходе струй)» |
| PT-4 | ПТ: the total of the hydraulic calculation against the sum of the ВПВ and АУПТ flows | **W** | GAP: «the total of ВПВ and АУПТ». REC: «… итоговой строки гидравлического расчёта с суммой расходов ВПВ и АУПТ». Rule 3: only when the text calls the total the sum; a larger-of-two or separate operation is not compared. | [PT-SUM] «итоговый расход и сумма расходов ВПВ и АУПТ — только если расход ВПВ, расход АУПТ и итог записаны в тексте и текст прямо называет итог суммой этих расходов; если сказано о большем из двух расходов или об отдельной работе систем, итог с суммой не сопоставляй.» |
| PT-5 | ПТ: any other factor or pair of units | **X** | Rule 4: any number not in the source and not a definitional factor stays forbidden. | [PT-UNITS-LIMIT] «Других коэффициентов и других пар единиц не применяй …» |

The four cross-section decisions of `PRODUCTION-WAVE-PW2B.md` section 2 for these sections: (1) site and contractor phrases **K**, unchanged; (2) «Итого» against the sum of rows was **K** and is now **W** for exactly the topics above and nowhere else (the brief's override); (3) text read from sheets **K** (the new paragraph reads written figures of tables, rule 2); (4) missing items **K**, and the coordinator's note after `SECTION-WIDEN-G1-01` that an omission has no quote and the grounding gate would publish a non-existence claim as «grounded» is followed: no omission topic was added.

### How each of the brief's rules shows in the sentences

| Rule | Where |
| --- | --- |
| (1) both figures written, difference beyond the rounding, tolerance in words | W-VISIBLE, VK-VISIBLE, PT-VISIBLE (written, same units, all rows visible); W-TOL, PT-TOL: «суммы половин единицы последнего записанного разряда …; меньшая разница — это округление». No numeral. |
| (2) never recompute from an unstated figure; no drawing, picture or OCR value | W-NONUM in all four; the «Других вычислений … не выполняй» closing of KM-CLOSE, W-CLOSE, PT-CLOSE |
| (3) overlap or stated basis | KM-BASIS (basis must be named), OV-PART, VK-PART, PT-PART (no subtotals or add-on rows; a stated included or excluded part must be in the rows), OV-SYSFLOW, PT-PRODUCT, PT-SUM, VK-SCOPE (parts named by the text) |
| (4) only definitional unit factors | PT-UNITS (`3,6`), PT-UNITS-LIMIT; allowlist entry `PT`, `3,6`; no other new numeral |
| (5) equivalent notations stay excluded | `С345` / `09Г2С` (KM-4): nothing written; `REI` / `EI` and `150/70` / `130/70` are not in this group |
| (6) a decision per topic | the table above |

## The prompt change in words

Every prompt gains two edits and nothing else (`git diff` of each `system_prompt.md` is insertions only: КМ 23, ОВ 28, ВК 24, ПТ 32 lines).

- **КМ.** After the mass bullet of the «where to look» block, a bullet says the total of the mass column and the sum of its rows are compared only under the paragraph below. After the exclusion paragraph, the paragraph «Единственное исключение …» says what is added (the «Итого» row of the mass column of the specification or the element schedule and the masses of the rows of that column) and lists the four conditions: both figures and every row written in the same units and visible; no number from a drawing, picture or recognised image and none restored from other values; the table or its note names the basis of the mass (weld metal, bolts, fire protection, reserve) and it is one basis for the total and the rows, with no subtotals or add-on rows; the difference exceeds the tolerance in words. If a condition fails the total is not compared with the sum. A finding is `internal_contradiction` citing the total row and every row; the mass of one element times its count is named as not calculated.
- **ОВ.** Same two edits. The scope names the «Итого» of the air-exchange table by system against the rooms of that system of the same kind, and the «Итого» of the heat-load table against its rows of the same kind of load; a system flow from the characteristics table or the specification is compared with the rooms only if the text calls it their sum («разница на подсосы и потери допустима»); supply is not compared with exhaust nor loads of different kinds. The conditions are the same four with «no subtotals or add-on rows, and no stated included or excluded part (losses, coefficient, reserve) unless the rows have it too» in place of the basis condition.
- **ВК.** Same two edits. The scope is the daily consumption only: the building total and the rows the text itself calls parts of it («в том числе», «из них»); hourly and secondly flows are not summed; a row that is itself a total or repeats another is not added. The four conditions as in ОВ (the stated part: irrigation, losses, reserve).
- **ПТ.** The paragraph is «три сверки»: (a) the same flow in л/с and м³/ч compared after conversion by 1 л/с = 3,6 м³/ч, with no other factor or pair of units and no comparison of a head in metres with a pressure in МПа; (b) the design flow of the ВПВ against jets times single-jet flow, only when all three are written for one system and the text does not say the design flow was determined otherwise; (c) the total against the sum of the ВПВ and АУПТ flows, only when all three are written and the text calls the total the sum. Conditions: written figures, visible addends, no drawing or recognised value, no subtotals or add-on rows, the tolerance counted with the multiplier or the conversion.

New numerals: one, `3,6` (ПТ); the `1` of «1 л/с» is v1's own numeral. New norm references: none. New designations other than `3,6`: `ВПВ`, `АУПТ`, `МПа` and `м³` in ПТ, all whole tokens of the pinned ПТ source. Findings: more than before only by the eight W topics, fewer by the PT-2 narrowing.

## Added fragments, verbatim

Whitespace-normalised: a fragment is the prompt text with every run of whitespace, line breaks included, replaced by one space. A fragment is checked against the prompt normalised the same way. The block is machine-readable so that `SECTION-PROMPT-SENTENCE-GUARD-01` can read it, in the format of `SECTION-WIDEN-G1-01.md`; 31 fragments, 40 (fragment, section) pairs. Together they cover every line this lane added to the four prompts (checked: the added text with the section's fragments removed leaves nothing).

| Fragment | Sections | Role |
|---|---|---|
| `W-HEAD` | KM, OV, VK | rule: the only permitted calculation, an exception to the calculation ban |
| `W-NONUM` | KM, OV, VK, PT | conservative rule 2: no drawing, picture or recognised value; nothing restored from other values |
| `W-TOL` | KM, OV, VK | conservative rule 1: the tolerance in words |
| `W-VISIBLE` | KM, OV | conservative rule 1: both figures written, same units, all rows visible |
| `W-CLOSE` | OV, VK | category and evidence: the existing internal_contradiction, the total and every row; no other calculation |
| `KM-HINT` | KM | hint bullet: where the check applies |
| `KM-SCOPE` | KM | scope: which totals may be added |
| `KM-BASIS` | KM | conservative rule 3: the mass total only when the text states its basis |
| `KM-CLOSE` | KM | category and evidence; no other calculation, the mass of an element times its count named as refused |
| `OV-HINT` | OV | hint bullet: where the check applies |
| `OV-SCOPE` | OV | scope: which totals may be added, supply with supply and exhaust with exhaust, one kind of load |
| `OV-SYSFLOW` | OV | conservative rule 3: a system flow with leaks is compared with the rooms only when the text calls it their sum |
| `OV-NOCROSS` | OV | scope: supply is not compared with exhaust, loads of different kinds are not compared |
| `OV-PART` | OV | conservative rule 3: no subtotals or add-on rows; a stated included or excluded part must be in the rows too |
| `VK-HINT` | VK | hint bullet: where the check applies |
| `VK-SCOPE` | VK | scope: the daily consumption only, parts named as parts of the total by the text |
| `VK-PEAKS` | VK | decision X: hourly and secondly flows of a building are not summed |
| `VK-NODOUBLE` | VK | double counting: a row that is itself a total or repeats another is not added |
| `VK-VISIBLE` | VK | conservative rule 1: both figures written, same units, all parts visible |
| `VK-PART` | VK | conservative rule 3: no subtotals or add-on rows; a stated included or excluded part must be in the rows too |
| `PT-HINT` | PT | hint bullet: where the three checks apply |
| `PT-HEAD` | PT | rule: the only permitted calculations, three checks of written values |
| `PT-UNITS` | PT | rule 4: the one definitional factor, 1 л/с = 3,6 м³/ч (allowlist entry PT 3,6) |
| `PT-UNITS-LIMIT` | PT | rule 4 and decision N: no other factor, no other pair of units; a head in metres is not compared with a pressure in МПа |
| `PT-PRODUCT` | PT | conservative rules 1 to 3: jets x single-jet flow only with all three factors written for one system and no other method stated |
| `PT-SUM` | PT | conservative rule 3: the ВПВ + АУПТ total only when every term is written and the text calls the total their sum |
| `PT-GATE` | PT | gate: all conditions at once |
| `PT-VISIBLE` | PT | conservative rule 1: every compared figure written, all addends visible |
| `PT-PART` | PT | conservative rule 3: no subtotals or add-on rows, no other method stated |
| `PT-TOL` | PT | conservative rule 1: the tolerance in words, with the multiplier or the conversion |
| `PT-CLOSE` | PT | category and evidence: the existing internal_contradiction, every place and the total; no other calculation |

<!-- fragments:begin -->
```json
[
 {
  "id": "W-HEAD",
  "sections": [
   "KM",
   "OV",
   "VK"
  ],
  "role": "rule: the only permitted calculation, an exception to the calculation ban",
  "text": "Единственное исключение из запрета на расчёты — сверка записанного итога с суммой записанных слагаемых."
 },
 {
  "id": "W-NONUM",
  "sections": [
   "KM",
   "OV",
   "VK",
   "PT"
  ],
  "role": "conservative rule 2: no drawing, picture or recognised value; nothing restored from other values",
  "text": "- ни одно число не прочитано с чертежа, рисунка или распознанного изображения и не восстановлено по другим значениям;"
 },
 {
  "id": "W-TOL",
  "sections": [
   "KM",
   "OV",
   "VK"
  ],
  "role": "conservative rule 1: the tolerance in words",
  "text": "- разницу считай расхождением, только если она больше погрешности округления — суммы половин единицы последнего записанного разряда итога и каждого слагаемого; меньшая разница — это округление."
 },
 {
  "id": "W-VISIBLE",
  "sections": [
   "KM",
   "OV"
  ],
  "role": "conservative rule 1: both figures written, same units, all rows visible",
  "text": "- итог и каждое слагаемое прямо записаны в тексте числами в одних и тех же единицах, а текст показывает, что эти строки составляют именно этот итог; все строки видны в переданном тексте — без пропусков, без «и т. д.» и без обрыва таблицы;"
 },
 {
  "id": "W-CLOSE",
  "sections": [
   "OV",
   "VK"
  ],
  "role": "category and evidence: the existing internal_contradiction, the total and every row; no other calculation",
  "text": "Если хотя бы одно условие не выполнено, итог с суммой не сопоставляй. Находка — только internal_contradiction: в evidence приведи цитату строки с итогом и цитату каждой строки-слагаемого. Других вычислений не выполняй."
 },
 {
  "id": "KM-HINT",
  "sections": [
   "KM"
  ],
  "role": "hint bullet: where the check applies",
  "text": "- итог столбца масс и сумма масс строк этого столбца в спецификации металлопроката и в ведомости элементов — только на условиях абзаца об исключении из запрета на расчёты ниже;"
 },
 {
  "id": "KM-SCOPE",
  "sections": [
   "KM"
  ],
  "role": "scope: which totals may be added",
  "text": "Для КМ это строка «Итого» («Всего», «Сумма») столбца масс в спецификации металлопроката или в ведомости элементов и сумма масс строк этого же столбца. Сверяй, только если выполнено всё сразу:"
 },
 {
  "id": "KM-BASIS",
  "sections": [
   "KM"
  ],
  "role": "conservative rule 3: the mass total only when the text states its basis",
  "text": "- у самой таблицы или в её примечании текст называет основу массы: включены ли в неё наплавленный металл, метизы, огнезащита, запас; основа одна и та же у итога и у всех строк, а между строками и итогом нет подытогов и строк-добавок;"
 },
 {
  "id": "KM-CLOSE",
  "sections": [
   "KM"
  ],
  "role": "category and evidence; no other calculation, the mass of an element times its count named as refused",
  "text": "Если хотя бы одно условие не выполнено, итог с суммой не сопоставляй. Находка — только internal_contradiction: в evidence приведи цитату строки с итогом и цитату каждой строки-слагаемого. Других вычислений (например, массу одного элемента, умноженную на количество) не выполняй."
 },
 {
  "id": "OV-HINT",
  "sections": [
   "OV"
  ],
  "role": "hint bullet: where the check applies",
  "text": "- итог таблицы воздухообмена по системе и сумма расходов её помещений; итог таблицы тепловых нагрузок и сумма её строк — только на условиях абзаца об исключении из запрета на расчёты ниже;"
 },
 {
  "id": "OV-SCOPE",
  "sections": [
   "OV"
  ],
  "role": "scope: which totals may be added, supply with supply and exhaust with exhaust, one kind of load",
  "text": "Для ОВ это строка «Итого» («Всего») таблицы воздухообмена по системе и сумма расходов помещений этой системы того же вида (приток с притоком, вытяжка с вытяжкой), а также строка «Итого» таблицы тепловых нагрузок и сумма её строк того же вида нагрузки."
 },
 {
  "id": "OV-SYSFLOW",
  "sections": [
   "OV"
  ],
  "role": "conservative rule 3: a system flow with leaks is compared with the rooms only when the text calls it their sum",
  "text": "Расход системы из таблицы характеристик систем или из спецификации с суммой расходов помещений сопоставляй, только если текст прямо называет его суммой расходов этих помещений: разница на подсосы и потери допустима."
 },
 {
  "id": "OV-NOCROSS",
  "sections": [
   "OV"
  ],
  "role": "scope: supply is not compared with exhaust, loads of different kinds are not compared",
  "text": "Приток с вытяжкой и нагрузки разных видов друг с другом не сопоставляй. Сверяй, только если выполнено всё сразу:"
 },
 {
  "id": "OV-PART",
  "sections": [
   "OV"
  ],
  "role": "conservative rule 3: no subtotals or add-on rows; a stated included or excluded part must be in the rows too",
  "text": "- между строками и итогом нет подытогов и строк-добавок, а текст не говорит, что итог включает или не включает какую-то часть либо получен иначе (с учётом потерь, коэффициента, резерва); если такое сказано, сверяй, только если эта же часть входит или не входит и в строки;"
 },
 {
  "id": "VK-HINT",
  "sections": [
   "VK"
  ],
  "role": "hint bullet: where the check applies",
  "text": "- суточное водопотребление здания и сумма его частей, которые текст сам называет частями этого итога, — только на условиях абзаца об исключении из запрета на расчёты ниже;"
 },
 {
  "id": "VK-SCOPE",
  "sections": [
   "VK"
  ],
  "role": "scope: the daily consumption only, parts named as parts of the total by the text",
  "text": "Для ВК это только суточное водопотребление: итог по зданию («Итого», «Всего») и строки по системам или потребителям, которые текст сам называет частями этого итога («в том числе», «из них»)."
 },
 {
  "id": "VK-PEAKS",
  "sections": [
   "VK"
  ],
  "role": "decision X: hourly and secondly flows of a building are not summed",
  "text": "Часовые и секундные расходы здания не суммируй: расходы отдельных систем в сумме не обязаны давать расход здания."
 },
 {
  "id": "VK-NODOUBLE",
  "sections": [
   "VK"
  ],
  "role": "double counting: a row that is itself a total or repeats another is not added",
  "text": "Строку, которая сама является итогом или повторяет другую строку (например, расход канализации, равный общему расходу воды), в сумму не включай. Сверяй, только если выполнено всё сразу:"
 },
 {
  "id": "VK-VISIBLE",
  "sections": [
   "VK"
  ],
  "role": "conservative rule 1: both figures written, same units, all parts visible",
  "text": "- итог и каждое слагаемое прямо записаны в тексте числами в одних и тех же единицах; все части итога видны в переданном тексте — без пропусков, без «и т. д.» и без обрыва таблицы;"
 },
 {
  "id": "VK-PART",
  "sections": [
   "VK"
  ],
  "role": "conservative rule 3: no subtotals or add-on rows; a stated included or excluded part must be in the rows too",
  "text": "- между частями и итогом нет подытогов и строк-добавок, а текст не говорит, что итог включает или не включает какую-то часть (полив, потери, резерв); если такое сказано, сверяй, только если эта же часть входит или не входит и в строки;"
 },
 {
  "id": "PT-HINT",
  "sections": [
   "PT"
  ],
  "role": "hint bullet: where the three checks apply",
  "text": "- один и тот же расход в разных единицах, расчётный расход ВПВ и произведение числа струй на расход одной струи, итоговый расход и сумма расходов ВПВ и АУПТ — только на условиях абзаца об исключении из запрета на расчёты ниже;"
 },
 {
  "id": "PT-HEAD",
  "sections": [
   "PT"
  ],
  "role": "rule: the only permitted calculations, three checks of written values",
  "text": "Единственное исключение из запрета на расчёты — три сверки записанных значений одной и той же системы или одного и того же насоса:"
 },
 {
  "id": "PT-UNITS",
  "sections": [
   "PT"
  ],
  "role": "rule 4: the one definitional factor, 1 л/с = 3,6 м³/ч (allowlist entry PT 3,6)",
  "text": "- один и тот же расход (подача одного и того же насоса, расход одной и той же системы), записанный в одном месте в л/с, а в другом в м³/ч: приведи к одним единицам по равенству 1 л/с = 3,6 м³/ч."
 },
 {
  "id": "PT-UNITS-LIMIT",
  "sections": [
   "PT"
  ],
  "role": "rule 4 and decision N: no other factor, no other pair of units; a head in metres is not compared with a pressure in МПа",
  "text": "Других коэффициентов и других пар единиц не применяй, а напор, записанный в метрах, и давление, записанное в МПа, между собой не сопоставляй;"
 },
 {
  "id": "PT-PRODUCT",
  "sections": [
   "PT"
  ],
  "role": "conservative rules 1 to 3: jets x single-jet flow only with all three factors written for one system and no other method stated",
  "text": "- расчётный расход ВПВ и произведение числа струй на расход одной струи — только если число струй, расход одной струи и расчётный расход записаны в тексте для одной и той же системы, а текст не говорит, что расчётный расход определён иначе (например, по гидравлическому расчёту при другом числе или расходе струй);"
 },
 {
  "id": "PT-SUM",
  "sections": [
   "PT"
  ],
  "role": "conservative rule 3: the ВПВ + АУПТ total only when every term is written and the text calls the total their sum",
  "text": "- итоговый расход и сумма расходов ВПВ и АУПТ — только если расход ВПВ, расход АУПТ и итог записаны в тексте и текст прямо называет итог суммой этих расходов; если сказано о большем из двух расходов или об отдельной работе систем, итог с суммой не сопоставляй."
 },
 {
  "id": "PT-GATE",
  "sections": [
   "PT"
  ],
  "role": "gate: all conditions at once",
  "text": "Сверяй, только если выполнено всё сразу:"
 },
 {
  "id": "PT-VISIBLE",
  "sections": [
   "PT"
  ],
  "role": "conservative rule 1: every compared figure written, all addends visible",
  "text": "- все сравниваемые величины прямо записаны в тексте числами; для суммы все слагаемые видны в переданном тексте — без пропусков, без «и т. д.» и без обрыва таблицы;"
 },
 {
  "id": "PT-PART",
  "sections": [
   "PT"
  ],
  "role": "conservative rule 3: no subtotals or add-on rows, no other method stated",
  "text": "- между величинами и итогом нет подытогов и строк-добавок, а текст не говорит, что итог включает или не включает какую-то часть либо получен иначе;"
 },
 {
  "id": "PT-TOL",
  "sections": [
   "PT"
  ],
  "role": "conservative rule 1: the tolerance in words, with the multiplier or the conversion",
  "text": "- разницу считай расхождением, только если она больше погрешности округления — суммы половин единицы последнего записанного разряда всех сравниваемых величин, каждой с учётом множителя, на который она умножается или в который пересчитана; меньшая разница — это округление."
 },
 {
  "id": "PT-CLOSE",
  "sections": [
   "PT"
  ],
  "role": "category and evidence: the existing internal_contradiction, every place and the total; no other calculation",
  "text": "Если хотя бы одно условие не выполнено, величины не сопоставляй. Находка — только internal_contradiction: в evidence приведи цитату каждого места, где записана сравниваемая величина, и цитату итога. Других вычислений не выполняй."
 }
]
```
<!-- fragments:end -->

Check (prints the fragments missing from the prompts of this tree; the expected answer is an empty list):

```text
F=$(python3 -I -c "print(chr(96)*3)"); python3 -I -c "import json,re,sys;f=sys.argv[1];t=open('docs/program/SECTION-WIDEN-G2-01.md',encoding='utf-8').read();fr=json.loads(re.search('<!-- fragments:begin -->\\\\s*'+f+'json\\n(.*?)\\n'+f+'\\\\s*<!-- fragments:end -->',t,re.S).group(1));n=lambda s:' '.join(s.split());bad=[(x['id'],c) for x in fr for c in x['sections'] if x['text'] not in n(open('src/auditmanager/analysis/text/profiles/'+c.lower()+'/system_prompt.md',encoding='utf-8').read())];print(len(fr),'fragments; missing',bad)" "$F"
```

Run on this tree: `31 fragments; missing []`. Row M3c of the mutation table shows why the check is worth having: a prompt sentence deleted together with a consistent rebuild of the recordings turns no other test red.

## Assumptions an expert would still want to check

None of these was checked by anyone with domain knowledge.

1. **The КМ check will rarely fire.** It needs the table or its note to name the basis of the masses (D5). A specification that says only «Масса, кг» is not checked. An expert may accept «the same table column» as a sufficient basis, or require the weld-metal statement; the lane took the stricter reading of rule 3.
2. **Tables in a text layer.** The extractor gives text, not a grid. A row may be split over lines, columns may interleave, a continued table may end at a page edge. The conditions (all rows visible, same units, no subtotals) are the lane's guard against that; how often the model can apply them to a real extract was not measured.
3. **ОВ.** A system flow in the air-exchange table may legitimately differ from its rooms by a balancing allowance that the text does not name; the prompt then reports it. The heat-load table may carry a coefficient of simultaneity or a loss that the text names only in a note elsewhere; the prompt then reports it, because only a part named «с учётом» / «без учёта» next to the total is excluded.
4. **ВК.** That daily consumption adds up from consumers named as parts, and that hourly and secondly flows of a building are not the sum of the flows of its systems, are the lane's engineering reasoning. No pinned file says either. If the second is wrong for some documents, the model will miss a real contradiction in a peak flow; if the first is wrong, it will report a legal difference (for example a row of irrigation outside the total).
5. **ПТ.** The design flow of a ВПВ may differ from jets times single-jet flow in a document that does not say why; the prompt reports it. A total of the ВПВ and АУПТ may be the larger of the two in some designs; the prompt compares only when the text calls it the sum. Whether a text says «по гидравлическому расчёту» in a form the model recognises was not measured.
6. **The tolerance.** The sum of the half-units of the last written digit presumes the digits written are the precision. A figure written as `1200` may be rounded to hundreds; then a real rounding difference is reported. The rule is in words and has no number, as the brief asks.
7. **PT-2.** A head in metres and a pressure in МПа for the same point are now never compared, so a real conflict between them is missed. An expert may want a stated conversion (with a stated density) instead.
8. **Model arithmetic.** Adding a column of up to a few dozen figures and multiplying two written figures are the model's own calculation; its reliability was not measured. The wording asks it to stay silent when unsure only through the conditions, not through a confidence rule.
9. **Vocabulary not from the source.** Plain words of the new sentences that none of the five pinned files of the section holds (the token guard reads designations, not words), picked by comparing the added text with the section's files, v1 and the old prompt: КМ «наплавленный металл», «запас», «подытогов», «строк-добавок»; ОВ «резерва», «коэффициента», «подсосы» (a form of «подсосов», which the 1.1.0 prompt has); ВК «полив», «потребителям», «часовые», «секундные», «в том числе»; ПТ «множителя», «пересчитана», «произведение». «Наплавленный металл» is named by the brief's rule 3 and by the record's question, not by the source.
10. **Nothing was measured.** The four routing recordings are the same hand-authored replies over the АР corpus as before; the specimens below are hand-authored too. They prove that a reply of this shape binds to its text, not that a model gives it.

## Token-guard additions

One entry, appended to `tests/unit/analysis/text_profiles/prompt_token_allowlist.json` (the file is otherwise byte-identical):

| Section | Token | Class | Reason (the entry's, abridged) |
| --- | --- | --- | --- |
| PT | `3,6` | a | The factor of 1 л/с = 3,6 м³/ч in the unit rule of `PRODUCTION-WAVE-PW4.md` section 6, rule 4: one litre per second is 3600 litres per hour, that is 3,6 cubic metres per hour, a definition of the units. The pinned ПТ files write the same flow in л/с and in м³/ч but hold no factor. `disclosed_by` is this report, which names the token. |

The audit as run on the tree (guard functions, the allowlist without the new entry): КМ 36 designations before and after, none new; ОВ 38 and 38; ВК 39 and 39; ПТ 33 before and 38 after, the five new being `3,6` (allowlist), `АУПТ`, `ВПВ`, `МПа` and `м³` (all whole tokens of the pinned ПТ source). Unexplained without the entry: `3,6` and nothing else. Rows M4, M13b, M14 and M15 show the guard red when the entry is removed, the factor is changed, a numeral is invented or this report stops naming the token.

## Specimens

One positive and one negative text per widened section, with the hand-authored reply a model would give. They were replayed through the real stage (`run_text_analysis`) with the section's own profile and a throw-away recorded directory in the session scratchpad; they are **not** committed as fixtures (D1). Every positive reply opens its `finding_text` with «Синтетический ответ (<раздел>), не результат вызова модели», as the existing recordings do. Both texts of a section carry the same **traps**, places where the prompt says not to compare and a naive sum or product would flag, so the empty negative reply and the single positive reply depend on the prompt's rules.

The seeded arithmetic (recomputed by the specimen test of commit `b91e2022`, 46 tests; tolerance = sum of the half-units, D4):

| Section | Relation | Positive: written / recomputed | Negative: written / recomputed | Tolerance |
| --- | --- | --- | --- | --- |
| КМ | «Итого» of the mass column against five marks | 5892,5 / 5982,5 (difference 90,0) | 5982,5 / 5982,5 | 0,30 |
| ОВ | «Итого по системе П1» against four rooms | 1200 / 1100 (100) | 1100 / 1100 | 2,5 |
| ОВ | «Итого» of the heat loads against three rows | 405,5 / 415,5 (10,0) | 415,5 / 415,5 | 0,20 |
| ВК | «всего» daily consumption against three parts | 121,4 / 118,4 (3,0) | 118,4 / 118,4 | 0,20 |
| ПТ | pump flow 10 л/с in 36 м³/ч against the written value | 40 м³/ч / 36 м³/ч (4) | 36 / 36 | 2,3 |
| ПТ | jets 2 times 2,6 л/с against the design flow | 4,8 / 5,2 (0,4) | 5,2 / 5,2 | 0,15 |
| ПТ | design flow ВПВ plus АУПТ 28,0 against the total | 34,0 / 32,8 (1,2) | 33,2 / 33,2 | 0,15 |

The traps (in both texts): КМ «с учётом наплавленного металла — 6071,7 кг» against a table that says «без учёта наплавленного металла и метизов» (another basis); ОВ «расход воздуха установки 1250 м³/ч (с учётом подсосов и потерь)» against the 1100 or 1200 of the rooms; ВК «общий 4,20, в том числе холодной воды 3,10 и горячей воды 2,00» (a secondly flow, 3,10 + 2,00 is 5,10); ПТ «расчётный расход — 6,1 л/с по результатам гидравлического расчёта» for 2 jets of 2,6 л/с (another method named), and «напор … 45 м; давление … 0,43 МПа» (not compared).

| Section | Case | Proposed | Emitted | Evidence unresolved |
| --- | --- | --- | --- | --- |
| КМ | positive (5892,5 against 5982,5) | 1 | 1 | 0 |
| КМ | negative (consistent, one trap) | 0 | 0 | 0 |
| КМ | positive with one quote altered by one character | 1 | 1 | 1 |
| ОВ | positive (air 1200 against 1100, heat 405,5 against 415,5) | 2 | 2 | 0 |
| ОВ | negative (consistent, one trap) | 0 | 0 | 0 |
| ОВ | positive with one altered quote | 2 | 2 | 1 |
| ВК | positive (121,4 against 118,4) | 1 | 1 | 0 |
| ВК | negative (consistent, secondly flows) | 0 | 0 | 0 |
| ВК | positive with one altered quote | 1 | 1 | 1 |
| ПТ | positive (units, product, sum) | 3 | 3 | 0 |
| ПТ | negative (consistent, two traps) | 0 | 0 | 0 |
| ПТ | positive with one altered quote | 3 | 3 | 1 |

The altered-quote rows are the mutation of this check: a quote that is not verbatim leaves the evidence unresolved, and the grounding gate would then refuse the finding. What these rows do **not** show: that a model gives these answers.

```json
{
 "KM": {
  "positive": {
   "pages": [
    "Раздел 4. Конструкции металлические (КМ)\nОбъект: многоквартирный жилой дом (вымышленный, для проверки)\nСтадия: П\nОбщие данные\nКонструктивная схема каркаса — рамно-связевая.\nОбщая масса металлоконструкций, прямо указанная в общих данных: 5892,5 кг.\n",
    "Спецификация металлопроката. Масса марок, кг\nМарка Профиль Количество, шт. Масса марки, кг\nБ1 Двутавр 30Б1 6 1240,5\nБ2 Двутавр 25Б1 4 868,0\nК1 Двутавр 30К1 8 2315,5\nК2 Двутавр 25К1 4 1102,0\nСв1 Уголок 100х8 20 456,5\nИтого 5892,5\nПримечание. Масса в таблице дана без учёта наплавленного металла и метизов.\n",
    "Пояснительная записка. Масса металлоконструкций с учётом наплавленного металла — 6071,7 кг.\n"
   ],
   "observations": [
    {
     "category": "internal_contradiction",
     "finding_text": "Синтетический ответ (КМ), не результат вызова модели: итог столбца масс в спецификации металлопроката записан как 5892,5 кг, а сумма масс пяти марок того же столбца — 5982,5 кг; разность больше погрешности округления, основа массы в таблице названа одна (без наплавленного металла и метизов).",
     "recommendation_text": "Проверить массы марок и итог спецификации и привести их в соответствие.",
     "evidence": [
      {
       "page_number": 2,
       "quote": "Итого 5892,5"
      },
      {
       "page_number": 2,
       "quote": "Б1 Двутавр 30Б1 6 1240,5"
      },
      {
       "page_number": 2,
       "quote": "Б2 Двутавр 25Б1 4 868,0"
      },
      {
       "page_number": 2,
       "quote": "К1 Двутавр 30К1 8 2315,5"
      },
      {
       "page_number": 2,
       "quote": "К2 Двутавр 25К1 4 1102,0"
      },
      {
       "page_number": 2,
       "quote": "Св1 Уголок 100х8 20 456,5"
      }
     ]
    }
   ]
  },
  "negative": {
   "pages": [
    "Раздел 4. Конструкции металлические (КМ)\nОбъект: многоквартирный жилой дом (вымышленный, для проверки)\nСтадия: П\nОбщие данные\nКонструктивная схема каркаса — рамно-связевая.\nОбщая масса металлоконструкций, прямо указанная в общих данных: 5982,5 кг.\n",
    "Спецификация металлопроката. Масса марок, кг\nМарка Профиль Количество, шт. Масса марки, кг\nБ1 Двутавр 30Б1 6 1240,5\nБ2 Двутавр 25Б1 4 868,0\nК1 Двутавр 30К1 8 2315,5\nК2 Двутавр 25К1 4 1102,0\nСв1 Уголок 100х8 20 456,5\nИтого 5982,5\nПримечание. Масса в таблице дана без учёта наплавленного металла и метизов.\n",
    "Пояснительная записка. Масса металлоконструкций с учётом наплавленного металла — 6071,7 кг.\n"
   ],
   "observations": []
  }
 },
 "OV": {
  "positive": {
   "pages": [
    "Раздел 5. Отопление, вентиляция и кондиционирование (ОВ)\nОбъект: многоквартирный жилой дом (вымышленный, для проверки)\nСтадия: П\nОбщие данные\nТеплоноситель систем отопления — вода.\n",
    "Таблица воздухообмена. Система П1 (приток), расход воздуха, м³/ч\n101 Тамбур 300\n102 Лифтовой холл 450\n103 Помещение охраны 200\n104 Электрощитовая 150\nИтого по системе П1 1200\nТаблица тепловых нагрузок, кВт\nОтопление 180,0\nВентиляция 95,5\nГорячее водоснабжение 140,0\nИтого 405,5\n",
    "Таблица характеристик систем\nСистема П1: расход воздуха установки 1250 м³/ч (с учётом подсосов и потерь).\n"
   ],
   "observations": [
    {
     "category": "internal_contradiction",
     "finding_text": "Синтетический ответ (ОВ), не результат вызова модели: итог таблицы воздухообмена по системе П1 записан как 1200 м³/ч, а сумма расходов четырёх помещений этой системы — 1100 м³/ч.",
     "recommendation_text": "Сверить расходы помещений системы П1 с итогом таблицы воздухообмена.",
     "evidence": [
      {
       "page_number": 2,
       "quote": "Итого по системе П1 1200"
      },
      {
       "page_number": 2,
       "quote": "101 Тамбур 300"
      },
      {
       "page_number": 2,
       "quote": "102 Лифтовой холл 450"
      },
      {
       "page_number": 2,
       "quote": "103 Помещение охраны 200"
      },
      {
       "page_number": 2,
       "quote": "104 Электрощитовая 150"
      }
     ]
    },
    {
     "category": "internal_contradiction",
     "finding_text": "Синтетический ответ (ОВ), не результат вызова модели: итог таблицы тепловых нагрузок записан как 405,5 кВт, а сумма трёх её строк — 415,5 кВт.",
     "recommendation_text": "Сверить строки таблицы тепловых нагрузок с её итогом.",
     "evidence": [
      {
       "page_number": 2,
       "quote": "Итого 405,5"
      },
      {
       "page_number": 2,
       "quote": "Отопление 180,0"
      },
      {
       "page_number": 2,
       "quote": "Вентиляция 95,5"
      },
      {
       "page_number": 2,
       "quote": "Горячее водоснабжение 140,0"
      }
     ]
    }
   ]
  },
  "negative": {
   "pages": [
    "Раздел 5. Отопление, вентиляция и кондиционирование (ОВ)\nОбъект: многоквартирный жилой дом (вымышленный, для проверки)\nСтадия: П\nОбщие данные\nТеплоноситель систем отопления — вода.\n",
    "Таблица воздухообмена. Система П1 (приток), расход воздуха, м³/ч\n101 Тамбур 300\n102 Лифтовой холл 450\n103 Помещение охраны 200\n104 Электрощитовая 150\nИтого по системе П1 1100\nТаблица тепловых нагрузок, кВт\nОтопление 180,0\nВентиляция 95,5\nГорячее водоснабжение 140,0\nИтого 415,5\n",
    "Таблица характеристик систем\nСистема П1: расход воздуха установки 1250 м³/ч (с учётом подсосов и потерь).\n"
   ],
   "observations": []
  }
 },
 "VK": {
  "positive": {
   "pages": [
    "Раздел 6. Водоснабжение и канализация (ВК)\nОбъект: многоквартирный жилой дом (вымышленный, для проверки)\nСтадия: П\nОбщие данные\nИсточник водоснабжения — городской водопровод.\n",
    "Таблица расчётных расходов воды\nСуточное водопотребление здания, м³/сут: всего 121,4, в том числе:\nжилая часть 96,2\nвстроенные помещения 14,6\nполив территории 7,6\nМаксимальный секундный расход, л/с: общий 4,20, в том числе холодной воды 3,10 и горячей воды 2,00.\n"
   ],
   "observations": [
    {
     "category": "internal_contradiction",
     "finding_text": "Синтетический ответ (ВК), не результат вызова модели: суточное водопотребление здания записано как 121,4 м³/сут, а сумма трёх частей, названных в тексте частями этого итога, — 118,4 м³/сут.",
     "recommendation_text": "Сверить части суточного водопотребления с итогом по зданию.",
     "evidence": [
      {
       "page_number": 2,
       "quote": "всего 121,4"
      },
      {
       "page_number": 2,
       "quote": "жилая часть 96,2"
      },
      {
       "page_number": 2,
       "quote": "встроенные помещения 14,6"
      },
      {
       "page_number": 2,
       "quote": "полив территории 7,6"
      }
     ]
    }
   ]
  },
  "negative": {
   "pages": [
    "Раздел 6. Водоснабжение и канализация (ВК)\nОбъект: многоквартирный жилой дом (вымышленный, для проверки)\nСтадия: П\nОбщие данные\nИсточник водоснабжения — городской водопровод.\n",
    "Таблица расчётных расходов воды\nСуточное водопотребление здания, м³/сут: всего 118,4, в том числе:\nжилая часть 96,2\nвстроенные помещения 14,6\nполив территории 7,6\nМаксимальный секундный расход, л/с: общий 4,20, в том числе холодной воды 3,10 и горячей воды 2,00.\n"
   ],
   "observations": []
  }
 },
 "PT": {
  "positive": {
   "pages": [
    "Раздел 7. Противопожарный водопровод (ПТ)\nОбъект: многоквартирный жилой дом (вымышленный, для проверки)\nСтадия: П\nОбщие данные\nПодача основного пожарного насоса — 10 л/с.\nВнутренний противопожарный водопровод: число струй — 2, расход одной струи — 2,6 л/с, расчётный расход ВПВ — 4,8 л/с.\n",
    "Спецификация оборудования\nНасос пожарный основной: подача 40 м³/ч, напор 55 м\nРасчётный расход АУПТ — 28,0 л/с.\nСуммарный расход ВПВ и АУПТ — 34,0 л/с.\n",
    "Внутренний противопожарный водопровод паркинга: число струй — 2, расход одной струи — 2,6 л/с, расчётный расход — 6,1 л/с по результатам гидравлического расчёта.\nНапор у диктующего пожарного крана — 45 м; давление у пожарного крана по таблице гидравлического расчёта — 0,43 МПа.\n"
   ],
   "observations": [
    {
     "category": "internal_contradiction",
     "finding_text": "Синтетический ответ (ПТ), не результат вызова модели: подача основного пожарного насоса записана как 10 л/с, что при равенстве 1 л/с = 3,6 м³/ч составляет 36 м³/ч, и как 40 м³/ч в спецификации; разность больше погрешности округления.",
     "recommendation_text": "Привести подачу основного пожарного насоса к одному значению.",
     "evidence": [
      {
       "page_number": 1,
       "quote": "Подача основного пожарного насоса — 10 л/с."
      },
      {
       "page_number": 2,
       "quote": "Насос пожарный основной: подача 40 м³/ч, напор 55 м"
      }
     ]
    },
    {
     "category": "internal_contradiction",
     "finding_text": "Синтетический ответ (ПТ), не результат вызова модели: расчётный расход ВПВ записан как 4,8 л/с, а число струй 2, умноженное на расход одной струи 2,6 л/с, даёт 5,2 л/с; текст не говорит, что расчётный расход определён иначе.",
     "recommendation_text": "Согласовать расчётный расход ВПВ с числом струй и расходом одной струи.",
     "evidence": [
      {
       "page_number": 1,
       "quote": "число струй — 2, расход одной струи — 2,6 л/с, расчётный расход ВПВ — 4,8 л/с"
      }
     ]
    },
    {
     "category": "internal_contradiction",
     "finding_text": "Синтетический ответ (ПТ), не результат вызова модели: суммарный расход ВПВ и АУПТ записан как 34,0 л/с, а сумма записанных расходов ВПВ (4,8 л/с) и АУПТ (28,0 л/с) — 32,8 л/с.",
     "recommendation_text": "Сверить суммарный расход с расходами ВПВ и АУПТ.",
     "evidence": [
      {
       "page_number": 2,
       "quote": "Суммарный расход ВПВ и АУПТ — 34,0 л/с."
      },
      {
       "page_number": 1,
       "quote": "расчётный расход ВПВ — 4,8 л/с"
      },
      {
       "page_number": 2,
       "quote": "Расчётный расход АУПТ — 28,0 л/с."
      }
     ]
    }
   ]
  },
  "negative": {
   "pages": [
    "Раздел 7. Противопожарный водопровод (ПТ)\nОбъект: многоквартирный жилой дом (вымышленный, для проверки)\nСтадия: П\nОбщие данные\nПодача основного пожарного насоса — 10 л/с.\nВнутренний противопожарный водопровод: число струй — 2, расход одной струи — 2,6 л/с, расчётный расход ВПВ — 5,2 л/с.\n",
    "Спецификация оборудования\nНасос пожарный основной: подача 36 м³/ч, напор 55 м\nРасчётный расход АУПТ — 28,0 л/с.\nСуммарный расход ВПВ и АУПТ — 33,2 л/с.\n",
    "Внутренний противопожарный водопровод паркинга: число струй — 2, расход одной струи — 2,6 л/с, расчётный расход — 6,1 л/с по результатам гидравлического расчёта.\nНапор у диктующего пожарного крана — 45 м; давление у пожарного крана по таблице гидравлического расчёта — 0,43 МПа.\n"
   ],
   "observations": []
  }
 }
}
```

The replay (the throw-away script of the lane; it needs `PYTHONPATH=src:$BS` and the repository root as the working directory):

```python
import json, tempfile
from pathlib import Path
from auditmanager.analysis.text import run_text_analysis
from auditmanager.analysis.text.adapter import build_request
from auditmanager.analysis.text.config import ProviderConfig, ProviderMode
from auditmanager.analysis.text.profile_registry import load_text_profile_registry
from auditmanager.analysis.text.recorded import RecordedAdapter, recording_document
from auditmanager.analysis.text.textlayer import load_text_layer
from auditmanager.shared.identity import RunId

BASE = json.loads(Path("fixtures/recorded/text_analysis/inputs/ar_baseline_text_layer.json").read_text("utf-8"))

def layer(pages):  # pages are concatenated with no separator, as the extractor's layer is
    out, start = [], 0
    for number, text in enumerate(pages, 1):
        out.append({"char_start": start, "char_end": start + len(text), "page_number": number, "text": text})
        start += len(text)
    return {**{k: v for k, v in BASE.items() if k != "pages"}, "pages": out, "total_char_count": start}

def replay(code, pages, observations):  # observations: the "observations" list of the specimen
    profile = load_text_profile_registry().entries[code].profile
    doc = layer(pages)
    request = build_request(model_id="claude-opus-5", bundle=profile.prompt_bundle, text_layer=load_text_layer(doc))
    recording = recording_document(request=request, output_text=json.dumps({"observations": observations}, ensure_ascii=False),
                                   stop_reason="end_turn", input_tokens=3000, output_tokens=300, latency_ms=9000, note="specimen")
    with tempfile.TemporaryDirectory() as tmp:
        (Path(tmp) / f"{request.request_sha256}.json").write_text(json.dumps(recording, ensure_ascii=False), "utf-8")
        config = ProviderConfig(mode=ProviderMode.RECORDED, model_id="claude-opus-5", run_cost_ceiling_usd=1.00,
                                api_key=None, ceiling_is_explicit=True)
        outcome = run_text_analysis(run_id=RunId.new(), text_layer_document=doc, adapter=RecordedAdapter(Path(tmp)),
                                    profile=profile, config=config)
    return outcome.status, outcome.metrics  # observations_proposed, observations_emitted, evidence_unresolved
```

## Mutation table

Each row was applied to the committed tree, the named tests were run, and the change was reverted with `git checkout` (the tree ended clean). «Red» lists what failed; counts are the tests of the run. The harness is outside the repository. Rows run on the tip:

| # | Mutation | Result | Red |
| --- | --- | --- | --- |
| M1 | `profile_version` of one package reverted to `1.1.0` (`profile.json` only), each of KM, OV, VK, PT in turn | 4 runs, each 3 failed, 160 passed | `test_the_tree_registers_without_error_and_without_an_ar_entry_or_package`, `test_every_line_agrees_with_its_package_profile_json`, `test_every_profile_manifest_has_the_text_profile_1_shape` |
| M2 | the section's expectations line reverted to `1.1.0` (that line only), each of the four | 4 runs, each 3 failed, 160 passed | the same three |
| M3 | the VK sentence «Часовые и секундные расходы здания не суммируй …» deleted, recordings not rebuilt | 7 failed, 102 passed (`test_section_recordings.py`); `build_fixtures.py --check` reports the VK file drift; fragment check missing `VK-PEAKS` | the VK recording tests, the usage-signature test, `test_the_builder_reports_no_drift` |
| M3c | the same deletion **and** the routing recordings rebuilt consistently | **324 passed**, `--check` prints `fixtures match`; only the fragment check names `('VK-PEAKS', 'VK')` | none of the repository's tests: the `D-224` residual in action; the fragment table is what catches it until the sentence guard reads it |
| M4 | the allowlist entry `PT`, `3,6` removed | 4 failed, 105 passed | `test_every_designation_is_in_the_pinned_source_in_v1_or_the_allowlist[PT]` and the three `test_inserting_an_invented_designation_turns_the_audit_red[…-PT]` |
| M5 | OV prompt re-spaced («Единственное  исключение», no rebuild) | 7 failed, 102 passed; `--check` drifts; the whitespace-normalised fragment check does not see it | the OV recording tests, `test_the_builder_reports_no_drift` |
| M12 | the `disclosed_by` pattern restored to a form that refuses this report | 1 failed, 110 passed | `test_the_allowlist_has_the_documented_shape` |
| M13 | the PT factor changed to `3,7`, recordings not rebuilt | 13 failed, 259 passed; `--check` drifts; fragment check missing `PT-UNITS` | the PT recording tests and the guard |
| M13b | the same change **with** the recordings rebuilt | 6 failed, 266 passed; fragment check missing `PT-UNITS` | `test_every_designation_…_allowlist[PT]` (`3,7` unexplained), `test_every_entry_still_appears_in_its_prompt_and_is_not_covered_by_v1` (`3,6` no longer in the prompt), the three invented-designation cases, `test_removing_an_allowlist_entry_turns_the_audit_red[PT-3,6]` |
| M14 | a numeral `999` put into the OV exception paragraph | 4 failed, 107 passed | `test_every_designation_…_allowlist[OV]` and the three invented-designation cases |
| M15 | this report stops mentioning `3,6` | 1 failed, 110 passed | `test_every_entry_names_a_report_that_contains_its_token` |

Rows run on the specimen test of commit `b91e2022` (46 tests, removed from the tip; `git checkout b91e2022 -- fixtures/recorded/sections_widen_g2 tests/integration/sections/test_section_widen_g2_recordings.py` brings it back):

| # | Mutation | Result | Red |
| --- | --- | --- | --- |
| M6 | the КМ positive text made consistent (the same text as the negative) and rebuilt | 5 failed, 41 passed | the seeded-defects test, the key/directory test, the drift test, the recording-keyed-to-the-prompt test, the altered-quote test (the two cases now share one key) |
| M7 | the ОВ negative text made inconsistent (air total 1100 to 1000) | 1 failed, 45 passed | `test_the_negative_text_is_consistent_in_every_relation_the_prompt_checks[OV]` |
| M8 | the ВК trap removed from both texts | 2 failed, 44 passed | `test_every_trap_is_in_the_text_and_a_naive_calculation_would_flag_it[VK-…]` |
| M9 | the ПТ positive recording deleted | 6 failed, 40 passed | the directory test, the keyed-to-prompt test, the replay test, the drift test and others |
| M10 | one digit of a quote changed inside the КМ positive recording | 2 failed, 44 passed | the grounded-replay test, the drift test |
| M11 | the first recorded category of the ОВ positive changed to `documentation` | 3 failed, 43 passed | the keyed-to-prompt test, the grounded-replay test, the drift test |
| M16 | a PT fragment typed with a typo in the test's own table (a real slip of the lane) | 1 failed on the first run | `test_the_prompt_carries_every_fragment_the_lane_added_exactly_once[PT]` |

## Commands and results

All with `BS=$(ls -d /root/projects/PDF-Analysis/.venv/bootstrap/lib/python3*/site-packages)` and `PYTHONPATH=src:$BS .venv/bin/python -m pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider`, one pytest at a time:

| Command | Result |
| --- | --- |
| `tests/unit/analysis/test_text_profile_registry.py` | 35 passed |
| `tests/unit/analysis/text_profiles` (of which `test_prompt_token_guard.py` 111, base 109) | 128 passed |
| `tests/integration/sections/test_section_recordings.py` | 109 passed |
| `tests/contract/analysis_packages` | 52 passed |
| the four above together | **324 passed** (base before any edit: 322; the two new cases are the allowlist entry's) |
| `fixtures/recorded/sections/build_fixtures.py --check` (last, `PYTHONPATH=src python3 -I`) | `fixtures match` |
| `tests/integration/composition/test_analysis_profiles_over_http.py` on the integrator's lane stack, once, with the lane's copy of its `.env` | 4 passed (run at `b91e2022`; the packages and the expectations file it reads are unchanged since) |
| `npx vitest run tests/unit/analysis-settings` in `web/` (`node_modules` symlinked, no `npm ci`) | 7 files, 96 passed |
| `tests/contract/program tests/contract/api_v1/test_doc_prose_facts.py tests/contract/api_v1/test_surface_counts_in_prose.py` on the committed tree | pending |
| `git diff --check` | exit 0, no output |
| the governance one-liner on the task file | `[]` |

## Recordings: what changed

The four routing recordings under `fixtures/recorded/sections/{km,ov,vk,pt}/` were rebuilt by `build_fixtures.py` (the prompt is part of the request, so each key moved); their replies, usage and latency are unchanged. The other ten are byte-identical.

| Section | Key before | Key after | Bundle `content_sha256` after |
| --- | --- | --- | --- |
| КМ | `3d3fb6f0…` | `bf39ab68…` | `70fb237a…` |
| ОВ | `93087ffb…` | `6ddd71ce…` | `df443a6d…` |
| ВК | `7a2b54d0…` | `9b542f7a…` | `9b7c2f9a…` |
| ПТ | `3fadac5b…` | `52b171b8…` | `1dd9243b…` |

## Files

```text
docs/program/SECTION-WIDEN-G2-01.md
docs/program/tasks/SECTION-WIDEN-G2-01.md
fixtures/recorded/sections/km/bf39ab681f910a00f543c3c3c7709fad9319672d03f24ddbda4da9bcbf1f2709.json
fixtures/recorded/sections/ov/6ddd71ce48ec81911c6c79ec849c0404a90d9760e7bb99de77fd0146042dc381.json
fixtures/recorded/sections/pt/52b171b8c2672dfa4f1c5cbe97891a00c44c3a981cf7b2c0cfa526a66c6fc9fa.json
fixtures/recorded/sections/vk/9b542f7ad51a8574406f716c98585ad9b55e3b21532f6d0ee18f797a76a4a748.json
src/auditmanager/analysis/text/profiles/km/profile.json
src/auditmanager/analysis/text/profiles/km/system_prompt.md
src/auditmanager/analysis/text/profiles/ov/profile.json
src/auditmanager/analysis/text/profiles/ov/system_prompt.md
src/auditmanager/analysis/text/profiles/pt/profile.json
src/auditmanager/analysis/text/profiles/pt/system_prompt.md
src/auditmanager/analysis/text/profiles/vk/profile.json
src/auditmanager/analysis/text/profiles/vk/system_prompt.md
tests/unit/analysis/text_profiles/prompt_token_allowlist.json
tests/unit/analysis/text_profiles/section_profile_expectations.json
tests/unit/analysis/text_profiles/test_prompt_token_guard.py
```

## Integration notes

1. **Expectations file.** Four lines moved to `1.2.0`; a conflict with `G1`/`G3` is only in neighbouring lines. Regenerate the four lines from each `profile.json`.
2. **Allowlist.** The `PT`, `3,6` entry is appended after the last entry; keep every group's entries when merging.
3. **The guard test.** The one line of `test_prompt_token_guard.py` is the integration branch's own (`fa7f2ae6`); an identical edit merges cleanly.
4. **Recordings.** Only the four routing recordings of this group changed. After the merge run `fixtures/recorded/sections/build_fixtures.py --check`; it must print `fixtures match`.
5. **Filing the specimens.** Either relax line 97 of `test_section_recordings.py` and extend the builder once for all groups, or restore the sibling directory of `b91e2022` (its builder, eight text layers, eight recordings and the 46-test file) and extend it to the other groups. The specimens in this report are ready for either.
6. **The sentence guard.** `SECTION-PROMPT-SENTENCE-GUARD-01` reads the JSON block above; the check command prints an empty list on this tree.
7. **Register rows to consider** (the lane edits none): the limits below, in particular that nothing here was measured with a model, that the КМ condition is the strict reading, and that PT-2 and VK-2 silence comparisons that 1.1.0 left to the model.

## Limits

- **Nothing was measured.** No model, no real text, no expert (`A-5`, `A-7`); the prompts are longer by 1,5 to 2,2 thousand characters and their effect on cost and on false findings is unknown.
- **The exception is the model's own arithmetic.** The prompt makes every comparison conditional and puts the tolerance in words, but no test can show the model applies it.
- **Table extraction.** The check assumes rows can be told apart in the text layer; for scanned or column-interleaved tables it will be quiet or wrong (assumption 2).
- **The КМ check is deliberately quiet** (D5), and the ВК check covers one of the three flows (D6).
- **The fragment table is documentation until the sentence guard reads it** (M3c).
- **The specimens are not filed** (D1), so no repository test replays them until an integrator lane files them.

## Proof that forbidden paths are untouched

`git diff --name-only 6075df88..HEAD` prints exactly the paths of the table «Files»: the four packages, the four rebuilt recordings (new key files and the removed old ones), two files under `tests/unit/analysis/text_profiles/` that the brief names (the expectations file and the allowlist), the one line of `test_prompt_token_guard.py` (D2) and the two documents of the lane. No file of another section, no contract, migration, web file, `infra/` file, `prompt.py`, `response.py`, `stage.py`, registry, `P02_LOCK.json`, `W59-SECTION-PROFILES-01.md`, `SECTION-REVIEW-LEDGER-01.md`, register or `CURRENT_STATE.md` is in it. `/root/projects/PDF-proverka` was only read: its `HEAD` is the pinned `16ba8e5d…` and `git status --short` there prints nothing.
