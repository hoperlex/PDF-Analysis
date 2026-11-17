/**
 * The sentence for a run's `interrupted_reason` (`RUN-RESTART-01`, `R-155c`): «Прогон остановлен: нет признаков работы 30 минут», and the
 * chip the silence was on when the run says so (`terminal_detail.stage_id`, a stage or procedure id the stage dictionary maps to a chip).
 * `null` for a reason that has no words of its own, which the screen prints as the server wrote it.
 */

import type { RunStatus } from '@/shared/api';
import { interruptedReasonLabel } from '@/shared/ui';
import { chipById, chipOfStage, interruptedReason } from '@/entities/audit-run';

export function interruptedSentence(status: Pick<RunStatus, 'interrupted_reason' | 'terminal_detail'>): string | null {
  const reason = interruptedReason(status);
  const label = reason === null ? null : interruptedReasonLabel(reason);
  if (label === null) return null;
  const stage = status.terminal_detail?.stage_id;
  const chip = typeof stage === 'string' ? (chipOfStage(stage) ?? chipById(stage)) : null;
  return chip === null ? `${label}.` : `${label} на этапе «${chip.short}».`;
}
