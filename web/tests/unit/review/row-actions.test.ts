/**
 * The decision field in a finding's row on «Разбор» (`R-151n`, `UIP-S06-02`).
 *
 * Each press is one decision event at once, through the panel's own command, and the text typed beside it goes in that event
 * (`row-reason.test.ts` presses it live and reads the request). This suite reads the markup the row draws: the entity's field with
 * ✓, ✕ and «Причина», the view's refusal to offer the press that would repeat the current verdict, a press on its way and the note
 * it left, and the one mechanism by which the field is emptied (a key that changes when a press is written). The model's proposed
 * severity is not a decision: a finding it proposed one for has the choice «Критичность» beside ✓, empty until the expert chooses
 * (`UIP-S06-08`), and a finding it proposed none for has no choice at all. A session that may not decide sees no field at all.
 */

import { Children, createElement, isValidElement, type ComponentProps, type ReactElement, type ReactNode } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it } from 'vitest';

import { SEVERITY_VALUES, queryKeys } from '@/shared/api';
import type { Severity } from '@/shared/api';
import { ReviewPage, acceptNeedsSeverity } from '@/_pages/review';
import { DecisionReasonControl } from '@/entities/expert-decision';
import { FindingList, FindingRowActions } from '@/widgets/finding-list';
import type { FindingRowActionsProps } from '@/widgets/finding-list';
import { SEVERITY_LABELS, groupByCategory } from '@/entities/finding';

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

/** The entity's field as the row returns it, before React draws it. Without a choice of severity it is the row's only child. */
function fieldElement(over: Partial<FindingRowActionsProps> = {}): ReactElement<ComponentProps<typeof DecisionReasonControl>> {
  const row = FindingRowActions(props(over)) as ReactElement<{ children: ReactNode }>;
  const field = Children.toArray(row.props.children).find((child) => isValidElement(child) && child.type === DecisionReasonControl);
  expect(field).toBeDefined();
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
    const accept: FindingRowActionsProps['onAccept'] = () => {};
    const reject: FindingRowActionsProps['onReject'] = () => {};
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

const CHOICE = (over: Partial<NonNullable<FindingRowActionsProps['severity']>> = {}): NonNullable<FindingRowActionsProps['severity']> =>
  ({ value: '', onChange: noop, required: true, invalid: false, ...over });

/** The opening tag of the select, as the markup draws it. */
function selectTag(markup: string): string {
  const found = /<select[^>]*>/.exec(markup);
  if (found === null) throw new Error(`no select in ${markup}`);
  return found[0];
}

describe('the choice of severity beside ✓ (`UIP-S06-08`)', () => {
  it('draws none for a finding the model proposed no severity for', () => {
    const markup = markupOf();
    expect(markup).not.toContain('<select');
    expect(markup).not.toContain('data-row-severity');
    expect(markup).not.toContain('Критичность');
  });

  it('draws «Критичность» with an empty first item and the five severities, and selects none of them', () => {
    const markup = markupOf({ severity: CHOICE() });
    expect(selectTag(markup)).toContain('aria-label="Критичность"');
    expect(selectTag(markup)).toContain('data-row-severity=""');
    const options = [...markup.matchAll(/<option value="([^"]*)"([^>]*)>([^<]*)<\/option>/g)].map((m) => [m[1], m[3]]);
    expect(options).toEqual([['', 'Критичность'], ...SEVERITY_VALUES.map((value) => [value, SEVERITY_LABELS[value]])]);
    const selected = [...markup.matchAll(/<option value="([^"]*)"[^>]*selected/g)].map((m) => m[1]);
    expect(selected).toEqual(['']);
  });

  it('shows the value it is handed and no other: the proposal is not its business', () => {
    for (const value of SEVERITY_VALUES) {
      const markup = markupOf({ severity: CHOICE({ value }) });
      expect([...markup.matchAll(/<option value="([^"]*)"[^>]*selected/g)].map((m) => m[1])).toEqual([value]);
    }
  });

  it('stands before ✓, so the choice is made on the way to it', () => {
    const markup = markupOf({ severity: CHOICE() });
    expect(markup.indexOf('<select')).toBeGreaterThan(-1);
    expect(markup.indexOf('<select')).toBeLessThan(markup.indexOf('data-intent="accept"'));
    expect(markup.indexOf('data-intent="accept"')).toBeLessThan(markup.indexOf('aria-label="Причина"'));
  });

  it('says it is required while ✓ needs a choice, and invalid after a ✓ was refused for want of one', () => {
    expect(selectTag(markupOf({ severity: CHOICE({ required: true }) }))).toContain('aria-required="true"');
    expect(selectTag(markupOf({ severity: CHOICE({ required: false }) }))).not.toContain('aria-required');
    expect(selectTag(markupOf({ severity: CHOICE() }))).not.toContain('aria-invalid');
    expect(selectTag(markupOf({ severity: CHOICE({ invalid: true }) }))).toContain('aria-invalid="true"');
  });

  it('is held while a press is on its way and once the finding is accepted, and open otherwise', () => {
    expect(selectTag(markupOf({ severity: CHOICE() }))).not.toContain('disabled');
    expect(selectTag(markupOf({ severity: CHOICE(), verdict: 'rejected' }))).not.toContain('disabled');
    expect(selectTag(markupOf({ severity: CHOICE(), sending: 'accept' }))).toContain('disabled');
    expect(selectTag(markupOf({ severity: CHOICE({ value: 'economic' }), verdict: 'accepted' }))).toContain('disabled');
  });

  it('hands the row a severity for the five values and the empty choice, and nothing for a value outside them', () => {
    const calls: (Severity | '')[] = [];
    const row = FindingRowActions(props({ severity: CHOICE({ onChange: (next) => { calls.push(next); } }) })) as ReactElement<{ children: ReactNode }>;
    const select = Children.toArray(row.props.children).find((child) => isValidElement(child) && child.type === 'select') as ReactElement<{
      onChange: (event: { target: { value: string } }) => void;
    }>;
    for (const value of [...SEVERITY_VALUES, '', 'urgent']) select.props.onChange({ target: { value } });
    expect(calls).toEqual([...SEVERITY_VALUES, '', '']);
  });

  it('is on the page for a finding the model proposed one for, and only there', () => {
    const client = newClient();
    client.setQueryData(queryKeys.account.me(), { user_uid: 'usr_01J9ZQ8K7NHVXW3T2R5M6P4Q8F', roles: ['expert'], login: 'эксперт' });
    client.setQueryData(queryKeys.runs.detail(RUN_ID), runStatus());
    const proposed = findingDetail({ finding_uid: 'fnd_01J9ZQ8K7NHVXW3T2R5M6P4QC1', observation: observation({ proposed_severity: 'critical' }) });
    const plain = findingDetail({ finding_uid: 'fnd_01J9ZQ8K7NHVXW3T2R5M6P4QC2', observation: observation({}) });
    client.setQueryData(queryKeys.runs.findings(RUN_ID), { data: { items: [proposed, plain], page: { next_cursor: null } } });
    const markup = renderScreen(client, createElement(ReviewPage, { projectUid: PROJECT_UID, runId: RUN_ID }));
    expect((markup.match(/data-row-actions=/g) ?? []).length).toBe(2);
    expect((markup.match(/data-row-severity=/g) ?? []).length).toBe(1);
    // It stands in the row of the finding that has the proposal: between its number and the next finding's row.
    const at = markup.indexOf('data-row-severity');
    expect(at).toBeGreaterThan(markup.indexOf(`data-row-key="${proposed.finding_uid}"`));
    expect(at).toBeLessThan(markup.indexOf(`data-row-key="${plain.finding_uid}"`));
    // The model's proposal is not selected in it.
    expect([...markup.matchAll(/<option value="([^"]*)"[^>]*selected/g)].map((m) => m[1])).toEqual(['']);
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
