/**
 * Fixtures of the «Прецеденты» suites (`PREC-WEB`): the contract's `PrecedentFindingLabel`, `RunPrecedents`, `FindingPrecedents` and
 * `VectorControl`, built by hand against the generated types, and a seeded «Разбор».
 */

import { createElement } from 'react';

import type { Finding, FindingPrecedents, PrecedentFindingLabel, PrecedentLabelCode, RunPrecedents, VectorControl } from '@/shared/api';
import { queryKeys } from '@/shared/api';
import { ReviewPage } from '@/_pages/review';
import { precedentKeys } from '@/entities/decision-memory';

import { newClient, renderWith } from '../screens/harness';
import { PROJECT_UID, RUN_ID, finding, findingDetail, observation, runStatus } from './fixtures';

export const uidOf = (tail: string) => `fnd_01J9ZQ8K7NHVXW3T2R5M6P4Q${tail}`;

export function label(findingUid: string, code: PrecedentLabelCode, over: Partial<PrecedentFindingLabel> = {}): PrecedentFindingLabel {
  const votes = { total: 10, rejected: 8, accepted: 2, independent: 7, projects: 3 };
  return { finding_uid: findingUid, label: code, critic_reviewed: true, hint_codes: [], revision: 1, votes, ...over };
}

export const runPrecedents = (items: readonly PrecedentFindingLabel[], over: Partial<RunPrecedents> = {}): RunPrecedents => ({
  run_id: RUN_ID, available: items.length > 0, items: [...items], pass_state: 'done', revision: 1, ...over,
});

export const vectorControl = (window: VectorControl['window']): VectorControl => ({
  paused: false, window, window_changed_at: '2026-11-10T20:00:00Z', window_state: 'closed',
});

export function cardOf(findingUid: string, over: Partial<FindingPrecedents> = {}): FindingPrecedents {
  return { finding_uid: findingUid, run_id: RUN_ID, available: true, hints: [], cases: [], possible_norms: [], ...over };
}

export function textFinding(tail: string, text: string, over: Partial<Finding> = {}): Finding {
  return finding({ finding_uid: uidOf(tail), observation: observation({ finding_text: text }), ...over });
}

export interface PageSeed {
  readonly findings: readonly Finding[];
  readonly roles?: readonly string[] | undefined;
  readonly precedents?: RunPrecedents | undefined;
  readonly control?: VectorControl | undefined;
  readonly card?: FindingPrecedents | undefined;
  readonly search?: string;
}

export const navigation = { search: '' };

/** The review screen over a seeded cache. `roles` seeds the account; without it the account is not known yet. */
export function reviewPage(seed: PageSeed): string {
  navigation.search = seed.search ?? '';
  const client = newClient();
  const envelope = { next_cursor: null } as { next_cursor: null };
  if (seed.roles !== undefined) client.setQueryData(queryKeys.account.me(), { user_uid: 'usr_01J9ZQ8K7NHVXW3T2R5M6P4Q8F', roles: seed.roles, login: 'эксперт' });
  client.setQueryData(queryKeys.runs.detail(RUN_ID), runStatus({ run_id: RUN_ID }));
  client.setQueryData(queryKeys.runs.findings(RUN_ID), { data: { items: seed.findings, page: envelope } });
  for (const one of seed.findings) {
    client.setQueryData(queryKeys.findings.detail(one.finding_uid), { data: findingDetail({ ...one }) });
    client.setQueryData(queryKeys.findings.decisions(one.finding_uid), { data: { items: [], page: envelope } });
  }
  if (seed.precedents !== undefined) client.setQueryData(precedentKeys.run(RUN_ID), seed.precedents);
  if (seed.control !== undefined) client.setQueryData(precedentKeys.vectorControl(), seed.control);
  if (seed.card !== undefined) client.setQueryData(precedentKeys.finding(seed.card.finding_uid), seed.card);
  return renderWith(client, createElement(ReviewPage, { projectUid: PROJECT_UID, runId: RUN_ID }));
}
