/**
 * `analysis_input_budget_exceeded` (`R-118`): refused up front by `startRun` and by
 * `reauditRun`, shown with its two figures, and never with a retry (`W55B-WEB-BLOCKS`).
 *
 * Three subjects: the figure sentence itself (the one place the numbers become words), the
 * two classifiers that meet the refusal — `classifyRunFailure` for the start-run control and
 * `executionFailure` for the queue's re-audit command — and the start-run control rendered
 * over a settled refusal, which is where a reader sees it.
 */

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it, vi } from 'vitest';

const settled = vi.hoisted(() => ({ error: null as unknown }));

// The control reads its refusal off its mutation; a static render cannot settle one, so the
// mutation hook answers with the refusal this file puts in `settled`.
vi.mock('@tanstack/react-query', async (importOriginal) => {
  const actual = await importOriginal<Record<string, unknown>>();
  return {
    ...actual,
    useMutation: () => ({ mutate: () => {}, isPending: false, error: settled.error }),
    useQueryClient: () => ({ setQueryData: () => {}, invalidateQueries: () => Promise.resolve() }),
  };
});

import type { ErrorEnvelope } from '@/shared/api';
import { ApiError, catalogMessage } from '@/shared/api';
import {
  DIGIT_GROUP_SEPARATOR,
  classifyRunFailure,
  groupDigits,
  inputBudgetFigures,
  inputBudgetSentence,
} from '@/entities/audit-run';
import { executionFailure } from '@/entities/execution';
import { StartRunControl } from '@/features/start-run';

const NNBSP = '\u202F';

function refusal(details?: Record<string, string | number | boolean | null>): ApiError {
  const envelope: ErrorEnvelope = {
    contract_version: '1.9.0',
    error_code: 'analysis_input_budget_exceeded',
    message: 'A caller-safe sentence.',
    correlation_id: 'cid-budget',
    retryable: false,
    ...(details === undefined ? {} : { details }),
  };
  return new ApiError(422, envelope, 'cid-budget');
}

const FIGURES = { character_count: 1523456, budget_characters: 152000 };
const SENTENCE = `Символов в тексте версии: 1${NNBSP}523${NNBSP}456; допустимо не более: 152${NNBSP}000.`;

describe('the figures are grouped by threes with a narrow no-break space', () => {
  it('groups every three digits from the right and leaves short numbers alone', () => {
    expect(DIGIT_GROUP_SEPARATOR).toBe(NNBSP);
    expect(groupDigits(0)).toBe('0');
    expect(groupDigits(999)).toBe('999');
    expect(groupDigits(1000)).toBe(`1${NNBSP}000`);
    expect(groupDigits(152000)).toBe(`152${NNBSP}000`);
    expect(groupDigits(1523456)).toBe(`1${NNBSP}523${NNBSP}456`);
  });

  it('keeps the digits exactly as returned', () => {
    for (const value of [7, 15234, 999999, 1000001]) {
      expect(groupDigits(value).split(NNBSP).join('')).toBe(String(value));
    }
  });
});

describe('the sentence says both figures, or nothing', () => {
  it('says both', () => {
    expect(inputBudgetFigures(FIGURES)).toEqual({ characterCount: 1523456, budgetCharacters: 152000 });
    expect(inputBudgetSentence(FIGURES)).toBe(SENTENCE);
  });

  it('invents nothing when a figure is missing, not an integer, negative or not a number', () => {
    for (const details of [
      {},
      { character_count: 1523456 },
      { budget_characters: 152000 },
      { character_count: '1523456', budget_characters: 152000 },
      { character_count: 1523456.5, budget_characters: 152000 },
      { character_count: -1, budget_characters: 152000 },
      { character_count: 1523456, budget_characters: null },
      { character_count: Number.NaN, budget_characters: 152000 },
      { character_count: 2 ** 60, budget_characters: 152000 },
    ]) {
      expect(inputBudgetFigures(details), JSON.stringify(details)).toBeNull();
      expect(inputBudgetSentence(details), JSON.stringify(details)).toBeNull();
    }
  });
});

describe('the start-run classifier: its own state, unsupported, no retry, the figures', () => {
  it('names the refusal and prints both figures after the catalog sentence', () => {
    const failure = classifyRunFailure(refusal(FIGURES));
    expect(failure.kind).toBe('input_budget_exceeded');
    expect(failure.presentation).toBe('unsupported');
    expect(failure.retryable).toBe(false);
    expect(failure.errorCode).toBe('analysis_input_budget_exceeded');
    expect(failure.detail.startsWith(catalogMessage('analysis_input_budget_exceeded'))).toBe(true);
    expect(failure.detail).toContain(SENTENCE);
    expect(failure.title).not.toBe('Запрос завершился ошибкой на сервере.');
  });

  it('keeps the catalog sentence alone when the figures are not there', () => {
    const failure = classifyRunFailure(refusal({ character_count: 'много' }));
    expect(failure.kind).toBe('input_budget_exceeded');
    expect(failure.detail).toContain(catalogMessage('analysis_input_budget_exceeded'));
    expect(failure.detail).not.toContain('Символов в тексте версии');
    expect(classifyRunFailure(refusal()).detail).not.toContain('Символов в тексте версии');
  });
});

describe('the re-audit classifier prints the same figures', () => {
  it('is a refusal, not an unknown outcome: the queue offers no repeat for it', () => {
    const failure = executionFailure(refusal(FIGURES), true);
    // `QueuePage` re-enables its confirm button, as «Повторить с тем же ключом», for
    // `unknown_outcome` only.
    expect(failure.kind).toBe('refusal');
    expect(failure.correlationId).toBe('cid-budget');
    expect(failure.detail).toBe(`${catalogMessage('analysis_input_budget_exceeded')} ${SENTENCE}`);
  });

  it('adds no figures when they are missing, and none to any other refusal', () => {
    expect(executionFailure(refusal({}), true).detail).toBe(catalogMessage('analysis_input_budget_exceeded'));
    const other = new ApiError(
      409,
      {
        contract_version: '1.9.0', error_code: 'state_transition_not_allowed', message: 'm',
        correlation_id: 'c', retryable: false, details: FIGURES as never,
      },
      'c',
    );
    expect(executionFailure(other, true).detail).not.toContain('Символов');
  });
});

describe('the start-run control shows the refusal with its figures and no retry', () => {
  function control(error: unknown): string {
    settled.error = error;
    // `EXEC-PAR-WEB-01`: the control reads the connections for its «Исполнитель» select, so it needs
    // a client; nothing is seeded, the list stays loading, and the select draws no button of its own.
    return renderToStaticMarkup(createElement(
      QueryClientProvider,
      { client: new QueryClient() },
      createElement(StartRunControl, {
        projectUid: 'prj_01J9ZQ8K7NHVXW3T2R5M6P4Q8B',
        versionUid: 'ver_01J9ZQ8K7NHVXW3T2R5M6P4Q8B',
      }),
    ));
  }

  it('renders the warning state with both figures, the correlation id and one button only', () => {
    const markup = control(refusal(FIGURES));
    expect(markup).toContain('am-state--warning');
    expect(markup).toContain('data-run-failure="input_budget_exceeded"');
    expect(markup).toContain(SENTENCE);
    expect(markup).toContain('cid-budget');
    expect(markup).toContain('Прогон не запущен.');
    // The start button and nothing else: a retry cannot help a text that is too large.
    expect(markup.match(/<button\b/g)).toHaveLength(1);
    expect(markup).toContain('>Запустить прогон<');
    expect(markup).not.toContain('Повторить');
  });

  it('renders the generic sentence alone when a figure is odd', () => {
    const markup = control(refusal({ character_count: 1.5, budget_characters: 152000 }));
    expect(markup).toContain('data-run-failure="input_budget_exceeded"');
    expect(markup).not.toContain('Символов в тексте версии');
    expect(markup).not.toContain('1.5');
  });
});
