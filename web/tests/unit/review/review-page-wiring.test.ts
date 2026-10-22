/**
 * What the review screen asks of the verdict feature when the panel's buttons are pressed
 * (`REVIEW-V2-UI-01`).
 *
 * The screen owns the closures between the decision panel and `useRecordVerdict`, and a
 * closure that forgets an argument is not seen by any suite that renders markup. So this one
 * stands the panel in with a recorder, renders the real screen over a seeded cache, takes the
 * props the screen gave the panel and calls its handlers, with the verdict hook replaced by a
 * recording `record`. What is asserted is the call the feature would receive:
 *
 *   - Accept passes the observation, the PROPOSED severity of the canonical observation, and
 *     the severity the panel handed up as DECIDED;
 *   - Reject passes the observation and no severity at all;
 *   - the screen hands the panel the proposal, the decided severity the server projects and
 *     the verdict feature's refusal, and nothing of its own invention.
 */

import { createElement } from 'react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

const seen = vi.hoisted(() => ({
  panelProps: null as null | Record<string, unknown>,
  record: null as null | ((...args: unknown[]) => void),
  refusal: null as unknown,
}));

vi.mock('@/widgets/decision-panel', () => ({
  DecisionPanel: (props: Record<string, unknown>) => {
    seen.panelProps = props;
    return null;
  },
}));

vi.mock('@/features/record-verdict', () => ({
  useRecordVerdict: () => ({
    record: (...args: unknown[]) => seen.record?.(...args),
    isPending: false,
    error: null,
    refusal: seen.refusal,
    result: null,
    reset: () => {},
  }),
}));

import { ReviewPage } from '@/_pages/review';
import { queryKeys } from '@/shared/api';
import type { FindingDetail } from '@/shared/api';

import { newClient, renderScreen } from '../screens/harness';
import {
  OBSERVATION_ID,
  PROJECT_UID,
  RUN_ID,
  findingDetail,
  observation,
  runStatus,
} from './fixtures';

function mount(detail: FindingDetail): void {
  const client = newClient();
  client.setQueryData(queryKeys.runs.detail(RUN_ID), runStatus());
  client.setQueryData(queryKeys.runs.findings(RUN_ID), {
    data: { items: [detail], page: { next_cursor: null } },
  });
  client.setQueryData(queryKeys.findings.detail(detail.finding_uid), { data: detail });
  client.setQueryData(queryKeys.findings.decisions(detail.finding_uid), {
    data: { items: [], page: { next_cursor: null } },
  });
  renderScreen(client, createElement(ReviewPage, { projectUid: PROJECT_UID, runId: RUN_ID }));
}

const calls: unknown[][] = [];

beforeEach(() => {
  seen.panelProps = null;
  seen.refusal = null;
  calls.length = 0;
  seen.record = (...args) => {
    calls.push(args);
  };
});

describe('the screen asks the verdict feature with the severity facts of the finding on screen', () => {
  const v2 = findingDetail({
    observation: observation({ proposed_severity: 'critical' }),
    decided_severity: 'economic',
  });

  it('passes the proposal and the expert’s pick on an accept', () => {
    mount(v2);
    (seen.panelProps?.onAccept as (id: string, decided: string) => void)(OBSERVATION_ID, 'recommendation');
    expect(calls).toEqual([
      ['accept', OBSERVATION_ID, { proposed: 'critical', decided: 'recommendation' }],
    ]);
  });

  it('passes the proposal and no pick when the expert picked none', () => {
    mount(v2);
    (seen.panelProps?.onAccept as (id: string, decided: undefined) => void)(OBSERVATION_ID, undefined);
    expect(calls).toEqual([['accept', OBSERVATION_ID, { proposed: 'critical', decided: undefined }]]);
  });

  it('passes no severity at all on a reject', () => {
    mount(v2);
    (seen.panelProps?.onReject as (id: string) => void)(OBSERVATION_ID);
    expect(calls).toEqual([['reject', OBSERVATION_ID]]);
  });

  it('hands the panel the proposal, the decided severity and the feature’s refusal', () => {
    seen.refusal = 'severity_required';
    mount(v2);
    expect(seen.panelProps).toMatchObject({
      observationId: OBSERVATION_ID,
      proposedSeverity: 'critical',
      decidedSeverity: 'economic',
      severityRefusal: 'severity_required',
    });
  });
});

describe('a finding without the fields reaches the panel without them', () => {
  const legacy = findingDetail();

  it('passes no proposal and no decided severity, and an accept carries no proposal', () => {
    mount(legacy);
    expect(seen.panelProps?.proposedSeverity).toBeUndefined();
    expect(seen.panelProps?.decidedSeverity).toBeUndefined();
    (seen.panelProps?.onAccept as (id: string, decided: undefined) => void)(OBSERVATION_ID, undefined);
    expect(calls).toEqual([['accept', OBSERVATION_ID, { proposed: undefined, decided: undefined }]]);
  });
});
