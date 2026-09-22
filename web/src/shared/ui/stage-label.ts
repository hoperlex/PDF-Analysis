/**
 * The Russian name of each analysis stage.
 *
 * The owner ruled on 2026-09-22 that everything a reviewer can read is shown in Russian
 * and the machine value keeps its home in a `data-` attribute. `D-62` records the place
 * that ruling had not reached: the run screen's stage table rendered
 * `<code>{row.stageId}</code>`, so the first column of the one table on that screen was
 * `source_preparation`, `page_geometry_extraction`, `document_context_build`,
 * `text_analysis` — four machine words and no sentence beside any of them. The language
 * guard permitted them because `StageId` was left in its `TRANSLATED_SCHEMAS` exception on
 * the argument that a stage id is an identifier shown deliberately beside its meaning.
 * That argument is true of `terminal_reason` and was false here.
 *
 * ## Why it lives in `shared/ui` and not in `entities/audit-run`
 *
 * `VERDICT_LABELS` and `STATE_LABELS` were each written private and each had to be
 * exported once a second consumer rendered around them — `decision-history` printed a
 * verdict, `run-progress` printed `<code>{status.state}</code>` in three sentences. This
 * map has **two** consumers on the day it is written: `entities/audit-run`'s stage table
 * and `widgets/run-progress`'s degradation list, which prints a stage id per `partial`
 * run. So the question is not whether to export it but where it has to sit to be
 * reachable by everything that will want it.
 *
 * A stage id is not the run aggregate's private vocabulary. It is a contract enum that
 * also arrives in an error envelope's `details.stage_id` (`analysis_input_invalid`,
 * `stale_attempt`) and in `RunStatus.degradation_set`. `shared` is reachable from every
 * layer; `entities/audit-run` is reachable from widgets, features and pages but not from
 * `shared/ui`'s own badges nor from another entity. Putting the map in the narrower place
 * is what made the other two maps move later, and it would have been the same mistake a
 * third time.
 *
 * It sits beside `STATE_LABELS` (`RunState`) and `STAGE_STATUS_LABELS` (`StageStatus`) for
 * the same reason those are here: a label is not an identity, and translating a contract
 * value for the screen is presentation, not domain logic.
 *
 * ## Why it is keyed on the type rather than on the four PC-01 schedules
 *
 * `Record<StageId, string>` over the whole contract enum. `W33-SECT` keyed its label maps
 * on the contract type and the type checker named two members its grep had not found. The
 * nine here are exactly the nine `openapi.json` publishes: a tenth stage cannot be added to
 * the contract without this file failing to compile, which is the difference between a map
 * and a list that was right once.
 *
 * The wording follows each stage's own `title` in `contracts/analysis/v1/stage-registry.json`
 * rather than being invented, so a reader who has the contract open recognises the row.
 * `web/tests/guards/stage-vocabulary.guard.test.ts` holds the keys to the contract enum in
 * both directions and refuses a label that is not Cyrillic.
 */

import type { StageId } from '@/shared/api';

export const STAGE_LABELS: Readonly<Record<StageId, string>> = {
  source_preparation: 'Подготовка источника',
  page_geometry_extraction: 'Извлечение геометрии страниц и блоков',
  document_context_build: 'Построение контекста документа',
  text_analysis: 'Анализ текста',
  block_analysis: 'Блочный и визуальный анализ',
  finding_merge: 'Слияние и дедупликация находок',
  finding_review: 'Проверка и обоснование находок',
  finding_correction: 'Исправление находок',
  norm_verification: 'Нормативная проверка',
};
