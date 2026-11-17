/**
 * The object selector of the frame, as data (`R-150b`, `R-150c`, `UI-PARITY-01` wave 1).
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
 *   - «Все объекты» on an optional screen is the explicit `?project=all` (`UIP-G-06`: the absence of the parameter would
 *     bring the account's last object back); elsewhere it opens the list.
 *
 * ## The object that is open (`UIP-G-06`)
 *
 * On an `optional` screen whose address names no object, the open object is the account's last one (`remembered`, from
 * `getMe`), as `resolveProjectContext` says; the button names it and its row carries the ✓. While `getMe` is on its way the
 * button says «Загрузка…». A `global` screen keeps what the address says.
 *
 * Choosing one object is also a command: the widget calls `setMyLastProject` for it (`chosenProject` says which object a
 * clicked link chose; «Все объекты», «Новый объект» and the full list are not objects). The command is the widget's and not
 * this module's: nothing here fetches.
 *
 * ## The two numbers of a row (`UIP-G-08`)
 *
 * The original shows two figures beside each object, as small badges with no words and the words in a tooltip. Both are the
 * contract's own, read as `Project.audit_counts` (`DocumentAuditCounts`): «не запускались» is `not_run`, «нет решений
 * эксперта» is `no_expert_decision` (`not_run + awaiting_decision`, `R-150o`). A row carries them as {@link RowFigure}s (the
 * count, its words and its tooltip), and its accessible name says the words beside the numbers, so the row means the same to
 * a screen reader as to an eye. A project whose answer carries no `audit_counts` carries **no** figures and shows no badge:
 * an absent count is unknown, never zero (a zero that the server did send is shown).
 *
 * ## The mark of the project that is open (`D-363`)
 *
 * The original's picker draws a ✓ at the current object and keeps the column on the other rows. Here the rows that are a
 * choice — each project and «Все проекты» — carry `current`: `true` on the one the address names (a project's uid, or no
 * project for «Все проекты»), `false` on the others, so `Menu` marks it and holds the column. «Остальные проекты» and
 * «Новый проект» are not choices and carry none. A project the address names that is not in the first page marks no row,
 * and says so in the button's value (`Проект вне первых N`), not by guessing.
 *
 * ## «Новый объект» (`UIP-S03-01`)
 *
 * The last entry makes an object, and **where the island can open the window «Новый объект» it does** (`creates` marks the
 * entry; `switcherMenuProps` turns it into an action when it is given the handler). The entry still carries the address of the
 * list's form, `routes.projects()`: that is what the first render, a render with no island and every instrument that draws the
 * menu without a handler show, so the entry works with no script too. It is left out when the account is known not to be an
 * expert (`SwitcherOptions.mayCreate`, `R-150e`): the server refuses the create to anyone else. When the window creates the
 * object, the object becomes the open one exactly as a click on its row does ({@link afterObjectCreated}): the choice is kept
 * (`setMyLastProject`) and the address is the one {@link chooseProject} computes.
 *
 * ## What is not shown
 *
 * Only the first page of the list is read (`PROJECT_PAGE_LIMIT`). When the server says more exist, the
 * model says so (the note «Показаны первые N», and the row linking to the full list); it never presents the first page as the
 * whole.
 *
 * ## The order of the rows (`UIP-S03-03`, owner ruling Г3-B)
 *
 * The selector asks for the list **ordered by name** (`order=name`): by the number written in the name, then alphabetically, as
 * the original's picker orders its rows. The SERVER orders the whole listing before it is paged, so the first page is the first
 * page of that order; the model keeps the order of the rows it is given and never sorts them (a list that is longer than its first
 * page would be sorted wrongly by a client). The list is its own cache entry, apart from the «new first» list the screens
 * «Объекты» and «Главная» read, which keep their order; a command that changes the projects refreshes both.
 */

import type { Project, ProjectPage } from '@/shared/api';
import { formatInstant, projectScopeOf, resolveProjectContext, routes, switchProject } from '@/shared/lib';
import type { ProjectScope, ProjectSource, SearchParamsLike } from '@/shared/lib';
import { classifyProjectListFailure } from '@/entities/project';
import type { ProjectListFailure } from '@/entities/project';

/** The word before the object's name in the button's accessible name; the button shows no caption (`UIP-G-08`). */
export const SWITCHER_LABEL = 'Объект';
export const ALL_PROJECTS_LABEL = 'Все объекты';
export const NEW_PROJECT_LABEL = 'Новый объект';
export const MORE_PROJECTS_LABEL = 'Остальные объекты — в списке';
export const RETRY_LABEL = 'Повторить загрузку';
/** Why the selector does not filter the screen it is on (`R-150c`: a global screen). */
export const GLOBAL_SCREEN_HINT = 'экран общий';

/** The two figures of a row, named as the original names them. */
export const NOT_RUN_LABEL = 'не запускались';
export const NO_EXPERT_DECISION_LABEL = 'нет решений эксперта';

/** One of the two figures of a row, drawn as a badge. The words are in its tooltip and in the row's accessible name. */
export interface RowFigure {
  readonly key: 'not_run' | 'no_expert_decision';
  readonly count: number;
  /** The figure's words, as the original names it. */
  readonly words: string;
  /** The tooltip of the badge: the words, then the count. */
  readonly title: string;
}

/** The address the selector reads: where the browser is, and its query string. */
export interface SwitcherAddress {
  /** The browser's pathname; `null` when it is not known (a render with no router). */
  readonly pathname: string | null;
  readonly searchParams: SearchParamsLike;
  /** `last_project_uid` of `getMe`: the object an `optional` screen opens on when the address names none; `null` or absent for none. */
  readonly remembered?: string | null | undefined;
  /** `getMe` is on its way: the object of an address that names none is not known yet. */
  readonly rememberedPending?: boolean | undefined;
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
      /**
       * A newer read is on its way (`UIP-S03-01`: a new object has just been made and the list is being read again). An
       * object the address names that these rows do not hold is then not yet unknown: the button says «Загрузка…».
       */
      readonly refreshing?: boolean;
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
      /** `UIP-G-06`: the entry chooses this object (a project's row); absent for «Все объекты», the list and «Новый объект». */
      readonly projectUid?: string;
      /** `UIP-G-08`: the row's two figures, `not_run` then `no_expert_decision`; absent when the project's answer carries none. */
      readonly figures?: readonly [RowFigure, RowFigure];
      /** `UIP-G-08`: what a screen reader says for a row with figures: the name, then the figures with their words. */
      readonly name?: string;
      /** `UIP-S03-01`: the entry makes an object. The island opens the window «Новый объект» for it; its `href` is the list's form. */
      readonly creates?: true;
    }
  | { readonly kind: 'retry'; readonly label: string };

/** What the model is told beside the address and the list. */
export interface SwitcherOptions {
  /** `false`: the account is known not to be an expert (`mayActAsExpert`), so «Новый объект» is not offered. Absent: it is. */
  readonly mayCreate?: boolean | undefined;
}

export interface SwitcherModel {
  /** The class of the screen being shown; `null` for an address the registry does not have. */
  readonly scope: ProjectScope | null;
  /** The project the address names, or `null` for «Все объекты». */
  readonly projectUid: string | null;
  /** What the button shows: the object's name, or the reason it cannot. */
  readonly value: string;
  /** «экран общий» on a global screen, else `null`. It is said in the button's tooltip and its accessible name, not drawn. */
  readonly hint: string | null;
  /** The button's accessible name: «Объект: <название>», or «Все объекты»; on a global screen the hint follows. */
  readonly triggerLabel: string;
  /** The button's tooltip: the hint of a global screen, else `null`. */
  readonly title: string | null;
  readonly notes: readonly SwitcherNote[];
  readonly entries: readonly [SwitcherEntry, ...SwitcherEntry[]];
}

/**
 * The class of the screen and the object it works in: the address's, or, on an `optional` screen whose address names none,
 * the account's last one (`address.remembered`).
 */
export function switcherContext(address: SwitcherAddress): {
  readonly scope: ProjectScope | null;
  readonly projectUid: string | null;
  readonly source: ProjectSource;
} {
  if (address.pathname === null) return { scope: null, projectUid: null, source: 'none' };
  const context = resolveProjectContext(address.pathname, address.searchParams, address.remembered);
  return { scope: projectScopeOf(address.pathname), projectUid: context.projectUid, source: context.source };
}

/**
 * Where choosing `projectUid` (`null` is «Все объекты») leads from `address`.
 *
 * An unregistered address (a 404) has no class and nothing to rewrite, so it behaves like a
 * global screen: the choice opens the project's page, or the list.
 */
export function chooseProject(address: SwitcherAddress, projectUid: string | null): string {
  const { scope, projectUid: open } = switcherContext(address);
  if (scope === 'optional' && address.pathname !== null) {
    const query = switchProject(address.searchParams, projectUid, open).toString();
    return query === '' ? address.pathname : `${address.pathname}?${query}`;
  }
  return projectUid === null || projectUid === '' ? routes.projects() : routes.project(projectUid);
}

/**
 * The object a click on the link `href` chose, or `null` when it chose none: «Все объекты», «Новый объект» and the full list
 * are links of the menu too, and the all-objects view is never kept on the server. The caller asks the server to keep it.
 */
export function chosenProject(model: SwitcherModel, href: string | null): string | null {
  if (href === null) return null;
  for (const entry of model.entries) {
    if (entry.kind === 'link' && entry.projectUid !== undefined && entry.href === href) return entry.projectUid;
  }
  return null;
}

/** What {@link afterObjectCreated} does, as the island gives it. */
export interface CreatedObjectEffects {
  /** Asks the server to keep the object as the account's last (`useRememberProject().remember`; a refusal is shown beside the button). */
  readonly remember: (projectUid: string) => void;
  /** Opens an address (`router.push`). */
  readonly navigate: (href: string) => void;
  /** Closes the window «Новый объект». */
  readonly close: () => void;
}

/**
 * The window «Новый объект» made `project` (`UIP-S03-01`): the new object becomes the open one, as a click on its row in the
 * list does (`UIP-G-06`): the choice is kept, the screen goes to the address {@link chooseProject} computes (`?project=` on a
 * screen that follows the object, the object's own page elsewhere), and the window closes. The choice is asked for first and the
 * address opened second, as the row's click does (the link follows whatever the server says); the window closes last.
 */
export function afterObjectCreated(address: SwitcherAddress, project: Pick<Project, 'project_uid'>, effects: CreatedObjectEffects): void {
  effects.remember(project.project_uid);
  effects.navigate(chooseProject(address, project.project_uid));
  effects.close();
}

/** A name for display: one line, no stray whitespace. The stored name is not changed. */
function displayName(project: Project): string {
  return project.name.replace(/\s+/g, ' ').trim();
}

/** `ДД.ММ.ГГГГ` of a creation instant, or the text `formatInstant` gives for one it cannot read. */
function createdDay(project: Project): string {
  const text = formatInstant(project.created_at);
  return /^\d\d\.\d\d\.\d{4}/.test(text) ? text.slice(0, 10) : text;
}

/** The two figures of a project in words, or `null` when its answer carries none. */
export function projectFigures(project: Project): string | null {
  const counts = project.audit_counts;
  if (counts === undefined) return null;
  return `${NOT_RUN_LABEL} ${counts.not_run} · ${NO_EXPERT_DECISION_LABEL} ${counts.no_expert_decision}`;
}

function figure(key: RowFigure['key'], count: number, words: string): RowFigure {
  return { key, count, words, title: `${words.charAt(0).toUpperCase()}${words.slice(1)}: ${count}` };
}

/** The two figures of a project as badges, `not_run` then `no_expert_decision`, or `null` when its answer carries none. */
export function projectBadges(project: Project): readonly [RowFigure, RowFigure] | null {
  const counts = project.audit_counts;
  if (counts === undefined) return null;
  return [figure('not_run', counts.not_run, NOT_RUN_LABEL), figure('no_expert_decision', counts.no_expert_decision, NO_EXPERT_DECISION_LABEL)];
}

/** The labels of the entries that are not projects. A project's row may not read as one of them. */
const RESERVED_LABELS: readonly string[] = [ALL_PROJECTS_LABEL, MORE_PROJECTS_LABEL, NEW_PROJECT_LABEL, RETRY_LABEL];

/**
 * One name per project, in the list's order: the name as displayed, told apart where the reader could not tell two rows apart.
 *
 * Two projects can carry the same name and the same figures (the badges are all that sets a row apart), and one can be named
 * like a fixed entry of the menu («Новый объект»). Such names get the day the project was created, and any that are still
 * equal get their place among the equals. Equal names with different figures are told apart by the figures and stay as they are.
 */
export function projectRowLabels(projects: readonly Project[]): string[] {
  const names = projects.map(displayName);
  const figures = projects.map((project) => projectFigures(project) ?? '');
  const tie = (name: string, index: number): string => `${name}\n${figures[index]}`;
  const taken = new Map<string, number>();
  names.forEach((name, index) => taken.set(tie(name, index), (taken.get(tie(name, index)) ?? 0) + 1));
  const withDay = names.map((name, index) =>
    (taken.get(tie(name, index)) ?? 0) > 1 || RESERVED_LABELS.includes(name)
      ? `${name} (создан ${createdDay(projects[index] as Project)})`
      : name,
  );
  const seen = new Map<string, number>();
  return withDay.map((name, index) => {
    const key = tie(name, index);
    const count = (seen.get(key) ?? 0) + 1;
    seen.set(key, count);
    return count === 1 ? name : `${name} №${count}`;
  });
}

/**
 * The list state for a query's `data` and `error` (`error` is `null` when the read has not failed). `refreshing`: a newer read of
 * rows already held is on its way (`isFetching` of a query that has `data`).
 */
export function switcherListOf(data: ProjectPage | undefined, error: unknown, refreshing = false): SwitcherList {
  if (data !== undefined) {
    return {
      kind: 'ready',
      projects: data.items,
      more: data.page.next_cursor !== null,
      refreshFailure: error === null || error === undefined ? null : classifyProjectListFailure(error),
      ...(refreshing ? { refreshing: true } : {}),
    };
  }
  if (error !== null && error !== undefined) return { kind: 'error', failure: classifyProjectListFailure(error) };
  return { kind: 'loading' };
}

/** What the button shows for `projectUid` given what is known of the list; `waiting` is an object still to be named by `getMe`. */
function valueOf(projectUid: string | null, list: SwitcherList, waiting: boolean): string {
  if (waiting) return 'Загрузка…';
  if (projectUid === null) return ALL_PROJECTS_LABEL;
  switch (list.kind) {
    case 'loading':
      return 'Загрузка…';
    case 'error':
      return 'Название недоступно';
    case 'ready': {
      const found = list.projects.find((project) => project.project_uid === projectUid);
      if (found !== undefined) return displayName(found);
      // The rows are being read again: an object made a moment ago is not in them yet, and is not unknown.
      if (list.refreshing === true) return 'Загрузка…';
      return list.more ? `Объект вне первых ${list.projects.length}` : 'Неизвестный объект';
    }
  }
}

function notesOf(list: SwitcherList): SwitcherNote[] {
  switch (list.kind) {
    case 'loading':
      return [{ tone: 'status', text: 'Загрузка объектов…' }];
    case 'error':
      return [
        {
          tone: 'alert',
          text: 'Объекты не загрузились',
          detail: list.failure.title,
          ...(list.failure.correlationId === null ? {} : { correlationId: list.failure.correlationId }),
        },
      ];
    case 'ready': {
      const notes: SwitcherNote[] = [];
      if (list.refreshFailure !== null) {
        notes.push({ tone: 'alert', text: 'Список мог устареть: обновить его не удалось.', detail: list.refreshFailure.title });
      }
      if (list.projects.length === 0) notes.push({ tone: 'status', text: 'Объектов пока нет.' });
      if (list.more) notes.push({ tone: 'status', text: `Показаны первые ${list.projects.length}.` });
      return notes;
    }
  }
}

/** «Все объекты», or «Объект: <название>», and on a global screen the hint after it (`UIP-G-08`: the button draws no caption). */
function triggerLabelOf(value: string, all: boolean, hint: string | null): string {
  const name = all ? ALL_PROJECTS_LABEL : `${SWITCHER_LABEL}: ${value}`;
  return hint === null ? name : `${name}, ${hint}`;
}

/** The whole selector for `address` and `list`. */
export function buildSwitcherModel(address: SwitcherAddress, list: SwitcherList, options: SwitcherOptions = {}): SwitcherModel {
  const { scope, projectUid, source } = switcherContext(address);
  // An `optional` screen whose address is silent waits for the account's answer before it can name the object.
  const waiting = address.rememberedPending === true && scope === 'optional' && source === 'none';
  const value = valueOf(projectUid, list, waiting);
  const hint = scope === 'global' ? GLOBAL_SCREEN_HINT : null;

  const entries: SwitcherEntry[] = [];
  const canRetry = list.kind === 'error' ? list.failure.retryable : list.kind === 'ready' && list.refreshFailure !== null && list.refreshFailure.retryable;
  if (canRetry) entries.push({ kind: 'retry', label: RETRY_LABEL });
  if (list.kind === 'ready') {
    const labels = projectRowLabels(list.projects);
    list.projects.forEach((project, index) => {
      const label = labels[index] as string;
      const figures = projectBadges(project);
      entries.push({
        kind: 'link',
        label,
        href: chooseProject(address, project.project_uid),
        current: projectUid === project.project_uid,
        projectUid: project.project_uid,
        // A project whose answer carries no counts has no badges and no words about them: unknown is not zero.
        ...(figures === null ? {} : { figures, name: `${label}: ${projectFigures(project)}` }),
      });
    });
  }
  entries.push({ kind: 'link', label: ALL_PROJECTS_LABEL, href: chooseProject(address, null), current: projectUid === null && !waiting });
  if (list.kind === 'ready' && list.more) entries.push({ kind: 'link', label: MORE_PROJECTS_LABEL, href: routes.projects() });
  // `UIP-S03-01`: the island opens the window «Новый объект» for this entry. The address is the list's own form, for a render that
  // has no island; the entry is not offered to an account known not to be an expert.
  if (options.mayCreate !== false) entries.push({ kind: 'link', label: NEW_PROJECT_LABEL, href: routes.projects(), creates: true });

  const [first, ...rest] = entries;
  return {
    scope,
    projectUid,
    value,
    hint,
    triggerLabel: triggerLabelOf(value, projectUid === null && !waiting, hint),
    title: hint,
    notes: notesOf(list),
    entries: [first as SwitcherEntry, ...rest],
  };
}
