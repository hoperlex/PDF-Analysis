/**
 * `EXEC2-FOLLOWUP-01` item 6 (ruling `R-149`, ADR-0026 decisions 14 and 15): a precise reason for «раннер не в сети».
 *
 * Work admitted on a group that waits with `runner_offline` carries one word for every case in which no member of the group can
 * take it. The screen now also reads the group's capacity (`getExecutorGroupCapacity`) and says what is actually wrong with the
 * members — «агент офлайн», «проверка связи не пройдена», «подключение в архиве», «подключение не обслуживается», «ревизия подключения
 * изменилась — группу нужно пересобрать» — and that the wait ends after the offline limit (30 minutes unless the stand sets another; the
 * sentence says «по умолчанию 30 минут» and shows no time). No contract changes, and no sentence is invented: a reading that does not
 * explain the wait explains nothing. The capacity describes the group's CURRENT revision, so work accepted on an earlier one is told so.
 *
 * Written under `R-149d` and not run in EXEC-2; none of it needs PostgreSQL. Every assertion is one a mutation of the source turns
 * red: the sentences and their order, the count of connections, the rules that return nothing (an eligible member, a member that is
 * only full, a member with no reason or one this screen has no word for), the 30 minutes, the gate that reads nothing for any other
 * reason, and the rule that the component holds no fetch.
 */

import { join } from 'node:path';
import { createElement } from 'react';
import { describe, expect, it } from 'vitest';

import type { ExecutorGroupCapacity, ExecutorGroupMemberIssue, ExecutorGroupMemberStatus, RunQueueReason, RunStatus } from '@/shared/api';
import { EXECUTOR_GROUP_MEMBER_ISSUE_VALUES, RUN_QUEUE_REASON_VALUES, queryKeys } from '@/shared/api';
import {
  CURRENT_STATE_NOTE,
  GroupWaitDetail,
  OFFLINE_WAIT_DEFAULT_MINUTES,
  OFFLINE_WAIT_END_SENTENCE,
  PREVIOUS_REVISION_ALONE,
  PREVIOUS_REVISION_NOTE,
  WAIT_CAUSE_SENTENCES,
  WAIT_DETAIL_UNAVAILABLE,
  executorGroupCapacityKey,
  groupWaitDetail,
  wantsGroupWaitDetail,
} from '@/entities/executor-group';
import { RunProgress } from '@/widgets/run-progress';

import { WEB_ROOT, readText } from '../../guards/lib/repo';
import { PROJECT_UID, runStatus } from '../review/fixtures';
import { newClient, renderWith, seedError } from '../screens/harness';
import { connectionId, revisionId } from '../workers/executor-fixtures';
import { groupId, groupRevisionId } from './executor-groups-fixtures';

const GROUP = groupId(1);
const SINCE = '2026-11-03T09:30:00.000Z';
const REVISION = groupRevisionId(1);
const NEXT_REVISION = groupRevisionId(2);

function member(n: number, issue?: ExecutorGroupMemberIssue | 'unknown_issue'): ExecutorGroupMemberStatus {
  return {
    connection_id: connectionId(n),
    snapshot_revision_id: revisionId(n),
    current_revision_id: revisionId(n),
    eligible: issue === undefined,
    ...(issue === undefined ? {} : { ineligible_reason: issue as ExecutorGroupMemberIssue }),
  };
}

function capacity(...members: ExecutorGroupMemberStatus[]): ExecutorGroupCapacity {
  return { group_id: GROUP, group_revision_id: REVISION, members, capacity: 0, used: 0, waiting: 1 };
}

describe('the words', () => {
  it('say the five cases the owner named, and the sixth in the words of the group card', () => {
    expect(WAIT_CAUSE_SENTENCES.revision_changed).toBe('ревизия подключения изменилась — группу нужно пересобрать');
    expect(WAIT_CAUSE_SENTENCES.connection_archived).toBe('подключение в архиве');
    expect(WAIT_CAUSE_SENTENCES.not_served).toBe('подключение не обслуживается');
    expect(WAIT_CAUSE_SENTENCES.probe_not_ok).toBe('проверка связи не пройдена');
    expect(WAIT_CAUSE_SENTENCES.runner_offline).toBe('агент офлайн');
    expect(WAIT_CAUSE_SENTENCES.at_capacity).toBe('все места подключения заняты');
  });

  it('have a word for every reason the contract has, and no other', () => {
    expect(Object.keys(WAIT_CAUSE_SENTENCES).sort()).toEqual([...EXECUTOR_GROUP_MEMBER_ISSUE_VALUES].sort());
  });

  it('keep the limit the owner kept for every case, as a default and not as a fact', () => {
    expect(OFFLINE_WAIT_DEFAULT_MINUTES).toBe(30);
    expect(OFFLINE_WAIT_END_SENTENCE).toContain('по истечении лимита ожидания (по умолчанию 30 минут)');
  });
});

describe('what is wrong with the group', () => {
  it.each(EXECUTOR_GROUP_MEMBER_ISSUE_VALUES.filter((issue) => issue !== 'at_capacity'))(
    'says %s for a group of one connection',
    (issue) => {
      expect(groupWaitDetail(capacity(member(1, issue)), REVISION)).toEqual({
        causes: [{ issue, members: 1 }],
        revision: 'same',
        sentence: `Подключение группы не может принять работу: ${WAIT_CAUSE_SENTENCES[issue]}.`,
      });
    },
  );

  it('says every cause once, in the contract’s order and with how many connections have it, for a group of several', () => {
    const detail = groupWaitDetail(capacity(
      member(1, 'probe_not_ok'), member(2, 'runner_offline'), member(3, 'runner_offline'), member(4, 'revision_changed'),
    ), REVISION)!;
    expect(detail.causes).toEqual([
      { issue: 'revision_changed', members: 1 },
      { issue: 'probe_not_ok', members: 1 },
      { issue: 'runner_offline', members: 2 },
    ]);
    expect(detail.sentence).toBe(
      'Ни одно подключение группы не может принять работу: ' +
      'ревизия подключения изменилась — группу нужно пересобрать (подключений: 1); ' +
      'проверка связи не пройдена (подключений: 1); агент офлайн (подключений: 2).',
    );
  });

  it('explains nothing when some member could take the work: the stored wait is out of date', () => {
    expect(groupWaitDetail(capacity(member(1, 'runner_offline'), member(2)), REVISION)).toBeNull();
  });

  it('explains nothing when a member only waits for a place: that wait has no end and is not this one', () => {
    expect(groupWaitDetail(capacity(member(1, 'runner_offline'), member(2, 'at_capacity')), REVISION)).toBeNull();
    expect(groupWaitDetail(capacity(member(1, 'at_capacity')), REVISION)).toBeNull();
  });

  it('invents no reason: a member with none, or one this screen has no word for, explains nothing', () => {
    const bare: ExecutorGroupMemberStatus = { ...member(1), eligible: false };
    expect(groupWaitDetail(capacity(bare), REVISION)).toBeNull();
    expect(groupWaitDetail(capacity(member(1, 'unknown_issue')), REVISION)).toBeNull();
    expect(groupWaitDetail(capacity(member(1, 'runner_offline'), bare), REVISION)).toBeNull();
  });

  it('explains nothing for a group with no members', () => {
    expect(groupWaitDetail(capacity(), REVISION)).toBeNull();
  });
});

describe('the revision the work waits on', () => {
  it('says that the work was accepted on a previous revision and shows the current revision’s cause when its members explain one', () => {
    expect(groupWaitDetail(capacity(member(1, 'runner_offline')), NEXT_REVISION)).toEqual({
      causes: [{ issue: 'runner_offline', members: 1 }],
      revision: 'previous',
      sentence: `${PREVIOUS_REVISION_NOTE} Подключение группы не может принять работу: агент офлайн.`,
    });
    expect(PREVIOUS_REVISION_NOTE).toBe('Работа принята на предыдущей ревизии группы; ниже — состояние текущей ревизии.');
  });

  it('says that the current revision gives no cause when its members are eligible or only full, and promises nothing of what it will serve', () => {
    for (const members of [[member(1)], [member(1, 'at_capacity')]]) {
      expect(groupWaitDetail(capacity(...members), NEXT_REVISION)).toEqual({
        causes: [], revision: 'previous', sentence: PREVIOUS_REVISION_ALONE,
      });
    }
    expect(PREVIOUS_REVISION_ALONE).toBe(
      'Работа принята на предыдущей ревизии группы; состояние текущей ревизии причины её ожидания не показывает.',
    );
    for (const sentence of [PREVIOUS_REVISION_NOTE, PREVIOUS_REVISION_ALONE]) {
      expect(sentence).not.toContain('не обслужит');
    }
  });

  it('says that what it shows is the group’s current state when the work names no revision, and does not claim more', () => {
    const detail = groupWaitDetail(capacity(member(1, 'runner_offline')))!;
    expect(detail.revision).toBe('unknown');
    expect(detail.sentence).toBe(`Подключение группы не может принять работу: агент офлайн. ${CURRENT_STATE_NOTE}`);
    expect(CURRENT_STATE_NOTE).toBe('Показано текущее состояние группы.');
    expect(groupWaitDetail(capacity(member(1, 'runner_offline')), REVISION)!.sentence).not.toContain(CURRENT_STATE_NOTE);
  });
});

describe('that the wait ends', () => {
  it('says so as a conditional with the limit as a default, and shows no time of its own', () => {
    expect(OFFLINE_WAIT_END_SENTENCE).toBe(
      'Если ничего не изменится, по истечении лимита ожидания (по умолчанию 30 минут) работа будет остановлена: исполнитель так и не появился.',
    );
    expect(OFFLINE_WAIT_END_SENTENCE).not.toMatch(/\d{4}-\d{2}-\d{2}|UTC|\d{2}:\d{2}/);
  });
});

describe('when the capacity is read at all', () => {
  it('is wanted for a wait for a runner on a named group, and for nothing else', () => {
    expect(wantsGroupWaitDetail({ groupId: GROUP, waitReason: 'runner_offline' })).toBe(true);
    expect(wantsGroupWaitDetail({ groupId: undefined, waitReason: 'runner_offline' })).toBe(false);
    expect(wantsGroupWaitDetail({ groupId: GROUP, waitReason: null })).toBe(false);
    for (const reason of RUN_QUEUE_REASON_VALUES.filter((value) => value !== 'runner_offline')) {
      expect(wantsGroupWaitDetail({ groupId: GROUP, waitReason: reason as RunQueueReason }), reason).toBe(false);
    }
  });

  it('is kept in a hook of the entity: the component and the screens hold no fetch of their own', () => {
    const component = readText(join(WEB_ROOT, 'src', 'entities', 'executor-group', 'ui', 'group-wait-detail.tsx'));
    expect(component).not.toMatch(/useQuery|getExecutorGroupCapacity|fetch\(/);
    const hook = readText(join(WEB_ROOT, 'src', 'entities', 'executor-group', 'api', 'use-group-wait-detail.ts'));
    expect(hook).toContain('useExecutorGroupCapacity(');
    expect(hook).not.toMatch(/refetchInterval|setInterval/);
  });
});

describe('the component', () => {
  function drawn(
    client: ReturnType<typeof newClient>, reason: RunQueueReason | null, over: { revisionId?: string | undefined; ends?: boolean } = {},
  ): string {
    return renderWith(client, createElement(GroupWaitDetail, { groupId: GROUP, revisionId: REVISION, waitReason: reason, ...over }));
  }

  it('says what is wrong and that the wait ends, from the capacity of the group', () => {
    const client = newClient();
    client.setQueryData(executorGroupCapacityKey(GROUP), capacity(member(1, 'probe_not_ok')));
    const markup = drawn(client, 'runner_offline');
    expect(markup).toContain('data-wait-detail="causes"');
    expect(markup).toContain('data-wait-causes="probe_not_ok"');
    expect(markup).toContain('Подключение группы не может принять работу: проверка связи не пройдена.');
    expect(markup).toContain(OFFLINE_WAIT_END_SENTENCE);
  });

  it('says that the work was accepted on a previous revision when the capacity is of the next', () => {
    const client = newClient();
    client.setQueryData(executorGroupCapacityKey(GROUP), { ...capacity(member(1, 'runner_offline')), group_revision_id: NEXT_REVISION });
    const markup = drawn(client, 'runner_offline');
    expect(markup).toContain('data-wait-detail="previous-revision"');
    expect(markup).toContain(`${PREVIOUS_REVISION_NOTE} Подключение группы не может принять работу: агент офлайн.`);
    expect(markup).not.toContain('не обслужит');
    expect(markup).toContain(OFFLINE_WAIT_END_SENTENCE);
  });

  it('says that it shows the current state when the work names no revision', () => {
    const client = newClient();
    client.setQueryData(executorGroupCapacityKey(GROUP), capacity(member(1, 'runner_offline')));
    expect(drawn(client, 'runner_offline', { revisionId: undefined })).toContain(CURRENT_STATE_NOTE);
  });

  it('makes the promise that the wait ends only for work that is counting down, never for paused work', () => {
    const client = newClient();
    client.setQueryData(executorGroupCapacityKey(GROUP), capacity(member(1, 'runner_offline')));
    const paused = drawn(client, 'runner_offline', { ends: false });
    expect(paused).toContain('Подключение группы не может принять работу: агент офлайн.');
    expect(paused).not.toContain('по истечении лимита ожидания');
    expect(drawn(client, 'runner_offline')).toContain('по истечении лимита ожидания');
  });

  it('draws nothing for any other reason, even when the capacity is in the cache', () => {
    const client = newClient();
    client.setQueryData(executorGroupCapacityKey(GROUP), capacity(member(1, 'runner_offline')));
    for (const reason of [null, 'executor_at_capacity', 'needs_reconsent'] as const) expect(drawn(client, reason), String(reason)).toBe('');
  });

  it('draws nothing while the capacity is not read, and nothing for a reading that explains nothing', () => {
    expect(drawn(newClient(), 'runner_offline')).toBe('');
    const client = newClient();
    client.setQueryData(executorGroupCapacityKey(GROUP), capacity(member(1, 'runner_offline'), member(2)));
    expect(drawn(client, 'runner_offline')).toBe('');
  });

  it('says that the reason could not be specified when the capacity cannot be read, and still that the wait ends', () => {
    const client = newClient();
    seedError(client, executorGroupCapacityKey(GROUP), new Error('отказ'));
    const markup = drawn(client, 'runner_offline');
    expect(markup).toContain('data-wait-detail="unavailable"');
    expect(markup).toContain(WAIT_DETAIL_UNAVAILABLE);
    expect(markup).toContain(OFFLINE_WAIT_END_SENTENCE);
  });

  it('draws nothing for work with no group', () => {
    expect(renderWith(newClient(), createElement(GroupWaitDetail, { groupId: undefined, waitReason: 'runner_offline' }))).toBe('');
  });
});

describe('the run page', () => {
  const PLAN = {
    executor_group_id: GROUP,
    executor_group_revision_id: REVISION,
    pin_id: 'модель-основная',
    gateway_model: 'шлюзовая-основная',
    billing: 'metered',
  } as const;

  function page(run: RunStatus, cap?: ExecutorGroupCapacity): string {
    const client = newClient();
    client.setQueryData(queryKeys.runs.detail(run.run_id), run);
    if (cap !== undefined) client.setQueryData(executorGroupCapacityKey(GROUP), cap);
    return renderWith(client, createElement(RunProgress, { projectUid: PROJECT_UID, runId: run.run_id }));
  }

  const waiting = (over: Partial<RunStatus> = {}): RunStatus =>
    runStatus({
      state: 'queued', terminal_at: null, binding_state: 'pending', planned: PLAN,
      wait_reason: 'runner_offline', waiting_since: SINCE, ...over,
    });

  it('says what is wrong with the group of a run that waits for a runner, under the sentence it already has', () => {
    const markup = page(waiting(), capacity(member(1, 'runner_offline')));
    expect(markup).toContain('В очереди: раннер не в сети.');
    expect(markup).toContain('Подключение группы не может принять работу: агент офлайн.');
    expect(markup).toContain(OFFLINE_WAIT_END_SENTENCE);
    expect(markup.indexOf('В очереди: раннер не в сети.')).toBeLessThan(markup.indexOf('Подключение группы не может принять работу'));
  });

  it('says that the run was accepted on a previous revision when the group has a newer one', () => {
    const markup = page(waiting(), { ...capacity(member(1, 'runner_offline')), group_revision_id: NEXT_REVISION });
    expect(markup).toContain(`${PREVIOUS_REVISION_NOTE} Подключение группы не может принять работу: агент офлайн.`);
    expect(markup).not.toContain('не обслужит');
  });

  it('keeps the page as it was when the reason is another, the run is bound or the capacity is not read', () => {
    expect(page(waiting({ wait_reason: 'executor_at_capacity' }), capacity(member(1, 'runner_offline')))).not.toContain('data-wait-detail');
    expect(page(waiting())).not.toContain('data-wait-detail');
    expect(page(runStatus({ state: 'running', terminal_at: null, binding_state: 'bound', planned: PLAN }), capacity(member(1, 'runner_offline'))))
      .not.toContain('data-wait-detail');
  });

  it('reads nothing for a run that waited before groups: it has no group', () => {
    const frozen = runStatus({ state: 'queued', terminal_at: null, queue_reason: 'runner_offline', executor: {
      connection_id: connectionId(1), display_name: 'Основной шлюз', pin_id: 'модель-основная',
    } });
    expect(page(frozen, capacity(member(1, 'runner_offline')))).not.toContain('data-wait-detail');
  });
});
