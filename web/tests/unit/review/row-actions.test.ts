/**
 * ✓/✕ in a finding's row on «Разбор» (`R-151n`).
 *
 * Each press is one decision event at once, through the panel's own command. The view does not offer the press
 * that would repeat the current verdict, shows a press on its way and the note it left. The model's proposed
 * severity is not a decision: ✓ on a finding whose severity the expert has not chosen needs the panel. A session
 * that may not decide sees no row action at all.
 */

import { createElement, isValidElement, type ReactElement, type ReactNode } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it } from 'vitest';

import { queryKeys } from '@/shared/api';
import { ReviewPage, acceptNeedsSeverity } from '@/_pages/review';
import { FindingList, FindingRowActions } from '@/widgets/finding-list';
import type { FindingRowActionsProps } from '@/widgets/finding-list';
import { groupByCategory } from '@/entities/finding';

import { newClient, renderScreen } from '../screens/harness';
import { PROJECT_UID, RUN_ID, findingDetail, observation, runStatus } from './fixtures';

const noop = (): void => {};

function props(over: Partial<FindingRowActionsProps> = {}): FindingRowActionsProps {
  return { verdict: 'pending', sending: null, note: null, onAccept: noop, onReject: noop, ...over };
}

function buttons(node: ReactNode, found: ReactElement<{ disabled?: boolean; onClick?: () => void; 'aria-label'?: string }>[] = []) {
  if (Array.isArray(node)) node.forEach((child) => buttons(child, found));
  else if (isValidElement<{ children?: ReactNode }>(node)) {
    if (node.type === 'button') found.push(node as ReactElement<{ disabled?: boolean; onClick?: () => void; 'aria-label'?: string }>);
    buttons(node.props.children, found);
  }
  return found;
}

describe('the row’s ✓ and ✕', () => {
  it('offers both on a finding awaiting a decision, and each press calls its own command once', () => {
    const pressed: string[] = [];
    const element = FindingRowActions(props({ onAccept: () => pressed.push('accept'), onReject: () => pressed.push('reject') }));
    const [accept, reject] = buttons(element);
    expect([accept?.props['aria-label'], reject?.props['aria-label']]).toEqual(['Принять', 'Отклонить']);
    expect([accept?.props.disabled, reject?.props.disabled]).toEqual([false, false]);
    accept?.props.onClick?.();
    reject?.props.onClick?.();
    expect(pressed).toEqual(['accept', 'reject']);
  });

  it('does not offer the press that would repeat the current verdict', () => {
    const [acceptOnAccepted] = buttons(FindingRowActions(props({ verdict: 'accepted' })));
    const [, rejectOnRejected] = buttons(FindingRowActions(props({ verdict: 'rejected' })));
    expect(acceptOnAccepted?.props.disabled).toBe(true);
    expect(rejectOnRejected?.props.disabled).toBe(true);
  });

  it('marks the button of the verdict the finding already has as pressed, as the original lights its ✓ or ✕', () => {
    const state = (verdict: FindingRowActionsProps['verdict']) =>
      buttons(FindingRowActions(props({ verdict }))).map((button) => (button.props as { 'aria-pressed'?: boolean })['aria-pressed']);
    expect(state('accepted')).toEqual([true, false]);
    expect(state('rejected')).toEqual([false, true]);
    expect(state('pending')).toEqual([false, false]);
  });

  it('holds both while a press is on its way, and shows the note the press left', () => {
    const sending = buttons(FindingRowActions(props({ sending: 'reject' })));
    expect(sending.map((button) => button.props.disabled)).toEqual([true, true]);
    expect(renderToStaticMarkup(createElement(FindingRowActions, props({ note: { tone: 'ok', text: 'Записано' } })))).toContain('role="status"');
    expect(renderToStaticMarkup(createElement(FindingRowActions, props({ note: { tone: 'fail', text: 'Отказ.' } })))).toContain('role="alert"');
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
