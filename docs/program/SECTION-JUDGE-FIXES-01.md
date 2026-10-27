# SECTION-JUDGE-FIXES-01 — the fixes for the independent judge's findings on the section-analysis path

Task: `docs/program/tasks/SECTION-JUDGE-FIXES-01.md`. Branch `agent/section-judge-fixes-01`, base `93bc5037` (`integration/ar-close-1026`).

(Report body: written last. This file already carries the machine-readable fragment block below, which the
sentence-guard builder reads.)

## The prompt sentences (finding 3)

<!-- fragments:begin -->
```json
[
 {
  "id": "J-INTRO",
  "sections": [
   "AI",
   "TX",
   "EOM",
   "SS",
   "ITP"
  ],
  "role": "category list: two categories for the question above, documentation only for the omission paragraph",
  "text": "Для вопроса выше — ровно две категории; третья, documentation, допустима только для пропуска из абзаца об исключении ниже:"
 },
 {
  "id": "J-HINT",
  "sections": [
   "AI",
   "TX",
   "EOM",
   "SS",
   "ITP"
  ],
  "role": "checklist hint: the two categories for the hints, documentation only for the omission paragraph",
  "text": "по этим подсказкам сообщай только то, что подпадает под одну из двух категорий выше (documentation — только для пропуска из абзаца об исключении ниже):"
 },
 {
  "id": "J-CATEGORY",
  "sections": [
   "AI",
   "TX",
   "EOM",
   "SS",
   "ITP"
  ],
  "role": "reply rule: the category value, documentation for the omission paragraph and nothing else",
  "text": "- category — одно из двух значений выше; documentation — только для пропуска из абзаца об исключении, и ни для чего другого."
 },
 {
  "id": "J-OLD-INTRO",
  "sections": [
   "AI",
   "TX",
   "EOM",
   "SS",
   "ITP"
  ],
  "kind": "absent",
  "role": "removed: «exactly two categories, there is no third» contradicted the schema that allows documentation",
  "text": "Ровно две категории, третьей нет:"
 },
 {
  "id": "J-OLD-HINT",
  "sections": [
   "AI",
   "TX",
   "EOM",
   "SS",
   "ITP"
  ],
  "kind": "absent",
  "role": "removed: «report only one of the two categories above» left no room for the omission paragraph",
  "text": "сообщай только то, что подпадает под одну из двух категорий выше:"
 },
 {
  "id": "J-OLD-CATEGORY",
  "sections": [
   "AI",
   "TX",
   "EOM",
   "SS",
   "ITP"
  ],
  "kind": "absent",
  "role": "removed: «category is strictly one of the two values above» contradicted the schema that allows documentation",
  "text": "- category — строго одно из двух значений выше."
 }
]
```
<!-- fragments:end -->
