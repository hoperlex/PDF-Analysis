/**
 * The one stage dictionary of the application (`RUN-SCREEN-01a`, plan `executors-runs-rework-plan` §4.1 and §9.2).
 *
 * The code runs ten phases under nine contract stage ids (`contracts/analysis/v1/stage-registry.json`) and the extended review's
 * procedure ids; a reader sees **eight chips**. A chip is a reader's name for the phase or phases of code that do one kind of work,
 * and this file is the only place that says which ids belong to which chip, what each is called — short on the rail, full in the
 * dialog and wherever a phase is named in a sentence — and whether the work calls a model. The rail, the «Этапы анализа раздела»
 * dialog and the batch panel of the extended review all read it, so one phase is called one thing everywhere (before this file the
 * block phase was «Анализ блоков» on the rail and «Анализ изображений» in the batch panel).
 *
 * A chip is a **display grouping, not an order of the contract's graph**: `text_analysis` and `block_analysis` wait for the same
 * stage and have no order between them (`STAGE_DEPENDS_ON`, held by `stage-vocabulary.guard.test.ts`). The order below is the order
 * the rail draws them in, which is the order the code runs them in today. `web/tests/guards/stage-dictionary.guard.test.ts` holds
 * the dictionary to the registry: every contract stage belongs to exactly one chip, and a chip calls a model exactly when its
 * stages are model-routed there.
 *
 * `comprehensive_analysis` is not a contract stage id: it is the extended review's procedure of that name, and it is the whole of
 * the «Сверка» chip. It is listed with the stage ids because the extended review's `procedures` are keyed by it.
 */

import { AR_V3_BETA_STAGE_LABELS } from '@/shared/ui';

/** The eight chips, in the order the rail draws them. */
export const RUN_CHIP_IDS = [
  'preparation',
  'text',
  'blocks',
  'cross_check',
  'merge',
  'norms',
  'review',
  'correction',
] as const;

export type RunChipId = (typeof RUN_CHIP_IDS)[number];

/** The chip of the separate AR v3 beta profile, which has one stage of its own and none of the eight. */
export const AR_V3_CHIP_ID = 'ar_v3' as const;

export interface RunChipDefinition {
  readonly id: RunChipId | typeof AR_V3_CHIP_ID;
  /** The name on the rail and in the dialog's list. */
  readonly short: string;
  /** The name in a sentence and in the dialog's heading. */
  readonly full: string;
  /** Every code id the chip covers: contract stage ids and the extended review's procedure ids. */
  readonly stageIds: readonly string[];
  /** Whether the chip's work calls a model. A chip that does not carries no model on the rail. */
  readonly callsModel: boolean;
}

export const RUN_CHIPS: readonly RunChipDefinition[] = [
  {
    id: 'preparation',
    short: 'Подготовка',
    full: 'Подготовка документа',
    stageIds: ['source_preparation', 'page_geometry_extraction', 'document_context_build'],
    callsModel: false,
  },
  { id: 'text', short: 'Текст', full: 'Анализ текста', stageIds: ['text_analysis'], callsModel: true },
  { id: 'blocks', short: 'Блоки', full: 'Анализ блоков', stageIds: ['block_analysis'], callsModel: true },
  { id: 'cross_check', short: 'Сверка', full: 'Комплексная сверка', stageIds: ['comprehensive_analysis'], callsModel: true },
  { id: 'merge', short: 'Свод', full: 'Свод наблюдений', stageIds: ['finding_merge'], callsModel: false },
  { id: 'norms', short: 'Нормы', full: 'Нормативная проверка', stageIds: ['norm_verification'], callsModel: true },
  { id: 'review', short: 'Критик', full: 'Критик наблюдений', stageIds: ['finding_review'], callsModel: true },
  { id: 'correction', short: 'Уточнение', full: 'Предложения по уточнению', stageIds: ['finding_correction'], callsModel: true },
];

/** The eight chips by id: a total lookup, for a caller that names a chip it knows is there. */
export const RUN_CHIP: Readonly<Record<RunChipId, RunChipDefinition>> = Object.fromEntries(
  RUN_CHIPS.map((chip) => [chip.id, chip] as const),
) as Record<RunChipId, RunChipDefinition>;

export const AR_V3_RUN_CHIP: RunChipDefinition = {
  id: AR_V3_CHIP_ID,
  short: 'Ссылки АР v3',
  full: AR_V3_BETA_STAGE_LABELS.ar_v3_citation_review,
  stageIds: ['ar_v3_citation_review'],
  callsModel: true,
};

const BY_STAGE: ReadonlyMap<string, RunChipDefinition> = new Map(
  [...RUN_CHIPS, AR_V3_RUN_CHIP].flatMap((chip) => chip.stageIds.map((stageId) => [stageId, chip] as const)),
);

const BY_ID: ReadonlyMap<string, RunChipDefinition> = new Map([...RUN_CHIPS, AR_V3_RUN_CHIP].map((chip) => [chip.id, chip] as const));

/** The chip that covers a code id (a contract stage id or a procedure id), or `null` for an id no chip covers. */
export function chipOfStage(stageId: string): RunChipDefinition | null {
  return BY_STAGE.get(stageId) ?? null;
}

/** The chip with this id, or `null`. */
export function chipById(id: string): RunChipDefinition | null {
  return BY_ID.get(id) ?? null;
}

/**
 * The full name of the phase a code id belongs to, or `null` when no chip covers it (the report phase, which has no chip).
 * The extended review's batch panel names its phases through this.
 */
export function phaseFullLabel(stageId: string): string | null {
  return chipOfStage(stageId)?.full ?? null;
}
