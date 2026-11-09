/**
 * The two AR v3 refusals of contract 1.38.0 are told as themselves (`AR-V3-OPT-IN`).
 *
 * «Повторный аудит» in «Очередь» for a member of an AR v3 group is refused by the server with `409 conflict` and `conflict_reason`
 * `ar_v3_member_not_repeatable`, both when the cost is estimated and when the repeat is sent. The web read every `conflict` as the
 * catalog's sentence «Параллельная запись проиграла…», so the refusal read as a lost race the reader could retry. The same goes for
 * `ar_v3_start_not_enabled` on the estimate and the start of the six checks.
 *
 * The queue item carries no `analysis_kind` (only `RunStatus` does, and the queue lists jobs), so the row cannot hide the button;
 * the refusal is what tells the reader, and it must say the right thing.
 */

import { QueryClientProvider } from '@tanstack/react-query';
import { createElement } from 'react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('@/shared/api', async (importOriginal) => ({
  ...await importOriginal<Record<string, unknown>>(),
  getRunStatus: vi.fn(), estimateRunCost: vi.fn(), reauditRun: vi.fn(),
}));
vi.mock('@/widgets/execution-queue', async (importOriginal) => ({
  ...await importOriginal<Record<string, unknown>>(), ComparisonQueueBlock: () => null,
}));

import type { ErrorCode, ErrorEnvelope, ExecutionQueueItem } from '@/shared/api';
import { ApiError, catalogMessage, estimateRunCost, getRunStatus, queryKeys, reauditRun } from '@/shared/api';
import { executionFailure } from '@/entities/execution';
import { classifyArV3GroupStartFailure } from '@/features/start-ar-v3-group';
import { QueuePage } from '@/_pages/queue';

import { newClient } from '../screens/harness';
import { VERSION_UID, runStatus } from '../review/fixtures';
import { costEstimate } from '../analysis-settings/cost-estimate-fixtures';
import { mountLive } from '../analysis-settings/live-render';
import type { LiveRender } from '../analysis-settings/live-render';
import { QUEUE_WORK } from './queue-work';

const MEMBER_TEXT = 'Прогон из группы АР v3 не повторяется: повторите группу новым запуском.';
const START_TEXT = 'Запуск АР v3 на этом сервере не разрешён.';
const RACE_TEXT = 'Параллельная запись проиграла';

function refusal(code: ErrorCode, status: number, details?: Record<string, string | number | boolean | null>): ApiError {
  const envelope: ErrorEnvelope = {
    contract_version: '1.47.0', error_code: code, message: 'A caller-safe sentence.', correlation_id: 'cid-arv3',
    retryable: false, ...(details === undefined ? {} : { details }),
  };
  return new ApiError(status, envelope, 'cid-arv3');
}
const conflict = (reason: string) => refusal('conflict', 409, { conflict_reason: reason });

describe('executionFailure tells an AR v3 conflict as itself', () => {
  it.each([
    ['a member of an AR v3 group is repeated', 'ar_v3_member_not_repeatable', MEMBER_TEXT],
    ['the start of AR v3 is not allowed on this server', 'ar_v3_start_not_enabled', START_TEXT],
  ])('%s', (_name, reason, sentence) => {
    for (const write of [true, false]) {
      const failure = executionFailure(conflict(reason), write);
      expect(failure.detail, `write=${write}`).toBe(sentence);
      expect(failure.detail).not.toContain(RACE_TEXT);
      // Still a definite refusal the queue shows as «Команда отклонена», with its correlation id.
      expect(failure.kind).toBe('conflict');
      expect(failure.correlationId).toBe('cid-arv3');
    }
  });

  it('keeps the catalog sentence for a conflict with no reason, with another reason, or a reason this client does not know', () => {
    expect(executionFailure(refusal('conflict', 409), true).detail).toBe(catalogMessage('conflict'));
    expect(executionFailure(conflict('run_cost_estimate_stale'), true).detail).toBe(catalogMessage('conflict'));
    expect(executionFailure(conflict('ar_v3_a_future_reason'), true).detail).toBe(catalogMessage('conflict'));
    // The reason names a sentence only under `conflict`: another code that carries it is not told as it.
    expect(executionFailure(refusal('permission_denied', 403, { conflict_reason: 'ar_v3_member_not_repeatable' }), true).detail)
      .toBe(catalogMessage('permission_denied'));
    // And the sentences are not the catalog's: the instrument below cannot pass on a map that returns the catalog text.
    expect(catalogMessage('conflict')).toContain(RACE_TEXT);
  });
});

describe('the start of the six checks tells its refusal', () => {
  it('names a server that does not allow starts, offers no retry, and says nothing was created', () => {
    const failure = classifyArV3GroupStartFailure(conflict('ar_v3_start_not_enabled'));
    expect(failure.kind).toBe('start_not_allowed');
    expect(failure.presentation).toBe('unsupported');
    expect(failure.retryable).toBe(false);
    expect(failure.title).toBe(START_TEXT);
    expect(failure.detail).toContain('Ни одна из шести проверок не создана.');
    expect(failure.correlationId).toBe('cid-arv3');
  });

  it('leaves every other conflict of the start to the generic reading', () => {
    for (const error of [refusal('conflict', 409), conflict('ar_v3_member_not_repeatable'), conflict('run_cost_estimate_stale')]) {
      expect(classifyArV3GroupStartFailure(error).kind).toBe('generic');
    }
  });
});

describe('«Повторный аудит» of an AR v3 group member in «Очередь»', () => {
  const RUN_ID = 'run_01J9ZQ8K7NHVXW3T2R5M6P4Q8F';
  const item: ExecutionQueueItem = {
    run_id: RUN_ID, job_id: 'job_01J9ZQ8K7NHVXW3T2R5M6P4Q8F', state: 'succeeded', priority: 0,
    available_at: '2026-10-30T00:00:00Z', created_at: '2026-10-30T00:00:00Z', ...QUEUE_WORK,
  };
  let live: LiveRender | null = null;

  beforeEach(() => {
    vi.resetAllMocks();
    vi.mocked(getRunStatus).mockImplementation(async ({ path }) => ({ data: {
      ...runStatus(), run_id: path.run_id, state: 'published', version_uid: VERSION_UID, analysis_kind: 'ar_v3_beta',
    } }) as never);
    vi.mocked(estimateRunCost).mockImplementation(async ({ body }) => ({ data: costEstimate(body) }) as never);
  });
  afterEach(async () => { await live?.unmount(); live = null; });

  async function open(): Promise<LiveRender> {
    const client = newClient();
    client.setQueryData(queryKeys.execution.queue(), { items: [item], page: { next_cursor: null }, paused: false });
    client.setQueryData(queryKeys.account.me(), { roles: ['expert'] });
    live = await mountLive(createElement(QueryClientProvider, { client }, createElement(QueuePage)));
    return live;
  }

  async function settleCost(view: LiveRender) {
    for (let tick = 0; tick < 20 && view.markup().includes('Загрузка: стоимость повторного аудита'); tick += 1) {
      await view.settle(() => undefined);
    }
    expect(view.markup()).not.toContain('Загрузка: стоимость повторного аудита');
  }

  it('is refused at the estimate with the sentence of the refusal, not a lost parallel write', async () => {
    vi.mocked(estimateRunCost).mockRejectedValue(conflict('ar_v3_member_not_repeatable'));
    const view = await open();
    await view.press('Повторный аудит');
    await settleCost(view);
    const markup = view.markup();
    expect(markup).toContain('Стоимость повторного аудита не оценена');
    expect(markup).toContain(MEMBER_TEXT);
    expect(markup).not.toContain(RACE_TEXT);
    // Nothing to agree to: no dialog, no «Запустить», and nothing is sent (`RUN-START-ONE-01b`).
    expect(markup).not.toContain('data-start-run-dialog');
    expect(view.count('Запустить')).toBe(0);
    expect(reauditRun).not.toHaveBeenCalled();
  });

  it('is refused at the command with the same sentence under «Команда отклонена»', async () => {
    vi.mocked(reauditRun).mockRejectedValue(conflict('ar_v3_member_not_repeatable'));
    const view = await open();
    await view.press('Повторный аудит');
    await settleCost(view);
    // The estimate can charge, so the one dialog asks; its «Запустить» is the agreement (`RUN-START-ONE-01b`).
    await view.press('Запустить');
    const markup = view.markup();
    expect(reauditRun).toHaveBeenCalledTimes(1);
    expect(markup).toContain('Команда отклонена');
    expect(markup).toContain(MEMBER_TEXT);
    expect(markup).not.toContain(RACE_TEXT);
  });
});
