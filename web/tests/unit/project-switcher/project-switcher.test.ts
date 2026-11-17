/**
 * `UI-PARITY-01` wave 1, `R-150b`: the «Проекты ▾» selector of the frame's top strip.
 *
 * The model is pure and read as data (what a choice leads to, what a row says, what the button
 * shows); the markup is read off one static pass of the real widget. The keyboard is `Menu`'s
 * (`tests/unit/ui/menu.test.ts`, `qa_w50/primitives-keyboard.test.ts`), and the hover, focus and
 * press that ask for the list are a browser fact: here the gate is read off the query the widget
 * registers (`enabled`), the way `qa_w50/r66-navigation.test.ts` reads the reads of a screen.
 */

import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it, vi } from 'vitest';

import { ApiError, listProjects } from '@/shared/api';
import type { Account, ErrorEnvelope, Project, ProjectPage } from '@/shared/api';
import { queryKeys } from '@/shared/api';
import { PROJECT_PAGE_LIMIT } from '@/entities/project';
import { ProjectList } from '@/widgets/project-list';
import { MENU_CLOSED } from '@/shared/ui';
import { MenuView } from '@/shared/ui/menu';
import {
  ALL_PROJECTS_LABEL,
  GLOBAL_SCREEN_HINT,
  MORE_PROJECTS_LABEL,
  NEW_PROJECT_LABEL,
  ObjectMenu,
  ObjectMenuView,
  ProjectSwitcher,
  ProjectSwitcherLive,
  ProjectSwitcherView,
  RETRY_LABEL,
  buildSwitcherModel,
  chooseProject,
  chosenProject,
  projectBadges,
  projectFigures,
  projectRowLabels,
  switcherListOf,
  switcherMenuProps,
} from '@/widgets/project-switcher';
import type { SwitcherAddress, SwitcherList } from '@/widgets/project-switcher';

import { auditCounts } from '../dashboard/audit-counts';
import { newClient, renderScreen, seedError } from '../screens/harness';

const navigation = vi.hoisted(() => ({ pathname: null as string | null, search: '' }));

vi.mock('@/shared/api', async (importOriginal) => ({
  ...(await importOriginal<Record<string, unknown>>()),
  listProjects: vi.fn(),
}));

vi.mock('next/navigation', async (importOriginal) => ({
  ...(await importOriginal<Record<string, unknown>>()),
  usePathname: () => navigation.pathname,
  useSearchParams: () => new URLSearchParams(navigation.search),
}));

// ----------------------------------------------------------------------------------- fixtures

/** `UIP-S03-03`: the selector's list is the one ordered by name, its own entry apart from the «new first» list of the other screens. */
const SWITCHER_LIST = queryKeys.projects.list(undefined, PROJECT_PAGE_LIMIT, 'name');
const NEWEST_FIRST_LIST = queryKeys.projects.list(undefined, PROJECT_PAGE_LIMIT);

const A = 'prj_01J9ZQ8K7NHVXW3T2R5M6P4Q8B';
const B = 'prj_01J9ZQ8K7NHVXW3T2R5M6P4Q8C';
const C = 'prj_01J9ZQ8K7NHVXW3T2R5M6P4Q8D';
const VERSION = 'ver_01J9ZQ8K7NHVXW3T2R5M6P4Q8B';

function project(uid: string, name: string, counts?: Partial<ReturnType<typeof auditCounts>> & { documents?: number }): Project {
  const { documents = 4, ...over } = counts ?? {};
  return {
    project_uid: uid,
    name,
    created_at: '2026-11-03T09:30:00Z',
    ...(counts === undefined ? {} : { audit_counts: auditCounts(documents, over) }),
  };
}

const MOST = project(A, 'Мост через Неву', { documents: 6, not_run: 2, awaiting_decision: 3, clean: 1, no_expert_decision: 5 });
const SCHOOL = project(B, 'Школа №7', { documents: 3, not_run: 0, awaiting_decision: 0, checked: 3, no_expert_decision: 0 });
const PROJECTS: readonly Project[] = [MOST, SCHOOL];

const ready = (projects: readonly Project[] = PROJECTS, over: Partial<Extract<SwitcherList, { kind: 'ready' }>> = {}): SwitcherList => ({
  kind: 'ready',
  projects,
  more: false,
  refreshFailure: null,
  ...over,
});

function at(pathname: string | null, search = '', remembered?: string | null): SwitcherAddress {
  return { pathname, searchParams: new URLSearchParams(search), ...(remembered === undefined ? {} : { remembered }) };
}

function apiError(status: number, code: ErrorEnvelope['error_code'], retryable: boolean): ApiError {
  const envelope: ErrorEnvelope = {
    contract_version: '1.57.0',
    error_code: code,
    message: 'Одна безопасная для вызывающей стороны фраза.',
    correlation_id: 'cid-switcher-1',
    retryable,
  };
  return new ApiError(status, envelope, 'cid-switcher-1');
}

const page = (items: readonly Project[], next: string | null = null): ProjectPage => ({ items: [...items], page: { next_cursor: next } });

/** The markup of the selector for `model`, closed: its popup is in the markup, `hidden`. */
function markupOf(address: SwitcherAddress, list: SwitcherList): string {
  return renderToStaticMarkup(createElement(ProjectSwitcherView, { model: buildSwitcherModel(address, list), onRetry: () => undefined }));
}

const CHECK_CELL = /<span class="am-menu__check"[^>]*>[^<]*<\/span>/;
const FIGURES_CELL = /<span class="[^"]*" data-object-figures="">(?:<span\b[^>]*>[^<]*<\/span>)*<\/span>/;
const decode = (text: string): string => text.replace(/&amp;/g, '&');

/** A row's name: its text, with the ✓ cell and the badges (which are the row's marks, not its words) taken out. */
function nameOf(inner: string): string {
  return decode(inner.replace(CHECK_CELL, '').replace(FIGURES_CELL, '').replace(/<[^>]+>/g, ''));
}

/** The menu items of a markup, in order: `[tag, href or null, name]`. */
function itemsOf(markup: string): [string, string | null, string][] {
  return [...markup.matchAll(/<(a|button)\b([^>]*role="menuitem"[^>]*)>([\s\S]*?)<\/(?:a|button)>/g)].map((m) => [
    m[1] as string,
    /\bhref="([^"]*)"/.exec(m[2] as string)?.[1] ?? null,
    nameOf(m[3] as string),
  ]);
}

/** One badge of a row: `[figure key, count, the badge's tone class, its tooltip]`. */
type DrawnFigure = [string, number, string, string];

/** The rows of a markup with what they say of themselves: the name, the badges drawn in them, and the accessible name of the row. */
function rowsOf(markup: string): { name: string; figures: DrawnFigure[]; ariaLabel: string | null; object: boolean }[] {
  return [...markup.matchAll(/<a\b([^>]*role="menuitem"[^>]*)>([\s\S]*?)<\/a>/g)].map((m) => ({
    name: nameOf(m[2] as string),
    figures: [...(m[2] as string).matchAll(/<span class="am-badge (am-badge--\w+) [^"]*" title="([^"]*)" aria-hidden="true" data-object-figure="(\w+)">(\d+)<\/span>/g)].map(
      (f): DrawnFigure => [f[3] as string, Number(f[4]), f[1] as string, decode(f[2] as string)],
    ),
    ariaLabel: /\baria-label="([^"]*)"/.exec(m[1] as string)?.[1] ?? null,
    object: /\bclass="[^"]*object[^"]*"/.test(m[1] as string),
  }));
}

/** The rows that carry the ✓ cell, `[name, the mark ('✓' or '')]`, and which of them is `aria-current`. */
function marksOf(markup: string): { readonly marks: [string, string][]; readonly current: string[] } {
  const rows = [...markup.matchAll(/<(a|button)\b([^>]*role="menuitem"[^>]*)>([\s\S]*?)<\/(?:a|button)>/g)];
  const marks: [string, string][] = [];
  const current: string[] = [];
  for (const row of rows) {
    const cell = /<span class="am-menu__check"[^>]*>([^<]*)<\/span>/.exec(row[3] as string);
    const label = nameOf(row[3] as string);
    if (cell !== null) marks.push([label, cell[1] as string]);
    if (/\baria-current="true"/.test(row[2] as string)) current.push(label);
  }
  return { marks, current };
}

/** What the button draws: the markup inside the menu button. */
function buttonFace(markup: string): string {
  return /<button\b[^>]*aria-haspopup="menu"[^>]*>([\s\S]*?)<\/button>/.exec(markup)?.[1] ?? '';
}

// ----------------------------------------------------------------------------- what a choice does

describe('choosing a project (R-150c): the address is rewritten, nothing else keeps the choice', () => {
  it('on an optional screen the screen stays and ?project= is rewritten; the old project\'s own parameters go', () => {
    const address = at('/dashboard', `project=${A}&section=AR&version=v&cursor=c&tab=t&view=compact`);
    expect(chooseProject(address, B)).toBe('/dashboard?project=' + B + '&view=compact');
  });

  it('on an optional screen with no project, the parameter is added and the others are kept', () => {
    expect(chooseProject(at('/knowledge-base', 'q=%D0%BF%D0%BE%D0%B6'), B)).toBe(`/knowledge-base?q=%D0%BF%D0%BE%D0%B6&project=${B}`);
    expect(chooseProject(at('/dashboard'), B)).toBe(`/dashboard?project=${B}`);
  });

  it('«Все объекты» on an optional screen is the explicit ?project=all, drops the dependent parameters and keeps the rest (UIP-G-06)', () => {
    expect(chooseProject(at('/dashboard', `project=${A}&section=AR&view=compact`), null)).toBe('/dashboard?project=all&view=compact');
    expect(chooseProject(at('/section-optimisation', `project=${A}`), null)).toBe('/section-optimisation?project=all');
    // never the bare address: that would open on the account's last object again
    expect(chooseProject(at('/dashboard', `project=${A}`, B), null)).not.toBe('/dashboard');
  });

  it('choosing the project the address already has changes nothing', () => {
    expect(chooseProject(at('/dashboard', `project=${A}&section=AR`), A)).toBe(`/dashboard?project=${A}&section=AR`);
    expect(chooseProject(at('/dashboard', 'project=all&section=AR'), null)).toBe('/dashboard?project=all&section=AR');
  });

  it('choosing the account\'s last object, which the screen is on with a silent address, writes it down and keeps the screen\'s own parameters', () => {
    expect(chooseProject(at('/dashboard', 'section=AR&view=compact', A), A)).toBe(`/dashboard?section=AR&view=compact&project=${A}`);
    // another object is a change, and the old object's parameters go
    expect(chooseProject(at('/dashboard', 'section=AR&view=compact', A), B)).toBe(`/dashboard?view=compact&project=${B}`);
    expect(chooseProject(at('/dashboard', 'section=AR&view=compact', A), null)).toBe('/dashboard?view=compact&project=all');
  });

  it('on a global or required screen the last object is not the screen\'s: the choice leads where it always led', () => {
    expect(chooseProject(at('/queue', '', A), B)).toBe(`/projects/${B}`);
    expect(chooseProject(at('/queue', '', A), null)).toBe('/projects');
    expect(chooseProject(at(`/projects/${A}`, '', B), B)).toBe(`/projects/${B}`);
  });

  it('on a required screen the choice opens the chosen project\'s page, whatever the path says', () => {
    const address = at(`/projects/${A}/versions/${VERSION}`);
    expect(chooseProject(address, B)).toBe(`/projects/${B}`);
    expect(chooseProject(at(`/projects/${A}`), A)).toBe(`/projects/${A}`);
  });

  it('«Все объекты» on a required screen opens the project list', () => {
    expect(chooseProject(at(`/projects/${A}`), null)).toBe('/projects');
  });

  it('on a global screen the choice opens the chosen project\'s page; «Все объекты» opens the list', () => {
    for (const pathname of ['/queue', '/logs', '/workers', '/projects', '/norms', '/admin/users']) {
      expect(chooseProject(at(pathname, `project=${A}`), B), pathname).toBe(`/projects/${B}`);
      expect(chooseProject(at(pathname, `project=${A}`), null), pathname).toBe('/projects');
    }
  });

  it('UIP-S01-01: on «Главная» the choice stays on the front door and rewrites ?project=; it no longer opens the object\'s page', () => {
    expect(chooseProject(at('/', `project=${A}`), B)).toBe(`/?project=${B}`);
    expect(chooseProject(at('/', `project=${A}`), null)).toBe('/?project=all');
    // the account's last object is what the screen is on while the address is silent; choosing it writes it down, another one replaces it
    expect(chooseProject(at('/', '', A), A)).toBe(`/?project=${A}`);
    expect(chooseProject(at('/', '', A), B)).toBe(`/?project=${B}`);
    expect(chooseProject(at('/', '', A), null)).toBe('/?project=all');
    // can fail: not the global behaviour, which led to the object's page or to the list
    expect(chooseProject(at('/', `project=${A}`), B)).not.toBe(`/projects/${B}`);
    expect(chooseProject(at('/', `project=${A}`), null)).not.toBe('/projects');
  });

  it('an address the registry does not have behaves like a global screen, and so does an unknown pathname', () => {
    expect(chooseProject(at('/no/such/screen', `project=${A}`), B)).toBe(`/projects/${B}`);
    expect(chooseProject(at(null), B)).toBe(`/projects/${B}`);
    expect(chooseProject(at(null), null)).toBe('/projects');
  });
});

// ------------------------------------------------------------------------------------- the rows

describe('a project row: the name and the original\'s two figures, each next to its words (R-150o)', () => {
  it('reads «не запускались» from not_run and «нет решений эксперта» from no_expert_decision, not from a sum', () => {
    expect(projectFigures(MOST)).toBe('не запускались 2 · нет решений эксперта 5');
    expect(projectFigures(SCHOOL)).toBe('не запускались 0 · нет решений эксперта 0');
    // The figure is the contract's field. A server whose no_expert_decision differs from the sum
    // is read as it says; the row does not recompute.
    expect(projectFigures(project(C, 'Склад', { documents: 9, not_run: 1, awaiting_decision: 1, no_expert_decision: 7 }))).toBe(
      'не запускались 1 · нет решений эксперта 7',
    );
  });

  it('shows no figures for a project whose answer carries no audit_counts: absent is unknown, never zero', () => {
    const bare = project(C, 'Склад');
    expect(bare.audit_counts).toBeUndefined();
    expect(projectFigures(bare)).toBeNull();
    expect(projectBadges(bare)).toBeNull();
    expect(projectRowLabels([bare])).toEqual(['Склад']);
    expect(projectRowLabels([bare])[0]).not.toMatch(/\d/);
    // in a list: the row of the project with no counts has no badge and no sentence about them; its neighbours keep theirs
    const rows = rowsOf(markupOf(at('/dashboard'), ready([MOST, bare])));
    expect(rows.slice(0, 2).map((row) => [row.name, row.figures.length, row.ariaLabel])).toEqual([
      ['Мост через Неву', 2, 'Мост через Неву: не запускались 2 · нет решений эксперта 5'],
      ['Склад', 0, null],
    ]);
  });

  it('a row\'s label is the name alone, on one line; the figures are not in it (UIP-G-08)', () => {
    expect(projectRowLabels(PROJECTS)).toEqual(['Мост через Неву', 'Школа №7']);
    // A name with its own line breaks and runs of spaces is one line; the stored name is not touched.
    expect(projectRowLabels([project(C, '  Склад\n  №3  ')])).toEqual(['Склад №3']);
  });

  it('turns the two figures into two badges, the words in the tooltip: «не запускались» is not_run, «нет решений эксперта» is no_expert_decision', () => {
    expect(projectBadges(MOST)).toEqual([
      { key: 'not_run', count: 2, words: 'не запускались', title: 'Не запускались: 2' },
      { key: 'no_expert_decision', count: 5, words: 'нет решений эксперта', title: 'Нет решений эксперта: 5' },
    ]);
    // the badge reads the contract's field, not a sum (2 + 3 awaiting would be 5, so use a server that says otherwise)
    expect(projectBadges(project(C, 'Склад', { documents: 9, not_run: 1, awaiting_decision: 1, no_expert_decision: 7 }))?.map((one) => one.count)).toEqual([1, 7]);
    // a zero the server sent is a badge; only an absent count is no badge
    expect(projectBadges(SCHOOL)?.map((one) => one.count)).toEqual([0, 0]);
  });

  it('renders each row as a link to its choice: the name, then the two badges in the two tones of meaning, the words in their titles', () => {
    const rows = rowsOf(markupOf(at('/dashboard'), ready()));
    expect(rows.slice(0, 2)).toEqual([
      {
        name: 'Мост через Неву',
        figures: [
          ['not_run', 2, 'am-badge--degraded', 'Не запускались: 2'],
          ['no_expert_decision', 5, 'am-badge--active', 'Нет решений эксперта: 5'],
        ],
        ariaLabel: 'Мост через Неву: не запускались 2 · нет решений эксперта 5',
        object: true,
      },
      {
        name: 'Школа №7',
        figures: [
          ['not_run', 0, 'am-badge--degraded', 'Не запускались: 0'],
          ['no_expert_decision', 0, 'am-badge--active', 'Нет решений эксперта: 0'],
        ],
        ariaLabel: 'Школа №7: не запускались 0 · нет решений эксперта 0',
        object: true,
      },
    ]);
    expect(itemsOf(markupOf(at('/dashboard'), ready())).slice(0, 2)).toEqual([
      ['a', `/dashboard?project=${A}`, 'Мост через Неву'],
      ['a', `/dashboard?project=${B}`, 'Школа №7'],
    ]);
  });

  it('the badges say nothing to assistive technology on their own: the row\'s name says both figures with their words', () => {
    const markup = markupOf(at('/dashboard'), ready());
    expect(markup.match(/data-object-figure="/g)).toHaveLength(4);
    for (const badge of markup.match(/<span class="am-badge [^"]*"[^>]*>/g) ?? []) expect(badge).toContain('aria-hidden="true"');
    // no row of fixed text has figures, and the fixed rows have no object step
    expect(rowsOf(markup).slice(2).map((row) => [row.name, row.figures.length, row.object])).toEqual([
      [ALL_PROJECTS_LABEL, 0, false],
      [NEW_PROJECT_LABEL, 0, false],
    ]);
  });

  it('keeps the contract\'s order and does not sort', () => {
    expect(projectRowLabels([SCHOOL, MOST])).toEqual(['Школа №7', 'Мост через Неву']);
  });

  it('keeps two projects with the same name and the same figures apart, and keeps a project named like a fixed entry apart', () => {
    const twin = (uid: string, created: string) => ({ ...project(uid, 'Тест', { documents: 1 }), created_at: created });
    const labels = projectRowLabels([twin(A, '2026-11-01T10:00:00Z'), twin(B, '2026-11-02T10:00:00Z'), twin(C, '2026-11-02T11:00:00Z')]);
    expect(new Set(labels).size).toBe(3);
    expect(labels[0]).toContain('создан 01.11.2026');
    expect(labels[1]).toContain('создан 02.11.2026');
    expect(labels[2]).toContain('создан 02.11.2026');
    expect(labels[2]).toContain('№2');
    // No figures: the label is the bare name, which a project can spell as a fixed entry.
    const named = projectRowLabels([project(A, NEW_PROJECT_LABEL), project(B, ALL_PROJECTS_LABEL)]);
    expect(named).not.toContain(NEW_PROJECT_LABEL);
    expect(named).not.toContain(ALL_PROJECTS_LABEL);
    expect(new Set(named).size).toBe(2);
  });
});

// ------------------------------------------------------------------------------------- the menu

describe('the menu: the rows, then «Все объекты», then «Новый объект»', () => {
  it('lists every project, then both fixed entries, in that order', () => {
    const items = itemsOf(markupOf(at('/dashboard'), ready()));
    expect(items.map(([, , text]) => text.split('\n')[0])).toEqual(['Мост через Неву', 'Школа №7', ALL_PROJECTS_LABEL, NEW_PROJECT_LABEL]);
  });

  it('«Новый объект» leads to the project list, where the form is; «Все объекты» is the screen\'s own address with ?project=all', () => {
    const optional = itemsOf(markupOf(at('/dashboard', `project=${A}`), ready())).slice(-2);
    expect(optional).toEqual([
      ['a', '/dashboard?project=all', ALL_PROJECTS_LABEL],
      ['a', '/projects', NEW_PROJECT_LABEL],
    ]);
    const global = itemsOf(markupOf(at('/queue', `project=${A}`), ready())).slice(-2);
    expect(global).toEqual([
      ['a', '/projects', ALL_PROJECTS_LABEL],
      ['a', '/projects', NEW_PROJECT_LABEL],
    ]);
  });

  it('has the two fixed entries before any list arrives, so the button works while it loads', () => {
    const markup = markupOf(at('/dashboard'), { kind: 'loading' });
    expect(itemsOf(markup).map(([, , text]) => text)).toEqual([ALL_PROJECTS_LABEL, NEW_PROJECT_LABEL]);
    expect(markup).toContain('Загрузка объектов…');
    expect(markup).toContain('role="status"');
  });

  it('says there are no projects when the list is empty, and still offers «Новый объект»', () => {
    const markup = markupOf(at('/dashboard'), ready([]));
    expect(markup).toContain('Объектов пока нет.');
    expect(itemsOf(markup).map(([, , text]) => text)).toEqual([ALL_PROJECTS_LABEL, NEW_PROJECT_LABEL]);
  });

  it('never presents the first page as the whole list: it says how many it shows and links to the rest', () => {
    const markup = markupOf(at('/dashboard'), ready(PROJECTS, { more: true }));
    expect(markup).toContain('Показаны первые 2.');
    expect(itemsOf(markup).map(([, href, text]) => [href, text.split('\n')[0]])).toEqual([
      [`/dashboard?project=${A}`, 'Мост через Неву'],
      [`/dashboard?project=${B}`, 'Школа №7'],
      ['/dashboard?project=all', ALL_PROJECTS_LABEL],
      ['/projects', MORE_PROJECTS_LABEL],
      ['/projects', NEW_PROJECT_LABEL],
    ]);
    expect(markupOf(at('/dashboard'), ready())).not.toContain('Показаны первые');
  });

  it('turns a page with a next cursor into more=true, and one without into more=false', () => {
    expect(switcherListOf(page(PROJECTS, 'cur_next'), null)).toMatchObject({ kind: 'ready', more: true });
    expect(switcherListOf(page(PROJECTS), null)).toMatchObject({ kind: 'ready', more: false });
    expect(switcherListOf(undefined, null)).toEqual({ kind: 'loading' });
  });
});

describe('a failed read: «Объекты не загрузились», a retry inside the menu, and the button still works', () => {
  const retryable = apiError(503, 'dependency_unavailable', true);

  it('shows the message as an alert with its correlation id, offers the retry first, and keeps both fixed entries', () => {
    const list = switcherListOf(undefined, retryable);
    expect(list.kind).toBe('error');
    const markup = markupOf(at('/dashboard'), list);
    expect(markup).toContain('Объекты не загрузились');
    expect(markup).toContain('role="alert"');
    expect(markup).toContain('Код обращения: cid-switcher-1');
    expect(itemsOf(markup)).toEqual([
      ['button', null, RETRY_LABEL],
      ['a', '/dashboard?project=all', ALL_PROJECTS_LABEL],
      ['a', '/projects', NEW_PROJECT_LABEL],
    ]);
  });

  it('does not offer a retry for a refusal retrying cannot change', () => {
    const list = switcherListOf(undefined, apiError(403, 'permission_denied', false));
    const markup = markupOf(at('/dashboard'), list);
    expect(markup).toContain('Объекты не загрузились');
    expect(itemsOf(markup).map(([, , text]) => text)).toEqual([ALL_PROJECTS_LABEL, NEW_PROJECT_LABEL]);
  });

  it('the retry is a menu item that runs the callback it is given', () => {
    const onRetry = vi.fn();
    const model = buildSwitcherModel(at('/dashboard'), switcherListOf(undefined, retryable));
    expect(model.entries[0]).toEqual({ kind: 'retry', label: RETRY_LABEL });
    // The island hands `onRetry` to the action item; `switcherMenuProps` is what builds it.
    const markup = renderToStaticMarkup(createElement(ProjectSwitcherView, { model, onRetry }));
    expect(markup).toMatch(/<button type="button" class="am-menu__item" role="menuitem" tabindex="-1">Повторить загрузку<\/button>/);
  });

  it('keeps real rows that a later failed refresh may have left old, and says so, with a retry', () => {
    const list = switcherListOf(page(PROJECTS), retryable);
    expect(list).toMatchObject({ kind: 'ready' });
    const markup = markupOf(at('/dashboard'), list);
    expect(markup).toContain('Список мог устареть');
    expect(itemsOf(markup).map(([, , text]) => text.split('\n')[0])).toEqual([
      RETRY_LABEL,
      'Мост через Неву',
      'Школа №7',
      ALL_PROJECTS_LABEL,
      NEW_PROJECT_LABEL,
    ]);
  });
});

// ------------------------------------------------------------------------------------ the button

describe('the button: the project\'s name, or «Все объекты», muted on a global screen with its hint', () => {
  it('shows «Все объекты» when the address names no project', () => {
    expect(buildSwitcherModel(at('/dashboard'), ready()).value).toBe(ALL_PROJECTS_LABEL);
    expect(buildSwitcherModel(at('/dashboard', 'project='), ready()).value).toBe(ALL_PROJECTS_LABEL);
  });

  it('shows the project\'s name from ?project= on an optional or global screen, and from the path on a required one', () => {
    expect(buildSwitcherModel(at('/dashboard', `project=${A}`), ready()).value).toBe('Мост через Неву');
    expect(buildSwitcherModel(at('/queue', `project=${B}`), ready()).value).toBe('Школа №7');
    expect(buildSwitcherModel(at(`/projects/${B}/versions/${VERSION}`, `project=${A}`), ready()).value).toBe('Школа №7');
  });

  it('says what it does not know instead of guessing: loading, failed, beyond the first page, unknown', () => {
    const named = at('/dashboard', `project=${C}`);
    expect(buildSwitcherModel(named, { kind: 'loading' }).value).toBe('Загрузка…');
    expect(buildSwitcherModel(named, switcherListOf(undefined, apiError(503, 'dependency_unavailable', true))).value).toBe('Название недоступно');
    expect(buildSwitcherModel(named, ready(PROJECTS, { more: true })).value).toBe('Объект вне первых 2');
    expect(buildSwitcherModel(named, ready()).value).toBe('Неизвестный объект');
  });

  it('UIP-S03-01: while the rows are read again, an object they do not hold yet is «Загрузка…», not unknown; one they hold keeps its name', () => {
    const named = at('/dashboard', `project=${C}`);
    expect(buildSwitcherModel(named, ready(PROJECTS, { refreshing: true })).value).toBe('Загрузка…');
    expect(buildSwitcherModel(named, ready(PROJECTS, { refreshing: false })).value).toBe('Неизвестный объект');
    expect(buildSwitcherModel(at('/dashboard', `project=${B}`), ready(PROJECTS, { refreshing: true })).value).toBe('Школа №7');
    // a page with more behind it says so once the read is over, and not before
    expect(buildSwitcherModel(named, ready(PROJECTS, { more: true, refreshing: true })).value).toBe('Загрузка…');
    expect(buildSwitcherModel(named, ready(PROJECTS, { more: true })).value).toBe('Объект вне первых 2');
  });

  it('UIP-S03-01: the island marks a read that is on its way over rows it holds (`isFetching` with data), and no other', () => {
    expect(switcherListOf(page(PROJECTS), null, true)).toMatchObject({ kind: 'ready', refreshing: true });
    expect(switcherListOf(page(PROJECTS), null)).not.toHaveProperty('refreshing');
    expect(switcherListOf(page(PROJECTS), null, false)).not.toHaveProperty('refreshing');
    expect(switcherListOf(undefined, null, true)).toEqual({ kind: 'loading' });
  });

  it('carries the hint «экран общий» only on a global screen, and mutes the button there', () => {
    expect(GLOBAL_SCREEN_HINT).toBe('экран общий');
    for (const pathname of ['/projects', '/queue', '/logs', '/workers', '/norms', '/admin/users']) {
      const model = buildSwitcherModel(at(pathname), ready());
      expect(model.hint, pathname).toBe(GLOBAL_SCREEN_HINT);
      expect(model.triggerLabel, pathname).toBe(`Все объекты, ${GLOBAL_SCREEN_HINT}`);
      expect(model.title, pathname).toBe(GLOBAL_SCREEN_HINT);
      const markup = markupOf(at(pathname), ready());
      expect(markup, pathname).toContain('data-project-scope="global"');
      expect(markup, pathname).toMatch(/class="[^"]*muted[^"]*" data-project-switcher/);
      // UIP-G-08: the hint is in the button's tooltip and its accessible name, and is not drawn
      expect(markup, pathname).toMatch(/<button\b[^>]*aria-label="Все объекты, экран общий" title="экран общий"/);
      expect(buttonFace(markup), pathname).not.toContain('экран общий');
    }
    // `UIP-S01-01`: «Главная» follows the object, so it says no «экран общий» and its button is not muted.
    for (const pathname of ['/', '/dashboard', '/knowledge-base', '/section-optimisation']) {
      const model = buildSwitcherModel(at(pathname), ready());
      expect(model.hint, pathname).toBeNull();
      expect(model.triggerLabel, pathname).toBe('Все объекты');
      expect(model.title, pathname).toBeNull();
      expect(markupOf(at(pathname), ready()), pathname).not.toMatch(/muted|экран общий/);
      expect(markupOf(at(pathname), ready()), pathname).not.toMatch(/<button\b[^>]*\btitle=/);
    }
    // A required screen is not muted and has no hint; its project is the path's.
    const required = buildSwitcherModel(at(`/projects/${A}`), ready());
    expect(required.hint).toBeNull();
    expect(required.triggerLabel).toBe('Объект: Мост через Неву');
    expect(markupOf(at(`/projects/${A}`), ready())).not.toMatch(/muted|экран общий/);
  });

  it('is a menu button named by what it shows: the trigger\'s accessible name is the model\'s', () => {
    const markup = markupOf(at('/dashboard', `project=${A}`), ready());
    expect(markup).toMatch(/<button\b[^>]*aria-haspopup="menu"[^>]*aria-label="Объект: Мост через Неву"/);
    expect(markup).toContain('data-project-scope="optional"');
  });

  it('draws the name and the ▾ and nothing else: no caption «Объекты»/«Проекты», however the object is named (UIP-G-08)', () => {
    for (const [address, list] of [
      [at('/dashboard', `project=${A}`), ready()],
      [at('/dashboard'), ready()],
      [at('/queue'), ready()],
      [at('/dashboard', `project=${C}`), { kind: 'loading' } as SwitcherList],
    ] as const) {
      const face = buttonFace(markupOf(address, list));
      const parts = face.replace(/<[^>]+>/g, '|').split('|').filter((part) => part !== '');
      // the value the model gives, and the ▾: a caption would be a third part before them
      expect(parts, JSON.stringify([address.pathname, address.searchParams.toString()])).toEqual([buildSwitcherModel(address, list).value, '▾']);
    }
    expect(buttonFace(markupOf(at('/dashboard', `project=${A}`), ready()))).toMatch(/>Мост через Неву<\/span><span class="[^"]*" aria-hidden="true">▾<\/span>/);
  });

  it('can fail: a caption the face drew would add a part, and a name that is not in the button is not read as one', () => {
    expect(buttonFace('<button class="am-menu__trigger" aria-haspopup="menu"><span><span>ОБЪЕКТЫ</span><span>Мост</span><span>▾</span></span></button>')).toContain('ОБЪЕКТЫ');
    expect(buttonFace(markupOf(at('/dashboard', `project=${A}`), ready()))).not.toContain('ОБЪЕКТЫ');
  });
});

// --------------------------------------------------------------------------------- the island

describe('the island: a render with no query client makes no request; the list is read only when needed', () => {
  it('the first render (the server\'s and the hydration\'s) is the closed selector, with no client and no fetch', () => {
    const fetch = vi.fn(() => Promise.reject(new Error('the selector must not fetch on first render')));
    vi.stubGlobal('fetch', fetch);
    try {
      navigation.pathname = '/dashboard';
      navigation.search = `project=${A}`;
      const markup = renderToStaticMarkup(createElement(ProjectSwitcher));
      expect(markup).toContain('data-project-switcher');
      expect(markup).toContain('Загрузка…');
      expect(itemsOf(markup).map(([, , text]) => text)).toEqual([ALL_PROJECTS_LABEL, NEW_PROJECT_LABEL]);
      expect(fetch).not.toHaveBeenCalled();
    } finally {
      vi.unstubAllGlobals();
    }
  });

  it('reads the cached first page into rows, and the button takes the name from it', () => {
    const client = newClient();
    client.setQueryData(SWITCHER_LIST, page(PROJECTS));
    const markup = renderScreen(client, createElement(ProjectSwitcherLive, { address: at('/dashboard', `project=${B}`) }));
    expect(markup).toContain('>Школа №7</span>');
    expect(itemsOf(markup).slice(0, 2).map(([, href]) => href)).toEqual([`/dashboard?project=${A}`, `/dashboard?project=${B}`]);
  });

  it('asks for the list on a screen that names a project, and does not on one that names none', () => {
    const enabledFor = (address: SwitcherAddress): boolean | undefined => {
      const client = newClient();
      renderScreen(client, createElement(ProjectSwitcherLive, { address }));
      // The account's answer (`getMe`) is its own query, asked for below; only the list is read here.
      const queries = client.getQueryCache().getAll().filter((query) => query.queryKey[0] !== 'account');
      expect(queries.map((query) => query.queryKey)).toEqual([SWITCHER_LIST]);
      return (queries[0]?.options as { enabled?: boolean }).enabled;
    };
    expect(enabledFor(at('/dashboard', `project=${A}`))).toBe(true);
    expect(enabledFor(at(`/projects/${A}`))).toBe(true);
    expect(enabledFor(at('/queue', `project=${A}`))).toBe(true);
    // Nobody reached for the selector and the address names no project: no request is made.
    expect(enabledFor(at('/dashboard'))).toBe(false);
    expect(enabledFor(at('/queue'))).toBe(false);
    expect(enabledFor(at('/'))).toBe(false);
  });

  it('UIP-S03-03: reads the list ordered by name, as an entry of its own: the key names the order and the request asks for it', async () => {
    const asked = vi.mocked(listProjects);
    asked.mockReset();
    asked.mockResolvedValue({ data: page(PROJECTS) } as never);
    const client = newClient();
    renderScreen(client, createElement(ProjectSwitcherLive, { address: at('/dashboard', `project=${A}`) }));
    const queries = client.getQueryCache().getAll().filter((query) => query.queryKey[0] !== 'account');
    expect(queries.map((query) => query.queryKey)).toEqual([SWITCHER_LIST]);
    expect(SWITCHER_LIST).not.toEqual(NEWEST_FIRST_LIST);
    await (queries[0]?.options as { queryFn: () => Promise<unknown> }).queryFn();
    expect(asked).toHaveBeenCalledTimes(1);
    expect(asked.mock.calls[0]?.[0]).toEqual({ query: { limit: PROJECT_PAGE_LIMIT, order: 'name' } });
  });

  it('UIP-S03-03: the other readers of the list keep «new first»: their key names no order and their request sends none', async () => {
    const asked = vi.mocked(listProjects);
    asked.mockReset();
    asked.mockResolvedValue({ data: page(PROJECTS) } as never);
    const client = newClient();
    renderScreen(client, createElement(ProjectList, {}));
    const queries = client.getQueryCache().getAll();
    expect(queries.map((query) => query.queryKey)).toEqual([NEWEST_FIRST_LIST]);
    await (queries[0]?.options as { queryFn: () => Promise<unknown> }).queryFn();
    expect(asked.mock.calls[0]?.[0]).toEqual({ query: { limit: PROJECT_PAGE_LIMIT } });
  });

  it('UIP-S03-03: one order is never served for the other: a «new first» page in the cache gives the selector no rows, and the reverse', () => {
    const newestOnly = newClient();
    newestOnly.setQueryData(NEWEST_FIRST_LIST, page(PROJECTS));
    const markup = renderScreen(newestOnly, createElement(ProjectSwitcherLive, { address: at('/dashboard', `project=${A}`) }));
    expect(itemsOf(markup).map(([, , text]) => text)).toEqual([ALL_PROJECTS_LABEL, NEW_PROJECT_LABEL]);
    expect(markup).toContain('Загрузка объектов…');

    const byName = newClient();
    byName.setQueryData(SWITCHER_LIST, page(PROJECTS));
    const rows = itemsOf(renderScreen(byName, createElement(ProjectSwitcherLive, { address: at('/dashboard', `project=${A}`) })));
    expect(rows.slice(0, 2).map(([, , text]) => text)).toEqual(['Мост через Неву', 'Школа №7']);
    // and the page «Объекты» does not read what the selector holds
    expect(renderScreen(byName, createElement(ProjectList, {}))).not.toContain('Мост через Неву');
  });

  it('UIP-S03-03: the rows are drawn in the order the server gave them, whatever it was: the widget does not sort', () => {
    const reversed = [SCHOOL, MOST];
    const rows = itemsOf(markupOf(at('/dashboard'), ready(reversed))).map(([, , text]) => text.split('\n')[0]);
    expect(rows.slice(0, 2)).toEqual(['Школа №7', 'Мост через Неву']);
    const shuffled = [project(C, 'Б'), project(A, '213. Школа'), project(B, '7 школа')];
    expect(itemsOf(markupOf(at('/dashboard'), ready(shuffled))).slice(0, 3).map(([, , text]) => text)).toEqual(['Б', '213. Школа', '7 школа']);
  });

  it('a note «Показаны первые N» stays when the server has more: the first page of the order is not the whole list (UIP-S03-03)', () => {
    const markup = markupOf(at('/dashboard'), ready(PROJECTS, { more: true }));
    expect(markup).toContain('Показаны первые 2.');
    expect(itemsOf(markup).map(([, , text]) => text)).toContain(MORE_PROJECTS_LABEL);
    expect(markupOf(at('/dashboard'), ready(PROJECTS))).not.toContain('Показаны первые');
  });

  it('shows the failure of a failed read inside the menu, with the retry', () => {
    const client = newClient();
    seedError(client, SWITCHER_LIST, apiError(503, 'dependency_unavailable', true));
    const markup = renderScreen(client, createElement(ProjectSwitcherLive, { address: at('/dashboard', `project=${A}`) }));
    expect(markup).toContain('Объекты не загрузились');
    expect(markup).toContain('Название недоступно');
    expect(itemsOf(markup)[0]).toEqual(['button', null, RETRY_LABEL]);
  });
});

describe('UIP-S03-01: once the island is live, «Новый объект» opens the window; the account decides whether it is offered', () => {
  const account = (roles: readonly string[]): Account =>
    ({ user_uid: 'usr_01J9ZQ8K7NHVXW3T2R5M6P4Q8B', roles, last_project_uid: null }) as unknown as Account;
  const live = (roles?: readonly string[], address: SwitcherAddress = at('/dashboard', `project=${A}`)): string => {
    const client = newClient();
    if (roles !== undefined) client.setQueryData(queryKeys.account.me(), account(roles));
    client.setQueryData(SWITCHER_LIST, page(PROJECTS));
    return renderScreen(client, createElement(ProjectSwitcherLive, { address }));
  };
  const lastItem = (markup: string) => itemsOf(markup).at(-1);

  it('is a button of the menu in the live island, not the link of the first render', () => {
    expect(lastItem(live(['expert']))).toEqual(['button', null, NEW_PROJECT_LABEL]);
    // the first render of the same selector, with no island yet, is still the link to the list's form
    navigation.pathname = '/dashboard';
    navigation.search = `project=${A}`;
    expect(itemsOf(renderToStaticMarkup(createElement(ProjectSwitcher))).at(-1)).toEqual(['a', '/projects', NEW_PROJECT_LABEL]);
  });

  it('is offered while the account is not known yet, and to an expert (the server refuses anyone else)', () => {
    expect(lastItem(live())?.[2]).toBe(NEW_PROJECT_LABEL);
    expect(lastItem(live(['expert']))?.[2]).toBe(NEW_PROJECT_LABEL);
    expect(lastItem(live(['admin', 'expert']))?.[2]).toBe(NEW_PROJECT_LABEL);
  });

  it('is not offered to an account known not to be an expert: «Наблюдатель», or an administrator alone', () => {
    for (const roles of [['viewer'], ['admin'], []]) {
      const markup = live(roles);
      expect(itemsOf(markup).map(([, , text]) => text), roles.join(',')).toEqual(['Мост через Неву', 'Школа №7', ALL_PROJECTS_LABEL]);
      expect(markup, roles.join(',')).not.toContain(NEW_PROJECT_LABEL);
    }
  });

  it('can fail: the rows of the objects and «Все объекты» stay links with the account known or not, so only this one row moves', () => {
    for (const roles of [undefined, ['expert'], ['viewer']] as const) {
      const rows = itemsOf(live(roles)).filter(([, , text]) => text !== NEW_PROJECT_LABEL);
      expect(rows.map(([tag]) => tag), String(roles)).toEqual(['a', 'a', 'a']);
    }
  });

  it('reads the account under the enabled the island already had, so the role costs no request of its own', () => {
    const enabledFor = (address: SwitcherAddress): boolean | undefined => {
      const client = newClient();
      renderScreen(client, createElement(ProjectSwitcherLive, { address }));
      return (client.getQueryCache().find({ queryKey: queryKeys.account.me() })?.options as { enabled?: boolean } | undefined)?.enabled;
    };
    expect(enabledFor(at('/dashboard'))).toBe(true);
    for (const address of [at('/dashboard', `project=${A}`), at('/queue'), at(`/projects/${A}`), at(null)]) {
      expect(enabledFor(address), JSON.stringify([address.pathname, address.searchParams.toString()])).toBe(false);
    }
  });
});

// ---------------------------------------------------------------------------- D-363: the mark of the open project

describe('D-363: the list marks the project that is open, as the original\'s picker does', () => {
  const SAME_NAME = project(C, 'Склад', { documents: 2 });

  it('flags the project the address names, on an optional screen and on a required one, and keeps the column on the other choices', () => {
    for (const address of [at('/dashboard', `project=${B}`), at(`/projects/${B}/versions/${VERSION}`)]) {
      const { marks, current } = marksOf(markupOf(address, ready()));
      expect(marks, address.pathname ?? '').toEqual([['Мост через Неву', ''], ['Школа №7', '\u2713'], [ALL_PROJECTS_LABEL, '']]);
      expect(current, address.pathname ?? '').toEqual(['Школа №7']);
    }
  });

  it('flags «Все объекты» when the address names no project, and no project', () => {
    const { marks, current } = marksOf(markupOf(at('/dashboard'), ready()));
    expect(marks).toEqual([['Мост через Неву', ''], ['Школа №7', ''], [ALL_PROJECTS_LABEL, '\u2713']]);
    expect(current).toEqual([ALL_PROJECTS_LABEL]);
  });

  it('flags nothing for a project the first page does not hold, and the button says why', () => {
    const markup = markupOf(at('/dashboard', `project=${C}`), ready(PROJECTS, { more: true }));
    expect(marksOf(markup).current).toEqual([]);
    expect(marksOf(markup).marks.every(([, mark]) => mark === '')).toBe(true);
    expect(markup).toContain('Объект вне первых 2');
  });

  it('puts the flag on the project\'s uid and not on its name: two projects of one name are told apart', () => {
    const other = project(A, 'Склад', { documents: 5 });
    const model = buildSwitcherModel(at('/dashboard', `project=${C}`), ready([other, SAME_NAME]));
    const links = model.entries.filter((entry) => entry.kind === 'link');
    expect(links.map((entry) => (entry.kind === 'link' ? entry.current : null))).toEqual([false, true, false, undefined]);
  });

  it('leaves «Остальные объекты», «Новый объект» and the retry out of the choices', () => {
    const { marks } = marksOf(markupOf(at('/dashboard', `project=${A}`), ready(PROJECTS, { more: true })));
    expect(marks.map(([label]) => label)).toEqual(['Мост через Неву', 'Школа №7', ALL_PROJECTS_LABEL]);
    const model = buildSwitcherModel(at('/dashboard', `project=${A}`), ready(PROJECTS, { more: true }));
    for (const entry of model.entries) {
      if (entry.kind === 'link' && (entry.label === MORE_PROJECTS_LABEL || entry.label === NEW_PROJECT_LABEL)) expect(entry.current).toBeUndefined();
    }
  });

  it('does not change a row\'s link or its words', () => {
    const marked = itemsOf(markupOf(at('/dashboard', `project=${A}`), ready()));
    const bare = itemsOf(markupOf(at('/dashboard'), ready()));
    expect(marked.map(([tag, href, text]) => [tag, href, text])).toEqual(bare.map(([tag, , text], index) => [tag, marked[index]?.[1], text]));
    expect(marked.map(([, , text]) => text.split('\n')[0])).toEqual(['Мост через Неву', 'Школа №7', ALL_PROJECTS_LABEL, NEW_PROJECT_LABEL]);
  });
});

// ----------------------------------------------------- UIP-G-06: the object the account chose last, and the command a choice is

describe('UIP-G-06: on a screen that follows the object, a silent address means the account\'s last object', () => {
  it('names it on the button and flags its row, on every optional screen', () => {
    for (const pathname of ['/dashboard', '/knowledge-base', '/dispatcher', '/version-comparison', '/stage-comparison', '/section-optimisation', '/optimisation']) {
      const model = buildSwitcherModel(at(pathname, '', B), ready());
      expect(model.projectUid, pathname).toBe(B);
      expect(model.value, pathname).toBe('Школа №7');
      expect(model.triggerLabel, pathname).toBe('Объект: Школа №7');
      const { marks, current } = marksOf(markupOf(at(pathname, '', B), ready()));
      expect(marks, pathname).toEqual([['Мост через Неву', ''], ['Школа №7', '✓'], [ALL_PROJECTS_LABEL, '']]);
      expect(current, pathname).toEqual(['Школа №7']);
    }
  });

  it('is beaten by ?project=<uid>, and by the explicit ?project=all, which names no object and flags «Все объекты»', () => {
    expect(buildSwitcherModel(at('/dashboard', `project=${A}`, B), ready()).value).toBe('Мост через Неву');
    const all = buildSwitcherModel(at('/dashboard', 'project=all', B), ready());
    expect(all.projectUid).toBeNull();
    expect(all.value).toBe(ALL_PROJECTS_LABEL);
    expect(marksOf(markupOf(at('/dashboard', 'project=all', B), ready())).current).toEqual([ALL_PROJECTS_LABEL]);
  });

  it('is beaten by the path of a required screen, and is not read at all on a global one', () => {
    expect(buildSwitcherModel(at(`/projects/${A}`, '', B), ready()).value).toBe('Мост через Неву');
    const global = buildSwitcherModel(at('/queue', '', B), ready());
    expect(global.value).toBe(ALL_PROJECTS_LABEL);
    expect(global.hint).toBe(GLOBAL_SCREEN_HINT);
  });

  it('with no last object (null, absent, empty) the button says «Все объекты», as before', () => {
    for (const remembered of [null, undefined, '']) {
      expect(buildSwitcherModel(at('/dashboard', '', remembered), ready()).value).toBe(ALL_PROJECTS_LABEL);
    }
  });

  it('says «Загрузка…» while the account\'s answer is on its way, and flags no row; once it is known it says the object', () => {
    const waiting: SwitcherAddress = { ...at('/dashboard'), rememberedPending: true };
    const model = buildSwitcherModel(waiting, ready());
    expect(model.value).toBe('Загрузка…');
    expect(marksOf(markupOf(waiting, ready())).current).toEqual([]);
    // waiting changes nothing where the address already says: an object, the explicit all, a global screen
    expect(buildSwitcherModel({ ...at('/dashboard', `project=${A}`), rememberedPending: true }, ready()).value).toBe('Мост через Неву');
    expect(buildSwitcherModel({ ...at('/dashboard', 'project=all'), rememberedPending: true }, ready()).value).toBe(ALL_PROJECTS_LABEL);
    expect(buildSwitcherModel({ ...at('/queue'), rememberedPending: true }, ready()).value).toBe(ALL_PROJECTS_LABEL);
    expect(buildSwitcherModel({ ...at('/dashboard', '', B), rememberedPending: false }, ready()).value).toBe('Школа №7');
  });

  it('can fail: the object that is open is not the first row, nor the one the address would have named without the account', () => {
    expect(buildSwitcherModel(at('/dashboard', '', B), ready()).value).not.toBe('Мост через Неву');
    expect(buildSwitcherModel(at('/dashboard', '', B), ready()).value).not.toBe(ALL_PROJECTS_LABEL);
  });

  it('the first render of the island, which knows nothing of the account, does not say «Все объекты» on such a screen', () => {
    navigation.pathname = '/dashboard';
    navigation.search = '';
    const markup = renderToStaticMarkup(createElement(ProjectSwitcher));
    expect(markup).toContain('Загрузка…');
    navigation.search = 'project=all';
    expect(renderToStaticMarkup(createElement(ProjectSwitcher))).not.toContain('Загрузка…');
  });
});

describe('UIP-G-06: which object a click on the menu chose', () => {
  const model = buildSwitcherModel(at('/dashboard', '', A), ready(PROJECTS, { more: true }));
  const hrefOf = (label: string): string => {
    const entry = model.entries.find((candidate) => candidate.kind === 'link' && candidate.label.split('\n')[0] === label);
    if (entry === undefined || entry.kind !== 'link') throw new Error(`no entry ${label}`);
    return entry.href;
  };

  it('is the object of a project\'s row, whatever the address it leads to', () => {
    expect(chosenProject(model, hrefOf('Мост через Неву'))).toBe(A);
    expect(chosenProject(model, hrefOf('Школа №7'))).toBe(B);
    const onGlobal = buildSwitcherModel(at('/queue'), ready());
    expect(chosenProject(onGlobal, `/projects/${B}`)).toBe(B);
  });

  it('is nothing for «Все объекты», «Остальные объекты», «Новый объект», a link that is no entry, and no link: the all-objects view is never sent', () => {
    expect(chosenProject(model, hrefOf(ALL_PROJECTS_LABEL))).toBeNull();
    expect(chosenProject(model, hrefOf(MORE_PROJECTS_LABEL))).toBeNull();
    expect(chosenProject(model, hrefOf(NEW_PROJECT_LABEL))).toBeNull();
    expect(chosenProject(model, '/somewhere/else')).toBeNull();
    expect(chosenProject(model, null)).toBeNull();
    const onGlobal = buildSwitcherModel(at('/queue'), ready());
    expect(chosenProject(onGlobal, '/projects')).toBeNull();
  });

  it('only a project\'s row carries the object it chooses', () => {
    const carried = model.entries.map((entry) => (entry.kind === 'link' ? (entry.projectUid ?? null) : 'retry'));
    expect(carried).toEqual([A, B, null, null, null]);
  });

  /** The wrapper's click handler, as the markup would carry it: `ProjectSwitcherView` is a plain component, so its element is read. */
  function clickHandler(onNavigate: (uid: string | null) => void, shown = model) {
    const element = ProjectSwitcherView({ model: shown, onRetry: () => undefined, onNavigate }) as { props: { onClick: (event: unknown) => void } };
    return element.props.onClick;
  }
  const clickOn = (href: string | null) => ({ target: { closest: () => (href === null ? null : { getAttribute: () => href }) } });

  it('the wrapper reports the object a click on a link of the menu chose, and null for a link that chose none', () => {
    const chosen = vi.fn();
    const onClick = clickHandler(chosen);
    onClick(clickOn(hrefOf('Школа №7')));
    onClick(clickOn(hrefOf(ALL_PROJECTS_LABEL)));
    onClick(clickOn(null));
    expect(chosen.mock.calls).toEqual([[B], [null]]);
  });

  it('a click on something that is not an element, or with no handler given, reports nothing and throws nothing', () => {
    const chosen = vi.fn();
    clickHandler(chosen)({ target: {} });
    clickHandler(chosen)({ target: null as never });
    expect(chosen).not.toHaveBeenCalled();
    const element = ProjectSwitcherView({ model, onRetry: () => undefined }) as { props: { onClick: (event: unknown) => void } };
    expect(() => element.props.onClick(clickOn(hrefOf('Школа №7')))).not.toThrow();
  });
});

describe('UIP-G-06: a refusal to keep the choice is said beside the button, not inside the closed list', () => {
  const model = buildSwitcherModel(at('/dashboard', `project=${A}`), ready());

  it('shows nothing when there is none', () => {
    for (const rememberFailure of [undefined, null]) {
      const markup = renderToStaticMarkup(createElement(ProjectSwitcherView, { model, onRetry: () => undefined, rememberFailure }));
      expect(markup).not.toContain('data-switcher-remember-failure');
    }
  });

  it('says the object is open but not kept, with the sentence and the correlation id, as an alert', () => {
    const markup = renderToStaticMarkup(
      createElement(ProjectSwitcherView, {
        model,
        onRetry: () => undefined,
        rememberFailure: { detail: 'Запрос не дошёл до сервера.', correlationId: 'cid-remember-1' },
      }),
    );
    expect(markup).toMatch(/<span class="[^"]*" role="alert" data-switcher-remember-failure="">Объект открыт, но не запомнен: Запрос не дошёл до сервера\. Код обращения: cid-remember-1<\/span>/);
    // beside the button: outside the popup, which is hidden while the list is closed
    expect(markup.indexOf('data-switcher-remember-failure')).toBeGreaterThan(markup.lastIndexOf('</ul></div>'));
  });

  it('leaves the correlation id out when there is none', () => {
    const markup = renderToStaticMarkup(
      createElement(ProjectSwitcherView, { model, onRetry: () => undefined, rememberFailure: { detail: 'Отказ.', correlationId: null } }),
    );
    expect(markup).toContain('Объект открыт, но не запомнен: Отказ.<');
    expect(markup).not.toContain('Код обращения');
  });
});

describe('UIP-G-06: the island reads the account only where its answer changes what the button says', () => {
  const account = (lastProject: string | null): Account =>
    ({ user_uid: 'usr_01J9ZQ8K7NHVXW3T2R5M6P4Q8B', roles: ['expert'], last_project_uid: lastProject }) as unknown as Account;

  const accountQuery = (address: SwitcherAddress) => {
    const client = newClient();
    renderScreen(client, createElement(ProjectSwitcherLive, { address }));
    return client.getQueryCache().find({ queryKey: queryKeys.account.me() });
  };

  it('asks (enabled) on an optional screen with a silent address, and nowhere else', () => {
    expect((accountQuery(at('/dashboard'))?.options as { enabled?: boolean }).enabled).toBe(true);
    expect((accountQuery(at('/knowledge-base', 'tab=x'))?.options as { enabled?: boolean }).enabled).toBe(true);
    // `UIP-S01-01`: «Главная» is an optional screen, so a silent address asks for the account's last object there too.
    expect((accountQuery(at('/'))?.options as { enabled?: boolean }).enabled).toBe(true);
    for (const address of [at('/dashboard', `project=${A}`), at('/dashboard', 'project=all'), at('/', `project=${A}`), at('/', 'project=all'), at(`/projects/${A}`), at('/queue'), at(null)]) {
      const query = accountQuery(address);
      expect(query === undefined || (query.options as { enabled?: boolean }).enabled === false, JSON.stringify([address.pathname, address.searchParams.toString()])).toBe(true);
    }
  });

  it('names the account\'s last object on the button once the one getMe query has it', () => {
    const client = newClient();
    client.setQueryData(queryKeys.account.me(), account(B));
    client.setQueryData(SWITCHER_LIST, page(PROJECTS));
    const markup = renderScreen(client, createElement(ProjectSwitcherLive, { address: at('/dashboard') }));
    expect(markup).toContain('>Школа №7</span>');
    expect(marksOf(markup).current).toEqual(['Школа №7']);
    // the row's link keeps the screen and writes the object down
    expect(itemsOf(markup).slice(0, 2).map(([, href]) => href)).toEqual([`/dashboard?project=${A}`, `/dashboard?project=${B}`]);
  });

  it('asks for the list, to name the object, as soon as the account has named one', () => {
    const client = newClient();
    client.setQueryData(queryKeys.account.me(), account(B));
    renderScreen(client, createElement(ProjectSwitcherLive, { address: at('/dashboard') }));
    const list = client.getQueryCache().find({ queryKey: SWITCHER_LIST });
    expect((list?.options as { enabled?: boolean }).enabled).toBe(true);
  });

  it('says «Все объекты» for an account with no last object, and «Загрузка…» while it is not known', () => {
    const known = newClient();
    known.setQueryData(queryKeys.account.me(), account(null));
    expect(renderScreen(known, createElement(ProjectSwitcherLive, { address: at('/dashboard') }))).toContain('>Все объекты</span>');
    expect(renderScreen(newClient(), createElement(ProjectSwitcherLive, { address: at('/dashboard') }))).toContain('>Загрузка…</span>');
  });
});

// ------------------------------------------------------------- UIP-G-08: the menu that draws the badges

describe('UIP-G-08: the selector\'s own menu is the shared menu\'s markup, class for class, plus the badges', () => {
  const model = buildSwitcherModel(at('/dashboard', `project=${A}`), ready());
  const props = switcherMenuProps(model, () => undefined);
  const idsOf = (markup: string) => ({
    triggerId: /<button\b[^>]*\bid="([^"]*)"/.exec(markup)?.[1] as string,
    menuId: /<ul\b[^>]*\bid="([^"]*)"/.exec(markup)?.[1] as string,
  });

  it('the island renders exactly the closed view, with the list in it and hidden', () => {
    const island = renderToStaticMarkup(createElement(ObjectMenu, props));
    const closed = renderToStaticMarkup(createElement(ObjectMenuView, { ...props, state: MENU_CLOSED, ...idsOf(island) }));
    expect(island).toBe(closed);
    expect(island).toContain('aria-expanded="false"');
    expect(island).toMatch(/<div class="am-menu__popup" hidden="">/);
  });

  it('draws the same markup as `Menu` for the rows that carry no badge: the shell\'s tests read this markup as they read that one', () => {
    const plain = switcherMenuProps(buildSwitcherModel(at('/queue'), { kind: 'loading' }), () => undefined);
    const ours = renderToStaticMarkup(createElement(ObjectMenuView, { ...plain, state: MENU_CLOSED, triggerId: 't', menuId: 'm' }));
    // `title` is the one attribute `Menu` has no prop for; the hint of a global screen is said there
    const theirs = renderToStaticMarkup(createElement(MenuView, { ...plain, state: MENU_CLOSED, triggerId: 't', menuId: 'm' }));
    expect(ours.replace(' title="экран общий"', '')).toBe(theirs);
    expect(ours).toContain('title="экран общий"');
  });

  it('opened, it shows the popup and the rows with their badges (the instrument that draws the menu open uses this view)', () => {
    const open = renderToStaticMarkup(createElement(ObjectMenuView, { ...props, state: { open: true, active: 0 }, triggerId: 't', menuId: 'm' }));
    expect(open).toContain('aria-expanded="true"');
    expect(open).not.toContain('hidden=""');
    expect(rowsOf(open)[0]?.figures.map(([key, count]) => [key, count])).toEqual([['not_run', 2], ['no_expert_decision', 5]]);
  });

  it('keeps the retry an action row with its handler, and the model\'s entries one row each, in order', () => {
    const failed = buildSwitcherModel(at('/dashboard'), switcherListOf(undefined, apiError(503, 'dependency_unavailable', true)));
    const retry = vi.fn();
    const items = switcherMenuProps(failed, retry).items;
    expect(items.map((item) => item.kind)).toEqual(['action', 'link', 'link']);
    const first = items[0];
    if (first.kind === 'action') first.onChoose?.();
    expect(retry).toHaveBeenCalledTimes(1);
    expect(switcherMenuProps(model, retry).items.map((item) => item.label)).toEqual(['Мост через Неву', 'Школа №7', ALL_PROJECTS_LABEL, NEW_PROJECT_LABEL]);
  });
});

describe('UIP-G-08: the module\'s rules read the picker\'s size tokens and leave the button no frame', () => {
  const WEB = fileURLToPath(new URL('../../..', import.meta.url));
  const MODULE = readFileSync(join(WEB, 'src', 'widgets', 'project-switcher', 'ui', 'project-switcher.module.css'), 'utf8');
  /** The declarations of the rule whose selector is exactly `selector`, or `null`. */
  const rule = (selector: string): string | null => {
    const at = MODULE.indexOf(`\n${selector} {`);
    return at < 0 ? null : MODULE.slice(MODULE.indexOf('{', at) + 1, MODULE.indexOf('}', at));
  };

  it('the panel is the picker\'s width, at most its ceiling, and never wider than the viewport', () => {
    const popup = rule('.switcher :global(.am-menu__popup)');
    expect(popup).toContain('min-width: min(var(--am-picker-width), calc(100vw - 32px))');
    expect(popup).toContain('max-width: min(var(--am-picker-width-max), calc(100vw - 32px))');
  });

  it('an object\'s row takes the picker\'s step, and a badge its narrowest width', () => {
    expect(rule('.switcher .object')).toContain('min-height: var(--am-picker-row-step)');
    expect(rule('.figure')).toContain('min-width: var(--am-picker-badge-min)');
    expect(rule('.figure')).toContain('font-variant-numeric: tabular-nums');
  });

  it('the button has no frame, fill or shadow of its own, and no caption rule is left in the module', () => {
    const trigger = rule('.switcher :global(.am-menu__trigger)') ?? '';
    expect(trigger).not.toBe('');
    expect(trigger).not.toMatch(/\bborder(?!-radius)[\w-]*:/);
    expect(trigger).not.toMatch(/\bbackground/);
    expect(trigger).not.toContain('box-shadow');
    expect(MODULE).not.toMatch(/\.caption\b|\.hint\b|uppercase/);
  });

  it('colours the badges with the global badge tones, so the module declares no colour pair of its own for them', () => {
    expect(rule('.figure')).not.toMatch(/\b(color|background)/);
    expect(rule('.figures')).not.toMatch(/\b(color|background)/);
  });

  it('can fail: a selector that is not in the file reads as no rule', () => {
    expect(rule('.switcher .no-such-rule')).toBeNull();
  });
});
