/**
 * `F5` of the 2026-11-10 judge report: the case screen is not unmounted when the administrator jumps from one cached case to another
 * (the browser's history, a link), so the state of «Отозвать» / «Вернуть» -- the chosen reason and the answer of the last change --
 * must belong to the case it was made on. A note «Дело отозвано» under a case that is in force, or a reason chosen for another
 * case already in the field, is a button one press from a wrong, if reversible, event.
 *
 * Live render (no DOM library: `tests/unit/analysis-settings/live-render.ts`): the same root gets new props, as it does in the browser.
 */

import { QueryClientProvider } from '@tanstack/react-query';
import { createElement } from 'react';
import type { ReactElement } from 'react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('@/shared/api', async (importOriginal) => ({
  ...await importOriginal<Record<string, unknown>>(),
  withdrawDecisionMemoryCase: vi.fn(),
  restoreDecisionMemoryCase: vi.fn(),
}));

import { withdrawDecisionMemoryCase } from '@/shared/api';
import { DecisionMemoryCaseView } from '@/widgets/decision-memory';

import { newClient } from '../screens/harness';
import { mountLive } from '../analysis-settings/live-render';
import type { LiveRender } from '../analysis-settings/live-render';
import { CASE_A, CASE_B, wholeCase } from './memory-fixtures';

const noop = () => undefined;
const SUCCESS_NOTE = 'Дело отозвано: оно больше не попадёт';

/** The case screen of one case, drawn for an administrator, inside the one query client both renders share. */
function screenOf(caseId: string, client = newClient()): (id?: string) => ReactElement {
  return (id = caseId) => createElement(QueryClientProvider, { client },
    createElement(DecisionMemoryCaseView, { data: wholeCase({}, { case_id: id as never, status: 'active' }), isLoading: false, error: null, manage: true, onBack: noop }));
}

/** The opening tag of the standing button, whose `disabled` attribute says whether a reason is chosen. */
function standingButton(markup: string): string {
  const found = markup.match(/<button[^>]*>Отозвать<\/button>/);
  if (found === null) throw new Error('the «Отозвать» button is not drawn');
  return found[0];
}

describe('the standing control follows the case, not the screen', () => {
  let live: LiveRender | undefined;

  beforeEach(() => {
    vi.mocked(withdrawDecisionMemoryCase).mockReset();
  });
  afterEach(async () => {
    await live?.unmount();
    live = undefined;
  });

  it('forgets the reason chosen for one case when the screen turns to another', async () => {
    const draw = screenOf(CASE_A);
    live = await mountLive(draw());
    expect(standingButton(live.markup())).toContain('disabled');
    await live.change('Причина', 'client_request');
    expect(standingButton(live.markup())).not.toContain('disabled');

    await live.update(draw(CASE_B));
    expect(live.markup()).toContain(`data-memory-case-view="${CASE_B}"`);
    expect(standingButton(live.markup())).toContain('disabled');
  });

  it('forgets the answer of the last change when the screen turns to another case', async () => {
    vi.mocked(withdrawDecisionMemoryCase).mockResolvedValue({
      data: { case_id: CASE_A, changed_at: '2026-11-10T09:00:00Z', kind: 'withdraw', reason_code: 'client_request', status: 'withdrawn', status_event_id: 'x' },
    } as never);
    const draw = screenOf(CASE_A);
    live = await mountLive(draw());
    await live.change('Причина', 'client_request');
    await live.press('Отозвать');
    expect(vi.mocked(withdrawDecisionMemoryCase)).toHaveBeenCalledTimes(1);
    expect(live.markup()).toContain(SUCCESS_NOTE);

    await live.update(draw(CASE_B));
    expect(live.markup()).toContain(`data-memory-case-view="${CASE_B}"`);
    expect(live.markup()).not.toContain(SUCCESS_NOTE);
  });
});
