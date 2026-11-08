/**
 * The counters beside the side menu's items, as data (`UI-A-05`, `UI-A-06`, `UI-A-91`).
 *
 * The original's menu carries small numbers on its items: the documents of a section that no expert has checked, the
 * jobs of the queue, the entries of the knowledge base. Here each number is **a figure the API already answers**, and
 * this module only names it: nothing is computed that the server did not count, and a figure that is not known is no
 * badge (never a zero, never an error mark).
 *
 *   - «Очередь»: two figures, both from the `overview` of `ExecutionQueuePage` (contract 1.28.0), read with `limit: 1`
 *     (`D-350`): the figure is the overview, not the page's rows.
 *       - The jobs that are waiting or being run, over the whole history. The overview counts every job in a state, so the
 *         states that end (`succeeded`, `failed`, `cancelled`, `dead_letter`) only grow; they are not a "now" and make
 *         no count badge.
 *       - The red error badge (`D-331`): the jobs accepted in the **last 24 hours** that ended in `failed` or
 *         `dead_letter`. The original's badge is `kpis.errors` of «Диспетчер»: the failed attempts that are still the
 *         job's live attempt, not a retried or superseded one. A failed job here is final (`state-machines.json`: `failed`
 *         and `dead_letter` have no way out) and a re-audit makes a new job, so "not yet retried" is not a figure the
 *         overview can give; a count over all history never returns to zero, and a badge that is always red says nothing.
 *         The window is the nearest figure that does return to zero: the overview takes `created_from`, so the count
 *         is of jobs *accepted* in the last day (a job accepted earlier that fails now is not in it).
 *   - «База знаний»: `DecisionRecordPage.total`, the decisions on findings (`D-362`). The screen behind the link opens on
 *     the type «Замечания» (`R-151h`), so this is the very number it opens on; the other journal, the decisions on
 *     optimisation proposals, is one click away («Тип») and is not in it, and the badge says «по замечаниям». The screen
 *     is `optional` (`R-150c`: it follows the header's project), so the number follows it too: with a project in the
 *     address it is that project's decisions, the very set the screen lists behind the link (which carries `?project=`),
 *     and the badge says so; without one it is the installation's. A project the address spells as no uid has no figure.
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
  /** `D-331`: the overview of the jobs accepted in the last 24 hours (`created_from`); its failed states make the red badge. */
  readonly queueRecentOverview?: readonly ExecutionQueueStateCount[] | undefined;
  readonly knowledgeBaseTotal?: number | undefined;
  /** `R-150c`: `knowledgeBaseTotal` counts one project's decisions (the address names one), not the installation's. */
  readonly knowledgeBaseOfProject?: boolean | undefined;
  readonly pendingRegistrations?: number | undefined;
}

/** The job states that are not over: waiting for a worker, held by one, being run, or waiting to be run again. */
export const QUEUE_OPEN_STATES = ['queued', 'leased', 'running', 'retry_wait'] as const satisfies readonly ExecutionQueueStateCount['state'][];

/** `D-331`: the job states that are an error, and end the job: `failed`, and `dead_letter` (stopped after the retries). */
export const QUEUE_ERROR_STATES = ['failed', 'dead_letter'] as const satisfies readonly ExecutionQueueStateCount['state'][];
/** `D-331`: how far back the red badge looks, in hours; the words of the badge say it. */
export const QUEUE_ERROR_WINDOW_HOURS = 24;

export const QUEUE_BADGE_LABEL = 'Задач в очереди и в работе';
export const QUEUE_ERRORS_BADGE_LABEL = `Заданий с ошибкой за последние ${QUEUE_ERROR_WINDOW_HOURS} часа`;
const QUEUE_ERRORS_BADGE_TITLE =
  'Задания, принятые за последние 24 часа и закончившиеся ошибкой или остановкой после повторов. Уходит из числа через сутки после постановки. Подробности — на экране «Очередь», в состояниях «Ошибка» и «Остановлена после повторов».';
/** `D-362`: the decisions on findings, the journal the screen behind the item opens on. */
export const KNOWLEDGE_BASE_BADGE_LABEL = 'Решений по замечаниям в базе знаний';
/** `R-150c`: the same count, when the address names a project and the screen behind the item lists that project's decisions. */
export const KNOWLEDGE_BASE_PROJECT_BADGE_LABEL = 'Решений по замечаниям в базе знаний выбранного проекта';
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
 * The queue's badges: the count of the jobs that are waiting or running, then the red mark of the jobs accepted in the last
 * 24 hours that ended in an error (`D-331`). Each comes from its own overview and is absent when that overview is unknown or
 * its figure is zero, so one read failing leaves the other badge.
 */
export function queueBadges(
  overview: readonly ExecutionQueueStateCount[] | undefined,
  recentOverview?: readonly ExecutionQueueStateCount[] | undefined,
): readonly MenuBadge[] {
  const badges: MenuBadge[] = [];
  const open = overview === undefined ? 0 : jobsIn(overview, QUEUE_OPEN_STATES);
  if (open > 0) badges.push({ tone: 'count', count: open, label: named(QUEUE_BADGE_LABEL, open) });
  const failed = recentOverview === undefined ? 0 : jobsIn(recentOverview, QUEUE_ERROR_STATES);
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
  add(routes.queue(), queueBadges(readings.queueOverview, readings.queueRecentOverview));
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
