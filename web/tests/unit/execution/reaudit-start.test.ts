/**
 * `RUN-START-ONE-01b`: the rules of the queue's repeated-Run start, as pure functions, and the optional subject line of the dialog.
 *
 * `reaudit-cost.test.ts` mounts the page and presses it; this file holds the table the page reads, so each step has a negative
 * that can fail without a mount: an estimate that charges nothing is not sent after a changed answer, a failed reading is never sent,
 * a failed send is never followed by another one by itself.
 */

import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it } from 'vitest';

import { ApiError } from '@/shared/api';
import { StartRunCostDialogView } from '@/features/start-run';
import { BINDING_CHANGED_REASON, ESTIMATE_STALE_REASON, reauditEstimateChanged, reauditStep } from '@/_pages/queue/model/reaudit-start';
import type { ReauditStepInput } from '@/_pages/queue/model/reaudit-start';

import { VERSION_UID } from '../review/fixtures';
import { costEstimate } from '../analysis-settings/cost-estimate-fixtures';

const READY: ReauditStepInput = { pending: false, error: null, ready: true, unmetered: false, lookAgain: false, failed: false };
const step = (over: Partial<ReauditStepInput>) => reauditStep({ ...READY, ...over });

describe('the step of a repeated Run', () => {
  it('reads while anything is being read, and while there is no estimate yet', () => {
    expect(step({ pending: true })).toBe('reading');
    expect(step({ pending: true, ready: false })).toBe('reading');
    expect(step({ ready: false })).toBe('reading');
    // A reading in flight wins over a failure of the one before it, and over everything that depends on an estimate.
    expect(step({ pending: true, error: new Error('x'), unmetered: true })).toBe('reading');
  });

  it('is unreadable when the reading failed, whatever else is true, and never sends', () => {
    expect(step({ error: new Error('x'), ready: false })).toBe('unreadable');
    expect(step({ error: new Error('x'), ready: true, unmetered: true })).toBe('unreadable');
    expect(step({ error: new Error('x'), unmetered: true, failed: true })).toBe('unreadable');
    expect(step({ error: undefined })).not.toBe('unreadable');
  });

  it('an estimate that charges nothing is sent by the click', () => {
    expect(step({ unmetered: true })).toBe('send');
  });

  it('an estimate that can charge asks', () => {
    expect(step({ unmetered: false })).toBe('ask');
  });

  it('a changed estimate is asked about even when the new one charges nothing', () => {
    expect(step({ unmetered: true, lookAgain: true })).toBe('ask');
    expect(step({ unmetered: false, lookAgain: true })).toBe('ask');
  });

  it('a failed send is said and is not sent again by the step, whatever the estimate', () => {
    expect(step({ unmetered: true, failed: true })).toBe('failed');
    expect(step({ unmetered: false, failed: true })).toBe('failed');
    expect(step({ unmetered: true, lookAgain: true, failed: true })).toBe('failed');
  });

  it('is exhaustive over the inputs: no combination has no step, and `send` needs all of its conditions', () => {
    const flags = [false, true];
    const sends: string[] = [];
    for (const pending of flags) for (const ready of flags) for (const unmetered of flags)
      for (const lookAgain of flags) for (const failed of flags) for (const error of [null, new Error('x')]) {
        const result = reauditStep({ pending, error, ready, unmetered, lookAgain, failed });
        expect(['reading', 'unreadable', 'send', 'ask', 'failed']).toContain(result);
        if (result === 'send') sends.push(JSON.stringify({ pending, error: error !== null, ready, unmetered, lookAgain, failed }));
      }
    // The one combination that sends: nothing pending, no error, an estimate, free, not looked-again, no failure.
    expect(sends).toEqual([JSON.stringify({ pending: false, error: false, ready: true, unmetered: true, lookAgain: false, failed: false })]);
  });
});

describe('what sends the person back to a fresh estimate', () => {
  const refusal = (status: number, code: 'conflict' | 'analysis_input_invalid', details: Record<string, string>) =>
    new ApiError(status, { contract_version: '1.47.0', error_code: code, message: 'refused', correlation_id: 'cid-reaudit', retryable: false, details }, 'cid-reaudit');

  it('is a stale digest or a changed binding, and nothing else', () => {
    expect(reauditEstimateChanged(refusal(409, 'conflict', { conflict_reason: ESTIMATE_STALE_REASON }))).toBe(true);
    expect(reauditEstimateChanged(refusal(422, 'analysis_input_invalid', { reason: BINDING_CHANGED_REASON }))).toBe(true);
    // The right words under the wrong code, another conflict, another reason, a transport failure, a plain value.
    expect(reauditEstimateChanged(refusal(422, 'analysis_input_invalid', { conflict_reason: ESTIMATE_STALE_REASON }))).toBe(false);
    expect(reauditEstimateChanged(refusal(409, 'conflict', { reason: BINDING_CHANGED_REASON }))).toBe(false);
    expect(reauditEstimateChanged(refusal(409, 'conflict', { conflict_reason: 'idempotency_key_reused' }))).toBe(false);
    expect(reauditEstimateChanged(refusal(422, 'analysis_input_invalid', { reason: 'comparison_only_version' }))).toBe(false);
    expect(reauditEstimateChanged(new TypeError('Failed to fetch'))).toBe(false);
    expect(reauditEstimateChanged(null)).toBe(false);
    expect(reauditEstimateChanged(undefined)).toBe(false);
  });
});

describe('the dialog\'s subject line', () => {
  const dialog = (over: Record<string, unknown>) => renderToStaticMarkup(createElement(StartRunCostDialogView, {
    estimate: costEstimate({ version_uid: VERSION_UID }), relaxed: false, ceiling: '1.5', changed: false, busy: false, staticOpen: true,
    onCeilingChange: () => undefined, onConfirm: () => undefined, onCancel: () => undefined, ...over,
  }));

  it('names what the start is about when it is given, and draws nothing when it is not', () => {
    const named = dialog({ subject: 'Повторный аудит прогона run_X.' });
    expect(named).toContain('data-start-run-subject');
    expect(named).toContain('Повторный аудит прогона run_X.');
    for (const absent of [{}, { subject: undefined }, { subject: null }]) {
      expect(dialog(absent)).not.toContain('data-start-run-subject');
    }
  });
});
