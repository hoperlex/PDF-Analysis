'use client';

import type { RunStatus } from '@/shared/api';
import { failureMessage } from '@/shared/api';
import { useExecutionJournal } from '@/entities/execution';
import { ErrorState } from '@/shared/ui';

import { pdfPrecheckReading } from '../model/pdf-precheck-progress';

export function PdfPrecheckProgress({ status }: { readonly status: RunStatus }) {
  const sourceDone = status.stages.some((stage) => stage.stage_id === 'source_preparation' && stage.status === 'succeeded');
  const enabled = !sourceDone && ['created', 'queued', 'running', 'validating', 'failed'].includes(status.state);
  const journal = useExecutionJournal(status.run_id, undefined, enabled);
  if (!enabled) return null;
  if (journal.error !== null) {
    const failure = failureMessage(journal.error);
    return <ErrorState title="Ход проверки PDF не прочитан" detail={failure.detail} correlationId={failure.correlationId}
      onRetry={failure.retryable ? () => void journal.refetch() : undefined} />;
  }
  const reading = pdfPrecheckReading(journal.data?.items ?? [], status.run_id);
  if (reading.kind === 'absent') return null;
  if (reading.kind === 'invalid') return <p role="alert">Сведения о ходе проверки PDF некорректны. Обновите журнал выполнения.</p>;
  if (status.state === 'failed' && reading.phase !== 'failed') return null;
  if (reading.phase === 'failed') return <p role="alert" data-pdf-precheck="failed">PDF не прошёл проверку; дальнейший анализ остановлен.</p>;
  return <section aria-label="Проверка PDF перед анализом" data-pdf-precheck={reading.phase}>
    <p role="status" aria-live="polite">{reading.phase === 'completed' ? 'Проверка PDF завершена' : 'Проверка PDF перед анализом'}
      {reading.total > 0 ? `: ${reading.completed} из ${reading.total} страниц.` : ': подготовка.'}</p>
    {reading.total === 0 ? null : <progress aria-label="Проверено страниц PDF" value={reading.completed} max={reading.total} />}
  </section>;
}
