/**
 * The words of the window «Этапы анализа раздела» for what `getRunStages` states (`RUN-STAGES-WEB-01`, ADR-0028 plan §9.4): one
 * line for each cell of a chip's plan, and the facts of the chip as short phrases.
 *
 * Pure: a stage of the answer in, strings out. A figure the answer does not carry is not written; nothing is estimated or filled
 * in, and a zero is written as a zero (a chip that made no call says «успешно 0», it does not go blank). The words of the roles,
 * the efforts and the access are the layout's and the servers' own (`entities/stage-layout`, `entities/executor-host`), so a
 * model is described in this window as it is in «Модели по этапам».
 */

import type { RunStageCell, RunStageFacts, StageCellRole } from '@/shared/api';
import { groupDigits, shortModelName } from '@/entities/audit-run';
import { microsAsUsd } from '@/shared/ui';
import { ACCESS_LABELS } from '@/entities/executor-host';
import { STAGE_EFFORT_LABELS, STAGE_ROLE_LABELS } from '@/entities/stage-layout';

/** «Модель» for the one answer of a chip; «Первая ветка», «Вторая ветка», «Судья» for the parts of an ensemble. */
export function cellRoleLabel(role: StageCellRole): string {
  const label = STAGE_ROLE_LABELS[role];
  return label === '' ? 'Модель' : `${label.charAt(0).toUpperCase()}${label.slice(1)}`;
}

export interface CellLine {
  /** A key that is the same on every read of the same run: the cell's own, else its role. */
  readonly key: string;
  readonly role: StageCellRole;
  readonly roleLabel: string;
  /** «Opus 5.5»; `null` where the answer names no model for the cell. */
  readonly model: string | null;
  /** The pin as the answer has it, for the tooltip and the small code beside a short name. */
  readonly pin: string | null;
  readonly effort: string | null;
  /** The server and the access, or `null` when the reader may not see them or the answer has neither. */
  readonly server: string | null;
}

function serverText(cell: RunStageCell): string | null {
  const access = cell.access === undefined ? null : ACCESS_LABELS[cell.access];
  if (cell.server !== undefined) return access === null ? `сервер ${cell.server}` : `сервер ${cell.server} · ${access}`;
  return access === null ? null : `${access} · сервер не назначен`;
}

/** One line for each cell of the plan, in the order the answer gives them (`main`, the legs, the judge). */
export function cellLines(plan: readonly RunStageCell[], showServer: boolean): readonly CellLine[] {
  return plan.map((cell) => ({
    key: cell.cell_key ?? cell.role,
    role: cell.role,
    roleLabel: cellRoleLabel(cell.role),
    model: shortModelName(cell.model_id),
    pin: cell.model_id ?? null,
    effort: cell.effort === undefined ? null : `усилие: ${STAGE_EFFORT_LABELS[cell.effort]}`,
    server: showServer ? serverText(cell) : null,
  }));
}

/** «успешно 5 · с ошибкой 1 · повторов 1»: the calls the journal ended, and the ones that repeated an earlier call. */
export function callsText(facts: RunStageFacts): string {
  return `успешно ${groupDigits(facts.calls_succeeded)} · с ошибкой ${groupDigits(facts.calls_failed)} · повторов ${groupDigits(facts.calls_retried)}`;
}

/** Whether the chip made any call or spent any token: a chip that did neither has no row of calls, tokens or cost to show. */
export function hasModelWork(facts: RunStageFacts): boolean {
  return facts.calls_succeeded + facts.calls_failed + facts.calls_retried + facts.input_tokens + facts.output_tokens > 0;
}

/**
 * «входных 61 240 · выходных 9 310», and, where a subscription served some, «по подписке: входных … · выходных …». The words are not
 * «вход» and «выход»: a sentence with the bare «вход» beside a «нет» reads to the screen guard as a denial of the sign-in.
 */
export function tokensText(facts: RunStageFacts): string {
  const total = `входных ${groupDigits(facts.input_tokens)} · выходных ${groupDigits(facts.output_tokens)}`;
  if (facts.subscription_input_tokens + facts.subscription_output_tokens === 0) return total;
  return `${total} · по подписке: входных ${groupDigits(facts.subscription_input_tokens)} · выходных ${groupDigits(facts.subscription_output_tokens)}`;
}

/**
 * The cost of the chip, or `null` for no row. A chip served wholly by a subscription has no price, and says so instead of «0»
 * (a subscription's tokens are never in `cost_micros`); a chip with no call has no cost to state. Otherwise the figure is the
 * dollar figure of the integer millionths as the «Расход» tile draws it (`microsAsUsd`), which never passes through a float.
 */
export function costText(facts: RunStageFacts): string | null {
  const total = facts.input_tokens + facts.output_tokens;
  const subscription = facts.subscription_input_tokens + facts.subscription_output_tokens;
  if (facts.cost_micros === 0 && total > 0 && subscription >= total) return 'по подписке, не считается';
  if (facts.cost_micros === 0 && !hasModelWork(facts)) return null;
  return `$${microsAsUsd(facts.cost_micros)}`;
}
