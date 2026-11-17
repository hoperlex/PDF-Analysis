/**
 * The decision field in a finding's row on «Разбор» (`R-151n`, `UIP-S06-02`).
 *
 * Each press is one decision event at once, through the panel's own command, and the text typed beside it goes in that event
 * (`row-reason.test.ts` presses it live and reads the request). This suite reads the markup the row draws: the entity's field with
 * ✓, ✕ and «Причина», the view's refusal to offer the press that would repeat the current verdict, a press on its way and the note
 * it left, and the one mechanism by which the field is emptied (a key that changes when a press is written). The model's proposed
 * severity is not a decision: ✓ on a finding whose severity the expert has not chosen needs the panel. A session that may not
 * decide sees no field at all.
 */

import { createElement, isValidElement, type ComponentProps, type ReactElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it } from 'vitest';

import { queryKeys } from '@/shared/api';
import { ReviewPage, acceptNeedsSeverity } from '@/_pages/review';
import { DecisionReasonControl } from '@/entities/expert-decision';
import { FindingList, FindingRowActions } from '@/widgets/finding-list';
import type { FindingRowActionsProps } from '@/widgets/finding-list';
import { groupByCategory } from '@/entities/finding';

import { newClient, renderScreen } from '../screens/harness';
import { PROJECT_UID, RUN_ID, findingDetail, observation, runStatus } from './fixtures';

const noop = (): void => {};

function props(over: Partial<FindingRowActionsProps> = {}): FindingRowActionsProps {
  return { verdict: 'pending', sending: null, note: null, onAccept: noop, onReject: noop, ...over };
}

const markupOf = (over: Partial<FindingRowActionsProps> = {}): string => renderToStaticMarkup(createElement(FindingRowActions, props(over)));

/** The opening tag of the button of this intent, as the markup draws it. */
function buttonOf(markup: string, intent: 'accept' | 'reject'): string {
  const found = markup.match(new RegExp(`<button[^>]*data-intent="${intent}"[^>]*>`));
  if (found === null) throw new Error(`no ${intent} button in ${markup}`);
  return found[0];
}

/** The entity's field as the row returns it, before React draws it. */
function fieldElement(over: Partial<FindingRowActionsProps> = {}): ReactElement<ComponentProps<typeof DecisionReasonControl>> {
  const row = FindingRowActions(props(over)) as ReactElement<{ children: unknown }>;
  const field = row.props.children;
  expect(isValidElement(field)).toBe(true);
  expect((field as ReactElement).type).toBe(DecisionReasonControl);
  return field as ReactElement<ComponentProps<typeof DecisionReasonControl>>;
}

describe('the row’s decision field', () => {
  it('draws ✓, ✕ and the one-line «Причина», named, inside the row’s marker', () => {
    const markup = markupOf();
    expect(markup).toContain('data-row-actions=""');
    expect(buttonOf(markup, 'accept')).toContain('aria-label="Принять"');
    expect(buttonOf(markup, 'reject')).toContain('aria-label="Отклонить"');
    expect(markup).toMatch(/<input[^>]*aria-label="Причина"[^>]*placeholder="Причина"/);
    expect(markup).toContain('>✓<');
    expect(markup).toContain('>✕<');
  });

  it('offers both on a finding awaiting a decision', () => {
    const markup = markupOf();
    expect(buttonOf(markup, 'accept')).not.toContain('disabled');
    expect(buttonOf(markup, 'reject')).not.toContain('disabled');
  });

  it('does not offer the press that would repeat the current verdict', () => {
    const accepted = markupOf({ verdict: 'accepted' });
    expect(buttonOf(accepted, 'accept')).toContain('disabled');
    expect(buttonOf(accepted, 'reject')).not.toContain('disabled');
    const rejected = markupOf({ verdict: 'rejected' });
    expect(buttonOf(rejected, 'reject')).toContain('disabled');
    expect(buttonOf(rejected, 'accept')).not.toContain('disabled');
  });

  it('marks the button of the verdict the finding already has as pressed, as the original lights its ✓ or ✕', () => {
    const state = (verdict: FindingRowActionsProps['verdict']) => {
      const markup = markupOf({ verdict });
      return (['accept', 'reject'] as const).map((intent) => buttonOf(markup, intent).includes('aria-pressed="true"'));
    };
    expect(state('accepted')).toEqual([true, false]);
    expect(state('rejected')).toEqual([false, true]);
    expect(state('pending')).toEqual([false, false]);
  });

  it('holds both while a press is on its way, and shows the note the press left', () => {
    const sending = markupOf({ sending: 'reject' });
    expect(buttonOf(sending, 'accept')).toContain('disabled');
    expect(buttonOf(sending, 'reject')).toContain('disabled');
    expect(markupOf({ note: { tone: 'ok', text: 'Записано' } })).toContain('role="status"');
    expect(markupOf({ note: { tone: 'fail', text: 'Отказ.' } })).toContain('role="alert"');
  });

  it('hands the screen’s commands to the field untouched, so the text goes to them and nowhere else', () => {
    const accept = (_reason: string): void => {};
    const reject = (_reason: string): void => {};
    const field = fieldElement({ onAccept: accept, onReject: reject });
    expect(field.props.onAccept).toBe(accept);
    expect(field.props.onReject).toBe(reject);
  });

  it('empties the field only when the key of the last written press changes', () => {
    const key = (recordedKey?: string): string | null => fieldElement(recordedKey === undefined ? {} : { recordedKey }).key;
    expect(key()).toBe(key());
    expect(key('dec_A')).toBe(key('dec_A'));
    expect(key('dec_B')).not.toBe(key('dec_A'));
    expect(key('dec_A')).not.toBe(key());
  });

  it('needs the panel for ✓ when the model proposed a severity and the expert chose none', () => {
    expect(acceptNeedsSeverity(findingDetail({ observation: observation({ proposed_severity: 'critical' }) }))).toBe(true);
    expect(acceptNeedsSeverity(findingDetail({ observation: observation({ proposed_severity: 'critical' }), decided_severity: 'economic' }))).toBe(false);
    expect(acceptNeedsSeverity(findingDetail({ observation: observation({}) }))).toBe(false);
  });
});

describe('who sees the row actions', () => {
  const FINDINGS = [findingDetail({ observation: observation({}) })];

  it('the list draws none unless the page hands it the actions', () => {
    const markup = renderToStaticMarkup(createElement(FindingList, { groups: groupByCategory(FINDINGS), selectedFindingUid: null, onSelect: noop }));
    expect(markup).not.toContain('data-row-actions');
  });

  function reviewAs(roles: readonly string[]): string {
    const client = newClient();
    client.setQueryData(queryKeys.account.me(), { user_uid: 'usr_01J9ZQ8K7NHVXW3T2R5M6P4Q8F', roles, login: 'наблюдатель' });
    client.setQueryData(queryKeys.runs.detail(RUN_ID), runStatus());
    client.setQueryData(queryKeys.runs.findings(RUN_ID), { data: { items: FINDINGS, page: { next_cursor: null } } });
    return renderScreen(client, createElement(ReviewPage, { projectUid: PROJECT_UID, runId: RUN_ID }));
  }

  it('an expert gets ✓/✕ in each row; a viewer gets none', () => {
    expect(reviewAs(['expert'])).toContain('data-row-actions');
    expect(reviewAs(['viewer'])).not.toContain('data-row-actions');
  });
});
