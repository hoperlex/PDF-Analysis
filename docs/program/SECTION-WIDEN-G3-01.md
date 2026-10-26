# SECTION-WIDEN-G3-01 — EOM SS ITP GP: the sum-of-rows check added to four prompts, a capacity rule and a unit rule added to two, the omission check refused for three, every topic decided

Task: `docs/program/tasks/SECTION-WIDEN-G3-01.md`. Branch `agent/section-widen-g3-01`, base `d1400994` (`integration/ar-close-1026`, which already contains lane G1's merge). Plan item `PROD-14`; owner rulings `R-146an`, `R-146ag`; accepted risks `A-5`, `A-7`; brief `docs/program/dispatch/PRODUCTION-WAVE-PW4.md` section 6. Format follows `SECTION-WIDEN-G1-01.md` (its method, decision table, specimens and fragment table).

## Result

The gap report (`ROADMAP-GAP-2026-10-27.md` section 2.3) marks eleven topics in these four sections as «reinstatable now». This lane decided each; 19 rows below (some topics split in two, and rule 5 and the unit rule add boundary rows): **W 8, K 2, N 0, X 9**.

- **Widened (W), one check in all four prompts.** `EOM`, `SS`, `ITP` and `GP` carry one paragraph, placed after condition 5, that lets the model add the rows of a table whose total the text itself writes and report `internal_contradiction` when the sum differs beyond the rounding of the written values. It is the same paragraph in the four prompts (a compact reading of lane G1's, about 400 characters shorter); only its scope sentence changes per section, and `SS` has its own basis list (it adds the cable reserve). The exclusion paragraph gets two clauses so that the ban on recalculation keeps this one exception.
- **Two more rules, each with one precondition.** `SS` gets a capacity rule (the number of connected addressable devices written in the text is greater than the capacity written in the text, one direction only) and `ITP` gets a unit rule (one load written in two of Гкал/ч, кВт, МВт is compared after conversion by the definition `1 Гкал/ч = 1,163 МВт = 1163 кВт`). The ITP rule **replaces** the sentence that `SECTION-ITP-FULL-01` (row ITP-1, N) put into the heat-load bullet; the replaced sentence is quoted under «The ledger fragment this lane supersedes».
- **Refused (X) for the omission topic in `EOM`, `SS` and `ITP`**, with the reasons of lane G1's row AI-1 (integrator decision (a)); **refused for** a design-power total (EOM-2), a count the text does not write (SS-4), the pair of notations of a temperature graph (ITP-3, rule 5), a requested value against a selected one (ITP-4), the rows against an unwritten 100 % (GP-3) and against a site area written elsewhere (GP-4).
- `profile_version` is `1.2.0` for `EOM SS ITP GP` (prompt text changed), `status` stays `reviewed`; the four recordings are rebuilt, the four expectations lines moved; the response schema, the two categories, the severity and every contract are untouched. **Three allowlist lines were added, all `ITP`**: the tokens `1,163`, `1163` and `МВт` of the unit rule (integrator decision (c)); each is disclosed by this report.

**`reviewed` carries no human review** (`R-146ag`, `A-7`). Nobody, neither an expert nor the owner, checked any sentence below, and nothing was measured on real text or with a model. The new sentences are the lane's reading of the record, the gap report and the brief's rules.

Premise: **match, with one difference that changes a deliverable and one that enables one** (task file P-01 to P-13). P-07: `tests/integration/sections/test_section_recordings.py` pins exactly one file in each section directory and exactly 14 planned recordings, and neither that test nor the builder is in this lane's allowed paths, so the positive and negative recordings of the brief are kept as specimens in this report, replayed through the real stage (section «Specimens»), as lane G1 did and as integrator decision (b) says; an integrator lane files them later. P-08: the token guard now admits `SECTION-WIDEN-G<n>-01.md` as a disclosure, so the unit-conversion tokens could go into the allowlist.

## Decisions

Quoted wording is the gap report's («Reinstatable now» cell, P-03) and the record's (P-05). «Fragment» ids point at the verbatim table below.

**The omission topics (EOM-4, SS-5, ITP-5) share the reasons of lane G1's row AI-1** (integrator decision (a)): (a) the evidence of every finding of these profiles is the quotes of the places that disagree, and an absence has no quote, so the grounding gate (P-09) would publish a claim that something does not exist as «grounded» without being able to check it; (b) v1 condition 5 says the opposite («Если документ ничего не говорит о чём-то — это не находка») and the category is defined as incompatible values of one attribute; (c) a volume above the one-call budget is analysed in whole-page windows that never see each other (lane `SECTION-CHUNKED-ANALYSIS-01`), where the absence of a row from a list in another window cannot be decided; (d) the identity an omission check needs is the one a `FULL` lane removed (designations repeat). Each row adds its section's own reason.

| # | Section | Topic | Decision | Reason | Exact sentence |
|---|---|---|---|---|---|
| EOM-1 | EOM | The total of the installed power of a load table against the rows it is made of (record q2, first half; gap cell «a load table total against its rows») | **W**, narrowed to the installed power | The total and the rows are written and quoted. Installed power is the sum of the receivers' own figures, so the rule applies; the power values are rounded, so the tolerance sentence applies (rule 1). Receivers marked as reserve or as belonging to another mode (the fire mode) are legally outside the total, so the scope sentence says so (rule 3). | `W-HEAD`, `W-SCOPE-EOM-G3`, `W-TRIGGER`, `W-B1-G3`, `W-B2-G3`, `W-B3-G3`, `W-B4`, `W-B5-G3`, `W-B6`, `W-NOTOTAL`, `W-CONDITIONS-G3`, `W-EVIDENCE-G3`, `W-NORMS-1`, `W-NORMS-2` |
| EOM-2 | EOM | A design power, a current or any value that carries a demand or simultaneity coefficient, against its rows | **X** | A design-power total is formed with a coefficient that the text may or may not state, and a current does not add across phases: the sum is a figure the text does not state (rule 2) and a stated basis may differ (rule 3). The coefficient value cannot be sourced from the five pinned files (decision (d)). Condition 2 already keeps installed and design power apart. | `W-SCOPE-EOM-G3`: «Расчётную мощность, ток и значения с коэффициентом спроса или одновременности не складывай» |
| EOM-3 | EOM | The total of the specification against its rows (record q2, second half «или спецификации») | **K** | The gap cell names the load table only. A specification gives a quantity and a value per unit or a meterage per mark, so a sum would multiply (forbidden by `W-B1-G3`) or add unlike items; the scope sentence does not list it. Nothing to add. | none |
| EOM-4 | EOM | A panel or apparatus named on a scheme and absent from the specification (excluded item 7; record q3) | **X** | The reasons (a) to (d) above. EOM's own: panel and group designations repeat across buildings, sections and floors (`SECTION-EOM-FULL-01` question 4b, N: «Обозначение группы само по себе не делает два упоминания одной и той же группой»), and the excluded item itself reads «без указанного количества — пропуск, а не два несовместимых значения». | none; the omission is not checked |
| SS-1 | SS | A ППКП or loop capacity against the number of connected addressable devices (record q5, second half; gap cell) | **W**, narrowed to written numbers and one direction | Both numbers are written and quoted; counts are exact, so no tolerance is needed. Only «connected greater than capacity» is incompatible; a count below the capacity is a reserve and is not reported. The sentence is the one exception to condition 2, which until now kept capacity and connected count apart. The capacity written on a condition («с резервом», «при использовании») or not provably of the same device is skipped (rule 3). | `W-CAP-SS-G3` |
| SS-2 | SS | The total of the cable journal (length of cable) against its rows (record q5, first half) | **W** | Same paragraph as EOM-1; the length is a rounded value (tolerance sentence); a cable reserve is a stated basis, so the basis sentence of `SS` adds «с запасом» (rule 3). | `W-HEAD`, `W-SCOPE-SS-G3`, `W-TRIGGER`, `W-B1-G3`, `W-B2-G3`, `W-B3-G3`, `W-B4-SS-G3`, `W-B5-G3`, `W-B6`, `W-NOTOTAL`, `W-CONDITIONS-G3`, `W-EVIDENCE-G3`, `W-NORMS-1`, `W-NORMS-2` |
| SS-3 | SS | The total of the specification (number of devices of one kind, length of cable) against its rows | **W** | The same fragments. A specification row that gives a quantity and a unit value is not multiplied (`W-B1-G3`), so most specifications, which carry no total, are silent. | the same fragments |
| SS-4 | SS | The number of connected devices or the capacity of a loop, obtained by counting positions or by multiplying the number of loops by the capacity of one loop | **X** | The count would be a figure the text does not state (rule 2), and a position count read from a text layer of a scheme is exactly the drawing-derived count that the record excludes. | `W-CAP-SS-G3`: «Устройства по позициям не считай, число шлейфов на ёмкость шлейфа не умножай» |
| SS-5 | SS | A list (signals shown at the dispatch point, composition of an access point) that is shorter in one place than in another (record q3; gap cell) | **X** | The reasons (a) to (d) above. SS's own: a list in the general data names systems while a scheme lists points, so a shorter list is often by design; the record asks the very question whether it is a contradiction or an incompleteness, and condition 5 answers «incompleteness» for v1. | none |
| ITP-1 | ITP | The same load of one object written in Гкал/ч, кВт or МВт in two places (record q1; gap cell) | **W** | Rule 4: the conversion `1 Гкал/ч = 1,163 МВт = 1163 кВт` is a definition of units, not a norm (task P-12: the pinned source holds neither the units nor the factor, so the allowlist takes `1,163`, `1163` and `МВт`). Both values must be written with their unit and relate to one load (conditions 1 to 4 apply); the difference after conversion must exceed the summed rounding of both values in the common unit; the model converts and checks by the reverse conversion. This **replaces** the N sentence of `SECTION-ITP-FULL-01` ITP-1, which stopped the comparison for lack of a source for the factor. | `W-UNITS-REF-ITP-G3`, `W-UNITS-ITP-G3`, `W-NORMS-1-ITP-G3`, `W-NORMS-2-ITP-G3` |
| ITP-2 | ITP | One load written in two units of which one is not Гкал/ч, кВт or МВт (for example Вт, ккал/ч, ГДж/ч) | **K** (the behaviour of the replaced N sentence stays for these pairs) | The prompt carries no factor for them (rule 4 names the two definitions only), so the pair is not compared. | `W-UNITS-ITP-G3`: «Значения в других единицах не сравнивай.» |
| ITP-3 | ITP | «150/70 со срезкой на 130» and «130/70» as one temperature graph (record q2; gap cell «conditional») | **X** | Rule 5: whether the two notations are one graph is a domain equivalence that no pinned file states (task P-05 of `SECTION-ITP-FULL-01`: `срезка` and `150/70` occur in none of them). `SECTION-ITP-FULL-01` ITP-2 (K) stands; under v1 both quotes are shown to the reviewer. | none |
| ITP-4 | ITP | A requested value (questionnaire, calculation table) against the selected one (specification) for the exchanger and the pump (excluded item 15; record q3; gap cell) | **X** | (i) The two differ by design: a selection carries a margin, and the record excludes exactly that judgement («запас мощности», «соответствие расхода и напора расчётным значениям»). (ii) The only comparison that needs no margin is one-sided, and its direction differs by attribute (power, flow and head must not fall below the request; a pressure drop must not exceed it): that is an expert's rule the text does not state (rule 2). (iii) Parallel units («2 по 50 %») and the operating point change the comparison, and the figure per unit may not be written. (iv) A tolerance that would make it conservative is a number that cannot be sourced (decision (d)). Condition 2's pair (design load and nominal power) stays. | none |
| ITP-5 | ITP | A scheme item with no specification row, and the reverse (excluded item 13) | **X** | The reasons (a) to (d) above. ITP's own: valves, filters and sensors are designated per circuit and repeat on the principal scheme, and the excluded item itself reads «отсутствие позиции не два несовместимых значения (v1, условие 5)». | none |
| ITP-6 | ITP | The total of the heat loads against the sum of the loads by circuit (record q5; gap cell «a loads total against its circuits») | **W** | The total and the circuit loads are written and quoted. The pinned source's own example (task P-12) writes the total as the sum of the three circuits (850 + 420 + 180 = 1450 kW), the only support the source gives. Basis (rule 3): the hot-water load enters a total by its maximum or its hourly-average value (condition 2 names the pair), so if both are written and the text does not say which is in the total, nothing is reported. Units must be the same: no conversion inside a sum. | `W-HEAD`, `W-SCOPE-ITP-G3`, `W-TRIGGER`, `W-B1-G3`, `W-B2-G3`, `W-B3-G3`, `W-B4`, `W-B5-G3`, `W-B6`, `W-NOTOTAL`, `W-CONDITIONS-G3`, `W-EVIDENCE-G3`, `W-NORMS-1-ITP-G3`, `W-NORMS-2-ITP-G3` |
| GP-1 | GP | The rows of a land balance (areas) against the written total of the same table (record q1; gap cell «against the site area») | **W**, narrowed to the table's own total | The total and the rows are written and quoted; an area is a rounded value (tolerance sentence). The «site area» is the table's last row («Итого», «Всего» or «Площадь участка»); `SECTION-GP-FULL-01` GP-2 (N) made the site area and the area within the landscaping or design boundary different attributes, so a figure of another boundary is never compared with the table's total. | `W-HEAD`, `W-SCOPE-GP-G3`, `W-TRIGGER`, `W-B1-G3`, `W-B2-G3`, `W-B3-G3`, `W-B4`, `W-B5-G3`, `W-B6`, `W-NOTOTAL`, `W-CONDITIONS-G3`, `W-EVIDENCE-G3`, `W-NORMS-1`, `W-NORMS-2` |
| GP-2 | GP | The shares of a land balance (percent) against the total of shares that the table writes (gap cell «against 100 %»; record q1) | **W**, narrowed to a total the text writes | The rows are shares and the total of shares is written in the same table; the prompt compares the two written figures and imports no figure (the numeral for 100 is not in the prompt). | the same fragments |
| GP-3 | GP | The same shares compared with 100 % when the table writes no total of shares | **X** | The figure is not in the text (rule 2) and, as lane G1 decided for POS-2, a prompt that supplied it would import a number. | `W-SCOPE-GP-G3`: «итог, которого в таблице нет, не подставляй»; `W-NOTOTAL` |
| GP-4 | GP | The rows compared with a site area that the text writes elsewhere (technical-economic indicators, general data) or for other boundaries (ГПЗУ, landscaping, design) | **X** | The same-attribute comparison of the site area across places is v1's own question (K, `SECTION-GP-FULL-01` GP-1); the area of another boundary is a different attribute (GP-2 N, condition 2). The balance rows are compared only with the total of their own table. | `W-SCOPE-GP-G3`: «Площадь, которую текст относит к другим границам (благоустройства, проектирования), с итогом не сравнивай» |

The unit-conversion factors of rule 4 are used once, in the ITP rule; `EOM`, `SS` and `GP` have no quantity stated in two units among their decided topics. No factor, norm or threshold stands in any other prompt, and the numerals of the added text are `1` and `4` (in «Условия 1–4») in all four, `2` in SS («условия 2») and, in the ITP unit rule, `1`, `1,163` and `1163`.

### How each of the brief's rules shows in the sentences

| Rule | Where it stands |
|---|---|
| (1) both figures written, tolerance in words | `W-B1-G3` (written explicitly, same units, one column), `W-B3-G3` (every row visible, also at a window or page boundary), `W-B5-G3` (counts exact; otherwise half a unit of the last written digit per value, summed over the addends and the total), `W-CAP-SS-G3` (both numbers written), `W-UNITS-ITP-G3` (the same tolerance, in the common unit) |
| (2) never recompute from an unstated figure | `W-NOTOTAL`, `W-B1-G3` (no value per unit, no product), `W-SCOPE-EOM-G3` (no design power), `W-CAP-SS-G3` (no count of positions, no loops times capacity), `W-SCOPE-GP-G3` (no imported total), `W-B6` (add twice), `W-UNITS-ITP-G3` (convert twice) |
| (3) legal overlap or stated basis | `W-B2-G3` («в том числе», «из них», subtotals), `W-B4` and `W-B4-SS-G3` («с учётом», «без учёта», «включая», «за исключением», «с запасом», coefficient), `W-SCOPE-EOM-G3` (reserve and another mode), `W-SCOPE-ITP-G3` (maximum and hourly-average hot-water load), `W-CAP-SS-G3` (a condition on the capacity) |
| (4) conversion factors only | the ITP unit rule; `1,163`, `1163` and `МВт` in the allowlist; nothing else |
| (5) equivalent notations stay excluded | ITP-3; nothing in the prompts equates two notations |
| (6) every topic decided | the table above |

## The prompt change in words

For each of `EOM`, `SS`, `ITP`, `GP`: (1) a new paragraph between condition 5 and the exclusion paragraph. It says the only addition the model may do is adding the rows of a table whose total the text writes; names the scope (a sentence per section); says to report `internal_contradiction` only when six things hold (same units, object and column and no per-unit or computed value; only the parts of the total, no «в том числе» lines and no subtotal added to its own rows; every row visible; no different stated basis; the difference exceeds the rounding of the written values; the rows were added twice with the same sum); says to add nothing when the text writes no total; says conditions 1 to 4 still apply; and asks for the quote of the total and of the rows as evidence, with the written total, the sum and the number of rows in `finding_text`. (2) The exclusion paragraph keeps its sentence but now says the ban on recalculation holds «кроме сложения строк по правилу выше» (ITP: «кроме сложения строк и перевода единиц по правилам выше»), and that what is compared is the written values and the sum of rows added by the rule (ITP: and the conversion). Nothing else moved: with the inserted paragraph(s), the exclusion clauses and (in ITP) the replaced bullet sentence reverted, the whitespace-normalised prompt equals the base prompt in all four sections (checked), and v1's question, categories, conditions headings and output contract are held by the package test.

| Section | What is specific | Prompt size |
|---|---|---|
| EOM | the scope sentence: installed power of a load table; reserve and fire-mode receivers outside the total; design power, current and coefficient-bearing values not added | 5,062 to 7,456 characters (+2,394) |
| SS | the scope sentence: the totals of the cable journal and of the specification; the basis sentence adds «с запасом»; a second paragraph after the first: the capacity rule (one exception to condition 2) | 6,491 to 9,298 (+2,807) |
| ITP | the scope sentence: the total heat load against the loads by circuit, with the hot-water basis; the heat-load bullet now ends «сравнивай только по правилу о единицах ниже» in place of the narrowing sentence; a second paragraph: the unit rule with the definition; the two exclusion clauses name the conversion too | 6,190 to 9,017 (+2,827) |
| GP | the scope sentence: the land balance, its areas against the total of areas and its shares against the total of shares; no imported total; areas of other boundaries and rows of different stages not mixed | 6,434 to 8,932 (+2,498) |

Lane G1 added 2,701 to 2,834 characters per prompt; this lane's four additions are 2,394 to 2,827. `AI`, `PS`, `POS`, `TX`, `KJ` and the nine other sections are untouched.

New numerals in the prompts: none besides the ITP unit rule (`1`, `1,163`, `1163`). New norm references: none. New class designations: none. New categories, fields, severities: none.

## Added fragments, verbatim

Whitespace-normalised: a fragment is the prompt text with every run of whitespace, line breaks included, replaced by one space. A fragment is checked against the prompt normalised the same way. The block is machine-readable (the format of the `SECTION-WIDEN-G1-01` block) so that `SECTION-PROMPT-SENTENCE-GUARD-01` can read it; 23 fragments, 59 (fragment, section) pairs. The ids that lane G1's table also carries (`W-HEAD`, `W-TRIGGER`, `W-B4`, `W-B6`, `W-NOTOTAL`, `W-NORMS-1`, `W-NORMS-2`) are byte-identical to G1's; every id with the suffix `-G3` is this lane's own wording.

| Fragment | Sections | Role |
|---|---|---|
| `W-HEAD` | EOM, SS, ITP, GP | rule: the only permitted addition |
| `W-SCOPE-EOM-G3` | EOM | scope: which totals may be added |
| `W-TRIGGER` | EOM, SS, ITP, GP | category: the existing internal_contradiction |
| `W-B1-G3` | EOM, SS, ITP, GP | conservative rule 2: only written values, one column, no unit values, no products |
| `W-B2-G3` | EOM, SS, ITP, GP | conservative rule 3: parts of the total only; subtotals |
| `W-B3-G3` | EOM, SS, ITP, GP | conservative rule 1: all rows visible (also at a window boundary) |
| `W-B4` | EOM, ITP, GP | conservative rule 3: the stated basis |
| `W-B5-G3` | EOM, SS, ITP, GP | conservative rule 1: tolerance in words |
| `W-B6` | EOM, SS, ITP, GP | double addition |
| `W-NOTOTAL` | EOM, SS, ITP, GP | conservative rule 2: no written total, no check |
| `W-CONDITIONS-G3` | EOM, SS, ITP, GP | the existing conditions still apply |
| `W-EVIDENCE-G3` | EOM, SS, ITP, GP | evidence: the total and the rows |
| `W-NORMS-1` | EOM, SS, GP | exclusion sentence: calculation ban, one exception |
| `W-NORMS-2` | EOM, SS, GP | exclusion sentence: what is compared |
| `W-SCOPE-SS-G3` | SS | scope: which totals may be added |
| `W-B4-SS-G3` | SS | conservative rule 3: the stated basis (cable reserve added) |
| `W-CAP-SS-G3` | SS | SS: capacity against the written count of connected addressable devices (one direction) |
| `W-SCOPE-ITP-G3` | ITP | scope: which totals may be added |
| `W-UNITS-REF-ITP-G3` | ITP | ITP: the heat-load bullet defers to the unit rule |
| `W-UNITS-ITP-G3` | ITP | ITP: the same load in Гкал/ч, кВт, МВт, converted by the definition |
| `W-NORMS-1-ITP-G3` | ITP | exclusion sentence: calculation ban, two exceptions |
| `W-NORMS-2-ITP-G3` | ITP | exclusion sentence: what is compared |
| `W-SCOPE-GP-G3` | GP | scope: which totals may be added |

<!-- fragments:begin -->
```json
[
 {
  "id": "W-HEAD",
  "sections": [
   "EOM",
   "SS",
   "ITP",
   "GP"
  ],
  "role": "rule: the only permitted addition",
  "text": "Единственное сложение, которое тебе разрешено, — сложение строк, из которых текст сам составляет записанный в нём итог."
 },
 {
  "id": "W-SCOPE-EOM-G3",
  "sections": [
   "EOM"
  ],
  "role": "scope: which totals may be added",
  "text": "Здесь это установленная мощность: записанный итог («Итого», «Всего» или подобная строка) таблицы нагрузок и строки электроприёмников, групп или линий, из которых он составлен. Приёмники, помеченные как резервные или как относящиеся к другому режиму работы (например, противопожарному), в сумму не входят. Расчётную мощность, ток и значения с коэффициентом спроса или одновременности не складывай, другие итоги не складывай."
 },
 {
  "id": "W-TRIGGER",
  "sections": [
   "EOM",
   "SS",
   "ITP",
   "GP"
  ],
  "role": "category: the existing internal_contradiction",
  "text": "Если сумма строк расходится с записанным итогом, сообщи internal_contradiction, но только когда выполнено всё перечисленное:"
 },
 {
  "id": "W-B1-G3",
  "sections": [
   "EOM",
   "SS",
   "ITP",
   "GP"
  ],
  "role": "conservative rule 2: only written values, one column, no unit values, no products",
  "text": "итог и каждая складываемая строка записаны в тексте явно, в одних единицах измерения, для одного объекта и признака; складываются значения одного столбца, записанные именно для строки; значение на единицу и значение, которого в строке нет и которое пришлось бы вычислять (в том числе умножением количества на значение единицы), в сумму не входят;"
 },
 {
  "id": "W-B2-G3",
  "sections": [
   "EOM",
   "SS",
   "ITP",
   "GP"
  ],
  "role": "conservative rule 3: parts of the total only; subtotals",
  "text": "в сумму входят только строки, из которых итог составлен по смыслу таблицы; строки «в том числе», «из них», «справочно» и строки другого варианта в сумму не входят; промежуточный итог не складывай со своими строками;"
 },
 {
  "id": "W-B3-G3",
  "sections": [
   "EOM",
   "SS",
   "ITP",
   "GP"
  ],
  "role": "conservative rule 1: all rows visible (also at a window boundary)",
  "text": "все строки читаются в переданном тексте: если часть строк оборвана (в том числе на последней переданной странице), оторвана от подписей или заменена многоточием либо словами «прочие» и «и другие» без значения, не сообщай;"
 },
 {
  "id": "W-B4",
  "sections": [
   "EOM",
   "ITP",
   "GP"
  ],
  "role": "conservative rule 3: the stated basis",
  "text": "если в тексте названо основание, на котором записан итог или строка («с учётом», «без учёта», «включая», «за исключением», коэффициент), а итог и строки записаны на разных основаниях, не сообщай;"
 },
 {
  "id": "W-B5-G3",
  "sections": [
   "EOM",
   "SS",
   "ITP",
   "GP"
  ],
  "role": "conservative rule 1: tolerance in words",
  "text": "расхождение больше погрешности округления: количества записаны точно, любое расхождение в них — находка; у остальных значений погрешность — половина единицы последнего записанного разряда, погрешность сравнения — сумма таких погрешностей слагаемых и итога;"
 },
 {
  "id": "W-B6",
  "sections": [
   "EOM",
   "SS",
   "ITP",
   "GP"
  ],
  "role": "double addition",
  "text": "ты сложил строки дважды, в прямом и в обратном порядке, и получил одну и ту же сумму."
 },
 {
  "id": "W-NOTOTAL",
  "sections": [
   "EOM",
   "SS",
   "ITP",
   "GP"
  ],
  "role": "conservative rule 2: no written total, no check",
  "text": "Если итог в тексте не записан, ничего не складывай."
 },
 {
  "id": "W-CONDITIONS-G3",
  "sections": [
   "EOM",
   "SS",
   "ITP",
   "GP"
  ],
  "role": "the existing conditions still apply",
  "text": "Условия 1–4 выше применяются и к такому расхождению."
 },
 {
  "id": "W-EVIDENCE-G3",
  "sections": [
   "EOM",
   "SS",
   "ITP",
   "GP"
  ],
  "role": "evidence: the total and the rows",
  "text": "В evidence приведи цитату итога и цитаты складываемых строк (при числе строк больше десяти — итога, первой и последней); в finding_text назови записанный итог, сумму и число строк."
 },
 {
  "id": "W-NORMS-1",
  "sections": [
   "EOM",
   "SS",
   "GP"
  ],
  "role": "exclusion sentence: calculation ban, one exception",
  "text": "кроме сложения строк по правилу выше,"
 },
 {
  "id": "W-NORMS-2",
  "sections": [
   "EOM",
   "SS",
   "GP"
  ],
  "role": "exclusion sentence: what is compared",
  "text": "и сумма строк, сложенных по правилу выше."
 },
 {
  "id": "W-SCOPE-SS-G3",
  "sections": [
   "SS"
  ],
  "role": "scope: which totals may be added",
  "text": "Здесь это записанный итог кабельного журнала или спецификации (общая длина кабеля, общее количество устройств одного вида) и строки (линии, марки, позиции), из которых он составлен. Другие итоги не складывай."
 },
 {
  "id": "W-B4-SS-G3",
  "sections": [
   "SS"
  ],
  "role": "conservative rule 3: the stated basis (cable reserve added)",
  "text": "если в тексте названо основание, на котором записан итог или строка («с учётом», «без учёта», «включая», «за исключением», «с запасом», коэффициент), а итог и строки записаны на разных основаниях, не сообщай;"
 },
 {
  "id": "W-CAP-SS-G3",
  "sections": [
   "SS"
  ],
  "role": "SS: capacity against the written count of connected addressable devices (one direction)",
  "text": "Единственное исключение из условия 2: если текст явно записывает ёмкость приёмно-контрольного прибора или шлейфа (число адресных устройств, на которое он рассчитан) и явно записывает число адресных устройств, подключённых к тому же прибору или шлейфу, и это число больше ёмкости, сообщи internal_contradiction, приведя цитаты обоих чисел. Число не больше ёмкости — запас, а не расхождение. Устройства по позициям не считай, число шлейфов на ёмкость шлейфа не умножай; если ёмкость записана на условии («с резервом», «при использовании») или неясно, что оба числа относятся к одному прибору или шлейфу, не сообщай."
 },
 {
  "id": "W-SCOPE-ITP-G3",
  "sections": [
   "ITP"
  ],
  "role": "scope: which totals may be added",
  "text": "Здесь это тепловые нагрузки: записанная суммарная нагрузка и нагрузки по контурам (отопление, вентиляция, ГВС), из которых она составлена. Если для ГВС записаны максимальная и среднечасовая нагрузки, а текст не называет, какая входит в суммарную, не сообщай. Другие итоги не складывай."
 },
 {
  "id": "W-UNITS-REF-ITP-G3",
  "sections": [
   "ITP"
  ],
  "role": "ITP: the heat-load bullet defers to the unit rule",
  "text": "значения одной нагрузки, записанные в разных единицах измерения, сравнивай только по правилу о единицах ниже;"
 },
 {
  "id": "W-UNITS-ITP-G3",
  "sections": [
   "ITP"
  ],
  "role": "ITP: the same load in Гкал/ч, кВт, МВт, converted by the definition",
  "text": "Единственный разрешённый перевод единиц — для тепловой нагрузки одного объекта, записанной в двух местах в Гкал/ч, кВт или МВт: переведи обе записи в одну единицу по определению 1 Гкал/ч = 1,163 МВт = 1163 кВт; проверь обратным пересчётом. Сообщай internal_contradiction, только когда оба значения записаны явно с единицей, текст относит их к одной нагрузке (условия 1–4 выше применяются), а разность после перевода больше суммы погрешностей округления обоих значений (половина единицы последнего записанного разряда каждого, в той же единице). Значения в других единицах не сравнивай."
 },
 {
  "id": "W-NORMS-1-ITP-G3",
  "sections": [
   "ITP"
  ],
  "role": "exclusion sentence: calculation ban, two exceptions",
  "text": "кроме сложения строк и перевода единиц по правилам выше,"
 },
 {
  "id": "W-NORMS-2-ITP-G3",
  "sections": [
   "ITP"
  ],
  "role": "exclusion sentence: what is compared",
  "text": "а также сумма строк и перевод единиц, выполненные по правилам выше."
 },
 {
  "id": "W-SCOPE-GP-G3",
  "sections": [
   "GP"
  ],
  "role": "scope: which totals may be added",
  "text": "Здесь это баланс территории: записанный итог («Итого», «Всего» или строка площади участка в конце той же таблицы) и строки позиций (застройка, твёрдые покрытия, озеленение и подобные), из которых он составлен, — площади или доли в процентах. Площади сравнивай с итогом площадей, доли — с записанным итогом долей; итог, которого в таблице нет, не подставляй. Площадь, которую текст относит к другим границам (благоустройства, проектирования), с итогом не сравнивай; строки разных очередей не смешивай. Другие итоги не складывай."
 }
]
```
<!-- fragments:end -->

Check (prints the fragments missing from the prompts of this tree; the expected answer is an empty list):

```text
F=$(python3 -I -c "print(chr(96)*3)"); python3 -I -c "import json,re,sys;f=sys.argv[1];t=open('docs/program/SECTION-WIDEN-G3-01.md',encoding='utf-8').read();fr=json.loads(re.search('<!-- fragments:begin -->\\\\s*'+f+'json\\n(.*?)\\n'+f+'\\\\s*<!-- fragments:end -->',t,re.S).group(1));n=lambda s:' '.join(s.split());bad=[(x['id'],c) for x in fr for c in x['sections'] if x['text'] not in n(open('src/auditmanager/analysis/text/profiles/'+c.lower()+'/system_prompt.md',encoding='utf-8').read())];print(len(fr),'fragments; missing',bad)" "$F"
```

### The ledger fragment this lane supersedes

`SECTION-REVIEW-LEDGER-01.md` lists, for `ITP`, the N decision ITP-1: it **adds** the sentence below to the heat-load bullet. `SECTION-PROMPT-SENTENCE-GUARD-01` will read that ledger table; the ITP prompt no longer carries the sentence, so the guard lane must treat the row as superseded by `W-UNITS-REF-ITP-G3` and `W-UNITS-ITP-G3`, or it will be red.

| Ledger row | Sentence removed from the `ITP` prompt (verbatim) | Replaced by |
|---|---|---|
| ITP-1 (N) | значения одной нагрузки, записанные в разных единицах измерения, между собой не сравнивай: пересчёт единиц и округление при нём — вычисление, которого ты не выполняешь; | `W-UNITS-REF-ITP-G3`: значения одной нагрузки, записанные в разных единицах измерения, сравнивай только по правилу о единицах ниже; |

## Assumptions an expert would still want to check

Short and honest (`A-7`): none of these was checked by anyone with domain knowledge.

1. **Whether a model should add at all.** The gap report calls a sum «a deterministic check» that «a model must not do» (class E2). The owner ordered the widening anyway (`R-146an`), so this lane keeps the addition behind six conditions; the only guard on the model's arithmetic is the instruction to add twice (to convert twice in the ITP rule), and it is unmeasured.
2. **The tolerance.** Half a unit of the last written digit per value, summed over the addends and the total, is the worst case of rounding. In a long table the allowance grows (forty rows at one decimal allow about two units), so a real small discrepancy in a long table is not reported. Shares written to one decimal in a balance of six positions allow 0,35 percentage points. Counts are called exact; a count written as «около» or «не менее» is not, and the prompt does not say so.
3. **Which line is a total.** «Итого», «Всего» «или подобная строка» is left to the model; a line such as «Общее количество» or «Сумма» may or may not be taken for one. For `GP` the total is also «строка площади участка в конце той же таблицы»: a balance table that puts «Площадь участка» first, or elsewhere than at the end, is not checked against it.
4. **EOM.** Real load tables mix installed-power and design-power columns, and the total row often carries a design figure with a coefficient; the model must tell the columns apart, and the scope sentence cannot show which column is meant. The words «резервные», «другому режиму работы» and «противопожарному» are the lane's, not the pinned source's (the source holds none of «установленная», «приёмник», «резерв» in this sense, «противопожар» or «спроса»). A genuine error in a design-power total is deliberately not reported (EOM-2).
5. **SS.** A ППКП's capacity is often given per loop and the connected devices per type («извещатели 250, модули 40»), so the typical overload is found only when the document writes one number for the devices connected to one panel or loop; the rule never adds or multiplies. «Адресных» and «с резервом» come from the record and the lane, not from the five files (they hold «адресн», «резерв» but not «подключённых»). The cable reserve «с запасом» as a stated basis is the lane's word (the source holds no «запас»).
6. **ITP.** The factor `1 Гкал/ч = 1,163 МВт = 1163 кВт` is the standard definition (exact for the International Table calorie) and the integrator's rule 4 allows it; no pinned file states it (P-12). With the summed-rounding tolerance a pair such as 1,2 Гкал/ч and 1,5 МВт (difference 0,104 МВт against an allowance of 0,108) passes as consistent: the rule misses real small differences between values written with few digits. Spellings other than «Гкал/ч», «кВт», «МВт» («Гкал/час», «Гкал в час») are left to the model, and a unit outside the three stays uncompared.
7. **ITP totals.** The hot-water basis sentence covers maximum against hourly-average load only; a total that also includes losses, a floor-heating circuit the table lists, or a circuit that the text excludes by a phrase other than the listed bases can give a false finding. The only support in the pinned source is a template value.
8. **ITP-4 and the omission refusals lose real classes.** A selected pump or exchanger below the requested value is a common finding of a human reviewer, and so is a panel, an item or a list entry missing from a specification (EOM-4, SS-5, ITP-5). This lane leaves them to the expert.
9. **GP.** A balance table may carry «в том числе» lines (underground built-up area, paved parking inside the covered area), and the model must keep them out of the sum; stages («очереди») in one table are told apart only by the sentence that rows of different stages are not mixed. The area of a ГПЗУ boundary appears beside the table and is not compared (GP-4).
10. **Evidence.** For more than ten rows the model quotes the total, the first and the last row, so the expert reads the middle of the table to confirm the sum.
11. **Vocabulary not from the five pinned files.** «Итого», «Всего», «электроприёмников», «режиму работы», «приёмно-контрольного», «подключённых», «запасом», «максимальная», «среднечасовая» (already in condition 2 of ITP), «очередей» (already in GP), «твёрдые покрытия» (one occurrence in the GP source) and the object lists of the scope sentences are the lane's words; the token guard does not check ordinary words.
12. **Nothing was measured.** The four replaced recordings are still the hand-authored replies over the АР corpus; they prove routing and replay. The specimens below are hand-authored too.

## Token-guard additions

Three append-only entries in `tests/unit/analysis/text_profiles/prompt_token_allowlist.json`, all `ITP`, all `disclosed_by` `SECTION-WIDEN-G3-01.md` (integrator decision (c); the guard test already admits that pattern, `fa7f2ae6`). The guard checks that this report contains each token, so each is named here:

| Token | Class | Where it stands | Why it is needed |
|---|---|---|---|
| `1,163` | a (digit) | the ITP unit rule `W-UNITS-ITP-G3`: megawatts per Гкал/ч | a unit-conversion definition, not a norm (rule 4); none of the five pinned ITP files holds a factor (P-12) |
| `1163` | a (digit) | the same sentence: kilowatts per Гкал/ч | the same |
| `МВт` | abbreviation | the same sentence and `W-UNITS-ITP-G3`'s «Гкал/ч, кВт или МВт» | the pinned files hold `кВт` (four times) but not `МВт` |

`Гкал` is an ordinary word for the guard (one capital letter) and `кВт` is sourced, so neither needed a line. `EOM`, `SS` and `GP` needed none: the guard passes against the pinned source with no new line for them (their added text has the numerals `1`, `2` and `4` of v1 only). Without the three lines the guard is red for `ITP` (`ITP: designation(s) ['1,163', '1163', 'МВт'] are whole tokens of none of the five pinned legacy files, of v1's prompt, or of prompt_token_allowlist.json`, 4 cases), and rows M9 to M11 below show it red again when a line or this report's mention is removed.

## Recordings: what changed

For each of EOM, SS, ITP, GP the new file differs from the old in `origin.prompt_bundle_sha256` and `request_sha256` only; the authored reply, usage and latency are unchanged (the reply is still the AR-corpus reply of `SECTION-RECORDINGS-01`). The other ten recordings are byte-identical after the builder runs (`git status` lists four deleted and four new files under `fixtures/recorded/sections/`).

| Section | Old file | New file | Bundle hash |
|---|---|---|---|
| EOM | `966f4f6f…8098` | `22dee872…f1d2` | `5bd11060` to `10e6fc2e` |
| SS | `dd6ccee8…70fa` | `f032738f…712e` | `3256b21c` to `46cc1ef7` |
| ITP | `b9b9d6a8…953b` | `c3e8bd56…f203` | `352c5a07` to `09e21dad` |
| GP | `9dbe139a…b959` | `414d336d…5165` | `fab79a6b` to `1d63b742` |

## Specimens

One or more positive and negative texts per widened rule, with the hand-authored reply a model would give: `EOM` one positive and one negative; `SS` a positive and a negative for the cable-journal total and for the capacity rule; `ITP` a positive and a negative for the unit rule and for the loads total; `GP` a positive for the areas and one for the shares, and two negatives (an area of another boundary beside the table; shares with no written total). They were replayed through the real stage (`run_text_analysis`) with the section's own profile and a throw-away recorded directory in the session scratchpad; they are **not** committed as fixtures (premise P-07, integrator decision (b)). Every positive reply opens its `finding_text` with «Синтетический ответ (<раздел>), не результат вызова модели», as the existing recordings do. Every negative text holds a trap that the intended answer leaves alone: a reserve or fire-mode receiver and a design power with a coefficient (EOM); a total «с запасом» (SS); a capacity on a condition and a connected count below the capacity (SS); the same load in 1,2 Гкал/ч and 1396 кВт (ITP, equal after conversion); both hot-water loads written and a total on the hourly-average one (ITP); an area of the improvement boundary beside a consistent table, and shares with no total (GP).

| Section | Case | Proposed | Emitted | Evidence unresolved |
|---|---|---|---|---|
| EOM | positive (15,0 kW against 13,7 kW) | 1 | 1 | 0 |
| EOM | negative (a fire-mode pump outside the total; a design power with a coefficient) | 0 | 0 | 0 |
| EOM | positive with one altered quote | 1 | 1 | 1 |
| SS | cable journal, positive (460 m against 445 m) | 1 | 1 | 0 |
| SS | cable journal, negative (a total «с запасом») | 0 | 0 | 0 |
| SS | cable journal, positive with one altered quote | 1 | 1 | 1 |
| SS | capacity, positive (250 against 280 connected) | 1 | 1 | 0 |
| SS | capacity, negative (240 connected; a capacity on a condition) | 0 | 0 | 0 |
| SS | capacity, positive with one altered quote | 1 | 1 | 1 |
| ITP | units, positive (1,2 Гкал/ч against 1,8 МВт) | 1 | 1 | 0 |
| ITP | units, negative (1,2 Гкал/ч and 1396 кВт) | 0 | 0 | 0 |
| ITP | units, positive with one altered quote | 1 | 1 | 1 |
| ITP | total, positive (1500 kW against 1450 kW) | 1 | 1 | 0 |
| ITP | total, negative (both hot-water loads written) | 0 | 0 | 0 |
| ITP | total, positive with one altered quote | 1 | 1 | 1 |
| GP | areas, positive (12000 against 11800) | 1 | 1 | 0 |
| GP | areas, positive with one altered quote | 1 | 1 | 1 |
| GP | shares, positive (100,0 against 98,4) | 1 | 1 | 0 |
| GP | shares, positive with one altered quote | 1 | 1 | 1 |
| GP | negative (an area of another boundary beside a consistent table) | 0 | 0 | 0 |
| GP | negative (shares with no written total) | 0 | 0 | 0 |

The altered-quote rows are the mutation of this check: a quote that is not verbatim leaves the evidence unresolved, and the grounding gate would then refuse the finding. What these rows do **not** show: that a model gives these answers, or that a model leaves the traps alone. The negatives prove only that an empty reply is accepted by the stage.

```json
{
 "EOM": {
  "positive": {
   "pages": [
    "Щит ЩР-1. Таблица нагрузок (вымышленный пример для проверки профиля)\nОсвещение — установленная мощность 4,2 кВт\nРозеточная сеть — установленная мощность 6,0 кВт\nВентиляция — установленная мощность 3,5 кВт\nИтого по щиту ЩР-1 — установленная мощность 15,0 кВт",
    "Общие данные. Категория надёжности электроснабжения — третья."
   ],
   "observations": [
    {
     "category": "internal_contradiction",
     "finding_text": "Синтетический ответ (ЭОМ), не результат вызова модели: итог установленной мощности щита ЩР-1 записан как 15,0 кВт, а три строки таблицы нагрузок дают 13,7 кВт.",
     "recommendation_text": "Свести итог установленной мощности щита ЩР-1 и строки таблицы нагрузок к одному значению.",
     "evidence": [
      {
       "page_number": 1,
       "quote": "Итого по щиту ЩР-1 — установленная мощность 15,0 кВт"
      },
      {
       "page_number": 1,
       "quote": "Освещение — установленная мощность 4,2 кВт"
      },
      {
       "page_number": 1,
       "quote": "Розеточная сеть — установленная мощность 6,0 кВт"
      },
      {
       "page_number": 1,
       "quote": "Вентиляция — установленная мощность 3,5 кВт"
      }
     ]
    }
   ]
  },
  "negative": {
   "pages": [
    "Щит ЩР-1. Таблица нагрузок (вымышленный пример для проверки профиля)\nОсвещение — установленная мощность 4,2 кВт\nРозеточная сеть — установленная мощность 6,0 кВт\nВентиляция — установленная мощность 3,5 кВт\nНасос пожаротушения (противопожарный режим) — установленная мощность 11,0 кВт\nИтого по щиту ЩР-1 в нормальном режиме — установленная мощность 13,7 кВт\nРасчётная мощность щита с коэффициентом спроса — 9,6 кВт",
    "Общие данные. Категория надёжности электроснабжения — третья."
   ],
   "observations": []
  }
 },
 "SS": {
  "journal_positive": {
   "pages": [
    "Кабельный журнал системы СКУД (вымышленный пример для проверки профиля)\nЛиния Л1 — длина 120 м\nЛиния Л2 — длина 85 м\nЛиния Л3 — длина 240 м\nИтого длина кабеля — 460 м",
    "Общие указания. Кабель — витая пара, категория 6."
   ],
   "observations": [
    {
     "category": "internal_contradiction",
     "finding_text": "Синтетический ответ (СС), не результат вызова модели: итог кабельного журнала записан как 460 м, а три строки линий дают 445 м.",
     "recommendation_text": "Согласовать итоговую длину кабеля и длины линий кабельного журнала.",
     "evidence": [
      {
       "page_number": 1,
       "quote": "Итого длина кабеля — 460 м"
      },
      {
       "page_number": 1,
       "quote": "Линия Л1 — длина 120 м"
      },
      {
       "page_number": 1,
       "quote": "Линия Л2 — длина 85 м"
      },
      {
       "page_number": 1,
       "quote": "Линия Л3 — длина 240 м"
      }
     ]
    }
   ]
  },
  "journal_negative": {
   "pages": [
    "Кабельный журнал системы СКУД (вымышленный пример для проверки профиля)\nЛиния Л1 — длина 120 м\nЛиния Л2 — длина 85 м\nЛиния Л3 — длина 240 м\nИтого длина кабеля с запасом — 490 м",
    "Общие указания. Кабель — витая пара, категория 6."
   ],
   "observations": []
  },
  "capacity_positive": {
   "pages": [
    "Пояснительная записка. Система пожарной сигнализации (вымышленный пример для проверки профиля)\nПрибор приёмно-контрольный ППКП-1 рассчитан на 250 адресных устройств.",
    "Спецификация. К прибору ППКП-1 подключено 280 адресных устройств."
   ],
   "observations": [
    {
     "category": "internal_contradiction",
     "finding_text": "Синтетический ответ (СС), не результат вызова модели: ёмкость прибора ППКП-1 записана как 250 адресных устройств, а число подключённых к нему адресных устройств — 280.",
     "recommendation_text": "Согласовать число адресных устройств, подключённых к ППКП-1, и его ёмкость.",
     "evidence": [
      {
       "page_number": 1,
       "quote": "рассчитан на 250 адресных устройств"
      },
      {
       "page_number": 2,
       "quote": "подключено 280 адресных устройств"
      }
     ]
    }
   ]
  },
  "capacity_negative": {
   "pages": [
    "Пояснительная записка. Система пожарной сигнализации (вымышленный пример для проверки профиля)\nПрибор приёмно-контрольный ППКП-1 рассчитан на 250 адресных устройств. Прибор ППКП-2 рассчитан на 250 адресных устройств при использовании двух шлейфов.",
    "Спецификация. К прибору ППКП-1 подключено 240 адресных устройств. К прибору ППКП-2 подключено 280 адресных устройств."
   ],
   "observations": []
  }
 },
 "ITP": {
  "units_positive": {
   "pages": [
    "Общие данные (вымышленный пример для проверки профиля). Тепловая нагрузка на отопление здания — 1,2 Гкал/ч.",
    "Таблица тепловых нагрузок. Тепловая нагрузка на отопление здания — 1,8 МВт."
   ],
   "observations": [
    {
     "category": "internal_contradiction",
     "finding_text": "Синтетический ответ (ИТП), не результат вызова модели: тепловая нагрузка на отопление здания записана как 1,2 Гкал/ч (1,396 МВт), а в таблице нагрузок — 1,8 МВт.",
     "recommendation_text": "Согласовать значение тепловой нагрузки на отопление в общих данных и в таблице нагрузок.",
     "evidence": [
      {
       "page_number": 1,
       "quote": "Тепловая нагрузка на отопление здания — 1,2 Гкал/ч"
      },
      {
       "page_number": 2,
       "quote": "Тепловая нагрузка на отопление здания — 1,8 МВт"
      }
     ]
    }
   ]
  },
  "units_negative": {
   "pages": [
    "Общие данные (вымышленный пример для проверки профиля). Тепловая нагрузка на отопление здания — 1,2 Гкал/ч.",
    "Таблица тепловых нагрузок. Тепловая нагрузка на отопление здания — 1396 кВт."
   ],
   "observations": []
  },
  "total_positive": {
   "pages": [
    "Таблица тепловых нагрузок (вымышленный пример для проверки профиля)\nОтопление — 850 кВт\nВентиляция — 180 кВт\nГВС — 420 кВт\nСуммарная тепловая нагрузка — 1500 кВт",
    "Принципиальная схема ИТП. Схема присоединения — независимая."
   ],
   "observations": [
    {
     "category": "internal_contradiction",
     "finding_text": "Синтетический ответ (ИТП), не результат вызова модели: суммарная тепловая нагрузка записана как 1500 кВт, а три нагрузки по контурам дают 1450 кВт.",
     "recommendation_text": "Согласовать суммарную тепловую нагрузку и нагрузки по контурам.",
     "evidence": [
      {
       "page_number": 1,
       "quote": "Суммарная тепловая нагрузка — 1500 кВт"
      },
      {
       "page_number": 1,
       "quote": "Отопление — 850 кВт"
      },
      {
       "page_number": 1,
       "quote": "Вентиляция — 180 кВт"
      },
      {
       "page_number": 1,
       "quote": "ГВС — 420 кВт"
      }
     ]
    }
   ]
  },
  "total_negative": {
   "pages": [
    "Таблица тепловых нагрузок (вымышленный пример для проверки профиля)\nОтопление — 850 кВт\nВентиляция — 180 кВт\nГВС максимальная — 420 кВт\nГВС среднечасовая — 150 кВт\nСуммарная тепловая нагрузка — 1180 кВт",
    "Принципиальная схема ИТП. Схема присоединения — независимая."
   ],
   "observations": []
  }
 },
 "GP": {
  "areas_positive": {
   "pages": [
    "Баланс территории (вымышленный пример для проверки профиля), м²\nЗастройка — 3200\nТвёрдые покрытия — 4100\nОзеленение — 4500\nИтого — площадь участка 12000",
    "Пояснительная записка. Участок расположен в границах кадастрового квартала."
   ],
   "observations": [
    {
     "category": "internal_contradiction",
     "finding_text": "Синтетический ответ (ГП), не результат вызова модели: площадь участка в итоговой строке баланса территории записана как 12000 м², а три позиции баланса дают 11800 м².",
     "recommendation_text": "Согласовать итоговую площадь участка и площади позиций баланса территории.",
     "evidence": [
      {
       "page_number": 1,
       "quote": "Итого — площадь участка 12000"
      },
      {
       "page_number": 1,
       "quote": "Застройка — 3200"
      },
      {
       "page_number": 1,
       "quote": "Твёрдые покрытия — 4100"
      },
      {
       "page_number": 1,
       "quote": "Озеленение — 4500"
      }
     ]
    }
   ]
  },
  "shares_positive": {
   "pages": [
    "Баланс территории (вымышленный пример для проверки профиля), %\nЗастройка — 26,7\nТвёрдые покрытия — 34,2\nОзеленение — 37,5\nИтого — 100,0",
    "Пояснительная записка. Участок расположен в границах кадастрового квартала."
   ],
   "observations": [
    {
     "category": "internal_contradiction",
     "finding_text": "Синтетический ответ (ГП), не результат вызова модели: итог долей баланса территории записан как 100,0 %, а три позиции дают 98,4 %.",
     "recommendation_text": "Согласовать итог долей и доли позиций баланса территории.",
     "evidence": [
      {
       "page_number": 1,
       "quote": "Итого — 100,0"
      },
      {
       "page_number": 1,
       "quote": "Застройка — 26,7"
      },
      {
       "page_number": 1,
       "quote": "Твёрдые покрытия — 34,2"
      },
      {
       "page_number": 1,
       "quote": "Озеленение — 37,5"
      }
     ]
    }
   ]
  },
  "boundary_negative": {
   "pages": [
    "Баланс территории (вымышленный пример для проверки профиля), м²\nЗастройка — 3200\nТвёрдые покрытия — 4100\nОзеленение — 4700\nИтого — площадь участка 12000",
    "Пояснительная записка. Площадь в границах благоустройства — 13500 м²."
   ],
   "observations": []
  },
  "nototal_negative": {
   "pages": [
    "Баланс территории (вымышленный пример для проверки профиля), %\nЗастройка — 30,0\nТвёрдые покрытия — 30,0\nОзеленение — 30,0",
    "Пояснительная записка. Участок расположен в границах кадастрового квартала."
   ],
   "observations": []
  }
 }
}
```

The replay (the throw-away script of the lane, identical to lane G1's; it needs `PYTHONPATH=src:$BS` and the repository root as the working directory):

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

One change at a time on the committed tree; the section set is `test_text_profile_registry.py`, `tests/unit/analysis/text_profiles`, `test_section_recordings.py` and `tests/contract/analysis_packages` (328 cases; the unmutated tree: `328 passed`). After each restore the SHA-256 over the profile, fixture, `text_profiles` test and report files equalled the one taken before (`restored=True`, `git status --short` empty).

| # | Mutation | Result | First red cases |
|---|---|---|---|
| M1 | `profile.json` version `1.2.0` back to `1.1.0`, once each for EOM, SS, ITP, GP (expectations kept) | 3 failed, 325 passed, each time | registry `test_the_tree_registers_without_error_and_without_an_ar_entry_or_package`; guard `test_every_line_agrees_with_its_package_profile_json`; packages `test_every_profile_manifest_has_the_text_profile_1_shape` |
| M2 | the expectations line back to `1.1.0`, once each for EOM, SS, ITP, GP (`profile.json` kept) | 3 failed, 325 passed, each time | the same three |
| M2b | the ITP line back to `1.1.0`, on the lane stack and in the web test | HTTP 1 failed, 3 passed; web 1 failed, 95 passed | `test_every_row_is_the_registry_entry_the_application_routes_by`; `has a line for exactly the packages that exist, with the status and version each declares` |
| M3 | the EOM paragraph deleted (the exclusion clauses kept), recording kept | 7 failed, 321 passed | `test_each_section_has_one_synthetic_recording_keyed_to_its_own_request[EOM]`, `test_the_builder_reports_no_drift`, `test_the_served_adapter_answers_each_recorded_section_and_the_canonical_alone_does_not[EOM]` |
| M4 | the SS recording replaced by the base file | 5 failed, 323 passed | the same recordings cases for SS |
| M5 | the GP paragraph and both exclusion clauses deleted **and** the recordings rebuilt consistently (the `D-224` residual case) | **328 passed**: no existing test notices; the fragment check prints `MISSING` for 14 of the 59 pairs, all GP | the fragment check is the only red |
| M5b | a temp copy of the SS prompt without the capacity paragraph | fragment check: `MISSING W-CAP-SS-G3 SS`, 1 of 59 | the fragment check |
| M5c | a temp copy of the ITP prompt with the replaced ITP-1 sentence put back | fragment check: `MISSING W-UNITS-REF-ITP-G3 ITP`, 1 of 59 | the fragment check |
| M6 | EOM paragraph: the word «десяти» replaced by the numeral `77` | 5 failed, 110 passed (the guard file, 115 cases) | `test_every_designation_is_in_the_pinned_source_in_v1_or_the_allowlist[EOM]`, `test_inserting_an_invented_designation_turns_the_audit_red[…-EOM]` |
| M6b | the same with the numeral `10` | **115 passed**: the guard stays green, because the whole token `10` is in the pinned EOM source (the RCD example «ванные 10 мА»); the guard checks that a token occurs, not what it means (its own Limits) | none |
| M7 | SS paragraph: a norm number «СП 999» added | 4 failed, 111 passed | `…[SS]` and the insertion cases for cable marking and class designation |
| M8 | ITP paragraph: a class designation «класс Г9» added | 6 failed, 109 passed | `…[ITP]` |
| M9 | the allowlist line for `1,163`, for `1163` and for `МВт` removed, one at a time | 6 failed, 107 passed, each time | `…[ITP]` and `test_removing_an_allowlist_entry_turns_the_audit_red[ITP-…]` of the other two tokens |
| M10 | this report no longer mentions `МВт` (and, separately, `1163`) | 1 failed, 114 passed, each time | `test_every_entry_names_a_report_that_contains_its_token` |
| M10c | `disclosed_by` of the ITP entries names `SECTION-WIDEN-G9-01.md`, which does not exist | 1 failed, 114 passed | `test_every_entry_names_a_report_that_contains_its_token` |
| M11 | one quote altered by one character in each of the seven positive specimens | `evidence_unresolved` 1 instead of 0, seven times | the stage metrics (see «Specimens») |

## Commands and results

From `/root/projects/PDF-Analysis/.local/worktrees/section-widen-g3-01`, shared venv (`.venv` is an untracked symlink), one pytest at a time; `$BS` is `/root/projects/PDF-Analysis/.venv/bootstrap/lib/python3.12/site-packages`.

| Command | Result |
|---|---|
| section set (above), base tree | `322 passed` |
| section set, after the change | `328 passed`: no test was added or edited; the six extra cases are the guard's per-entry tests `test_no_allowlist_entry_is_already_sourced` and `test_removing_an_allowlist_entry_turns_the_audit_red` for the three new allowlist lines |
| `PYTHONPATH=src python3 -I fixtures/recorded/sections/build_fixtures.py`, then `--check` | four recordings replaced (`removed …` and `wrote …` for EOM, SS, ITP, GP; the other ten byte-identical); `--check`: `fixtures match`, rc 0 |
| `tests/unit/analysis/text_profiles/test_prompt_token_guard.py` | `115 passed`, none skipped |
| `tests/integration/composition/test_analysis_profiles_over_http.py`, lane `.env` exported | `4 passed` |
| `npx vitest run tests/unit/analysis-settings` in `web/` (`node_modules` symlinked to the `gate-night` worktree's) | `7 passed` files, `96 passed` |
| fragment check (above) | `23 fragments; missing []` |
| governance one-liner on the task file | `[]` |
| `tests/contract/program tests/contract/api_v1/test_doc_prose_facts.py tests/contract/api_v1/test_surface_counts_in_prose.py`, `git diff --check d1400994..HEAD` | run after the last commit (next row) |

Free disk: 1.9 GiB at the start, 1.9 GiB at the end. No docker command, no push, no tag, no model call, no network, no process killed, no database created.

## Integration notes

1. **Merge.** The expectations file changes four lines (`EOM SS ITP GP`: `1.2.0`); on a conflict regenerate each line from its `profile.json`. Recordings: four keys changed, the other ten are byte-identical after the builder runs. The allowlist gained three entries **appended at the end**; lane G2 may append at the same place, so a textual conflict is possible: keep every entry of both sides and the JSON commas (the guard's shape test reads the file).
2. **The recordings test blocks the specimens (P-07).** As in lane G1's note 2: either relax line 97 of `tests/integration/sections/test_section_recordings.py` and extend `build_fixtures.py` once for all lanes, or add a sibling directory (for example `fixtures/recorded/sections_widen/<code>/`, which the served adapter does not search) with a test that replays the specimens above through the stage. The 14 specimen texts in this report (7 positive, 7 negative) are ready for either.
3. **For `SECTION-PROMPT-SENTENCE-GUARD-01`.** (a) The fragment table of this report has 23 fragments and 59 pairs; seven ids are byte-identical to lane G1's (`W-HEAD`, `W-TRIGGER`, `W-B4`, `W-B6`, `W-NOTOTAL`, `W-NORMS-1`, `W-NORMS-2`), every id with the suffix `-G3` is this lane's own, so the two tables can be read as one namespace without a conflict (checked). (b) The ITP row ITP-1 (N) of the ledger names a sentence that **no longer stands** in the ITP prompt; the guard must read it as superseded (table «The ledger fragment this lane supersedes»), not as a loss.
4. **Two variants of one paragraph.** Lane G1 wrote the sum-of-rows paragraph for `PS POS TX KJ` in a longer wording (+2,701 to +2,834 characters); this lane wrote a compact reading with the same six conditions (about 435 characters shorter in the shared part), because the budget term does not count a section prompt (note 5). The two readings differ in wording only (conditions, tolerance, evidence). The integrator may keep both, or harmonise `PS POS TX KJ` and `KM OV VK PT` (lane G2) to one reading later; nothing in the tests depends on it.
5. **The input budget does not count a section's prompt** (P-10; lane G1's note 5). `budget.py` subtracts the АР bundle's prompt (about 3,000 characters); the four prompts are now 7,456 to 9,298 characters. The additions are 2,394 to 2,827 characters, under 2 % of the 152,361-character figure for the pinned model at a ceiling of 1.00. `budget.py` is not changed here; lane `SECTION-CHUNKED-ANALYSIS-01` owns it.
6. **Windows.** `W-B3-G3` tells the model not to report a table that is cut off at the last page it was given, so a total in one window and its rows in the next are not compared; the capacity rule has the same property (a capacity in one window and the count in the next are not compared, because the model cannot see both). A run of independent windows should say so in its summary (the CH lane's task).
7. **A stored run keeps the old profile hash** (as in lane G1's note 7): a run made with `1.1.0` carries the old `analysis_profile_sha256` and `prompt_bundle_sha256`; the registry resolves by the identity pair and serves the new text. Development stand only, no migration.
8. **Debt.** The refusal of the omission topic (EOM-4, SS-5, ITP-5), the refusal of the requested-against-selected comparison (ITP-4), the unmeasured model arithmetic, the superseded ledger row, the two paragraph variants, the specimens that no test reads and the budget term are the limits for a debt row; the lane did not edit `DEBT_REGISTER.md`.

## Limits

- No test reads the new sentences (`D-224` residual; M5 shows it). The fragment table above is the stand-in until `SECTION-PROMPT-SENTENCE-GUARD-01` reads it.
- No model was called. The effect of the paragraph, of the capacity rule and of the unit rule on a real model (false findings from mis-added tables or a wrong conversion, missed findings from the strict conditions) is unknown.
- The specimens are hand-authored and not filed as fixtures.
- The unit factor and the tolerance are the integrator's rule and the lane's reading; no pinned file states either (P-12).
- The lane did not change `W59-SECTION-PROFILES-01.md`, the ledger or the web label; the record still says the questions it asked, and the ledger still lists K or N for the topics this lane now answers W (EOM q2, SS q5, ITP q1 and q5, GP q1).

## Proof that forbidden paths are untouched

`git diff --name-only --no-renames d1400994..HEAD` on the final tree prints exactly these 20 paths, all inside the task's allowed paths (without `--no-renames` git folds each replaced recording into a rename):

```text
docs/program/SECTION-WIDEN-G3-01.md
docs/program/tasks/SECTION-WIDEN-G3-01.md
fixtures/recorded/sections/eom/22dee8720e48cace823f348412adae9884023a8507823f5798db105b17b5f1d2.json
fixtures/recorded/sections/eom/966f4f6fd773c064d26b8e27a798967a919be2aa1d0c04ba80497829637d8098.json
fixtures/recorded/sections/gp/414d336dca6967b36431ba3282f198d1f770d5d0b2fcd6293ff8c3611df05165.json
fixtures/recorded/sections/gp/9dbe139a3b025683b91448992b6890a0a7bd54750e95969a3a396c60b7a8b959.json
fixtures/recorded/sections/itp/b9b9d6a8dc98d75291fd0ad13bf1d532204a25270691511d4e6522f61279953b.json
fixtures/recorded/sections/itp/c3e8bd56d8c4cf6f66efd6b4f9058069822eba53abf9fb1e4b26bd36a7daf203.json
fixtures/recorded/sections/ss/dd6ccee83f95994a6bff7ae3c088fbc56e29d8b4908178c44bea313b89cc70fa.json
fixtures/recorded/sections/ss/f032738f038457c6c4e39a55f3ec08f6e91bc73213a5c2f03390a1aa33e1712e.json
src/auditmanager/analysis/text/profiles/eom/profile.json
src/auditmanager/analysis/text/profiles/eom/system_prompt.md
src/auditmanager/analysis/text/profiles/gp/profile.json
src/auditmanager/analysis/text/profiles/gp/system_prompt.md
src/auditmanager/analysis/text/profiles/itp/profile.json
src/auditmanager/analysis/text/profiles/itp/system_prompt.md
src/auditmanager/analysis/text/profiles/ss/profile.json
src/auditmanager/analysis/text/profiles/ss/system_prompt.md
tests/unit/analysis/text_profiles/prompt_token_allowlist.json
tests/unit/analysis/text_profiles/section_profile_expectations.json
```

No other section's files, no `W59-SECTION-PROFILES-01.md`, ledger, registry, `P02_LOCK.json`, `contracts/**`, migration, `web/**`, `infra/**`, `tests/integration/sections/**`, `test_prompt_token_guard.py`, `build_fixtures.py`, `budget.py` or `DEBT_REGISTER.md` appears. `/root/projects/PDF-proverka` was only read: its `HEAD` is the pinned `16ba8e5d…` and `git status --short` there prints nothing.

