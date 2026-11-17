/**
 * The designer's execution status of an accepted finding (`R-151g`, contract 1.24.0), in the original's SU-10 words.
 * Not an expert decision: it is shown beside the verdict, never instead of it.
 */

import type { FindingExecutionStatus } from '@/shared/api';

export const EXECUTION_STATUS_LABELS: Readonly<Record<FindingExecutionStatus, string>> = {
  taken_into_account: 'Учтено',
  amended: 'Внесено',
  declined: 'Отклонено',
  agreed: 'По согласованию',
};

export const EXECUTION_STATUS_ORDER: readonly FindingExecutionStatus[] = ['taken_into_account', 'amended', 'declined', 'agreed'];

/**
 * The second group of the knowledge base's cards, «Заказчик и проектировщик» (`UIP-S12-04`, `Г12-B`): two cards over the four statuses.
 * «Приняли в работу» is the designer's «Учтено» and «По согласованию»; «Исправили замечание» is «Внесено». The status «Отклонено» is in
 * none of them until the owner rules where it goes (the question is open): a finding the designer declined is neither taken into work
 * nor fixed, and no card says it is.
 */
export type ExecutionGroup = 'working' | 'fixed';

export const EXECUTION_GROUP_LABELS: Readonly<Record<ExecutionGroup, string>> = {
  working: 'Приняли в работу',
  fixed: 'Исправили замечание',
};

export const EXECUTION_GROUP_STATUSES: Readonly<Record<ExecutionGroup, readonly FindingExecutionStatus[]>> = {
  working: ['taken_into_account', 'agreed'],
  fixed: ['amended'],
};

/**
 * The statuses as the contract's `execution_status` filter takes them: one text, the values joined by commas. They are written in
 * `EXECUTION_STATUS_ORDER` whatever order they come in, so one set of statuses is one text and one cache entry.
 */
export function executionStatusQuery(statuses: readonly FindingExecutionStatus[]): string {
  return EXECUTION_STATUS_ORDER.filter((status) => statuses.includes(status)).join(',');
}

/** Every status there is: «the journal holds at least one», for the group of cards to be drawn at all. */
export const ANY_EXECUTION_STATUS_QUERY: string = executionStatusQuery(EXECUTION_STATUS_ORDER);
