/**
 * `EXEC-PAR-WEB-01`: the journal entry a start that names its executor writes
 * (`audit_run.executor_chosen`, `EXEC-PAR-START-01`) has a label, and it is the one the task words.
 */

import { describe, expect, it } from 'vitest';

import type { ExecutionJournalEntry } from '@/shared/api';
import { visibleJournal } from '@/entities/execution';

function entry(eventType: string, payload: Record<string, unknown> = {}): ExecutionJournalEntry {
  return {
    event_id: 'evt_01J9ZQ8K7NHVXW3T2R5M6P4Q8F',
    run_id: 'run_01J9ZQ8K7NHVXW3T2R5M6P4Q8F',
    aggregate_id: 'run_01J9ZQ8K7NHVXW3T2R5M6P4Q8F',
    aggregate_type: 'AuditRun',
    event_type: eventType,
    occurred_at: '2026-10-26T10:00:00Z',
    payload,
  } as ExecutionJournalEntry;
}

describe('the journal names the choice of an executor', () => {
  it('labels audit_run.executor_chosen «Выбран исполнитель»', () => {
    expect(visibleJournal(entry('audit_run.executor_chosen')).event).toBe('Выбран исполнитель');
  });

  it('shows nothing the entry’s payload carries: the connection and its revision stay out', () => {
    const shown = visibleJournal(entry('audit_run.executor_chosen', {
      connection_id: 'exc_01J9ZQ8K7NHVXW3T2R5M6P4Q8F', revision_id: 'excr_01J9ZQ8K7NHVXW3T2R5M6P4Q8F',
    }));
    expect(shown).toEqual({ event: 'Выбран исполнитель', state: null, code: null });
  });

  it('keeps the other labels, and still calls an event it does not know by the general name', () => {
    expect(visibleJournal(entry('audit_run.created')).event).toBe('Прогон создан');
    expect(visibleJournal(entry('audit_run.executor_chosen_elsewhere')).event).toBe('Другое событие выполнения');
  });
});
