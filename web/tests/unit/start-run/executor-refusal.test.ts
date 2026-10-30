/**
 * `EXEC-PAR-WEB-01`: a start that names an executor the stand will not use.
 *
 * `503 dependency_unavailable` (`details.dependency: executor_connection`) and `422
 * validation_failed` (`details.field: executor_connection_id`) are said as themselves, in Russian,
 * with a retry under the same key when the envelope says it is retryable — and with NO offer of
 * another executor or of the default route. The last describe block is the one that must be able
 * to fail: it renders the refusal and the whole control over a settled refusal and looks for
 * anything that would let the person go elsewhere from the refusal itself.
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
    useMutation: () => ({ mutate: () => {}, reset: () => {}, isPending: false, error: settled.error }),
    useQueryClient: () => ({ setQueryData: () => {}, invalidateQueries: () => Promise.resolve() }),
  };
});

import type { ErrorCode, ErrorEnvelope } from '@/shared/api';
import { ApiError } from '@/shared/api';
import { classifyRunFailure } from '@/entities/audit-run';
import { StartRunControl, StartRunFailureView } from '@/features/start-run';

const PROJECT = 'prj_01J9ZQ8K7NHVXW3T2R5M6P4Q8B';
const VERSION = 'ver_01J9ZQ8K7NHVXW3T2R5M6P4Q8B';
const RETRY = 'Повторить с тем же ключом';
const NOT_REPLACED = 'Вместо выбранного исполнителя прогон не запускается ни на каком другом.';

function apiError(
  status: number,
  code: ErrorCode,
  retryable: boolean,
  details: Record<string, string | number | boolean | null>,
  message = 'A caller-safe sentence.',
): ApiError {
  const envelope: ErrorEnvelope = {
    contract_version: '1.13.0', error_code: code, message, correlation_id: 'cid-exec', retryable, details,
  };
  return new ApiError(status, envelope, 'cid-exec');
}

const cannotServe = (reason?: string) =>
  apiError(503, 'dependency_unavailable', true, { dependency: 'executor_connection' },
    reason === undefined
      ? 'the chosen executor connection cannot serve a run now'
      : `the chosen executor connection cannot serve a run now (${reason})`);

const rejected = (constraint?: string) =>
  apiError(422, 'validation_failed', false,
    constraint === undefined ? { field: 'executor_connection_id' } : { field: 'executor_connection_id', constraint });

describe('an executor that cannot serve now is its own state', () => {
  const failure = classifyRunFailure(cannotServe('archived'));

  it('is not the generic provider refusal', () => {
    expect(failure.kind).toBe('executor_unavailable');
    expect(failure.kind).not.toBe('provider_unavailable');
    expect(failure.presentation).toBe('error');
    expect(failure.retryable).toBe(true);
    expect(failure.correlationId).toBe('cid-exec');
    expect(failure.errorCode).toBe('dependency_unavailable');
  });

  it('says it in Russian, as the task words it', () => {
    expect(failure.title).toBe('Выбранный исполнитель сейчас не может выполнить прогон.');
    expect(failure.detail).toContain('Прогон не запущен');
    expect(failure.detail).toContain('тот же ключ идемпотентности и тот же выбор исполнителя');
    expect(failure.detail).toContain(NOT_REPLACED);
  });

  it('prints no code identifier and no word of the stand’s English message', () => {
    const text = `${failure.title} ${failure.detail}`;
    expect(text).not.toMatch(/[A-Za-z]/);
    expect(text).not.toContain('executor_connection');
    expect(text).not.toContain('dependency');
    expect(text).not.toContain('archived');
  });

  it('gives each reason word the stand writes its own sentence', () => {
    const sentences = new Map([
      ['archived', 'Причина: подключение в архиве.'],
      ['kind_not_served', 'Причина: этот стенд не обслуживает такой вид подключения.'],
      ['not_probed', 'Причина: для текущих настроек и ключа нет успешной проверки.'],
      ['no_revision', 'Причина: настройки подключения ещё не заданы.'],
    ]);
    for (const [word, sentence] of sentences) {
      const detail = classifyRunFailure(cannotServe(word)).detail;
      expect(detail, word).toContain(sentence);
      expect(detail, word).not.toMatch(/[A-Za-z]/);
    }
    expect(new Set(sentences.values()).size).toBe(4);
  });

  it('names no reason it was not told: an unknown word, or none, leaves the sentence out', () => {
    for (const message of [cannotServe(), cannotServe('exploded'), cannotServe('constructor')]) {
      expect(classifyRunFailure(message).detail).not.toContain('Причина');
    }
    // The word counts only at the end of the message, as the stand writes it.
    const early = apiError(503, 'dependency_unavailable', true, { dependency: 'executor_connection' },
      '(archived) the chosen executor connection cannot serve a run now');
    expect(classifyRunFailure(early).detail).not.toContain('Причина');
  });

  it('follows the envelope on whether a retry can help', () => {
    const notRetryable = apiError(503, 'dependency_unavailable', false, { dependency: 'executor_connection' });
    expect(classifyRunFailure(notRetryable).retryable).toBe(false);
  });

  it('leaves every other dependency to the provider sentence', () => {
    const other = classifyRunFailure(apiError(503, 'dependency_unavailable', true, { dependency: 'model_provider' }));
    expect(other.kind).toBe('provider_unavailable');
    const none = classifyRunFailure(apiError(503, 'dependency_unavailable', true, {}));
    expect(none.kind).toBe('provider_unavailable');
  });
});

describe('an executor identifier the stand rejects is its own state', () => {
  it('says which rejection it was, in Russian', () => {
    const table = new Map([
      ['unknown_connection', 'Такого исполнителя на стенде нет.'],
      ['pattern', 'Идентификатор выбранного исполнителя имеет неверный вид.'],
      ['kind_not_routable', 'Подключение такого вида не выполняет прогоны.'],
      ['something_new', 'Стенд не принял выбранного исполнителя.'],
    ]);
    for (const [constraint, sentence] of table) {
      const failure = classifyRunFailure(rejected(constraint));
      expect(failure.kind, constraint).toBe('executor_invalid');
      expect(failure.title).toBe('Выбранный исполнитель не подходит для этого прогона.');
      expect(failure.detail, constraint).toContain(sentence);
      expect(failure.detail, constraint).toContain(NOT_REPLACED);
      expect(`${failure.title} ${failure.detail}`, constraint).not.toMatch(/[A-Za-z]/);
    }
    expect(classifyRunFailure(rejected()).detail).toContain('Стенд не принял выбранного исполнителя.');
  });

  it('is refused again until the choice changes, so it carries no retry', () => {
    const failure = classifyRunFailure(rejected('unknown_connection'));
    expect(failure.presentation).toBe('unsupported');
    expect(failure.retryable).toBe(false);
  });

  it('is not claimed for another field', () => {
    const other = classifyRunFailure(apiError(422, 'validation_failed', false, { field: 'version_uid', constraint: 'pattern' }));
    expect(other.kind).toBe('request_invalid');
    const bare = classifyRunFailure(apiError(422, 'validation_failed', false, {}));
    expect(bare.kind).toBe('request_invalid');
  });
});

describe('a refused start offers a retry under the same key and nothing else', () => {
  const view = (error: ApiError) =>
    renderToStaticMarkup(createElement(StartRunFailureView, {
      failure: classifyRunFailure(error), projectUid: PROJECT, versionUid: VERSION, onRetry: () => {},
    }));

  it('draws one button, the retry, for an executor that cannot serve now', () => {
    const markup = view(cannotServe('not_probed'));
    expect(markup).toContain('data-run-failure="executor_unavailable"');
    expect(markup).toContain('role="alert"');
    expect(markup.match(/<button\b/g)).toHaveLength(1);
    expect(markup).toContain(`>${RETRY}</button>`);
    expect(markup).toContain('cid-exec');
  });

  it('offers no other executor and no default route', () => {
    for (const error of [cannotServe('archived'), cannotServe(), rejected('unknown_connection'), rejected('pattern')]) {
      const markup = view(error);
      expect(markup).not.toContain('<select');
      expect(markup).not.toContain('<option');
      expect(markup).not.toContain('<a ');
      expect(markup).not.toContain('href=');
      expect(markup).not.toContain('type="radio"');
      // Neither the route nor the default, in any case, and no verb that offers a way round.
      expect(markup).not.toMatch(/умолчани|маршрут/i);
      expect(markup).not.toMatch(/запустите|выберите|попробуйте|используйте/i);
      expect(markup).not.toContain('recorded');
      expect(markup.match(/<button\b/g) ?? []).toHaveLength(error.retryable ? 1 : 0);
    }
  });

  it('draws no retry for an identifier that is refused again', () => {
    const markup = view(rejected('kind_not_routable'));
    expect(markup).toContain('data-run-failure="executor_invalid"');
    expect(markup).toContain('Прогон не запущен.');
    expect(markup).not.toContain(RETRY);
    expect(markup).not.toContain('<button');
  });
});

describe('the control keeps the select and the start beside a refusal', () => {
  function control(error: unknown): string {
    settled.error = error;
    return renderToStaticMarkup(createElement(
      QueryClientProvider,
      { client: new QueryClient() },
      createElement(StartRunControl, { projectUid: PROJECT, versionUid: VERSION }),
    ));
  }

  it('shows the refusal, the select with its choice, the start button and exactly one retry', () => {
    const markup = control(cannotServe('archived'));
    expect(markup).toContain('data-run-failure="executor_unavailable"');
    expect(markup).toContain('data-executor-select');
    // the executor's select and, since `ANALYSIS-PRESETS-01`, the preset's beside it
    expect(markup.match(/<select\b/g)).toHaveLength(2);
    expect(markup).toContain('>Запустить прогон</button>');
    expect(markup.match(new RegExp(RETRY, 'g'))).toHaveLength(1);
    // The start button, the retry, and the select’s own «Прочитать список снова» is absent here.
    expect(markup.match(/<button\b/g)).toHaveLength(3); // estimate, start and same-key retry
  });

  it('shows nothing of a refusal before one has happened', () => {
    const markup = control(null);
    expect(markup).not.toContain('data-run-failure');
    expect(markup).not.toContain(RETRY);
  });
});
