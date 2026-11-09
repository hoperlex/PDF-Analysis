/**
 * `D-495`: «Память решений» inside «База знаний» -- the expert's and the administrator's view of the decision memory.
 *
 * Mounted live under `routed-address.ts` (a press and a select change are events the one-pass render cannot deliver); only the
 * transport is replaced. Each case can fail:
 *
 *   - the viewer sees nothing of the tab: no button, and an address that names it shows the first screen with no memory read;
 *   - while the account is not known the tab waits and reads nothing;
 *   - the expert reads the list and the case and is offered no standing change and no status read; the administrator is offered
 *     both, and the status line;
 *   - «Отозвать» / «Вернуть» need the closed reason, send it with ONE idempotency key per intent (the same on a retry, another
 *     for another reason), and the case follows the answer;
 *   - a crop is text, a forgotten case is its tombstone, and nothing requests a crop's bytes.
 */

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { createElement } from 'react';
import type { ReactElement } from 'react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('@/shared/api', async (importOriginal) => {
  const actual = await importOriginal<Record<string, unknown>>();
  return {
    ...actual,
    getMe: vi.fn(),
    listDecisions: vi.fn(),
    listProjects: vi.fn(),
    listDecisionMemoryCases: vi.fn(),
    getDecisionMemoryCase: vi.fn(),
    getDecisionMemoryStatus: vi.fn(),
    withdrawDecisionMemoryCase: vi.fn(),
    restoreDecisionMemoryCase: vi.fn(),
  };
});

import { KnowledgeBaseEagerSeam, KnowledgeBasePage } from '@/_pages/knowledge-base';
import {
  getDecisionMemoryCase,
  getDecisionMemoryStatus,
  getMe,
  listDecisionMemoryCases,
  listDecisions,
  listProjects,
  restoreDecisionMemoryCase,
  withdrawDecisionMemoryCase,
} from '@/shared/api';
import type { ApiResponse, DecisionMemoryCase, DecisionMemoryStatusChange } from '@/shared/api';
import { MEMORY_PAGE_LIMIT } from '@/entities/decision-memory';
import { KnowledgeBase } from '@/widgets/knowledge-base';

import { mountLive } from '../analysis-settings/live-render';
import type { LiveRender } from '../analysis-settings/live-render';
import '../review/fixtures';
import { COUNTS, CASE_A, CASE_B, CASE_C, PROJECT, summary, wholeCase } from '../decision-memory/memory-fixtures';
import { RoutedAddress, currentSearch } from './routed-address';

const me = vi.mocked(getMe);
const journal = vi.mocked(listDecisions);
const projects = vi.mocked(listProjects);
const cases = vi.mocked(listDecisionMemoryCases);
const oneCase = vi.mocked(getDecisionMemoryCase);
const counts = vi.mocked(getDecisionMemoryStatus);
const withdraw = vi.mocked(withdrawDecisionMemoryCase);
const restore = vi.mocked(restoreDecisionMemoryCase);

const ok = <T>(data: T): ApiResponse<T> => ({ data, status: 200, correlationId: 'cid-memory' });

type Query = { status?: string; verdict?: string; category?: string; section_code?: string; data_class?: string; origin_project_uid?: string; cursor?: string; limit?: number };
const listQueries = (): Query[] => cases.mock.calls.map((call) => (call[0] as { query: Query }).query);

/** What the server holds: the standing of CASE_A moves with a withdraw and a restore, as the real one does. */
let standing: 'active' | 'withdrawn' | 'forgotten';

function currentCase(): DecisionMemoryCase {
  if (standing === 'forgotten') {
    return wholeCase(
      { content: null, decisions: [], evidence: [], norm_refs: [], crops: [], status_events: [
        { status_event_id: 'dmw_01M2545JSD15ETSNNV904X997F', kind: 'forget', reason_code: 'client_request', created_at: '2026-11-09T12:00:00Z', forgotten_content_sha256: 'b'.repeat(64) },
      ] },
      { status: 'forgotten', current_verdict: 'accepted' },
    );
  }
  return wholeCase(
    standing === 'withdrawn'
      ? { status_events: [{ status_event_id: 'dmw_01M2545JSD15ETSNNV904X996E', kind: 'withdraw', reason_code: 'test_data', created_at: '2026-11-09T10:00:00Z', forgotten_content_sha256: null }] }
      : {},
    standing === 'withdrawn' ? { status: 'withdrawn', status_reason_code: 'test_data', status_changed_at: '2026-11-09T10:00:00Z' } : {},
  );
}

function change(kind: 'withdraw' | 'restore', reason: DecisionMemoryStatusChange['reason_code']): DecisionMemoryStatusChange {
  return { case_id: CASE_A, status_event_id: 'dmw_01M2545JSD15ETSNNV904X998G', kind, status: kind === 'withdraw' ? 'withdrawn' : 'active', reason_code: reason, changed_at: '2026-11-09T11:00:00Z' };
}

beforeEach(() => {
  standing = 'active';
  me.mockReset();
  me.mockResolvedValue(ok({ roles: ['expert'] }) as never);
  journal.mockReset();
  journal.mockResolvedValue(ok({ items: [], page: { next_cursor: null }, total: 0 }) as never);
  projects.mockReset();
  projects.mockResolvedValue(ok({ items: [{ project_uid: PROJECT, name: 'Школа' }], page: { next_cursor: null } }) as never);
  cases.mockReset();
  cases.mockImplementation((async (input: { query: Query }) => {
    if (input.query.cursor === 'cursor-1') return ok({ items: [summary({ case_id: CASE_C })], page: { next_cursor: null } });
    return ok({
      items: [summary({ status: standing === 'forgotten' ? 'forgotten' : standing }), summary({ case_id: CASE_B, current_verdict: 'rejected', current_severity: null, decision_count: 3 })],
      page: { next_cursor: 'cursor-1' },
    });
  }) as never);
  oneCase.mockReset();
  oneCase.mockImplementation((async () => ok(currentCase())) as never);
  counts.mockReset();
  counts.mockResolvedValue(ok(COUNTS) as never);
  withdraw.mockReset();
  withdraw.mockImplementation((async (input: { body: { reason_code: DecisionMemoryStatusChange['reason_code'] } }) => {
    standing = 'withdrawn';
    return ok(change('withdraw', input.body.reason_code));
  }) as never);
  restore.mockReset();
  restore.mockImplementation((async (input: { body: { reason_code: DecisionMemoryStatusChange['reason_code'] } }) => {
    standing = 'active';
    return ok(change('restore', input.body.reason_code));
  }) as never);
});

describe('«Память решений»', () => {
  let live: LiveRender | null = null;
  afterEach(async () => {
    await live?.unmount();
    live = null;
  });

  const freshClient = (): QueryClient =>
    new QueryClient({ defaultOptions: { queries: { retry: false, refetchOnMount: false, gcTime: Infinity, staleTime: 30_000 } } });

  function page(client: QueryClient, query: string): ReactElement {
    return createElement(
      QueryClientProvider,
      { client },
      createElement(
        KnowledgeBaseEagerSeam.Provider,
        { value: KnowledgeBase },
        createElement(RoutedAddress, { query }, createElement(KnowledgeBasePage)),
      ),
    );
  }

  async function settled(view: LiveRender): Promise<void> {
    for (let round = 0; round < 6; round += 1) {
      await view.settle(() => new Promise<void>((done) => setTimeout(done, 0)));
    }
  }

  async function mountAt(query: string, roles: readonly string[] = ['expert']): Promise<LiveRender> {
    me.mockResolvedValue(ok({ roles }) as never);
    live = await mountLive(page(freshClient(), query));
    await settled(live);
    return live;
  }

  describe('who is offered it', () => {
    it('hides the tab from the viewer: no button, and an address that names it shows the first screen with no memory read', async () => {
      const view = await mountAt('kind=memory', ['viewer']);
      expect(view.count('Память решений')).toBe(0);
      expect(view.markup()).not.toContain('Память решений');
      expect(view.markup()).not.toContain('data-memory-results');
      expect(cases).not.toHaveBeenCalled();
      expect(counts).not.toHaveBeenCalled();
      // The first screen is «Замечания»: the journal is read, and it is what is on screen.
      expect(journal).toHaveBeenCalled();
      expect(view.markup()).toMatch(/aria-pressed="true"[^>]*data-kb-kind="findings"/);
    });

    it('offers it to the expert and to the administrator', async () => {
      expect((await mountAt('', ['expert'])).count('Память решений')).toBe(1);
      await live?.unmount();
      expect((await mountAt('', ['admin'])).count('Память решений')).toBe(1);
    });

    it('waits for the account when the address names the tab, and reads nothing meanwhile', async () => {
      me.mockReset();
      me.mockImplementation((() => new Promise(() => undefined)) as never);
      live = await mountLive(page(freshClient(), 'kind=memory'));
      await settled(live);
      expect(live.markup()).toContain('Загрузка: память решений');
      expect(cases).not.toHaveBeenCalled();
      expect(journal).not.toHaveBeenCalled();
    });

    it('does not wait for ever on an account that cannot be read: the tab stays hidden', async () => {
      me.mockReset();
      me.mockRejectedValue(new Error('no'));
      live = await mountLive(page(freshClient(), 'kind=memory'));
      await settled(live);
      expect(live.count('Память решений')).toBe(0);
      expect(cases).not.toHaveBeenCalled();
    });
  });

  describe('the list', () => {
    it('writes the tab onto the address, reads one page of cases and says what the memory is', async () => {
      const view = await mountAt('');
      expect(cases).not.toHaveBeenCalled();
      journal.mockClear();
      await view.press('Память решений');
      await settled(view);
      expect(currentSearch()).toBe('kind=memory');
      expect(listQueries()).toEqual([{ limit: MEMORY_PAGE_LIMIT }]);
      expect(view.markup().match(/data-memory-case="dmc_/g)).toHaveLength(2);
      expect(view.markup()).toContain('Память решений: то, что эксперт видел и решил');
      expect(view.markup()).toContain('Принято');
      expect(view.markup()).toContain('решений: 3');
      // The journal is not read for a tab that does not draw it.
      expect(journal).not.toHaveBeenCalled();
    });

    it('opens on the filters the address names and reads the project as the origin', async () => {
      const view = await mountAt(`project=${PROJECT}&kind=memory&mstatus=withdrawn&mclass=real&msection=KJ`);
      expect(listQueries()).toEqual([
        { status: 'withdrawn', data_class: 'real', section_code: 'KJ', origin_project_uid: PROJECT, limit: MEMORY_PAGE_LIMIT },
      ]);
      expect(view.markup()).toContain('data-memory-scope="project"');
    });

    it('writes a chosen filter onto the address, replacing the entry, and reads again with it', async () => {
      const view = await mountAt('kind=memory');
      await view.change('Состояние', 'withdrawn');
      await settled(view);
      expect(currentSearch()).toBe('kind=memory&mstatus=withdrawn');
      expect(listQueries().at(-1)).toEqual({ status: 'withdrawn', limit: MEMORY_PAGE_LIMIT });
      await view.change('Данные', 'real');
      await settled(view);
      expect(listQueries().at(-1)).toEqual({ status: 'withdrawn', data_class: 'real', limit: MEMORY_PAGE_LIMIT });
      await view.change('Состояние', 'all');
      await settled(view);
      expect(currentSearch()).toBe('kind=memory&mclass=real');
    });

    it('walks the server’s cursors and forgets them when a filter changes', async () => {
      const view = await mountAt('kind=memory');
      await view.press('Далее');
      await settled(view);
      expect(listQueries().at(-1)).toEqual({ cursor: 'cursor-1', limit: MEMORY_PAGE_LIMIT });
      expect(view.markup()).toContain(`data-memory-case="${CASE_C}"`);
      await view.change('Вердикт', 'rejected');
      await settled(view);
      expect(listQueries().at(-1)).toEqual({ verdict: 'rejected', limit: MEMORY_PAGE_LIMIT });
    });

    it('says an empty page under a filter is about the filter, and resets it', async () => {
      cases.mockResolvedValue(ok({ items: [], page: { next_cursor: null } }) as never);
      const view = await mountAt('kind=memory&mclass=real');
      expect(view.markup()).toContain('В памяти решений нет дел под этот отбор.');
      await view.press('Сбросить отбор');
      await settled(view);
      expect(currentSearch()).toBe('kind=memory');
    });

    it('leaving the tab takes its parameters off the address', async () => {
      const view = await mountAt('kind=memory&mstatus=withdrawn');
      await view.press('Замечания');
      await settled(view);
      expect(currentSearch()).toBe('');
    });

    it('says a failed read in Russian with its correlation id', async () => {
      cases.mockRejectedValue(new Error('boom'));
      const view = await mountAt('kind=memory');
      expect(view.markup()).toContain('Память решений не открылась');
    });
  });

  describe('the case', () => {
    it('opens from the list as a step of the history and shows what the expert saw and said, with the crops as text', async () => {
      const view = await mountAt('kind=memory');
      await view.pressMarked('data-memory-open', CASE_A);
      await settled(view);
      expect(currentSearch()).toBe(`kind=memory&mcase=${CASE_A}`);
      expect(oneCase).toHaveBeenCalledWith({ path: { case_id: CASE_A } });
      const markup = view.markup();
      expect(markup).toContain('Отметка пола в плане не совпадает с отметкой на разрезе.');
      expect(markup).toContain('Подтверждаю: отметки расходятся.');
      expect(markup).toContain('Отметка пола +0,300');
      expect(markup).toContain('СП 54.13330.2022');
      expect(markup).toContain('п. 5.2');
      // A crop is a description: its page, box, size and digest -- and no image is drawn or asked for.
      expect(markup).toContain('data-memory-crop="dmx_01M2545JSD15ETSNNV904X995D"');
      expect(markup).toContain('640×480 пикс.');
      expect(markup).toContain('a'.repeat(64));
      expect(markup).toContain('Фрагмент плана первого этажа');
      expect(markup).toContain('Изображения кадров пока не открываются');
      expect(markup).not.toContain('<img');
      expect(markup).not.toContain('/crop');
      // The first read of the list is not repeated while the case is open.
      expect(cases).toHaveBeenCalledTimes(1);
    });

    it('opens on an address that names the case, with no read of the list', async () => {
      const view = await mountAt(`kind=memory&mcase=${CASE_A}`);
      expect(oneCase).toHaveBeenCalledTimes(1);
      expect(cases).not.toHaveBeenCalled();
      expect(view.markup()).toContain(`data-memory-case-view="${CASE_A}"`);
    });

    it('goes back to the list with «К списку дел»', async () => {
      const view = await mountAt('kind=memory');
      await view.pressMarked('data-memory-open', CASE_A);
      await settled(view);
      await view.press('← К списку дел');
      await settled(view);
      expect(currentSearch()).toBe('kind=memory');
      expect(view.markup()).toContain('data-memory-table');
    });

    it('says a case that cannot be read, and offers the way back', async () => {
      oneCase.mockRejectedValue(new Error('gone'));
      const view = await mountAt(`kind=memory&mcase=${CASE_A}`);
      expect(view.markup()).toContain('Дело не открылось');
      expect(view.count('← К списку дел')).toBe(1);
    });

    it('shows a forgotten case as its tombstone only, with nothing to change', async () => {
      standing = 'forgotten';
      const view = await mountAt(`kind=memory&mcase=${CASE_A}`, ['admin']);
      const markup = view.markup();
      expect(markup).toContain('data-memory-standing-note="forgotten"');
      expect(markup).toContain('Содержимое дела забыто');
      expect(markup).toContain('b'.repeat(64));
      expect(markup).not.toContain('data-memory-finding-text');
      expect(markup).not.toContain('data-memory-standing-control');
      expect(view.count('Отозвать')).toBe(0);
      expect(view.count('Вернуть')).toBe(0);
    });
  });

  describe('what the expert is not offered', () => {
    it('reads the list and the case and is offered no standing change and no status read', async () => {
      const view = await mountAt(`kind=memory&mcase=${CASE_A}`, ['expert']);
      expect(view.markup()).toContain('data-memory-case-view');
      expect(view.count('Отозвать')).toBe(0);
      expect(view.count('Вернуть')).toBe(0);
      expect(view.markup()).not.toContain('data-memory-standing-control');
      expect(view.markup()).not.toContain('data-memory-status-line');
      expect(counts).not.toHaveBeenCalled();
    });
  });

  describe('what the administrator is offered', () => {
    it('shows one compact status line from the counts and the settings', async () => {
      const view = await mountAt('kind=memory', ['admin']);
      const markup = view.markup();
      expect(counts).toHaveBeenCalledTimes(1);
      expect(markup).toContain('data-memory-status-line=""');
      expect(markup).toContain('data-memory-data-class="test"');
      expect(markup).toContain('data-memory-training-use="off"');
      expect(markup).toContain('действует, тестовые: 4');
      expect(markup).toContain('отозвано, тестовые: 1');
      expect(markup).toContain('обучение на памяти: <strong>выключено</strong>');
    });

    it('says when the counts cannot be read, and the list still works', async () => {
      counts.mockRejectedValue(new Error('no counts'));
      const view = await mountAt('kind=memory', ['admin']);
      expect(view.markup()).toContain('data-memory-status-line="failed"');
      expect(view.markup().match(/data-memory-case="dmc_/g)).toHaveLength(2);
    });

    it('withdraws a case with the reason it needs, under one key, and the case follows the answer', async () => {
      const view = await mountAt(`kind=memory&mcase=${CASE_A}`, ['admin']);
      // Nothing is sent without a reason.
      expect(await view.press('Отозвать')).toBe(false);
      expect(withdraw).not.toHaveBeenCalled();
      await view.change('Причина', 'wrong_decision');
      expect(await view.press('Отозвать')).toBe(true);
      await settled(view);
      expect(withdraw).toHaveBeenCalledTimes(1);
      const sent = withdraw.mock.calls[0]?.[0] as unknown as { path: { case_id: string }; body: { reason_code: string }; idempotencyKey: string };
      expect(sent.path).toEqual({ case_id: CASE_A });
      expect(sent.body).toEqual({ reason_code: 'wrong_decision' });
      expect(sent.idempotencyKey).toMatch(/^ik_/);
      expect(restore).not.toHaveBeenCalled();
      // The case was read again and now stands withdrawn: «Вернуть» is what is offered, with the history and the note.
      expect(view.markup()).toContain('data-memory-standing-note="withdrawn"');
      expect(view.markup()).toContain('data-memory-standing-control="restore"');
      expect(view.count('Отозвать')).toBe(0);
      expect(view.count('Вернуть')).toBe(1);
      expect(view.markup()).toContain('data-memory-event-kind="withdraw"');
      expect(view.markup()).toContain('Дело отозвано: оно больше не попадёт в подсказки');
      // The counts were read again.
      expect(counts.mock.calls.length).toBeGreaterThan(1);
    });

    it('restores a withdrawn case, with its own reason', async () => {
      standing = 'withdrawn';
      const view = await mountAt(`kind=memory&mcase=${CASE_A}`, ['admin']);
      expect(view.count('Отозвать')).toBe(0);
      await view.change('Причина', 'capture_defect');
      await view.press('Вернуть');
      await settled(view);
      expect(restore).toHaveBeenCalledTimes(1);
      expect(withdraw).not.toHaveBeenCalled();
      const sent = restore.mock.calls[0]?.[0] as unknown as { body: { reason_code: string }; idempotencyKey: string };
      expect(sent.body).toEqual({ reason_code: 'capture_defect' });
      expect(sent.idempotencyKey).toMatch(/^ik_/);
      expect(view.markup()).toContain('data-memory-standing-control="withdraw"');
    });

    it('retries a failed withdraw under the SAME key, and a different reason is a different intent with another key', async () => {
      const view = await mountAt(`kind=memory&mcase=${CASE_A}`, ['admin']);
      withdraw.mockReset();
      withdraw.mockRejectedValueOnce(new Error('network'));
      withdraw.mockImplementation((async (input: { body: { reason_code: DecisionMemoryStatusChange['reason_code'] } }) => {
        standing = 'withdrawn';
        return ok(change('withdraw', input.body.reason_code));
      }) as never);
      await view.change('Причина', 'other');
      await view.press('Отозвать');
      await settled(view);
      expect(view.markup()).toContain('Состояние дела не изменено');
      expect(view.markup()).toContain('data-memory-standing-failure');
      await view.press('Отозвать');
      await settled(view);
      const keys = withdraw.mock.calls.map((call) => (call[0] as unknown as { idempotencyKey: string }).idempotencyKey);
      expect(keys).toHaveLength(2);
      expect(keys[1]).toBe(keys[0]);
    });

    it('mints another key for another reason', async () => {
      const view = await mountAt(`kind=memory&mcase=${CASE_A}`, ['admin']);
      withdraw.mockReset();
      withdraw.mockRejectedValue(new Error('network'));
      await view.change('Причина', 'other');
      await view.press('Отозвать');
      await settled(view);
      await view.change('Причина', 'test_data');
      await view.press('Отозвать');
      await settled(view);
      const keys = withdraw.mock.calls.map((call) => (call[0] as unknown as { idempotencyKey: string }).idempotencyKey);
      expect(keys).toHaveLength(2);
      expect(keys[1]).not.toBe(keys[0]);
    });
  });
});
