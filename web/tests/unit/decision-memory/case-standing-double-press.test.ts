/**
 * `D-503` (lane MEM-JOURNEY): one press of «Отозвать» / «Вернуть» sends one request, however many presses reach the button before the
 * answer.
 *
 * Found by the browser journey: pressing the button twice sent two `POST`s under one Idempotency-Key. The server answered both with
 * the same status event and wrote one, so nothing was lost -- but the screen sent a request it had no reason to send, and every other
 * keyed button of the application (`classify-version`, `correct-version-classification`) is held to "pressed twice, one request".
 * `disabled={isPending}` is a re-render late: a double click delivers its second press to the button as it was drawn.
 *
 * The live harness (`tests/unit/analysis-settings/live-render.ts`: real React, no DOM library) is used the way a double click is
 * delivered: both presses start in the SAME tick, before React has re-rendered the button disabled. The control that follows shows
 * the harness can see the fault: a button guarded only by `isPending` sends twice under the very same double press.
 */

import { QueryClientProvider } from '@tanstack/react-query';
import { createElement, useState } from 'react';
import type { ReactElement } from 'react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('@/shared/api', async (importOriginal) => ({
  ...await importOriginal<Record<string, unknown>>(),
  withdrawDecisionMemoryCase: vi.fn(),
  restoreDecisionMemoryCase: vi.fn(),
}));

import { withdrawDecisionMemoryCase } from '@/shared/api';
import { useIntentKey } from '@/shared/lib';
import { MEMORY_REASON_CODES } from '@/entities/decision-memory';
import type { MemoryReason } from '@/entities/decision-memory';
import { CaseStandingControl, createSingleFlight, pressStanding, standingIntentSignature, useChangeStanding } from '@/features/manage-decision-memory';
import type { StandingChange } from '@/features/manage-decision-memory';

import { newClient } from '../screens/harness';
import { mountLive } from '../analysis-settings/live-render';
import type { LiveRender } from '../analysis-settings/live-render';
import { CASE_A } from './memory-fixtures';

const CHANGE = {
  data: { case_id: CASE_A, changed_at: '2026-11-10T09:00:00Z', kind: 'withdraw', reason_code: 'client_request', status: 'withdrawn', status_event_id: 'dmw_X' },
};

/** The control as the screen draws it, inside a query client. */
function drawn(control: ReactElement): ReactElement {
  return createElement(QueryClientProvider, { client: newClient() }, control);
}

/**
 * The button as it was BEFORE the gate: held by `isPending` alone, sending through `mutate`. Not exported, not used by the
 * application -- it exists so that this file can show that the double press below really does reach a button of that kind twice.
 */
function GuardedByPendingOnly({ caseId }: { readonly caseId: string }) {
  const [reason, setReason] = useState<MemoryReason | ''>('');
  const change = useChangeStanding();
  const key = useIntentKey(standingIntentSignature('withdraw', caseId as never, reason));
  return createElement('div', null,
    createElement('label', { htmlFor: 'r' }, 'Причина'),
    createElement('select', { id: 'r', value: reason, onChange: (event: { target: { value: string } }) => setReason(event.target.value as MemoryReason | '') },
      createElement('option', { value: '' }, 'Выберите причину'),
      ...MEMORY_REASON_CODES.map((code) => createElement('option', { key: code, value: code }, code))),
    createElement('button', {
      type: 'button',
      disabled: reason === '' || change.isPending,
      onClick: () => {
        if (reason === '' || change.isPending) return;
        change.mutate({ kind: 'withdraw', caseId: caseId as never, reason, idempotencyKey: key });
      },
    }, 'Отозвать'));
}

describe('one press, one request', () => {
  let live: LiveRender | undefined;

  beforeEach(() => {
    vi.mocked(withdrawDecisionMemoryCase).mockReset();
  });
  afterEach(async () => {
    await live?.unmount();
    live = undefined;
  });

  it('sends one keyed request when the button is pressed twice in the same tick, and says the change was made', async () => {
    vi.mocked(withdrawDecisionMemoryCase).mockResolvedValue(CHANGE as never);
    live = await mountLive(drawn(createElement(CaseStandingControl, { caseId: CASE_A, status: 'active' })));
    await live.change('Причина', 'client_request');

    const delivered = await Promise.all([live.press('Отозвать'), live.press('Отозвать')]);

    expect(delivered).toEqual([true, true]);
    expect(vi.mocked(withdrawDecisionMemoryCase)).toHaveBeenCalledTimes(1);
    const sent = vi.mocked(withdrawDecisionMemoryCase).mock.calls[0]?.[0] as unknown as { body: { reason_code: string }; idempotencyKey: string; path: { case_id: string } };
    expect(sent.body).toEqual({ reason_code: 'client_request' });
    expect(sent.path.case_id).toBe(CASE_A);
    expect(sent.idempotencyKey).toMatch(/\S/);
    expect(live.markup()).toContain('Дело отозвано');
  });

  it('control: a button held by isPending alone sends twice under the same double press', async () => {
    vi.mocked(withdrawDecisionMemoryCase).mockResolvedValue(CHANGE as never);
    live = await mountLive(drawn(createElement(GuardedByPendingOnly, { caseId: CASE_A })));
    await live.change('Причина', 'client_request');

    await Promise.all([live.press('Отозвать'), live.press('Отозвать')]);

    expect(vi.mocked(withdrawDecisionMemoryCase)).toHaveBeenCalledTimes(2);
    const keys = vi.mocked(withdrawDecisionMemoryCase).mock.calls.map((call) => (call[0] as unknown as { idempotencyKey: string }).idempotencyKey);
    expect(new Set(keys).size).toBe(1);
  });

  it('opens again once the answer is in: a second, separate press is a second intent', async () => {
    vi.mocked(withdrawDecisionMemoryCase).mockResolvedValue(CHANGE as never);
    live = await mountLive(drawn(createElement(CaseStandingControl, { caseId: CASE_A, status: 'active' })));
    await live.change('Причина', 'client_request');
    await live.press('Отозвать');
    expect(vi.mocked(withdrawDecisionMemoryCase)).toHaveBeenCalledTimes(1);

    // The reason was cleared on success, so the button is held again and nothing more is sent without a new choice.
    expect(await live.press('Отозвать')).toBe(false);
    expect(vi.mocked(withdrawDecisionMemoryCase)).toHaveBeenCalledTimes(1);
    await live.change('Причина', 'other');
    await live.press('Отозвать');
    expect(vi.mocked(withdrawDecisionMemoryCase)).toHaveBeenCalledTimes(2);
  });

  it('says a refusal and can be pressed again: the gate reopens when the request fails', async () => {
    vi.mocked(withdrawDecisionMemoryCase).mockRejectedValueOnce(new Error('network'));
    live = await mountLive(drawn(createElement(CaseStandingControl, { caseId: CASE_A, status: 'active' })));
    await live.change('Причина', 'client_request');
    await Promise.all([live.press('Отозвать'), live.press('Отозвать')]);
    expect(vi.mocked(withdrawDecisionMemoryCase)).toHaveBeenCalledTimes(1);
    expect(live.markup()).toContain('Состояние дела не изменено');

    vi.mocked(withdrawDecisionMemoryCase).mockResolvedValue(CHANGE as never);
    await live.press('Отозвать');
    expect(vi.mocked(withdrawDecisionMemoryCase)).toHaveBeenCalledTimes(2);
    expect(live.markup()).toContain('Дело отозвано');
  });
});

describe('pressStanding', () => {
  const command: StandingChange = { kind: 'withdraw', caseId: CASE_A, reason: 'client_request', idempotencyKey: 'key-1' };

  it('sends nothing without a reason and leaves the gate open', () => {
    const flight = createSingleFlight();
    const send = vi.fn(() => Promise.resolve());
    expect(pressStanding(flight, null, send, () => undefined)).toBe(false);
    expect(send).not.toHaveBeenCalled();
    expect(flight.busy).toBe(false);
  });

  it('sends once for presses in the same tick, then again after the answer', async () => {
    const flight = createSingleFlight();
    let release: () => void = () => undefined;
    const send = vi.fn(() => new Promise<void>((resolve) => { release = resolve; }));
    const sent = vi.fn();
    expect(pressStanding(flight, command, send, sent)).toBe(true);
    expect(pressStanding(flight, command, send, sent)).toBe(false);
    expect(send).toHaveBeenCalledTimes(1);
    expect(sent).not.toHaveBeenCalled();
    release();
    await Promise.resolve();
    await Promise.resolve();
    expect(sent).toHaveBeenCalledTimes(1);
    expect(flight.busy).toBe(false);
    expect(pressStanding(flight, command, send, sent)).toBe(true);
    expect(send).toHaveBeenCalledTimes(2);
  });

  it('reopens the gate when the request is refused, and does not say it was sent', async () => {
    const flight = createSingleFlight();
    const sent = vi.fn();
    expect(pressStanding(flight, command, () => Promise.reject(new Error('refused')), sent)).toBe(true);
    await Promise.resolve();
    await Promise.resolve();
    expect(sent).not.toHaveBeenCalled();
    expect(flight.busy).toBe(false);
  });
});
