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
