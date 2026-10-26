# SECTION-WIDEN-G1-01 — AI PS POS TX KJ: the sum-of-rows check added to four prompts, the omission check refused for two, every topic decided

Task: `docs/program/tasks/SECTION-WIDEN-G1-01.md`. Branch `agent/section-widen-g1-01`, base `6075df88` (`integration/ar-close-1026`). Plan item `PROD-14`; owner rulings `R-146an`, `R-146ag`; accepted risks `A-5`, `A-7`; brief `docs/program/dispatch/PRODUCTION-WAVE-PW4.md` section 6. Format follows `SECTION-PS-FULL-01.md` and `SECTION-PROMPT-TOKEN-GUARD-01.md`.

## Result

The gap report (`ROADMAP-GAP-2026-10-27.md` section 2.3) marks nine topics in these five sections as «reinstatable now». This lane decided each (13 rows below: some topics split in two, and rule 5 adds one notation row, KJ-3): **W 6, K 1, N 0, X 6**.

- **Widened (W), one check in four prompts.** `PS`, `POS`, `TX` and `KJ` now carry one paragraph, placed after condition 5, that lets the model add the rows of a table whose total the text itself writes and report `internal_contradiction` when the sum differs beyond the rounding of the written values. It is the same paragraph in the four prompts; only its scope sentence (which totals) and the object list of its first condition change per section. The exclusion paragraph gets two clauses so that the ban on recalculation keeps this one exception.
- **Refused (X) for `AI` and for the omission half of `TX`.** «An item named in one place and absent from another» is not carried honestly by the existing evidence (reasons in row AI-1), so `AI`, whose only reinstatable topic it is, is unchanged and stays at `1.1.0`.
- **Not widened (X)** where the conservative rules say so: a coefficient recomputed from areas (PS-3), a distribution compared with a «100 %» the text does not write (POS-2), the sum of stage durations (POS-3), the old and new designations of a rebar class (KJ-3).
- `profile_version` is `1.2.0` for `PS POS TX KJ` (prompt text changed), `status` stays `reviewed`; the four recordings are rebuilt, the four expectations lines moved; the response schema, the two categories, the severity and every contract are untouched, and no allowlist line was needed.

**`reviewed` carries no human review** (`R-146ag`, `A-7`). Nobody, neither an expert nor the owner, checked any sentence below, and nothing was measured on real text or with a model. The new sentences are the lane's reading of the record, the gap report and the brief's rules.

Premise: **match, with one difference that changes a deliverable** (task file P-01 to P-11). The brief asks for a positive and a negative recording per widened section under `fixtures/recorded/sections/<code>/` through `build_fixtures.py`. `tests/integration/sections/test_section_recordings.py` pins exactly one file in each such directory (line 97) and exactly 14 planned recordings (line 156), and neither that test nor the builder is in this lane's allowed paths (P-07). The lane did not touch them; it rebuilt the existing recordings and kept the positive and negative specimens in this report, replayed through the real stage (section «Specimens»).

## Decisions

Quoted wording is the gap report's («Reinstatable now» cell, P-03) and the record's. «Fragment» ids point at the verbatim table below.

| # | Section | Topic | Decision | Reason | Exact sentence |
|---|---|---|---|---|---|
| AI-1 | AI | An item on a plan or in the explication that the finishing schedule does not list, and the reverse (omission pair of cross-section question 4; excluded item 5, its required-presence form) | **X** | (a) The evidence of every finding of these profiles is the quotes of the places that disagree, so a reader sees the conflict from the quotes alone; an absence has no quote, and the quote of a heading says only where to look. The grounding gate (P-09) checks that every quote exists, so it would publish a claim that something does not exist as «grounded» without being able to check it. (b) v1 condition 5 says the opposite («Если документ ничего не говорит о чём-то — это не находка») and the category is defined as incompatible values of one attribute; the record calls the omission «not two incompatible values», and the wave table fixed it K. (c) A volume above the one-call budget is analysed in whole-page windows that never see each other (lane `SECTION-CHUNKED-ANALYSIS-01`), where the absence of a row from a list on another window cannot be decided. (d) Room numbers repeat across floors and apartment types; `SECTION-AI-FULL-01` removed the number as an identity (question 4, N), and an omission check needs exactly that identity. | none; the AI prompt is unchanged |
| PS-1 | PS | A flat-count total against its rows (question 1) | **W** | The record asks it (P-05); the total and the rows are written, and the quotes carry the disagreement. A count is exact, so any difference counts. | `W-HEAD`, `W-SCOPE-PS`, `W-TRIGGER`, `W-B1-PS`, `W-B2`–`W-B6`, `W-NOTOTAL`, `W-CONDITIONS`, `W-EVIDENCE` |
| PS-2 | PS | The total area of flats against the rows by type, section or floor (question 1; the record's excluded sum «сумм площадей и квартир по типам») | **W** | Same sentence as PS-1; the area is a rounded value, so the tolerance sentence applies (rule 1). The basis sentence defers to the text where it names a basis (loggias counted or not, rule 3). | the same fragments |
| PS-3 | PS | A ТЭП coefficient (built-up ratio, density) recomputed from written areas (excluded item 3) | **X** | A ratio needs its formula (which areas enter it), which neither the text nor the five pinned files give; that is a definition by norm or convention that the text must state (rule 3), and the recomputed ratio is a figure the text does not state (rule 2). | `W-SCOPE-PS` keeps the clause «Коэффициенты застройки и плотности застройки не пересчитывай» so the new rule cannot be stretched to them |
| PS-4 | PS | A recapped value of another volume against the same записка's ТЭП (question 4) | **K** | Both values are written in this one document, so it is v1's own question; decided K in `SECTION-PS-FULL-01` (PS-4). Nothing to add. | none |
| POS-1 | POS | A distribution of volumes or investments by period against its written total (question 2, «a total against 100 %») | **W**, narrowed to a total the text writes | The rows are shares or sums and the total is written; the prompt compares the two written figures and does not import «100» (rule 2, rule 4). | `W-HEAD`, `W-SCOPE-POS`, `W-TRIGGER`, `W-B1-POS`, `W-B2`–`W-B6`, `W-NOTOTAL`, `W-CONDITIONS`, `W-EVIDENCE` |
| POS-2 | POS | The same rows compared with «100 %» when the text writes no total | **X** | The figure 100 is not in the text (rule 2) and not in the pinned source (rule 4); the prompt cannot carry it without a numeral the guard rejects, and no allowlist line can be added from this lane (P-08). | `W-NOTOTAL`: «Если итог в тексте не записан, ничего не складывай.» |
| POS-3 | POS | The sum of stage durations against the total duration | **X** | Overlapping stages are legal (record question 2; the gap report: «not safe»). Rule 3 would allow flagging only where the text states the basis (stages run one after another); a text almost never does, and even then the total may include breaks the stage table does not list, so the gain is nil and the false-positive surface is the stage table of every ПОС. The prompt therefore says not to add durations at all. | `W-SCOPE-POS` keeps «Продолжительности этапов не складывай: этапы могут выполняться одновременно, и сумма их продолжительностей не обязана равняться общей продолжительности.» |
| TX-1 | TX | A position in the explication with no specification row, and the reverse (question 4) | **X** | The reasons (a), (b) and (c) of AI-1; and position numbers repeat across rooms and enterprises (`SECTION-TX-FULL-01`, question 2, N), so the identity an omission check needs is the one that lane removed. | none |
| TX-2 | TX | A записка (or general-data) power, water, sewage or heat total against the sum of the load, connection or specification table of the same enterprise (question 3) | **W** | The total and the rows are written and quoted. Installed against consumed power and hourly against daily water stay different attributes (condition 2); a total on a named basis («с учётом коэффициента спроса») is not compared with rows on another (`W-B4`); a specification row that gives power per unit and a quantity is not multiplied (`W-B1-TX`), so most specifications will not be checked. | `W-HEAD`, `W-SCOPE-TX`, `W-TRIGGER`, `W-B1-TX`, `W-B2`–`W-B6`, `W-NOTOTAL`, `W-CONDITIONS`, `W-EVIDENCE` |
| KJ-1 | KJ | The total of a steel-consumption sheet against its rows by mark, class or diameter (question 4) | **W** | The sheet is a table whose total row is written; the mass is a rounded value (tolerance sentence); a torn table is excluded by `W-B3`. | `W-HEAD`, `W-SCOPE-KJ`, `W-TRIGGER`, `W-B1-KJ`, `W-B2`–`W-B6`, `W-NOTOTAL`, `W-CONDITIONS`, `W-EVIDENCE` |
| KJ-2 | KJ | The total of the reinforcement specification against its rows (question 4 names both) | **W** | Same sentence as KJ-1. | the same fragments |
| KJ-3 | KJ | The old and the new designation of a rebar class or concrete class as one value (question 1; not a «reinstatable now» topic, listed because rule 5 names such notations) | **X** | Reading А-III as А400 or В25 as М350 needs an equivalence table; no hash-pinned file states one (rule 5). | none |

The unit-conversion factors of rule 4 are not used: none of these five sections has a quantity stated in two units among its decided topics, `W-B1-*` requires the same units, and no factor, norm or threshold stands in any prompt.

### How each of the brief's rules shows in the sentences

| Rule | Where it stands |
|---|---|
| (1) both figures written, tolerance in words | `W-B1-*` (written explicitly, same units), `W-B3` (every row visible, also at a window or page boundary), `W-B5` (counts exact; otherwise half a unit of the last written digit per value, summed over the addends and the total) |
| (2) never recompute from an unstated figure | `W-NOTOTAL`, `W-B1-*` (no value per unit, no product of quantity and unit value), `W-SCOPE-PS` (coefficients), `W-B6` (add twice) |
| (3) legal overlap or stated basis | `W-SCOPE-POS` (durations), `W-B4` («с учётом», «без учёта», «включая», «за исключением», a coefficient), `W-B2` («в том числе», «из них», subtotals) |
| (4) conversion factors only | not used; no number appears in any added sentence; the token guard passes with an unchanged allowlist |
| (5) equivalent notations stay excluded | KJ-3; nothing in the prompts equates two notations |
| (6) every topic decided | the table above |

## The prompt change in words

For each of `PS`, `POS`, `TX`, `KJ`: (1) a new paragraph between condition 5 and the exclusion paragraph. It says the only addition the model may do is adding the rows of a table whose total the text writes; names the scope; says to report `internal_contradiction` only when six things hold (same units, object and column and no per-unit or computed value; only the parts of the total, no «в том числе» lines and no subtotal added to its own rows; every row visible; no different stated basis; the difference exceeds the rounding of the written values; the rows were added twice with the same sum); says to add nothing when the text writes no total; says conditions 1 to 4 still apply; and asks for the quote of the total and of the rows as evidence, with the written total, the sum and the number of rows in `finding_text`. (2) The exclusion paragraph keeps its sentence but now says the ban on recalculation holds «кроме сложения строк по правилу выше», and that what is compared is the written values «и сумма строк, сложенных по правилу выше». Nothing else moved: with the paragraph and the two clauses removed, the whitespace-normalised prompt equals the base prompt in all four sections (checked), and v1's question, categories, conditions and output contract are held by the package test.

| Section | Scope sentence (what may be added) | Prompt size |
|---|---|---|
| PS | the number of flats and the total flat area against the rows by flat type, section or floor in the ТЭП table and the flat schedule; coefficients are not recomputed | 6,696 to 9,416 characters (+2,720) |
| POS | the distribution of work volumes or investments by construction period, shares or sums, against its written total; stage durations are never added | 6,559 to 9,393 (+2,834) |
| TX | installed power, water, sewage and heat or cold release of the equipment of one enterprise or room: a written total against the rows of the load, connection or specification table | 6,080 to 8,901 (+2,821) |
| KJ | the mass of reinforcement: the written total of the steel-consumption sheet or of the reinforcement specification against the rows by mark, class or diameter; concrete volume is not added | 6,287 to 8,988 (+2,701) |
| AI | none | unchanged (6,088 characters; hash `1e5f2521…` as at the base) |

New numerals: none (the only digits are `1` and `4` in «Условия 1–4», v1's own numerals). New norm references: none. New class designations: none. New categories, fields, severities: none.

## Added fragments, verbatim

Whitespace-normalised: a fragment is the prompt text with every run of whitespace, line breaks included, replaced by one space. A fragment is checked against the prompt normalised the same way. The block is machine-readable so that `SECTION-PROMPT-SENTENCE-GUARD-01` can read it; 20 fragments, 56 (fragment, section) pairs.

| Fragment | Sections | Role |
|---|---|---|
| `W-HEAD` | PS, POS, TX, KJ | rule: the only permitted addition |
| `W-SCOPE-PS` | PS | scope: which totals may be added |
| `W-SCOPE-POS` | POS | scope: which totals may be added |
| `W-SCOPE-TX` | TX | scope: which totals may be added |
| `W-SCOPE-KJ` | KJ | scope: which totals may be added |
| `W-TRIGGER` | PS, POS, TX, KJ | category: the existing internal_contradiction |
| `W-B1-PS` | PS | conservative rule 2: only written values, one column, no unit values, no products |
| `W-B1-POS` | POS | conservative rule 2: only written values, one column, no unit values, no products |
| `W-B1-TX` | TX | conservative rule 2: only written values, one column, no unit values, no products |
| `W-B1-KJ` | KJ | conservative rule 2: only written values, one column, no unit values, no products |
| `W-B2` | PS, POS, TX, KJ | conservative rule 3: parts of the total only; subtotals |
| `W-B3` | PS, POS, TX, KJ | conservative rule 1: all rows visible (also at a window boundary) |
| `W-B4` | PS, POS, TX, KJ | conservative rule 3: the stated basis |
| `W-B5` | PS, POS, TX, KJ | conservative rule 1: tolerance in words |
| `W-B6` | PS, POS, TX, KJ | double addition |
| `W-NOTOTAL` | PS, POS, TX, KJ | conservative rule 2: no written total, no check |
| `W-CONDITIONS` | PS, POS, TX, KJ | the five conditions still apply |
| `W-EVIDENCE` | PS, POS, TX, KJ | evidence: the total and the rows |
| `W-NORMS-1` | PS, POS, TX, KJ | exclusion sentence: calculation ban, one exception |
| `W-NORMS-2` | PS, POS, TX, KJ | exclusion sentence: what is compared |

<!-- fragments:begin -->
```json
[
 {
  "id": "W-HEAD",
  "sections": [
   "PS",
   "POS",
   "TX",
   "KJ"
  ],
  "role": "rule: the only permitted addition",
  "text": "Единственное сложение, которое тебе разрешено, — сложение строк, из которых текст сам составляет записанный в нём итог."
 },
 {
  "id": "W-SCOPE-PS",
  "sections": [
   "PS"
  ],
  "role": "scope: which totals may be added",
  "text": "Здесь это количество квартир и общая площадь квартир: записанный итог («Итого», «Всего» или подобная строка) в таблице ТЭП или в квартирографии и строки по типам квартир, секциям или этажам, из которых он составлен. Коэффициенты застройки и плотности застройки не пересчитывай, другие итоги не складывай."
 },
 {
  "id": "W-SCOPE-POS",
  "sections": [
   "POS"
  ],
  "role": "scope: which totals may be added",
  "text": "Здесь это распределение по периодам строительства объёмов работ или капитальных вложений: записанный итог («Итого», «Всего» или подобная строка) и строки периодов, из которых он составлен, — доли (в процентах) или суммы. Продолжительности этапов не складывай: этапы могут выполняться одновременно, и сумма их продолжительностей не обязана равняться общей продолжительности. Другие итоги не складывай."
 },
 {
  "id": "W-SCOPE-TX",
  "sections": [
   "TX"
  ],
  "role": "scope: which totals may be added",
  "text": "Здесь это установленная электрическая мощность, расход воды, расход стоков и тепло- и холодовыделение технологического оборудования одного и того же предприятия или помещения: записанный итог в пояснительной записке, в общих данных или в сводной таблице нагрузок и строки (позиции оборудования) таблицы нагрузок, таблицы подключений или спецификации, из которых он составлен. Другие итоги не складывай."
 },
 {
  "id": "W-SCOPE-KJ",
  "sections": [
   "KJ"
  ],
  "role": "scope: which totals may be added",
  "text": "Здесь это масса арматуры: записанный итог («Итого», «Всего» или подобная строка) ведомости расхода стали или спецификации арматуры и строки по маркам конструкций, классам арматуры или диаметрам, из которых он составлен. Другие итоги, в том числе объём бетона, не складывай."
 },
 {
  "id": "W-TRIGGER",
  "sections": [
   "PS",
   "POS",
   "TX",
   "KJ"
  ],
  "role": "category: the existing internal_contradiction",
  "text": "Если сумма строк расходится с записанным итогом, сообщи internal_contradiction, но только когда выполнено всё перечисленное:"
 },
 {
  "id": "W-B1-PS",
  "sections": [
   "PS"
  ],
  "role": "conservative rule 2: only written values, one column, no unit values, no products",
  "text": "итог и каждая складываемая строка записаны в тексте явно и в одних и тех же единицах измерения, и текст относит их к одному и тому же объекту и признаку (к одной таблице, одному перечню, одному зданию или одной секции); складываются значения одного столбца, записанные именно для строки; значение на одну единицу (например, площадь одной квартиры) и значение, которого в строке нет и которое пришлось бы вычислять, в том числе умножением количества на значение единицы, в сумму не входят;"
 },
 {
  "id": "W-B1-POS",
  "sections": [
   "POS"
  ],
  "role": "conservative rule 2: only written values, one column, no unit values, no products",
  "text": "итог и каждая складываемая строка записаны в тексте явно и в одних и тех же единицах измерения, и текст относит их к одному и тому же объекту и признаку (к одной таблице, одному перечню, одному зданию или одной очереди строительства); складываются значения одного столбца, записанные именно для строки; значение на одну единицу (например, цена единицы объёма работ) и значение, которого в строке нет и которое пришлось бы вычислять, в том числе умножением количества на значение единицы, в сумму не входят;"
 },
 {
  "id": "W-B1-TX",
  "sections": [
   "TX"
  ],
  "role": "conservative rule 2: only written values, one column, no unit values, no products",
  "text": "итог и каждая складываемая строка записаны в тексте явно и в одних и тех же единицах измерения, и текст относит их к одному и тому же объекту и признаку (к одной таблице, одному перечню, одному предприятию или помещению); складываются значения одного столбца, записанные именно для строки; значение на одну единицу (например, мощность одного прибора) и значение, которого в строке нет и которое пришлось бы вычислять, в том числе умножением количества на значение единицы, в сумму не входят;"
 },
 {
  "id": "W-B1-KJ",
  "sections": [
   "KJ"
  ],
  "role": "conservative rule 2: only written values, one column, no unit values, no products",
  "text": "итог и каждая складываемая строка записаны в тексте явно и в одних и тех же единицах измерения, и текст относит их к одному и тому же объекту и признаку (к одной ведомости, одной таблице, одной конструкции или одному зданию); складываются значения одного столбца, записанные именно для строки; значение на одну единицу (например, масса одного погонного метра) и значение, которого в строке нет и которое пришлось бы вычислять, в том числе умножением количества на значение единицы, в сумму не входят;"
 },
 {
  "id": "W-B2",
  "sections": [
   "PS",
   "POS",
   "TX",
   "KJ"
  ],
  "role": "conservative rule 3: parts of the total only; subtotals",
  "text": "в сумму входят только строки, из которых итог составлен по смыслу таблицы; строки «в том числе», «из них», «справочно» и строки, которые текст относит к другому варианту, в сумму не входят; промежуточный итог не складывай вместе со строками, из которых он сам составлен;"
 },
 {
  "id": "W-B3",
  "sections": [
   "PS",
   "POS",
   "TX",
   "KJ"
  ],
  "role": "conservative rule 1: all rows visible (also at a window boundary)",
  "text": "все строки читаются в переданном тексте: если часть строк или значений не видна, оборвана (в том числе на последней переданной странице), оторвана от своих подписей или заменена многоточием либо словами «прочие» и «и другие» без значения, не сообщай;"
 },
 {
  "id": "W-B4",
  "sections": [
   "PS",
   "POS",
   "TX",
   "KJ"
  ],
  "role": "conservative rule 3: the stated basis",
  "text": "если в тексте названо основание, на котором записан итог или строка («с учётом», «без учёта», «включая», «за исключением», коэффициент), а итог и строки записаны на разных основаниях, не сообщай;"
 },
 {
  "id": "W-B5",
  "sections": [
   "PS",
   "POS",
   "TX",
   "KJ"
  ],
  "role": "conservative rule 1: tolerance in words",
  "text": "расхождение больше погрешности округления: количества (квартир, штук) записаны точно и погрешности не имеют, поэтому любое расхождение — находка; у остальных значений погрешность не больше половины единицы последнего записанного разряда, а погрешность сравнения — сумма таких погрешностей всех слагаемых и итога; расхождение в пределах этой погрешности — согласованность;"
 },
 {
  "id": "W-B6",
  "sections": [
   "PS",
   "POS",
   "TX",
   "KJ"
  ],
  "role": "double addition",
  "text": "ты сложил строки дважды, в прямом и в обратном порядке, и получил одну и ту же сумму."
 },
 {
  "id": "W-NOTOTAL",
  "sections": [
   "PS",
   "POS",
   "TX",
   "KJ"
  ],
  "role": "conservative rule 2: no written total, no check",
  "text": "Если итог в тексте не записан, ничего не складывай."
 },
 {
  "id": "W-CONDITIONS",
  "sections": [
   "PS",
   "POS",
   "TX",
   "KJ"
  ],
  "role": "the five conditions still apply",
  "text": "Условия 1–4 выше применяются и к такому расхождению; условие 5 не мешает, потому что и итог, и строки в тексте есть."
 },
 {
  "id": "W-EVIDENCE",
  "sections": [
   "PS",
   "POS",
   "TX",
   "KJ"
  ],
  "role": "evidence: the total and the rows",
  "text": "В evidence приведи цитату итога и цитаты складываемых строк (если строк больше десяти — цитаты итога, первой и последней из них); в finding_text назови записанный итог, полученную сумму и число сложенных строк."
 },
 {
  "id": "W-NORMS-1",
  "sections": [
   "PS",
   "POS",
   "TX",
   "KJ"
  ],
  "role": "exclusion sentence: calculation ban, one exception",
  "text": "кроме сложения строк по правилу выше,"
 },
 {
  "id": "W-NORMS-2",
  "sections": [
   "PS",
   "POS",
   "TX",
   "KJ"
  ],
  "role": "exclusion sentence: what is compared",
  "text": "и сумма строк, сложенных по правилу выше."
 }
]
```
<!-- fragments:end -->

Check (prints the fragments missing from the prompts of this tree; the expected answer is an empty list):

```text
F=$(python3 -I -c "print(chr(96)*3)"); python3 -I -c "import json,re,sys;f=sys.argv[1];t=open('docs/program/SECTION-WIDEN-G1-01.md',encoding='utf-8').read();fr=json.loads(re.search('<!-- fragments:begin -->\\\\s*'+f+'json\\n(.*?)\\n'+f+'\\\\s*<!-- fragments:end -->',t,re.S).group(1));n=lambda s:' '.join(s.split());bad=[(x['id'],c) for x in fr for c in x['sections'] if x['text'] not in n(open('src/auditmanager/analysis/text/profiles/'+c.lower()+'/system_prompt.md',encoding='utf-8').read())];print(len(fr),'fragments; missing',bad)" "$F"
```

## Assumptions an expert would still want to check

Short and honest (`A-7`): none of these was checked by anyone with domain knowledge.

1. **Whether a model should add at all.** The gap report calls a sum «a deterministic check» that «a model must not do» (class E2). The owner ordered the widening anyway (`R-146an`), so this lane keeps the addition behind six conditions; the only guard on the model's arithmetic is the instruction to add twice, and it is unmeasured.
2. **The tolerance.** Half a unit of the last written digit per value, summed over the addends and the total, is the worst case of rounding. In a long table the allowance grows (forty rows at one decimal allow about two units), so a real small discrepancy in a long table is not reported. Counts are called exact («записаны точно»); a count written as «около» or «не менее» is not, and the prompt does not say so.
3. **Which line is a total.** «Итого», «Всего» «или подобная строка» is left to the model; a line such as «Общее количество» or «Сумма» may or may not be taken for one, and a line that is a subtotal is told apart from the grand total only by the sentence on subtotals.
4. **PS.** The total area of flats is written with and without loggia coefficients in practice; the prompt defers to a basis the text names, so two unnamed bases remain a source of false findings. «По типам, секциям или этажам» rows may carry «в том числе» lines (for example flats for people with limited mobility) that the prompt tells the model to skip.
5. **POS.** «Объёмов работ или капитальных вложений» comes from the record's question 2, not from the five pinned files (they hold no «капитальные вложения»). Shares written as rounded percentages are covered only by the tolerance sentence. Headcounts per period are not named as non-additive; they are out of scope only because the scope sentence does not list them.
6. **TX.** A specification normally gives power per unit and a quantity; the prompt forbids the multiplication, so only tables with a per-row total or per-item loads are checked, and most specifications are silent. A записка total on a demand or simultaneity basis is skipped only where the text names the coefficient.
7. **KJ.** A steel-consumption sheet is a table of class by diameter; when the text layer tears numbers from their columns the prompt says not to report, but a model can still assign a number to the wrong column.
8. **Evidence.** For more than ten rows the model quotes the total, the first and the last row, so the expert reads the middle of the table to confirm the sum.
9. **Vocabulary not from the five pinned files.** «Итого», «Всего», «промежуточный итог», «справочно», «погонный метр», «квартирография» (already in the PS prompt) and the object lists of the first condition are the lane's words; the token guard does not check ordinary words.
10. **The omission refusal (AI-1, TX-1) loses a real class of defects.** A position missing from a specification is a common finding of a human reviewer; this lane leaves it to the expert.
11. **Nothing was measured.** The four replaced recordings are still the hand-authored replies over the АР corpus; they prove routing and replay. The specimens below are hand-authored too.

## Token-guard additions

None. `tests/unit/analysis/text_profiles/prompt_token_allowlist.json` is byte-identical to the base (`git diff --name-only 6075df88..HEAD` does not list it). The paragraph's designation tokens are `internal_contradiction`, `evidence` and `finding_text` (v1's own words) and, in `PS`, `ТЭП` (in the PS pinned source and already in the prompt); the guard's 109 cases pass against the pinned source with none skipped. The allowlist could not take a line from this lane anyway: `disclosed_by` must match `SECTION-[A-Z]+-FULL-01\.md` (P-08). Rows M6 to M8 below show the guard red when a numeral, a norm number or a class designation is put into the paragraph.

## Specimens

One positive and one negative text per widened section, with the hand-authored reply a model would give. They were replayed through the real stage (`run_text_analysis`) with the section's own profile and a throw-away recorded directory in the session scratchpad; they are **not** committed as fixtures (premise P-07). Every positive reply opens its `finding_text` with «Синтетический ответ (<раздел>), не результат вызова модели», as the existing recordings do. The negative texts hold a trap each (a «в том числе» line, an overlap of stages, a coefficient basis) that the intended answer leaves alone.

| Section | Case | Proposed | Emitted | Evidence unresolved |
|---|---|---|---|---|
| PS | positive (116 against 120 flats) | 1 | 1 | 0 |
| PS | negative (116 flats and a «в том числе» line) | 0 | 0 | 0 |
| PS | positive with one quote altered by one character | 1 | 1 | 1 |
| POS | positive (shares add to 90, total 100) | 1 | 1 | 0 |
| POS | negative (stage durations overlap) | 0 | 0 | 0 |
| POS | positive with one altered quote | 1 | 1 | 1 |
| TX | positive (22,5 against 28) | 1 | 1 | 0 |
| TX | negative (a coefficient basis named) | 0 | 0 | 0 |
| TX | positive with one altered quote | 1 | 1 | 1 |
| KJ | positive (7205 against 7500) | 1 | 1 | 0 |
| KJ | negative (a «в том числе» line) | 0 | 0 | 0 |
| KJ | positive with one altered quote | 1 | 1 | 1 |

The altered-quote rows are the mutation of this check: a quote that is not verbatim leaves the evidence unresolved, and the grounding gate would then refuse the finding. What these rows do **not** show: that a model gives these answers.

```json
{
 "PS": {
  "positive": {
   "pages": [
    "Пояснительная записка (вымышленный пример для проверки профиля)\nТаблица ТЭП. Количество квартир по типам:\nСтудии — 20\nОднокомнатные — 40\nДвухкомнатные — 36\nТрёхкомнатные — 20\nИтого квартир — 120",
    "Раздел «Объёмно-планировочные решения»\nЗдание секционное, жилые этажи со второго по девятый."
   ],
   "observations": [
    {
     "category": "internal_contradiction",
     "finding_text": "Синтетический ответ (ПЗ), не результат вызова модели: общее количество квартир в таблице ТЭП записано как 120, а четыре строки по типам квартир дают 116.",
     "recommendation_text": "Свести итог и строки по типам квартир к одному значению.",
     "evidence": [
      {
       "page_number": 1,
       "quote": "Итого квартир — 120"
      },
      {
       "page_number": 1,
       "quote": "Студии — 20"
      },
      {
       "page_number": 1,
       "quote": "Однокомнатные — 40"
      },
      {
       "page_number": 1,
       "quote": "Двухкомнатные — 36"
      },
      {
       "page_number": 1,
       "quote": "Трёхкомнатные — 20"
      }
     ]
    }
   ]
  },
  "negative": {
   "pages": [
    "Пояснительная записка (вымышленный пример для проверки профиля)\nТаблица ТЭП. Количество квартир по типам:\nСтудии — 20\nОднокомнатные — 40\nДвухкомнатные — 36\nТрёхкомнатные — 20\nв том числе для МГН — 12\nИтого квартир — 116",
    "Раздел «Объёмно-планировочные решения»\nЗдание секционное, жилые этажи со второго по девятый."
   ],
   "observations": []
  }
 },
 "POS": {
  "positive": {
   "pages": [
    "Проект организации строительства (вымышленный пример для проверки профиля)\nРаспределение капитальных вложений по годам строительства, %\nПервый год — 25\nВторой год — 45\nТретий год — 20\nИтого — 100",
    "Календарный план. Общая продолжительность строительства — 11 месяцев."
   ],
   "observations": [
    {
     "category": "internal_contradiction",
     "finding_text": "Синтетический ответ (ПОС), не результат вызова модели: итог распределения капитальных вложений записан как 100, а три строки по годам дают 90.",
     "recommendation_text": "Согласовать итог распределения и доли по годам строительства.",
     "evidence": [
      {
       "page_number": 1,
       "quote": "Итого — 100"
      },
      {
       "page_number": 1,
       "quote": "Первый год — 25"
      },
      {
       "page_number": 1,
       "quote": "Второй год — 45"
      },
      {
       "page_number": 1,
       "quote": "Третий год — 20"
      }
     ]
    }
   ]
  },
  "negative": {
   "pages": [
    "Проект организации строительства (вымышленный пример для проверки профиля)\nРаспределение капитальных вложений по годам строительства, %\nПервый год — 25\nВторой год — 45\nТретий год — 30\nИтого — 100",
    "Календарный план. Подготовительный период — 3 месяца, основной период — 9 месяцев. Общая продолжительность строительства — 11 месяцев."
   ],
   "observations": []
  }
 },
 "TX": {
  "positive": {
   "pages": [
    "Таблица технологических нагрузок. Предприятие «Кафе» (вымышленный пример для проверки профиля)\nПечь конвекционная — установленная мощность 12 кВт\nХолодильный шкаф — установленная мощность 1,5 кВт\nПосудомоечная машина — установленная мощность 9 кВт",
    "Пояснительная записка. Суммарная установленная мощность технологического оборудования предприятия «Кафе» составляет 28 кВт."
   ],
   "observations": [
    {
     "category": "internal_contradiction",
     "finding_text": "Синтетический ответ (ТХ), не результат вызова модели: суммарная установленная мощность оборудования предприятия «Кафе» в записке 28 кВт, а три строки таблицы нагрузок дают 22,5 кВт.",
     "recommendation_text": "Согласовать суммарную мощность в записке со строками таблицы нагрузок.",
     "evidence": [
      {
       "page_number": 2,
       "quote": "составляет 28 кВт"
      },
      {
       "page_number": 1,
       "quote": "установленная мощность 12 кВт"
      },
      {
       "page_number": 1,
       "quote": "установленная мощность 1,5 кВт"
      },
      {
       "page_number": 1,
       "quote": "установленная мощность 9 кВт"
      }
     ]
    }
   ]
  },
  "negative": {
   "pages": [
    "Таблица технологических нагрузок. Предприятие «Кафе» (вымышленный пример для проверки профиля)\nПечь конвекционная — установленная мощность 12 кВт\nХолодильный шкаф — установленная мощность 1,5 кВт\nПосудомоечная машина — установленная мощность 9 кВт",
    "Пояснительная записка. Суммарная установленная мощность технологического оборудования предприятия «Кафе» составляет 22,5 кВт, расчётная мощность с учётом коэффициента спроса — 18 кВт."
   ],
   "observations": []
  }
 },
 "KJ": {
  "positive": {
   "pages": [
    "Ведомость расхода стали (вымышленный пример для проверки профиля), кг\nКолонны К1 — 1240\nПлита перекрытия П1 — 3860\nСтены С1 — 2105\nИтого — 7500"
   ],
   "observations": [
    {
     "category": "internal_contradiction",
     "finding_text": "Синтетический ответ (КЖ), не результат вызова модели: итог ведомости расхода стали записан как 7500 кг, а три строки по маркам дают 7205 кг.",
     "recommendation_text": "Согласовать итог ведомости расхода стали со строками по маркам конструкций.",
     "evidence": [
      {
       "page_number": 1,
       "quote": "Итого — 7500"
      },
      {
       "page_number": 1,
       "quote": "Колонны К1 — 1240"
      },
      {
       "page_number": 1,
       "quote": "Плита перекрытия П1 — 3860"
      },
      {
       "page_number": 1,
       "quote": "Стены С1 — 2105"
      }
     ]
    }
   ]
  },
  "negative": {
   "pages": [
    "Ведомость расхода стали (вымышленный пример для проверки профиля), кг\nКолонны К1 — 1240\nПлита перекрытия П1 — 3860\nСтены С1 — 2105\nв том числе закладные детали — 140\nИтого — 7205"
   ],
   "observations": []
  }
 }
}
```

The replay (the throw-away script of the lane, shortened; it needs `PYTHONPATH=src:$BS` and the repository root as the working directory):

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

One change at a time on the committed tree; the section set is `test_text_profile_registry.py`, `tests/unit/analysis/text_profiles`, `test_section_recordings.py` and `tests/contract/analysis_packages` (322 cases; the unmutated tree: `322 passed`). After each restore the SHA-256 over the profile, fixture and test files equalled the one taken before (`restored=True`).

| # | Mutation | Result | First red cases |
|---|---|---|---|
| M1 | `profile.json` version `1.2.0` back to `1.1.0`, once each for PS, POS, TX, KJ (expectations kept) | 3 failed, 319 passed, each time | registry `test_the_tree_registers_without_error_and_without_an_ar_entry_or_package`; guard `test_every_line_agrees_with_its_package_profile_json`; packages `test_every_profile_manifest_has_the_text_profile_1_shape` |
| M2 | the expectations line back to `1.1.0`, once each for PS, POS, TX, KJ (`profile.json` kept) | 3 failed, 319 passed, each time | the same three |
| M2b | the PS line back to `1.1.0`, on the lane stack and in the web test | HTTP 1 failed, 3 passed; web 1 failed, 95 passed | `test_every_row_is_the_registry_entry_the_application_routes_by`; `has a line for exactly the packages that exist, with the status and version each declares` |
| M3 | the PS paragraph deleted, recording kept | 8 failed, 314 passed | `test_each_section_has_one_synthetic_recording_keyed_to_its_own_request[PS]`, `test_the_builder_reports_no_drift`, `test_the_served_adapter_answers_each_recorded_section_and_the_canonical_alone_does_not[PS]` |
| M4 | the TX recording replaced by the base file | 7 failed, 315 passed | the same recordings cases for TX |
| M5 | the PS paragraph deleted **and** the recordings rebuilt consistently | **322 passed**: no existing test notices (the `D-224` residual); the fragment check prints `MISSING` for 12 of the 56 pairs, all PS | the fragment check is the only red |
| M5b | a temp copy of the TX prompt without the tolerance bullet | fragment check: `MISSING W-B5 TX`, 1 of 56 | the fragment check |
| M6 | POS paragraph: the word «десяти» replaced by the numeral `10` | 5 failed, 104 passed | `test_every_designation_is_in_the_pinned_source_in_v1_or_the_allowlist[POS]` |
| M7 | KJ paragraph: a norm number «СП 999» added | 4 failed, 105 passed | `…[KJ]`, `test_inserting_an_invented_designation_turns_the_audit_red[cable marking-KJ]` |
| M8 | TX paragraph: a class designation «класс Г9» added | 3 failed, 106 passed | `…[TX]` |
| M9 | «revert the allowlist line» | not applicable: no line was added (see «Token-guard additions»); M6 to M8 show the guard is not vacuous for these prompts | none |
| M10 | one quote altered by one character in each positive specimen | `evidence_unresolved` 1 instead of 0, four times | the stage metrics (see «Specimens») |

## Commands and results

From `/root/projects/PDF-Analysis/.local/worktrees/section-widen-g1-01`, shared venv, one pytest at a time; `$BS` is `/root/projects/PDF-Analysis/.venv/bootstrap/lib/python3.12/site-packages`.

| Command | Result |
|---|---|
| section set (above), base tree | `322 passed` |
| section set, after the change | `322 passed` (no test added or edited, so no assertion was weakened) |
| `PYTHONPATH=src python3 -I fixtures/recorded/sections/build_fixtures.py`, then `--check` | four recordings replaced (`removed …` and `wrote …` for PS, POS, TX, KJ; the other ten byte-identical); `--check`: `fixtures match` |
| `tests/unit/analysis/text_profiles/test_prompt_token_guard.py` | `109 passed`, none skipped |
| `tests/integration/composition/test_analysis_profiles_over_http.py`, lane `.env` exported | `4 passed` |
| `npx vitest run tests/unit/analysis-settings` in `web/` | `7 passed` files, `96 passed` |
| governance one-liner on the task file | `[]` |
| `tests/contract/program tests/contract/api_v1/test_doc_prose_facts.py tests/contract/api_v1/test_surface_counts_in_prose.py`, `git diff --check` (committed, clean tree) | `105 passed` (about 21 s); `git diff --check 6075df88..HEAD` rc 0 |

Free disk: 1.9 GiB at the start, 1.8 GiB at the end. No docker command, no push, no tag, no model call, no network, no process killed, no database created.

## Recordings: what changed

For each of PS, POS, TX, KJ the new file differs from the old in `origin.prompt_bundle_sha256` and `request_sha256` only; the authored reply, usage and latency are unchanged (the reply is still the AR-corpus reply of `W59-ANALYSIS-SETTINGS-01` and `SECTION-RECORDINGS-01`). `AI` has the same key as before.

| Section | Old file | New file | Bundle hash |
|---|---|---|---|
| PS | `caf8aa0f…ab85` | `37de6fe1…dd23` | `6a34bb49` to `a7454996` |
| POS | `e399ef16…85f1` | `2ab0587d…08ae` | `30c5af14` to `f37abd4c` |
| TX | `1fa3402c…9313` | `13a339f2…658e` | `734b5c3e` to `5bc0b42d` |
| KJ | `0f614712…4bea` | `9fc3a5df…0340` | `3feca94f` to `0e31f979` |

## Integration notes

1. **Merge.** The expectations file changes four lines (`PS POS TX KJ`: `1.2.0`); on a conflict regenerate each line from its `profile.json`. Recordings: four keys changed, the other ten are byte-identical after the builder runs. Lanes G2 and G3 may reuse the paragraph word for word (fragments `W-HEAD` to `W-NORMS-2` except the scope and first-condition fragments) so that the sentence guard reads one table.
2. **The recordings test blocks the specimens (P-07).** To file a positive and a negative recording per section, either relax line 97 of `tests/integration/sections/test_section_recordings.py` (the section's own key file must be present; others may exist) and extend `build_fixtures.py` once for all lanes, or add a sibling directory (for example `fixtures/recorded/sections_widen/<code>/`, which the served adapter does not search) with a test that replays the specimens above through the stage. The specimens in this report are ready for either; both need a path outside every lane's allowed list, and three lanes would otherwise edit the same builder table.
3. **The allowlist cannot take lines from a widening lane (P-08).** `disclosed_by` must be a `SECTION-<CODE>-FULL-01.md` report. Lanes G2 and G3 may want the conversion factors of rule 4 (`3.6`, `1.163`, `1163`) in the prompts; that needs a change to the guard test or a decision to disclose them through a `FULL` report, both outside their paths. This lane avoided the problem by writing no designation.
4. **One rule for the omission topic across sections.** `EOM`, `SS` and `ITP` carry the same omission topic as `AI` and `TX`; reasons (a) to (c) of row AI-1 apply to them unchanged. The integrator may want the three lanes to decide it the same way.
5. **The input budget does not count a section's prompt (P-10).** `budget.py` subtracts the АР bundle's prompt length (about 3,000 characters), while a section's prompt was already 6,000 to 6,700 and is now 8,900 to 9,400. A document near the budget limit therefore costs a little more than the budget assumed (the new paragraph adds about 2,700 to 2,800 characters, under 2 % of the 152,361-character figure for the pinned model at a ceiling of 1.00). The lane that owns `budget.py` (`SECTION-CHUNKED-ANALYSIS-01`) may want the section bundle's own length in that term.
6. **Windows.** `W-B3` tells the model not to report a table that is cut off at the last page it was given, so a total in one window and its rows in the next are not compared; a run of independent windows should say so in its summary (the CH lane's task).
7. **A stored run keeps the old profile hash** (as in `SECTION-AI-FULL-01`, note 2): a run made with `1.1.0` carries the old `analysis_profile_sha256` and `prompt_bundle_sha256`; the registry resolves by the identity pair and serves the new text. Development stand only, no migration.
8. **Debt.** The refusal of the omission topic (AI-1, TX-1), the unmeasured model arithmetic, the specimens that no test reads and the budget term are the limits for a debt row; the lane did not edit `DEBT_REGISTER.md`.

## Limits

- No test reads the new sentences (`D-224` residual; M5 shows it). The fragment table above is the stand-in until `SECTION-PROMPT-SENTENCE-GUARD-01` reads it.
- No model was called. The effect of the paragraph on a real model (false findings from mis-added tables, missed findings from the strict conditions) is unknown.
- The specimens are hand-authored and not filed as fixtures.
- The lane did not change `W59-SECTION-PROFILES-01.md`, the ledger or the web label; the record still says the questions it asked, and the ledger still lists K for the cross-section question 2 that this lane now partly answers W.

## Proof that forbidden paths are untouched

`git diff --name-only --no-renames 6075df88..HEAD` on the final tree prints exactly these 19 paths, all inside the task's allowed paths (without `--no-renames` git folds each replaced recording into a rename):

```text
docs/program/SECTION-WIDEN-G1-01.md
docs/program/tasks/SECTION-WIDEN-G1-01.md
fixtures/recorded/sections/kj/0f61471253016dc653d9df836d5a0449443eff32c8be2836a2f7b780459e4bea.json
fixtures/recorded/sections/kj/9fc3a5dfc963a4cd72f8897c4bbc44c24ac1d991770b180c94b6575a4a090340.json
fixtures/recorded/sections/pos/2ab0587db7b2d22212cabbc7238f45d567361d25699a5c1bc7c3b709292b08ae.json
fixtures/recorded/sections/pos/e399ef16a725e478d9e15734776b81de7de726140bafbc6bea8b4126223785f1.json
fixtures/recorded/sections/ps/37de6fe13bdecb615949ecd331a1e88816d5e7b7698f35abe7fb58f9544dfd23.json
fixtures/recorded/sections/ps/caf8aa0fe2a34349618b85b74dd04175f4757579f9c4d0b64f726b5c2902ab85.json
fixtures/recorded/sections/tx/13a339f2aeebcec2be7ef4d14df9568c05231e420a9e77c16c617c6349ae658e.json
fixtures/recorded/sections/tx/1fa3402cd61588729135e440bdd0143a3d6f0e222785048771f08fcca89d9313.json
src/auditmanager/analysis/text/profiles/kj/profile.json
src/auditmanager/analysis/text/profiles/kj/system_prompt.md
src/auditmanager/analysis/text/profiles/pos/profile.json
src/auditmanager/analysis/text/profiles/pos/system_prompt.md
src/auditmanager/analysis/text/profiles/ps/profile.json
src/auditmanager/analysis/text/profiles/ps/system_prompt.md
src/auditmanager/analysis/text/profiles/tx/profile.json
src/auditmanager/analysis/text/profiles/tx/system_prompt.md
tests/unit/analysis/text_profiles/section_profile_expectations.json
```

No other section's files, no `W59-SECTION-PROFILES-01.md`, ledger, registry, `P02_LOCK.json`, `contracts/**`, migration, `web/**`, `infra/**`, `tests/integration/sections/**`, `build_fixtures.py` or allowlist appears. `/root/projects/PDF-proverka` was only read: its `HEAD` is the pinned `16ba8e5d…` and `git status --short` there prints nothing.
