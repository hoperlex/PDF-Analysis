/**
 * What the review screen derives from the verdict and comment features before it hands the
 * decision panel its props (`WEB-REVIEW-FOLLOWUPS-01`, items 2, 3 and 4).
 *
 *   2. The busy wording follows the REQUEST in flight: a pending reject reads «Отклоняю…», not
 *      «Принимаю…». The screen used to say `'accept'` for any pending verdict.
 *   3. The verdict shown is the answer to the press only when the feature says it answers THIS
 *      finding; the feature returns nothing for another one, and the screen falls back to the
 *      finding's own verdict.
 *   4. Picking a severity in the panel clears the feature's refusal: the screen hands the panel
 *      the feature's `clearRefusal`, and nothing of its own.
 *
 * The verdict and comment features are replaced by recorders with the real module's other
 * exports kept (the panel imports their refusal wording from the same modules); the PANEL is
 * the real one, wrapped to record its props, so the cases read what a reviewer would read.
 * Each case goes red under a quoted mutation (`docs/program/WEB-REVIEW-FOLLOWUPS-01.md`).
 */

import { createElement } from 'react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

const seen = vi.hoisted(() => ({
  panelProps: null as null | Record<string, unknown>,
  verdict: {} as Record<string, unknown>,
  commentPending: false,
  clearRefusal: null as null | (() => void),
}));

vi.mock('@/widgets/decision-panel', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/widgets/decision-panel')>();
  return {
    ...actual,
    DecisionPanel: (props: Record<string, unknown>) => {
      seen.panelProps = props;
      return createElement(actual.DecisionPanel, props as never);
    },
  };
});

vi.mock('@/features/record-verdict', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/features/record-verdict')>();
  return {
    ...actual,
    useRecordVerdict: () => ({
      record: () => {},
      isPending: false,
      pendingIntent: null,
      error: null,
      refusal: null,
      clearRefusal: () => seen.clearRefusal?.(),
      result: null,
      reset: () => {},
      ...seen.verdict,
    }),
  };
});

vi.mock('@/features/append-comment', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/features/append-comment')>();
  return {
    ...actual,
    useAppendComment: () => ({
      append: () => {},
      isPending: seen.commentPending,
      error: null,
      refusal: null,
      result: null,
      reset: () => {},
    }),
  };
});

import { ReviewPage } from '@/_pages/review';
import { queryKeys } from '@/shared/api';
import type { AppendDecisionResponse, FindingDetail } from '@/shared/api';

import { newClient, renderScreen } from '../screens/harness';
import {
  FINDING_UID,
  PROJECT_UID,
  RUN_ID,
  decisionEvent,
  findingDetail,
  observation,
  runStatus,
} from './fixtures';

function mount(detail: FindingDetail): string {
  const client = newClient();
  client.setQueryData(queryKeys.runs.detail(RUN_ID), runStatus());
  client.setQueryData(queryKeys.runs.findings(RUN_ID), {
    data: { items: [detail], page: { next_cursor: null } },
  });
  client.setQueryData(queryKeys.findings.detail(detail.finding_uid), { data: detail });
  client.setQueryData(queryKeys.findings.decisions(detail.finding_uid), {
    data: { items: [], page: { next_cursor: null } },
  });
  return renderScreen(client, createElement(ReviewPage, { projectUid: PROJECT_UID, runId: RUN_ID }));
}

const v2 = findingDetail({ observation: observation({ proposed_severity: 'critical' }) });

beforeEach(() => {
  seen.panelProps = null;
  seen.verdict = {};
  seen.commentPending = false;
  seen.clearRefusal = null;
});

// ------------------------------------------------------------------ item 2

describe('the busy wording follows the request in flight', () => {
  it('says «Отклоняю…» while a reject is pending, and not «Принимаю…»', () => {
    seen.verdict = { isPending: true, pendingIntent: 'reject' };
    const markup = mount(v2);
    expect(seen.panelProps?.pendingIntent).toBe('reject');
    expect(markup).toContain('Отклоняю…');
    expect(markup).not.toContain('Принимаю…');
  });

  it('says «Принимаю…» while an accept is pending, and not «Отклоняю…»', () => {
    seen.verdict = { isPending: true, pendingIntent: 'accept' };
    const markup = mount(v2);
    expect(seen.panelProps?.pendingIntent).toBe('accept');
    expect(markup).toContain('Принимаю…');
    expect(markup).not.toContain('Отклоняю…');
  });

  it('says «Добавляю…» while a comment is pending and no verdict is', () => {
    seen.commentPending = true;
    const markup = mount(v2);
    expect(seen.panelProps?.pendingIntent).toBe('comment');
    expect(markup).toContain('Добавляю…');
    expect(markup).not.toContain('Принимаю…');
    expect(markup).not.toContain('Отклоняю…');
  });

  it('says nothing busy when nothing is pending', () => {
    const markup = mount(v2);
    expect(seen.panelProps?.pendingIntent).toBeNull();
    expect(markup).not.toContain('Принимаю…');
    expect(markup).not.toContain('Отклоняю…');
    expect(markup).not.toContain('Добавляю…');
  });

  it('keeps the three buttons disabled while a reject is pending', () => {
    seen.verdict = { isPending: true, pendingIntent: 'reject' };
    const markup = mount(v2);
    for (const intent of ['accept', 'reject', 'comment']) {
      expect(markup).toMatch(new RegExp(`<button type="button" class="am-button" data-intent="${intent}" disabled=""`));
    }
  });
});

// ------------------------------------------------------------------ item 3

describe('the verdict shown is the answer only for the finding it answers', () => {
  const answer: AppendDecisionResponse = {
    current_verdict: 'rejected',
    event: decisionEvent({ finding_uid: FINDING_UID, event_type: 'reject', verdict: 'rejected' }),
  };

  it('shows the answer the feature holds for this finding', () => {
    seen.verdict = { result: answer };
    mount(findingDetail({ current_verdict: 'pending' }));
    expect(seen.panelProps?.currentVerdict).toBe('rejected');
  });

  it('shows the finding’s own verdict when the feature holds no answer for it', () => {
    seen.verdict = { result: null };
    mount(findingDetail({ current_verdict: 'accepted' }));
    expect(seen.panelProps?.currentVerdict).toBe('accepted');
  });
});

// ------------------------------------------------------------------ item 4

describe('picking a severity clears the refusal through the feature', () => {
  it('hands the panel a handler that calls the feature’s clearRefusal, once per call', () => {
    const calls: string[] = [];
    seen.clearRefusal = () => {
      calls.push('clear');
    };
    mount(v2);
    const handler = seen.panelProps?.onSeverityChosen as (() => void) | undefined;
    expect(typeof handler).toBe('function');
    handler?.();
    expect(calls).toEqual(['clear']);
    handler?.();
    expect(calls).toEqual(['clear', 'clear']);
  });

  it('hands the panel the feature’s refusal as it stands', () => {
    seen.verdict = { refusal: 'severity_required' };
    mount(v2);
    expect(seen.panelProps?.severityRefusal).toBe('severity_required');
  });
});
