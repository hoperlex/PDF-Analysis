/**
 * The project selector of the frame, as data (`R-150b`, `R-150c`, `UI-PARITY-01` wave 1).
 *
 * Pure functions over the address and the project list. Nothing here renders, fetches or
 * navigates: the widget turns a {@link SwitcherModel} into markup, and a choice is a plain link
 * to the address {@link chooseProject} computes, so the choice survives a reload, a pasted link
 * and Back/Forward (the address is the only source of the project).
 *
 * ## What a choice does
 *
 *   - on an `optional` screen the screen stays and `?project=` is rewritten
 *     (`switchProject`, which also drops the parameters that only meant something inside the old
 *     project);
 *   - on a `required` or `global` screen the choice opens the chosen project's page;
 *   - «Все проекты» on an optional screen removes the parameter; elsewhere it opens the list.
 *
 * ## The two numbers of a row
 *
 * The original shows two figures beside each object. Both are the contract's own, read as
 * `Project.audit_counts` (`DocumentAuditCounts`): «не запускались» is `not_run`, «нет решений
 * эксперта» is `no_expert_decision` (`not_run + awaiting_decision`, `R-150o`). Each figure is
 * written next to the words that name it, so the row means the same to a screen reader as to an
 * eye. A project whose answer carries no `audit_counts` shows **no** figures: an absent count is
 * unknown, never zero.
 *
 * ## The mark of the project that is open (`D-363`)
 *
 * The original's picker draws a ✓ at the current object and keeps the column on the other rows. Here the rows that are a
 * choice — each project and «Все проекты» — carry `current`: `true` on the one the address names (a project's uid, or no
 * project for «Все проекты»), `false` on the others, so `Menu` marks it and holds the column. «Остальные проекты» and
 * «Новый проект» are not choices and carry none. A project the address names that is not in the first page marks no row,
 * and says so in the button's value (`Проект вне первых N`), not by guessing.
 *
 * ## What is not shown
 *
 * Only the first page of the list is read (`PROJECT_PAGE_LIMIT`, the page the home and the
 * project screens already read, so the cache serves it). When the server says more exist, the
 * model says so and links to the full list; it never presents the first page as the whole.
 */

import type { Project, ProjectPage } from '@/shared/api';
import { formatInstant, projectScopeOf, readProjectContext, routes, switchProject } from '@/shared/lib';
import type { ProjectScope, SearchParamsLike } from '@/shared/lib';
import { classifyProjectListFailure } from '@/entities/project';
import type { ProjectListFailure } from '@/entities/project';

export const SWITCHER_CAPTION = 'Проекты';
export const ALL_PROJECTS_LABEL = 'Все проекты';
export const NEW_PROJECT_LABEL = 'Новый проект';
export const MORE_PROJECTS_LABEL = 'Остальные проекты — в списке';
export const RETRY_LABEL = 'Повторить загрузку';
/** Why the selector does not filter the screen it is on (`R-150c`: a global screen). */
export const GLOBAL_SCREEN_HINT = 'экран общий';

/** The two figures of a row, named as the original names them. */
export const NOT_RUN_LABEL = 'не запускались';
export const NO_EXPERT_DECISION_LABEL = 'нет решений эксперта';

/** The address the selector reads: where the browser is, and its query string. */
export interface SwitcherAddress {
  /** The browser's pathname; `null` when it is not known (a render with no router). */
  readonly pathname: string | null;
  readonly searchParams: SearchParamsLike;
}

/** What is known of the project list. */
export type SwitcherList =
  /** Not read yet, or in flight. */
  | { readonly kind: 'loading' }
  | { readonly kind: 'error'; readonly failure: ProjectListFailure }
  | {
      readonly kind: 'ready';
      readonly projects: readonly Project[];
      /** The server has more projects than this page holds. */
      readonly more: boolean;
      /** A newer read failed after this one succeeded; the rows are real but may be old. */
      readonly refreshFailure: ProjectListFailure | null;
    };

/** One line above the entries: a status, or a fault. */
export interface SwitcherNote {
  readonly tone: 'status' | 'alert';
  readonly text: string;
  readonly detail?: string;
  readonly correlationId?: string;
}

/** One entry of the menu. A retry is the only entry that is not an address. */
export type SwitcherEntry =
  | {
      readonly kind: 'link';
      readonly label: string;
      readonly href: string;
      /** `D-363`: the entry is a choice (a project, or «Все проекты»), and `true` marks the one made. Absent: not a choice. */
      readonly current?: boolean;
    }
  | { readonly kind: 'retry'; readonly label: string };

export interface SwitcherModel {
  /** The class of the screen being shown; `null` for an address the registry does not have. */
  readonly scope: ProjectScope | null;
  /** The project the address names, or `null` for «Все проекты». */
  readonly projectUid: string | null;
  /** What the button shows: the project's name, or the reason it cannot. */
  readonly value: string;
  /** «экран общий» on a global screen, else `null`. */
  readonly hint: string | null;
  /** The button's accessible name. */
  readonly triggerLabel: string;
  readonly notes: readonly SwitcherNote[];
  readonly entries: readonly [SwitcherEntry, ...SwitcherEntry[]];
}

/** The class of the screen and the project its address names. */
export function switcherContext(address: SwitcherAddress): {
  readonly scope: ProjectScope | null;
  readonly projectUid: string | null;
} {
  if (address.pathname === null) return { scope: null, projectUid: null };
  return {
    scope: projectScopeOf(address.pathname),
    projectUid: readProjectContext(address.pathname, address.searchParams).projectUid,
  };
}

/**
 * Where choosing `projectUid` (`null` is «Все проекты») leads from `address`.
 *
 * An unregistered address (a 404) has no class and nothing to rewrite, so it behaves like a
 * global screen: the choice opens the project's page, or the list.
 */
export function chooseProject(address: SwitcherAddress, projectUid: string | null): string {
  const { scope } = switcherContext(address);
  if (scope === 'optional' && address.pathname !== null) {
    const query = switchProject(address.searchParams, projectUid).toString();
    return query === '' ? address.pathname : `${address.pathname}?${query}`;
  }
  return projectUid === null || projectUid === '' ? routes.projects() : routes.project(projectUid);
}

/** A name for display: one line, no stray whitespace. The stored name is not changed. */
function displayName(project: Project): string {
  return project.name.replace(/\s+/g, ' ').trim();
}

/** `YYYY-MM-DD` of a creation instant, or the text `formatInstant` gives for one it cannot read. */
function createdDay(project: Project): string {
  const text = formatInstant(project.created_at);
  return /^\d{4}-\d\d-\d\d/.test(text) ? text.slice(0, 10) : text;
}

/** The two figures of a project, or `null` when its answer carries none. */
export function projectFigures(project: Project): string | null {
  const counts = project.audit_counts;
  if (counts === undefined) return null;
  return `${NOT_RUN_LABEL} ${counts.not_run} · ${NO_EXPERT_DECISION_LABEL} ${counts.no_expert_decision}`;
}

function rowLabel(name: string, figures: string | null): string {
  // A newline: the menu item's text is a plain string, and the widget's style reads it as a line break
  // (`white-space: pre-line`), so the name and the figures are two lines of one item.
  return figures === null ? name : `${name}\n${figures}`;
}

/** The labels of the entries that are not projects. A project's row may not read as one of them. */
const RESERVED_LABELS: readonly string[] = [ALL_PROJECTS_LABEL, MORE_PROJECTS_LABEL, NEW_PROJECT_LABEL, RETRY_LABEL];

/**
 * One label per project, in the list's order, and none like another or like a fixed entry.
 *
 * The menu keys an item by its label, and two projects can carry the same name and the same
 * figures (or one can be named «Новый проект» when the answer carries no figures); the reader
 * could not tell those rows apart either. Equal labels get the day the project was created,
 * and any that are still equal get their place among the equals.
 */
export function projectRowLabels(projects: readonly Project[]): string[] {
  const names = projects.map(displayName);
  const figures = projects.map(projectFigures);
  const labels = names.map((name, index) => rowLabel(name, figures[index] ?? null));
  const taken = new Map<string, number>();
  for (const label of [...RESERVED_LABELS, ...labels]) taken.set(label, (taken.get(label) ?? 0) + 1);
  const withDay = labels.map((label, index) =>
    (taken.get(label) ?? 0) > 1
      ? rowLabel(`${names[index]} (создан ${createdDay(projects[index] as Project)})`, figures[index] ?? null)
      : label,
  );
  const seen = new Map<string, number>(RESERVED_LABELS.map((label) => [label, 1]));
  return withDay.map((label) => {
    const count = (seen.get(label) ?? 0) + 1;
    seen.set(label, count);
    return count === 1 ? label : `${label} №${count}`;
  });
}

/** The list state for a query's `data` and `error` (`error` is `null` when the read has not failed). */
export function switcherListOf(data: ProjectPage | undefined, error: unknown): SwitcherList {
  if (data !== undefined) {
    return {
      kind: 'ready',
      projects: data.items,
      more: data.page.next_cursor !== null,
      refreshFailure: error === null || error === undefined ? null : classifyProjectListFailure(error),
    };
  }
  if (error !== null && error !== undefined) return { kind: 'error', failure: classifyProjectListFailure(error) };
  return { kind: 'loading' };
}

/** What the button shows for `projectUid` given what is known of the list. */
function valueOf(projectUid: string | null, list: SwitcherList): string {
  if (projectUid === null) return ALL_PROJECTS_LABEL;
  switch (list.kind) {
    case 'loading':
      return 'Загрузка…';
    case 'error':
      return 'Название недоступно';
    case 'ready': {
      const found = list.projects.find((project) => project.project_uid === projectUid);
      if (found !== undefined) return displayName(found);
      return list.more ? `Проект вне первых ${list.projects.length}` : 'Неизвестный проект';
    }
  }
}

function notesOf(list: SwitcherList): SwitcherNote[] {
  switch (list.kind) {
    case 'loading':
      return [{ tone: 'status', text: 'Загрузка проектов…' }];
    case 'error':
      return [
        {
          tone: 'alert',
          text: 'Проекты не загрузились',
          detail: list.failure.title,
          ...(list.failure.correlationId === null ? {} : { correlationId: list.failure.correlationId }),
        },
      ];
    case 'ready': {
      const notes: SwitcherNote[] = [];
      if (list.refreshFailure !== null) {
        notes.push({ tone: 'alert', text: 'Список мог устареть: обновить его не удалось.', detail: list.refreshFailure.title });
      }
      if (list.projects.length === 0) notes.push({ tone: 'status', text: 'Проектов пока нет.' });
      if (list.more) notes.push({ tone: 'status', text: `Показаны первые ${list.projects.length}.` });
      return notes;
    }
  }
}

/** The whole selector for `address` and `list`. */
export function buildSwitcherModel(address: SwitcherAddress, list: SwitcherList): SwitcherModel {
  const { scope, projectUid } = switcherContext(address);
  const value = valueOf(projectUid, list);
  const hint = scope === 'global' ? GLOBAL_SCREEN_HINT : null;

  const entries: SwitcherEntry[] = [];
  const canRetry = list.kind === 'error' ? list.failure.retryable : list.kind === 'ready' && list.refreshFailure !== null && list.refreshFailure.retryable;
  if (canRetry) entries.push({ kind: 'retry', label: RETRY_LABEL });
  if (list.kind === 'ready') {
    const labels = projectRowLabels(list.projects);
    list.projects.forEach((project, index) => {
      entries.push({
        kind: 'link',
        label: labels[index] as string,
        href: chooseProject(address, project.project_uid),
        current: projectUid === project.project_uid,
      });
    });
  }
  entries.push({ kind: 'link', label: ALL_PROJECTS_LABEL, href: chooseProject(address, null), current: projectUid === null });
  if (list.kind === 'ready' && list.more) entries.push({ kind: 'link', label: MORE_PROJECTS_LABEL, href: routes.projects() });
  // The creation form lives on the project list; the selector links to it rather than copying it.
  entries.push({ kind: 'link', label: NEW_PROJECT_LABEL, href: routes.projects() });

  const [first, ...rest] = entries;
  return {
    scope,
    projectUid,
    value,
    hint,
    triggerLabel: `${SWITCHER_CAPTION}: ${value}${hint === null ? '' : `, ${hint}`}`,
    notes: notesOf(list),
    entries: [first as SwitcherEntry, ...rest],
  };
}
