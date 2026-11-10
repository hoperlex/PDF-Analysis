/**
 * Every state of the decision memory's widgets that one static pass can reach, as screen cases (`D-495`).
 *
 * `tests/guards/rendered-language.guard.test.ts` renders each in every cache state of its matrix: no Latin word a contract did not
 * put there, and every mandatory-state branch of the widgets seen by some state. The states a press would reach (a withdraw
 * refused by the server, a filter chosen) are not here: the harness fires no event.
 */

import type { QueryClient } from '@tanstack/react-query';
import { Fragment, createElement } from 'react';
import type { ReactElement } from 'react';

import { DecisionMemoryCaseView, DecisionMemoryFilters, DecisionMemoryList, DecisionMemoryStatusLine } from '@/widgets/decision-memory';
import { NO_MEMORY_FILTERS } from '@/entities/decision-memory';

import { COUNTS, CASE_B, CASE_C, summary, wholeCase } from './memory-fixtures';

export interface MemoryShape {
  readonly name: string;
  readonly make: () => ReactElement;
  readonly seedClient?: (client: QueryClient) => void;
}

const noop = () => undefined;

const listOf = (props: Partial<Parameters<typeof DecisionMemoryList>[0]>) =>
  createElement(DecisionMemoryList, { cases: [], isLoading: false, error: null, narrowed: false, onOpen: noop, ...props });

const caseOf = (props: Partial<Parameters<typeof DecisionMemoryCaseView>[0]>) =>
  createElement(DecisionMemoryCaseView, { data: wholeCase(), isLoading: false, error: null, manage: true, onBack: noop, ...props });

const WITHDRAWN = wholeCase(
  { status_events: [{ status_event_id: 'dmw_01M2545JSD15ETSNNV904X996E', kind: 'withdraw', reason_code: 'test_data', created_at: '2026-11-09T10:00:00Z', forgotten_content_sha256: null }] },
  { status: 'withdrawn', status_reason_code: 'test_data', status_changed_at: '2026-11-09T10:00:00Z' },
);

const FORGOTTEN = wholeCase(
  {
    content: null, decisions: [], evidence: [], norm_refs: [], crops: [],
    status_events: [{ status_event_id: 'dmw_01M2545JSD15ETSNNV904X997F', kind: 'forget', reason_code: 'client_request', created_at: '2026-11-09T12:00:00Z', forgotten_content_sha256: 'c'.repeat(64) }],
  },
  { status: 'forgotten', status_reason_code: 'client_request' },
);

export const MEMORY_SHAPES: readonly MemoryShape[] = [
  {
    name: 'memory-list-every-standing',
    make: () =>
      listOf({
        cases: [
          summary(),
          summary({ case_id: CASE_B, status: 'withdrawn', status_reason_code: 'wrong_decision', current_verdict: 'rejected', current_severity: null, data_class: 'real', decision_count: 2 }),
          summary({ case_id: CASE_C, status: 'forgotten', status_reason_code: 'client_request', current_verdict: null, current_severity: null, section_code: null }),
        ],
      }),
  },
  { name: 'memory-list-loading', make: () => listOf({ isLoading: true }) },
  { name: 'memory-list-empty', make: () => listOf({}) },
  { name: 'memory-list-empty-under-a-selection', make: () => listOf({ narrowed: true, onResetFilters: noop }) },
  { name: 'memory-list-failed', make: () => listOf({ error: { title: 'Память решений не открылась', detail: 'Сервер не ответил. Проверьте соединение и повторите запрос.', correlationId: '3f2504e0-4f89-11d3-9a0c-0305e82c3301' } }) },
  { name: 'memory-case-active', make: () => caseOf({}) },
  { name: 'memory-case-read-only', make: () => caseOf({ manage: false }) },
  { name: 'memory-case-withdrawn', make: () => caseOf({ data: WITHDRAWN }) },
  { name: 'memory-case-forgotten', make: () => caseOf({ data: FORGOTTEN }) },
  { name: 'memory-case-loading', make: () => caseOf({ data: undefined, isLoading: true }) },
  { name: 'memory-case-failed', make: () => caseOf({ data: undefined, error: { title: 'Дело не открылось', detail: 'Запрошенного дела нет.', correlationId: '3f2504e0-4f89-11d3-9a0c-0305e82c3302' } }) },
  {
    name: 'memory-status-line',
    make: () =>
      createElement(
        Fragment,
        null,
        createElement(DecisionMemoryStatusLine, { status: COUNTS, error: null }),
        createElement(DecisionMemoryStatusLine, { status: { ...COUNTS, data_class: 'real', training_use: 'on' }, error: null }),
        createElement(DecisionMemoryStatusLine, { status: undefined, error: { title: 'Сводка памяти не получена', detail: 'Сервер не ответил.', correlationId: '3f2504e0-4f89-11d3-9a0c-0305e82c3303' } }),
      ),
  },
  { name: 'memory-filters', make: () => createElement(DecisionMemoryFilters, { value: NO_MEMORY_FILTERS, onChange: noop }) },
];
