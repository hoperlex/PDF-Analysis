/**
 * The journal is a table of one-line events, as the original's log is a column of one-line records: time, what happened,
 * the state and code the closed projection allows, and the run -- a link that narrows the journal to it.
 */

import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it } from 'vitest';

import type { ExecutionJournalEntry } from '@/shared/api';
import { ExecutionJournal } from '@/widgets/execution-journal';

const RUN_ID = 'run_01J9ZQ8K7NHVXW3T2R5M6P4Q8F';
const entry = (id: string, eventType: string, payload: ExecutionJournalEntry['payload']): ExecutionJournalEntry => ({
  event_id: `evt_01J9ZQ8K7NHVXW3T2R5M6P4Q8${id}`, run_id: RUN_ID, aggregate_id: RUN_ID, aggregate_type: 'AuditRun',
  event_type: eventType, occurred_at: '2026-10-09T10:00:00Z', payload,
});

function drawn(entries: readonly ExecutionJournalEntry[]): string {
  return renderToStaticMarkup(createElement(ExecutionJournal, { entries, onNext: null, onPrevious: null }));
}

describe('the journal lines', () => {
  it('draws one table row per event under five named columns', () => {
    const markup = drawn([entry('F', 'audit_run.created', {}), entry('G', 'audit_run.transition', { to_state: 'queued' })]);
    expect(markup).toContain('data-journal-table');
    for (const heading of ['Время', 'Событие', 'Состояние', 'Код', 'Прогон']) expect(markup).toContain(`>${heading}</th>`);
    expect(markup.match(/<tr>/g)).toHaveLength(3);
  });

  it('links the run to the journal narrowed to it', () => {
    expect(drawn([entry('F', 'audit_run.created', {})])).toContain(`href="/logs?run_id=${RUN_ID}"`);
  });

  it('draws no table for an empty first page', () => {
    const markup = drawn([]);
    expect(markup).not.toContain('<table');
    expect(markup).toContain('Записей пока нет');
  });
});
