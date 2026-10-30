import { describe, expect, it } from 'vitest';

import type { ExecutionJournalEntry } from '@/shared/api';
import { pdfPrecheckReading } from '@/widgets/run-progress/model/pdf-precheck-progress';

const RUN = 'run_01M2545JSD15ETSNNV904X991J';
function entry(payload: ExecutionJournalEntry['payload'], second = 1): ExecutionJournalEntry {
  return { event_id: `evt_${second}`, event_type: 'stage.pdf_precheck', aggregate_type: 'AuditRun', aggregate_id: RUN,
    run_id: RUN, occurred_at: `2026-10-30T00:00:0${second}Z`, payload: { stage_id: 'source_preparation', ...payload } };
}

describe('durable PDF validation progress', () => {
  it('shows the latest real page count regardless of page ordering', () => {
    expect(pdfPrecheckReading([
      entry({ phase: 'checking', completed_pages: 3, total_pages: 20 }, 3),
      entry({ phase: 'started', completed_pages: 0, total_pages: 20 }, 1),
    ], RUN)).toEqual({ kind: 'progress', phase: 'checking', completed: 3, total: 20 });
  });
  it('accepts completed and failed records without claiming analysis success', () => {
    expect(pdfPrecheckReading([entry({ phase: 'completed', completed_pages: 20, total_pages: 20 })], RUN))
      .toEqual({ kind: 'progress', phase: 'completed', completed: 20, total: 20 });
    expect(pdfPrecheckReading([entry({ phase: 'failed', completed_pages: 3, total_pages: 20, error_code: 'analysis_failed' })], RUN))
      .toEqual({ kind: 'progress', phase: 'failed', completed: 3, total: 20 });
  });
  it('never falls back from malformed newer evidence to older progress', () => {
    expect(pdfPrecheckReading([entry({ phase: 'checking', completed_pages: 3, total_pages: 20 }),
      entry({ phase: 'completed', completed_pages: 5, total_pages: 20 }, 2)], RUN)).toEqual({ kind: 'invalid' });
  });
  it.each([[-1, 20], [21, 20], [1.5, 20], [0, -1], [true, 20]])('refuses impossible counts %s/%s', (completed, total) => {
    expect(pdfPrecheckReading([entry({ phase: 'checking', completed_pages: completed, total_pages: total })], RUN)).toEqual({ kind: 'invalid' });
  });
  it('does not borrow progress from another run or unrelated event', () => {
    expect(pdfPrecheckReading([{ ...entry({ phase: 'checking', completed_pages: 3, total_pages: 20 }), run_id: 'run_other' }], RUN)).toEqual({ kind: 'absent' });
    expect(pdfPrecheckReading([], RUN)).toEqual({ kind: 'absent' });
  });
});
