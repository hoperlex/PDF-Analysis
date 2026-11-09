/**
 * What is actually wrong when work admitted on a group waits for «раннер не в сети» (`EXEC2-FOLLOWUP-01`, ruling `R-149`,
 * ADR-0026 decisions 14 and 15), read from `getExecutorGroupCapacity`.
 *
 * The stored reason `runner_offline` is one word for every case in which **no member of the group can take the work** and none
 * is merely full: a `pull` connection with no runner on line, but also a connection whose revision changed after the group
 * remembered it, one in the archive, one this release does not serve, one whose probe did not pass. The contract carries that
 * precision on the group's capacity — each `ExecutorGroupMemberStatus` has `eligible` and, when it is false, the first
 * `ineligible_reason` of dispatch — and this module turns it into a sentence. It changes no contract and no limit.
 *
 * Rules that keep the sentence honest:
 *
 * - **The reading is of the group's CURRENT revision; the work waits on its FROZEN one.** `ExecutorGroupCapacity.group_revision_id` is the
 *   current revision, and work admitted earlier is dispatched from the revision it froze (`planned.executor_group_revision_id`). When the
 *   two differ the members read are not the ones the work was accepted on: the sentence says that the work was accepted on a previous
 *   revision and that what follows is the state of the current one — it claims nothing of what the new revision will or will not serve.
 *   When the work names no revision, the sentence says that what it shows is the group's current state.
 * - **No reason is invented.** A reading with a member that is eligible (the stored wait is out of date and the next dispatch
 *   will take the work), with a member that is only at capacity (the wait is for a place, which has no end), with a member that
 *   carries no reason, or with a reason this screen has no word for, explains nothing: `null`, and the screen keeps the sentence
 *   it already had.
 * - **The words are a `Record` over the contract's own set**, so a reason the contract gains later is a type error here and not
 *   a code on a screen.
 * - **Every cause is said once**, in the contract's order, with how many connections it holds when the group has more than one.
 * - **The limit is a setting, not a fact.** The wait ends after `AUDITMANAGER_GROUP_OFFLINE_WAIT_SECONDS`, 30 minutes unless the stand sets
 *   another (`R-149c`); the sentence says «по умолчанию 30 минут» and computes no time of its own.
 */

import type { ExecutorGroupCapacity, ExecutorGroupMemberIssue } from '@/shared/api';
import { EXECUTOR_GROUP_MEMBER_ISSUE_VALUES } from '@/shared/api';

/** The limit when the stand sets none (`R-149`: 30 minutes, for every case). */
export const OFFLINE_WAIT_DEFAULT_MINUTES = 30;

/** Why one connection of the group cannot take the work now, in the words of the cases the owner named. */
export const WAIT_CAUSE_SENTENCES: Readonly<Record<ExecutorGroupMemberIssue, string>> = {
  revision_changed: 'ревизия подключения изменилась — группу нужно пересобрать',
  connection_archived: 'подключение в архиве',
  not_served: 'подключение не обслуживается',
  probe_not_ok: 'проверка связи не пройдена',
  runner_offline: 'агент офлайн',
  at_capacity: 'все места подключения заняты',
  host_disabled: 'сервер выключен',
  model_not_verified: 'модель на сервере не подтверждена',
  model_cooling_down: 'сервер временно снял модель',
};

/** The work was accepted on an earlier revision of the group than the one the capacity describes; what follows describes the current one. */
export const PREVIOUS_REVISION_NOTE = 'Работа принята на предыдущей ревизии группы; ниже — состояние текущей ревизии.';

/** The same, when the current revision explains nothing: the reader is told the revisions differ and that the current one gives no cause. */
export const PREVIOUS_REVISION_ALONE =
  'Работа принята на предыдущей ревизии группы; состояние текущей ревизии причины её ожидания не показывает.';

/** The work names no revision, so the reading cannot be tied to the one it waits on. */
export const CURRENT_STATE_NOTE = 'Показано текущее состояние группы.';

export interface WaitCause {
  readonly issue: ExecutorGroupMemberIssue;
  /** How many connections of the group have this as the first thing wrong. */
  readonly members: number;
}

export interface GroupWaitExplanation {
  /** The causes in the capacity read (the current revision's), in the contract's order. Empty only when the work waits on a previous revision and the current one explains nothing. */
  readonly causes: readonly WaitCause[];
  /**
   * How the reading relates to the revision the work waits on. `same`: the members read are the ones that serve it. `previous`: it was
   * accepted on an earlier revision, and the members read are the current revision's, not its own. `unknown`: it names no revision.
   */
  readonly revision: 'same' | 'previous' | 'unknown';
  readonly sentence: string;
}

const isKnownIssue = (value: unknown): value is ExecutorGroupMemberIssue =>
  (EXECUTOR_GROUP_MEMBER_ISSUE_VALUES as readonly unknown[]).includes(value);

interface MemberCauses {
  readonly causes: readonly WaitCause[];
  readonly said: string;
}

/** What the members of one reading say is wrong, or `null` when they explain nothing (an eligible member, a member only full, no reason). */
function explainMembers(members: ExecutorGroupCapacity['members']): MemberCauses | null {
  if (!Array.isArray(members) || members.length === 0) return null;
  const counts = new Map<ExecutorGroupMemberIssue, number>();
  for (const member of members) {
    if (member.eligible !== false) return null;
    const issue = member.ineligible_reason;
    if (!isKnownIssue(issue) || issue === 'at_capacity') return null;
    counts.set(issue, (counts.get(issue) ?? 0) + 1);
  }
  const causes: WaitCause[] = [];
  for (const issue of EXECUTOR_GROUP_MEMBER_ISSUE_VALUES) {
    const held = counts.get(issue);
    if (held !== undefined) causes.push({ issue, members: held });
  }
  const said =
    members.length === 1
      ? `Подключение группы не может принять работу: ${WAIT_CAUSE_SENTENCES[causes[0]!.issue]}.`
      : `Ни одно подключение группы не может принять работу: ${causes
          .map((cause) => `${WAIT_CAUSE_SENTENCES[cause.issue]} (подключений: ${cause.members})`)
          .join('; ')}.`;
  return { causes, said };
}

/**
 * Why no member of the group can take work that waits for a runner, or `null` when the reading does not say (see the rules in
 * the header). `workRevisionId` is the group revision the work froze (`planned.executor_group_revision_id`).
 *
 * One member: «Подключение группы не может принять работу: агент офлайн.» Several:
 * «Ни одно подключение группы не может принять работу: агент офлайн (подключений: 2); проверка связи не пройдена (подключений: 1).»
 * A previous revision: «Работа принята на предыдущей ревизии группы; ниже — состояние текущей ревизии. …» with the current revision's causes
 * after it, or, when they explain nothing, «… состояние текущей ревизии причины её ожидания не показывает.»
 */
export function groupWaitDetail(
  capacity: Pick<ExecutorGroupCapacity, 'members' | 'group_revision_id'>,
  workRevisionId?: string | undefined,
): GroupWaitExplanation | null {
  const relation =
    workRevisionId === undefined ? 'unknown' : workRevisionId === capacity.group_revision_id ? 'same' : 'previous';
  const explained = explainMembers(capacity.members);
  if (relation === 'previous') {
    return explained === null
      ? { causes: [], revision: 'previous', sentence: PREVIOUS_REVISION_ALONE }
      : { causes: explained.causes, revision: 'previous', sentence: `${PREVIOUS_REVISION_NOTE} ${explained.said}` };
  }
  if (explained === null) return null;
  return {
    causes: explained.causes,
    revision: relation,
    sentence: relation === 'unknown' ? `${explained.said} ${CURRENT_STATE_NOTE}` : explained.said,
  };
}

/**
 * That the wait is not for ever: «Если ничего не изменится, по истечении лимита ожидания (по умолчанию 30 минут) работа будет остановлена:
 * исполнитель так и не появился.» No time is computed: the limit is the stand's setting and the clock restarts when the reason for the wait
 * changes, which is why the sentence is conditional. Said only of work that is queued or running, never of work that is paused.
 */
export const OFFLINE_WAIT_END_SENTENCE =
  `Если ничего не изменится, по истечении лимита ожидания (по умолчанию ${OFFLINE_WAIT_DEFAULT_MINUTES} минут) работа будет остановлена: исполнитель так и не появился.`;
