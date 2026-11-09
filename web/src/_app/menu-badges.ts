/**
 * The counters beside the side menu's items, as data (`UI-A-05`, `UI-A-06`, `UI-A-91`).
 *
 * The original's menu carries small numbers on its items: the documents of a section that no expert has checked, the
 * jobs of the queue, the entries of the knowledge base. Here each number is **a figure the API already answers**, and
 * this module only names it: nothing is computed that the server did not count, and a figure that is not known is no
 * badge (never a zero, never an error mark).
 *
 *   - «Очередь»: two figures from one read of `listExecutionQueue` with `limit: 1` (`D-350`): the figure is the page's counts,
 *     not its rows.
 *       - The jobs that are waiting or being run, over the whole history: the `overview` of `ExecutionQueuePage` (contract
 *         1.28.0). It counts every job in a state, so the states that end (`succeeded`, `failed`, `cancelled`,
 *         `dead_letter`) only grow; they are not a "now" and make no count badge.
 *       - The red error badge (`D-331`, `D-395`): `live_failure_count` of the same page (contract 1.43.0) -- the failed
 *         (`failed`, `dead_letter`) jobs that nothing has answered yet, over all history. The original's badge is
 *         `kpis.errors` of «Диспетчер»: the failed attempts that are still the job's live attempt, not a retried or
 *         superseded one. The server says it: a failed job counts unless a later job of the same document version and
 *         analysis exists (it was run again, re-audited or started from a stage). So the figure returns to zero by being
 *         answered and not by ageing, and a failure that happened today is in it whenever its job was accepted. (Until
 *         1.43.0 the badge counted the jobs *accepted* in the last 24 hours that ended in an error, the nearest figure the
 *         overview could give; that window is gone.)
 *   - «База знаний»: `KnowledgeBaseEntryPage.total`, the entries of both journals together -- the decisions on findings and
 *     those on optimisation proposals (`D-362`). The screen behind the link opens on the type «Замечания» (`R-151h`), whose
 *     own total is the findings alone, so the number is larger than the one the reader meets until they choose «Все» (which
 *     shows exactly this figure). **It keeps counting both, as the original's does** (`kbStats.total` is the whole base,
 *     while its screen opens on one tab, «Отклонённые»), and the badge SAYS so: «(замечания и предложения вместе)».
 *     Counting the findings alone would read a different operation (`listDecisions`) on every screen, which is a change to
 *     every route's declared calls in the PC-01 journey's manifest, outside this lane's paths. The screen is `optional`
 *     (`R-150c`: it follows the header's project), so the number follows it too: with a project in the address it is
 *     the entries of that project, the very set the screen lists behind the link (which carries `?project=`), and the
 *     badge says so; without one it is the installation's. A project the address spells as no uid has no figure.
 *   - «Заявки на регистрацию»: `RegistrationRequestPage.pending_total`, the requests waiting for a decision, the
 *     figure of the home page's tile.
 *   - a section of «Разделы»: `SectionDocumentCount.audit_counts.awaiting_decision`, the documents of the section whose
 *     result run has a finding no expert has decided (`docs/program/UI-PARITY-METRICS.md` §2, `R-150o`): the red badge.
 *
 * **Who sees which badge is the menu's own rule.** An item is in the navigation only for a session that may open its
 * screen (`buildNavigation`), and a badge is looked for only on an item that is there: the queue is closed to
 * «Наблюдатель», the registrations to everyone but an administrator, so neither is ever read for them.
 *
 * Every badge has a name in Russian that says what the number counts, which the item's accessible name and the badge's
 * tooltip both carry.
 */

import type { ExecutionQueueStateCount } from '@/shared/api';
import { routes } from '@/shared/lib';
import { KNOWLEDGE_BASE_SCREEN } from '@/entities/expert-decision';
import { REGISTRATIONS_REQUESTS_SCREEN } from '@/entities/registration-request';

import type { Navigation } from './navigation';

/** The reads that feed the menu's badges, one per item that carries one. */
export type MenuBadgeSource = 'queue' | 'knowledge-base' | 'registrations';

/** How a badge is drawn: a plain count, or the red mark of something that waits for a person. */
export type MenuBadgeTone = 'count' | 'alert';

export interface MenuBadge {
  readonly tone: MenuBadgeTone;
  /** Always at least 1: a zero is no badge. */
  readonly count: number;
  /** What the number counts, in the words of the item's accessible name: `Задач в очереди и в работе: 3`. */
  readonly label: string;
  /** The tooltip, when it says more than the label. */
  readonly title?: string;
}

/** The badges of the menu's items, by the item's address. An item with no entry has none. */
export type MenuBadges = Readonly<Record<string, readonly MenuBadge[]>>;

/** The item addresses that carry a badge, and the read behind each. */
const SOURCE_BY_ADDRESS: ReadonlyMap<string, MenuBadgeSource> = new Map([
  [routes.queue(), 'queue'],
  [KNOWLEDGE_BASE_SCREEN, 'knowledge-base'],
  [REGISTRATIONS_REQUESTS_SCREEN, 'registrations'],
]);

/** The read behind the badge of the item at `address`, or `null` when that item carries none. */
export function badgeSourceAt(address: string): MenuBadgeSource | null {
  return SOURCE_BY_ADDRESS.get(address) ?? null;
}

/** The reads this session's menu needs: those whose item the navigation holds. Empty: the frame reads nothing. */
export function badgeSourcesOf(navigation: Navigation): ReadonlySet<MenuBadgeSource> {
  const sources = new Set<MenuBadgeSource>();
  for (const group of navigation.groups) {
    for (const item of group.items) {
      const source = badgeSourceAt(item.address);
      if (source !== null) sources.add(source);
    }
  }
  return sources;
}

/** What the reads hold. `undefined` is "no figure": still loading, refused, failed, or not asked for. */
export interface MenuBadgeReadings {
  readonly queueOverview?: readonly ExecutionQueueStateCount[] | undefined;
  /** `D-395`: the server's count of the failed jobs nothing has answered yet (`live_failure_count`); it makes the red badge. */
  readonly queueLiveFailures?: number | undefined;
  readonly knowledgeBaseTotal?: number | undefined;
  /** `R-150c`: `knowledgeBaseTotal` counts one project's entries (the address names one), not the installation's. */
  readonly knowledgeBaseOfProject?: boolean | undefined;
  readonly pendingRegistrations?: number | undefined;
}

/** The job states that are not over: waiting for a worker, held by one, being run, or waiting to be run again. */
export const QUEUE_OPEN_STATES = ['queued', 'leased', 'running', 'retry_wait'] as const satisfies readonly ExecutionQueueStateCount['state'][];

export const QUEUE_BADGE_LABEL = 'Задач в очереди и в работе';
/** `D-395`: the original's «ошибки» figure -- failures nobody has run again -- in the words of the badge. */
export const QUEUE_ERRORS_BADGE_LABEL = 'Заданий с ошибкой, которые ещё не повторяли';
const QUEUE_ERRORS_BADGE_TITLE =
  'Задания, закончившиеся ошибкой или остановкой после повторов, после которых тот же документ ещё не запускали заново. Число уменьшается, когда документ запущен повторно, и не зависит от того, когда задание было принято. Подробности — на экране «Очередь», в группе «Ошибки».';
/** `D-362`: both journals, said in the label: the screen opens on «Замечания» and shows this figure under «Все». */
export const KNOWLEDGE_BASE_BADGE_LABEL = 'Записей в базе знаний (замечания и предложения вместе)';
/** `R-150c`: the same count, when the address names a project and the screen behind the item lists that project's entries. */
export const KNOWLEDGE_BASE_PROJECT_BADGE_LABEL = 'Записей в базе знаний выбранного проекта (замечания и предложения вместе)';
export const REGISTRATIONS_BADGE_LABEL = 'Заявок на регистрацию, ожидающих решения';
export const UNCHECKED_BADGE_LABEL = 'Не проверено экспертом';
const UNCHECKED_BADGE_TITLE =
  'Документы с замечаниями, по которым эксперт ещё не принял решения. Документы, которые не анализировались, не считаются.';

const named = (label: string, count: number): string => `${label}: ${count}`;

/** How many jobs of `overview` stand in one of `states`. */
function jobsIn(overview: readonly ExecutionQueueStateCount[], states: readonly string[]): number {
  return overview.filter((entry) => states.includes(entry.state)).reduce((sum, entry) => sum + entry.count, 0);
}

/**
 * The queue's badges: the count of the jobs that are waiting or running, then the red mark of the failed jobs nobody has run
 * again (`D-331`, `D-395`). The first comes from the overview, the second from the server's `live_failure_count`; each is absent
 * when its figure is unknown or zero, so a page that carried one and not the other leaves the other badge.
 */
export function queueBadges(
  overview: readonly ExecutionQueueStateCount[] | undefined,
  liveFailures?: number | undefined,
): readonly MenuBadge[] {
  const badges: MenuBadge[] = [];
  const open = overview === undefined ? 0 : jobsIn(overview, QUEUE_OPEN_STATES);
  if (open > 0) badges.push({ tone: 'count', count: open, label: named(QUEUE_BADGE_LABEL, open) });
  const failed = liveFailures ?? 0;
  if (failed > 0) {
    badges.push({
      tone: 'alert',
      count: failed,
      label: named(QUEUE_ERRORS_BADGE_LABEL, failed),
      title: `${named(QUEUE_ERRORS_BADGE_LABEL, failed)}. ${QUEUE_ERRORS_BADGE_TITLE}`,
    });
  }
  return badges;
}

/** A plain count of something the item leads to, or no badge for an unknown figure and for zero. */
function countBadge(label: string, count: number | undefined): readonly MenuBadge[] {
  return count !== undefined && count > 0 ? [{ tone: 'count', count, label: named(label, count) }] : [];
}

/** The red mark of a section: its documents no expert has checked, or no badge when none is known or none waits. */
export function uncheckedBadges(awaitingDecision: number | null | undefined): readonly MenuBadge[] {
  if (awaitingDecision === undefined || awaitingDecision === null || awaitingDecision <= 0) return [];
  return [{
    tone: 'alert',
    count: awaitingDecision,
    label: named(UNCHECKED_BADGE_LABEL, awaitingDecision),
    title: `${named(UNCHECKED_BADGE_LABEL, awaitingDecision)}. ${UNCHECKED_BADGE_TITLE}`,
  }];
}

/** The red badge's words inside a sentence, `не проверено экспертом: 2`, or `null` when the section has no badge. */
export function uncheckedClause(awaitingDecision: number | null | undefined): string | null {
  const badge = uncheckedBadges(awaitingDecision)[0];
  return badge === undefined ? null : `${badge.label.charAt(0).toLowerCase()}${badge.label.slice(1)}`;
}

/** The menu's badges from what the reads hold, keyed by the item's address. Only items that have a badge are present. */
export function menuBadgesOf(readings: MenuBadgeReadings): MenuBadges {
  const found: Record<string, readonly MenuBadge[]> = {};
  const add = (address: string, badges: readonly MenuBadge[]): void => {
    if (badges.length > 0) found[address] = badges;
  };
  add(routes.queue(), queueBadges(readings.queueOverview, readings.queueLiveFailures));
  add(
    KNOWLEDGE_BASE_SCREEN,
    countBadge(
      readings.knowledgeBaseOfProject === true ? KNOWLEDGE_BASE_PROJECT_BADGE_LABEL : KNOWLEDGE_BASE_BADGE_LABEL,
      readings.knowledgeBaseTotal,
    ),
  );
  add(REGISTRATIONS_REQUESTS_SCREEN, countBadge(REGISTRATIONS_BADGE_LABEL, readings.pendingRegistrations));
  return found;
}

/** What a badge shows: the number, and `99+` past two digits, which the label and the tooltip then spell out. */
export function badgeText(count: number): string {
  return count > 99 ? '99+' : String(count);
}

/** The accessible name of an item that carries badges: its own name, then what each number counts. */
export function itemLabelWithBadges(label: string, badges: readonly MenuBadge[]): string {
  return badges.length === 0 ? label : `${label}. ${badges.map((badge) => badge.label).join('. ')}`;
}
