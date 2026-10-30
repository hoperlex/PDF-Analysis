import type { ExecutionJournalEntry } from '@/shared/api';

export type PdfPrecheckPhase = 'started' | 'checking' | 'completed' | 'failed';
export type PdfPrecheckReading =
  | { readonly kind: 'absent' }
  | { readonly kind: 'invalid' }
  | { readonly kind: 'progress'; readonly phase: PdfPrecheckPhase; readonly completed: number; readonly total: number };

const PHASES: readonly string[] = ['started', 'checking', 'completed', 'failed'];

/** Latest authority-fenced event only; a malformed latest event cannot revive an older progress bar. */
export function pdfPrecheckReading(entries: readonly ExecutionJournalEntry[], runId: string): PdfPrecheckReading {
  const row = entries.filter((entry) => entry.run_id === runId && entry.aggregate_type === 'AuditRun'
    && entry.aggregate_id === runId && entry.event_type === 'stage.pdf_precheck')
    .sort((left, right) => right.occurred_at.localeCompare(left.occurred_at) || right.event_id.localeCompare(left.event_id))[0];
  if (row === undefined) return { kind: 'absent' };
  const { phase, completed_pages: completed, total_pages: total, stage_id: stage } = row.payload;
  if (stage !== 'source_preparation' || typeof phase !== 'string' || !PHASES.includes(phase)
    || typeof completed !== 'number' || !Number.isSafeInteger(completed) || completed < 0
    || typeof total !== 'number' || !Number.isSafeInteger(total) || total < 0 || completed > total
    || (phase === 'completed' && (total === 0 || completed !== total))) return { kind: 'invalid' };
  return { kind: 'progress', phase: phase as PdfPrecheckPhase, completed, total };
}
