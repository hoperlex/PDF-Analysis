/**
 * `UI-A-60` / `R-151i`: what «Запустить с этапа» offers, and how a refusal of the reuse reads.
 *
 * A run is started from a stage of an **ended** run of the standard analysis; the stages before it are taken from that run
 * and the chosen one and the later ones are computed (`docs/program/RUN-FROM-STAGE-01.md`). The first stage reuses nothing --
 * that is a re-audit -- so only the three after it are offered. The server decides what may be taken; this file only names
 * the choices and puts the server's typed refusal into words.
 */

import type { RunState, StageId } from '@/shared/api';
import { ApiError } from '@/shared/api';
import { runStageLabel } from '@/shared/ui';
import { PC01_STAGE_IDS } from '@/entities/audit-run';

/** The stages a run may be started from: every stage PC-01 schedules after the first. */
export const STARTABLE_STAGE_IDS: readonly StageId[] = PC01_STAGE_IDS.slice(1);

const ENDED: ReadonlySet<RunState> = new Set<RunState>(['published', 'partial', 'failed', 'cancelled']);

/** A run that has ended has finished stages to take; one that has not has none. */
export function startableState(state: RunState | undefined): boolean {
  return state !== undefined && ENDED.has(state);
}

/** The roles `startRunFromStage` admits (as `reauditRun`); an unknown account is left to the server. */
export function mayStartFromStage(roles: readonly string[] | undefined): boolean {
  return roles === undefined || roles.includes('expert') || roles.includes('admin');
}

/** «2. Извлечение геометрии…»: the stage as the run's rail numbers it. */
export function startStageOption(stageId: StageId): string {
  const index = PC01_STAGE_IDS.indexOf(stageId as (typeof PC01_STAGE_IDS)[number]);
  return `${index < 0 ? '' : `${index + 1}. `}${runStageLabel(stageId)}`;
}

/** What each `reason` of an `analysis_input_invalid` refusal of the reuse says, for the stage it names. */
const REFUSAL_REASONS: Readonly<Record<string, (stage: string) => string>> = {
  source_stage_not_completed: (stage) => `Этап «${stage}» исходного прогона не завершён успешно, его результат взять нельзя.`,
  source_stage_version_changed: (stage) => `Результат этапа «${stage}» получен более старой версией этапа, чем действует сейчас; брать его нельзя.`,
  source_stage_output_incomplete: (stage) => `В результате этапа «${stage}» исходного прогона нет обязательных данных.`,
  source_artifact_unavailable: (stage) => `Сохранённый результат этапа «${stage}» исходного прогона недоступен.`,
  source_artifact_changed: (stage) => `Сохранённый результат этапа «${stage}» исходного прогона не совпадает с записанным.`,
  source_stage_inputs_changed: (stage) => `Условия выполнения этапа «${stage}» изменились с исходного прогона (допуск страниц без текстового слоя); результат взять нельзя.`,
};

function isStageId(value: unknown): value is StageId {
  return typeof value === 'string' && (PC01_STAGE_IDS as readonly string[]).includes(value);
}

/**
 * The sentence for a refused reuse, or `null` when the failure is anything else (the caller then says what it always says).
 * The refusal names the first stage that cannot be taken; the server wrote nothing and recomputed nothing.
 */
export function reuseRefusal(error: unknown): string | null {
  if (!(error instanceof ApiError) || error.errorCode !== 'analysis_input_invalid') return null;
  const reason = error.details.reason;
  const stage = error.details.stage_id;
  if (typeof reason !== 'string' || !isStageId(stage)) return null;
  const say = REFUSAL_REASONS[reason];
  return say === undefined ? null : `${say(runStageLabel(stage))} Новый прогон не создан; ничего не пересчитано вместо него.`;
}

export const REUSE_REFUSAL_REASONS: readonly string[] = Object.keys(REFUSAL_REASONS);
