/**
 * `RUN-DELETE-01`: where «Удалить прогон» is offered, to whom, and what its confirmation says.
 *
 * Rendered to static markup over a seeded cache, as the neighbouring screen tests do: the control draws nothing for a state or an account it
 * does not apply to (the owner's rule: what is unavailable is hidden, not disabled), a row of the run list carries it only where the run
 * may be deleted, and the run page offers it beside «Отменить прогон». What must be pressed (the key, the command, the navigation) is the
 * command test's and the browser journey's.
 */
import { createElement } from 'react';
import { describe, expect, it } from 'vitest';

import type { RunState, RunStatus } from '@/shared/api';
import { RUN_STATE_VALUES, queryKeys } from '@/shared/api';
import { RunPage } from '@/_pages/run';
import { RUN_PAGE_LIMIT, RunTable } from '@/entities/audit-run';
import {
  DELETABLE_STATES,
  DELETE_RUN_NOTE,
  DeleteRunConfirm,
  DeleteRunControl,
  deletable,
  mayDelete,
} from '@/features/delete-run';
import { RunList } from '@/widgets/run-list';

import { PROJECT_UID, RUN_ID, VERSION_UID, render, runStatus } from '../review/fixtures';
import { newClient, renderScreen } from '../screens/harness';

const runIdAt = (digit: string): string => `${RUN_ID.slice(0, -1)}${digit}`;
const OFFER = 'data-run-delete="offer"';

function clientOf(roles?: readonly string[]) {
  const client = newClient();
  if (roles !== undefined) client.setQueryData(queryKeys.account.me(), { roles });
  return client;
}

function control(props: Record<string, unknown>, roles?: readonly string[], seed?: RunStatus): string {
  const client = clientOf(roles);
  if (seed !== undefined) client.setQueryData(queryKeys.runs.detail(seed.run_id), seed);
  return renderScreen(client, createElement(DeleteRunControl, { runId: RUN_ID, ...props }));
}

describe('who may delete which run', () => {
  it('a run that ended without a clean result: partial, failed and cancelled, and no other', () => {
    expect([...DELETABLE_STATES].sort()).toEqual(['cancelled', 'failed', 'partial']);
    for (const state of RUN_STATE_VALUES) expect(deletable(state)).toBe(['partial', 'failed', 'cancelled'].includes(state));
    expect(deletable(undefined)).toBe(false);
  });

  it('an expert or an administrator, as for cancelling, never a viewer; an account not known yet is left to the server', () => {
    expect(mayDelete(['expert'])).toBe(true);
    expect(mayDelete(['admin'])).toBe(true);
    expect(mayDelete(['viewer'])).toBe(false);
    expect(mayDelete([])).toBe(false);
    expect(mayDelete(undefined)).toBe(true);
  });
});

describe('the control', () => {
  it('is drawn for each deletable state and hidden for every other', () => {
    for (const state of RUN_STATE_VALUES as readonly RunState[]) {
      const markup = control({ state }, ['expert']);
      if (deletable(state)) expect(markup, state).toContain(OFFER);
      else expect(markup, state).not.toContain('data-run-delete');
    }
  });

  it('is drawn for an expert and an administrator, hidden for a viewer and for an account with no role', () => {
    for (const roles of [['expert'], ['admin'], ['admin', 'expert']]) expect(control({ state: 'failed' }, roles)).toContain(OFFER);
    for (const roles of [['viewer'], []]) expect(control({ state: 'failed' }, roles)).not.toContain('data-run-delete');
    expect(control({ state: 'failed' })).toContain(OFFER);
  });

  it('reads the state from the run\'s status when the screen does not pass one, and draws nothing until it is known', () => {
    expect(control({}, ['expert'], runStatus({ state: 'failed' }))).toContain(OFFER);
    expect(control({}, ['expert'], runStatus({ state: 'partial' }))).toContain(OFFER);
    expect(control({}, ['expert'], runStatus({ state: 'published' }))).not.toContain('data-run-delete');
    expect(control({}, ['expert'], runStatus({ state: 'running', terminal_at: null }))).not.toContain('data-run-delete');
    expect(control({}, ['expert'])).not.toContain('data-run-delete');
  });

  it('says «Удалить прогон» on the run page and «Удалить» in a row, one button either way', () => {
    const page = control({ state: 'failed' }, ['expert']);
    expect(page).toMatch(/<button[^>]*data-run-delete="offer"[^>]*>Удалить прогон<\/button>/);
    const row = control({ state: 'failed', compact: true }, ['expert']);
    expect(row).toMatch(/<button[^>]*data-run-delete="offer"[^>]*>Удалить<\/button>/);
    expect(row).toContain('am-button--small');
    expect(page.match(/<button/g)).toHaveLength(1);
    expect(row.match(/<button/g)).toHaveLength(1);
  });

  it('asks once, in words: the question, what deleting does, «Удалить» and «Отмена»', () => {
    const markup = control({ state: 'failed', initiallyConfirming: true }, ['expert']);
    expect(markup).toContain('data-run-delete="confirm"');
    expect(markup).toContain('role="group"');
    expect(markup).toContain('Удалить прогон?');
    expect(markup).toContain('Прогон исчезнет из списков. Замечания и решения эксперта сохранятся.');
    expect(markup).toMatch(/<button[^>]*data-run-delete-confirm=""[^>]*>Удалить<\/button>/);
    expect(markup).toContain('>Отмена</button>');
    expect(markup).not.toContain(OFFER);
    expect(markup).not.toContain('disabled');
    expect(markup).not.toContain('role="alert"');
  });

  it('keeps the confirmation hidden from a viewer even when it would start open', () => {
    expect(control({ state: 'failed', initiallyConfirming: true }, ['viewer'])).not.toContain('data-run-delete');
  });
});

describe('the open confirmation', () => {
  const noop = (): void => undefined;

  it('is inactive while the command is sent, so a second press is not a second command', () => {
    const markup = render(createElement(DeleteRunConfirm, { pending: true, failure: null, onConfirm: noop, onCancel: noop }));
    expect(markup.match(/disabled=""/g)).toHaveLength(2);
  });

  it('says what the server refused, as an alert under the buttons', () => {
    const sentence = 'Этот прогон удалить нельзя: он не частичный, не с ошибкой и не отменён.';
    const markup = render(createElement(DeleteRunConfirm, { pending: false, failure: sentence, onConfirm: noop, onCancel: noop }));
    expect(markup).toMatch(/role="alert"[^>]*data-run-delete-failure=""[^>]*>Этот прогон удалить нельзя/);
    expect(markup).toContain(DELETE_RUN_NOTE);
  });
});

describe('the run list', () => {
  const STATES: readonly RunState[] = ['published', 'partial', 'failed', 'cancelled', 'running', 'queued'];

  function list(roles?: readonly string[]): string {
    const client = clientOf(roles);
    client.setQueryData(queryKeys.runs.list(VERSION_UID, undefined, RUN_PAGE_LIMIT), {
      items: STATES.map((state, index) => runStatus({ run_id: runIdAt(String(index)), state, ...(state === 'running' || state === 'queued' ? { terminal_at: null } : {}) })),
      page: { next_cursor: null },
    });
    return renderScreen(client, createElement(RunList, { projectUid: PROJECT_UID, versionUid: VERSION_UID }));
  }

  /** The body rows of the table, by run, with whether each carries the delete action. */
  function rows(markup: string): Map<string, boolean> {
    const found = new Map<string, boolean>();
    for (const row of markup.split('<tr').slice(1)) {
      const id = /data-row-key="([^"]+)"/.exec(row)?.[1];
      if (id !== undefined) found.set(id, row.includes(OFFER));
    }
    return found;
  }

  it('carries «Удалить» on the rows of a partial, failed or cancelled run and on no other row', () => {
    const found = rows(list(['expert']));
    expect(found.size).toBe(STATES.length);
    STATES.forEach((state, index) => expect(found.get(runIdAt(String(index))), state).toBe(deletable(state)));
  });

  it('shows it to an administrator, and to an account not known yet', () => {
    for (const roles of [['admin'], undefined]) expect(list(roles).match(/data-run-delete="offer"/g)).toHaveLength(3);
  });

  it('shows it to a viewer on no row', () => {
    expect(list(['viewer'])).not.toContain('data-run-delete');
  });

  it('keeps «Прогон» and «Разобрать» where they were, the action after them', () => {
    const row = list(['expert']).split('<tr').find((part) => part.includes(`data-row-key="${runIdAt('2')}"`)) as string;
    expect(row.indexOf('>Прогон<')).toBeGreaterThan(0);
    expect(row.indexOf('>Прогон<')).toBeLessThan(row.indexOf(OFFER));
  });

  it('is not the table\'s business: a table given no action draws none', () => {
    const markup = render(createElement(RunTable, {
      runs: [runStatus({ state: 'failed' })], runHref: () => '/run', reviewHref: () => '/review',
    }));
    expect(markup).not.toContain('data-run-delete');
  });
});

describe('the run page', () => {
  function page(over: Partial<RunStatus>, roles?: readonly string[]): string {
    const client = clientOf(roles);
    const status = runStatus(over);
    client.setQueryData(queryKeys.runs.detail(status.run_id), status);
    return renderScreen(client, createElement(RunPage, { projectUid: PROJECT_UID, runId: status.run_id }));
  }

  it('offers «Удалить прогон» in the head of a failed, partial or cancelled run, to an expert', () => {
    for (const state of ['failed', 'partial', 'cancelled'] as const) {
      const markup = page({ state, ...(state === 'partial' ? {} : { published_finding_count: 0 }) }, ['expert']);
      expect(markup, state).toMatch(/data-run-head=""[\s\S]*?data-run-delete="offer"[^>]*>Удалить прогон</);
    }
  });

  it('offers cancelling a run that is open and deleting a run that has ended, never both', () => {
    const open = page({ state: 'running', terminal_at: null }, ['expert']);
    expect(open).toContain('data-run-cancel="offer"');
    expect(open).not.toContain('data-run-delete');
    const ended = page({ state: 'failed' }, ['expert']);
    expect(ended).toContain(OFFER);
    expect(ended).not.toContain('data-run-cancel');
  });

  it('offers nothing to delete for a published run or to a viewer', () => {
    expect(page({ state: 'published' }, ['expert'])).not.toContain('data-run-delete');
    expect(page({ state: 'failed' }, ['viewer'])).not.toContain('data-run-delete');
  });
});
