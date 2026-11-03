/**
 * What is actually wrong when work admitted on a group waits for «раннер не в сети» (`EXEC2-FOLLOWUP-01`, ruling `R-149`,
 * ADR-0026 decisions 14 and 15), read from `getExecutorGroupCapacity`.
 *
 * The stored reason `runner_offline` is one word for every case in which **no member of the group can take the work** and none
 * is merely full: a `pull` connection with no runner on line, but also a connection whose revision changed after the group
 * remembered it, one in the archive, one this release does not serve, one whose probe did not pass. The contract carries that
 * precision on the group's capacity — each `ExecutorGroupMemberStatus` has `eligible` and, when it is false, the first
 * `ineligible_reason` of dispatch — and this module turns it into a sentence. It changes no contract and no limit: the wait
 * ends after the 30 minutes the owner kept for every case, and the sentence says so.
 *
 * Rules that keep the sentence honest:
 *
 * - **No reason is invented.** A reading with a member that is eligible (the stored wait is out of date and the next dispatch
 *   will take the work), with a member that is only at capacity (the wait is for a place, which has no end), with a member that
 *   carries no reason, or with a reason this screen has no word for, explains nothing: `null`, and the screen keeps the sentence
 *   it already had.
 * - **The words are a `Record` over the contract's own set**, so a reason the contract gains later is a type error here and not
 *   a code on a screen.
 * - **Every cause is said once**, in the contract's order, with how many connections it holds when the group has more than one.
 */

import type { ExecutorGroupCapacity, ExecutorGroupMemberIssue } from '@/shared/api';
import { EXECUTOR_GROUP_MEMBER_ISSUE_VALUES } from '@/shared/api';
import { formatInstant } from '@/shared/lib';

/** How long work waits with no member able to take it before it ends (`R-149`: 30 minutes, for every case). */
export const OFFLINE_WAIT_LIMIT_MINUTES = 30;

const MINUTE_MS = 60_000;

/** Why one connection of the group cannot take the work now, in the words of the cases the owner named. */
export const WAIT_CAUSE_SENTENCES: Readonly<Record<ExecutorGroupMemberIssue, string>> = {
  revision_changed: 'ревизия подключения изменилась — группу нужно пересобрать',
  connection_archived: 'подключение в архиве',
  not_served: 'подключение не обслуживается',
  probe_not_ok: 'проверка связи не пройдена',
  runner_offline: 'агент офлайн',
  at_capacity: 'все места подключения заняты',
};

export interface WaitCause {
  readonly issue: ExecutorGroupMemberIssue;
  /** How many connections of the group have this as the first thing wrong. */
  readonly members: number;
}

export interface GroupWaitExplanation {
  /** The causes, in the contract's order. Never `at_capacity`, never empty. */
  readonly causes: readonly WaitCause[];
  /** «Подключение группы не может принять работу: агент офлайн.» */
  readonly sentence: string;
}

const isKnownIssue = (value: unknown): value is ExecutorGroupMemberIssue =>
  (EXECUTOR_GROUP_MEMBER_ISSUE_VALUES as readonly unknown[]).includes(value);

/**
 * Why no member of the group can take work that waits for a runner, or `null` when the reading does not say (see the rules in
 * the header). One member: «Подключение группы не может принять работу: агент офлайн.» Several:
 * «Ни одно подключение группы не может принять работу: агент офлайн (подключений: 2); проверка связи не пройдена (подключений: 1).»
 */
export function groupWaitDetail(capacity: Pick<ExecutorGroupCapacity, 'members'>): GroupWaitExplanation | null {
  const members = capacity.members;
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
  const sentence =
    members.length === 1
      ? `Подключение группы не может принять работу: ${WAIT_CAUSE_SENTENCES[causes[0]!.issue]}.`
      : `Ни одно подключение группы не может принять работу: ${causes
          .map((cause) => `${WAIT_CAUSE_SENTENCES[cause.issue]} (подключений: ${cause.members})`)
          .join('; ')}.`;
  return { causes, sentence };
}

/** When the wait that began at `waitingSince` ends if nothing changes: 30 minutes later, or `null` for a time that is not one. */
export function offlineWaitEnd(waitingSince: string | null | undefined): string | null {
  if (waitingSince === undefined || waitingSince === null) return null;
  const began = Date.parse(waitingSince);
  if (Number.isNaN(began)) return null;
  return new Date(began + OFFLINE_WAIT_LIMIT_MINUTES * MINUTE_MS).toISOString();
}

/**
 * That the wait is not for ever: «Если ничего не изменится, ожидание закончится 2026-11-03 10:00:00 UTC (через 30 минут после
 * начала), и работа будет остановлена: исполнитель так и не появился.» Without a start time it says «через 30 минут после начала».
 * The limit restarts when the reason for the wait changes, which is why it is conditional.
 */
export function offlineWaitEndSentence(waitingSince: string | null | undefined): string {
  const end = offlineWaitEnd(waitingSince);
  const when =
    end === null
      ? `через ${OFFLINE_WAIT_LIMIT_MINUTES} минут после начала`
      : `${formatInstant(end)} (через ${OFFLINE_WAIT_LIMIT_MINUTES} минут после начала)`;
  return `Если ничего не изменится, ожидание закончится ${when}, и работа будет остановлена: исполнитель так и не появился.`;
}
