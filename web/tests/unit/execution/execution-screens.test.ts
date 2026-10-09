import { readFileSync } from 'node:fs';
import { renderToStaticMarkup } from 'react-dom/server';
import { createElement } from 'react';
import { describe, expect, it } from 'vitest';

import type { ExecutionJournalEntry, ExecutionQueueItem, Role } from '@/shared/api';
import { ApiError, TransportError } from '@/shared/api';
import {
  canExecute, executionFailure, journalQueryOptions, queueAgeLabel, queueQueryOptions,
  visibleJournal,
} from '@/entities/execution';
import { ExecutionJournal } from '@/widgets/execution-journal';
import { ExecutionQueue } from '@/widgets/execution-queue';
import { intentLabel } from '@/_pages/queue/ui/queue-page';

const RUN_ID = 'run_01J9ZQ8K7NHVXW3T2R5M6P4Q8F';
const JOB_ID = 'job_01J9ZQ8K7NHVXW3T2R5M6P4Q8F';
const INSTANT = '2026-10-09T10:00:00Z';
const noop = () => {};
const queued: ExecutionQueueItem = {
  job_id: JOB_ID, run_id: RUN_ID, state: 'queued', priority: 2,
  created_at: INSTANT, available_at: INSTANT,
};

function queue(roles: Role[], item: ExecutionQueueItem = queued): string {
  return renderToStaticMarkup(createElement(ExecutionQueue, {
    items: [item], roles, asOf: Date.parse('2026-10-09T10:05:00Z'), busy: false,
    onCancel: noop, onReaudit: noop, onPriority: noop,
    onNext: null, onPrevious: null,
  }));
}

function envelope(code: 'permission_denied' | 'state_transition_not_allowed' | 'dependency_unavailable') {
  return {
    contract_version: '1.0.0-draft.1', error_code: code,
    message: 'Безопасный отказ.', correlation_id: 'cid-execution-1', retryable: false,
  } as const;
}

describe('execution roles and visible controls', () => {
  it('covers every role combination for each sealed action', () => {
    const cases: readonly [Role[], boolean, boolean][] = [
      [[], false, false], [['expert'], true, false],
      [['admin'], true, true], [['expert', 'admin'], true, true],
    ];
    for (const [roles, runCommand, adminCommand] of cases) {
      expect(canExecute(roles, 'cancel')).toBe(runCommand);
      expect(canExecute(roles, 'reaudit')).toBe(runCommand);
      expect(canExecute(roles, 'priority')).toBe(adminCommand);
      expect(canExecute(roles, 'pause')).toBe(adminCommand);
    }
  });

  it('hides unavailable actions while preserving server-side refusal handling', () => {
    expect(queue([])).not.toContain('Отменить прогон');
    expect(queue(['expert'])).toContain('Отменить прогон');
    expect(queue(['expert'])).not.toContain('Изменить</button>');
    expect(queue(['admin'])).toContain('Изменить</button>');
    expect(queue(['admin'], { ...queued, state: 'succeeded' })).toContain('Повторный аудит');
    expect(queue(['admin'], { ...queued, state: 'succeeded' })).not.toContain('Отменить прогон');
  });

  it('names the exact run in every row confirmation', () => {
    for (const kind of ['cancel', 'reaudit', 'priority'] as const) {
      const label = kind === 'priority'
        ? intentLabel({ kind, item: queued, priority: 7, key: 'ik-same-intent' })
        : intentLabel({ kind, item: queued, key: 'ik-same-intent' });
      expect(label).toContain(RUN_ID);
    }
  });
});

describe('typed read and command failures', () => {
  it('classifies a server 403 even when the control was visible from stale roles', () => {
    const failure = executionFailure(new ApiError(403, envelope('permission_denied'), null), true);
    expect(failure.kind).toBe('permission');
    expect(failure.correlationId).toBe('cid-execution-1');
  });

  it('keeps validating cancellation as a typed state refusal', () => {
    expect(executionFailure(new ApiError(409, envelope('state_transition_not_allowed'), null), true).kind)
      .toBe('transition');
  });

  it('does not turn an ambiguous 503 or network failure into a definite refusal', () => {
    expect(executionFailure(new ApiError(503, envelope('dependency_unavailable'), null), true).kind)
      .toBe('unknown_outcome');
    expect(executionFailure(new TransportError('connection closed'), true).kind)
      .toBe('unknown_outcome');
    expect(executionFailure(new TransportError('connection closed'), false).kind)
      .toBe('read_unavailable');
  });
});

describe('bounded journal and queue presentation', () => {
  const known: ExecutionJournalEntry = {
    event_id: 'evt_01J9ZQ8K7NHVXW3T2R5M6P4Q8F', run_id: RUN_ID,
    aggregate_id: RUN_ID, aggregate_type: 'AuditRun', event_type: 'audit_run.transition',
    occurred_at: INSTANT,
    payload: { to_state: 'queued', error_code: 'analysis_failed', secret: 'NEVER_RENDER_THIS' },
  };

  it('keeps a generic legacy event beside a known event without exposing raw fields', () => {
    const unknown: ExecutionJournalEntry = {
      ...known,
      event_id: 'evt_01J9ZQ8K7NHVXW3T2R5M6P4Q8G',
      event_type: 'raw.secret.provider.event',
      payload: { path: '/secret/provider/key', prompt: 'NEVER_RENDER_THIS' },
    };
    const markup = renderToStaticMarkup(createElement(ExecutionJournal, {
      entries: [known, unknown], onNext: null, onPrevious: null,
    }));
    expect(markup).toContain('Состояние прогона');
    expect(markup).toContain('Другое событие выполнения');
    expect(markup).toContain('в очереди');
    expect(markup).toContain('analysis_failed');
    expect(markup).not.toContain('raw.secret.provider.event');
    expect(markup).not.toContain('NEVER_RENDER_THIS');
    expect(markup).not.toContain('/secret/provider/key');
    expect(visibleJournal(unknown).code).toBeNull();
  });

  it('keeps queue cursors and run-filtered journal cursors separate and refreshes on focus', () => {
    expect(queueQueryOptions('first').queryKey).not.toEqual(queueQueryOptions('second').queryKey);
    expect(journalQueryOptions(RUN_ID, 'first').queryKey).not.toEqual(
      journalQueryOptions(RUN_ID, 'second').queryKey,
    );
    expect(journalQueryOptions(RUN_ID, 'first').queryKey).not.toEqual(
      journalQueryOptions('run_01J9ZQ8K7NHVXW3T2R5M6P4Q8G', 'first').queryKey,
    );
    expect(queueQueryOptions().refetchOnWindowFocus).toBe('always');
    expect(journalQueryOptions().refetchOnWindowFocus).toBe('always');
  });

  it('shows age without a timer and preserves long opaque identities at 780 px', () => {
    expect(queueAgeLabel(INSTANT, Date.parse('2026-10-09T10:05:00Z'))).toBe('5 мин');
    const markup = queue(['admin']);
    expect(markup).toContain(RUN_ID);
    const css = readFileSync(new URL('../../../src/widgets/execution-queue/ui/execution-queue.module.css', import.meta.url), 'utf8');
    expect(css).toContain('overflow-wrap: anywhere');
    expect(css).toContain('max-width: 100%');
    expect(css).not.toMatch(/min-width:\s*\d+px/);
  });

  it('keeps the back control when a cursor resolves to an empty page', () => {
    const markup = renderToStaticMarkup(createElement(ExecutionJournal, {
      entries: [], onNext: null, onPrevious: noop,
    }));
    expect(markup).toContain('На этой странице записей нет');
    expect(markup).toContain('>Назад</button>');
  });
});
