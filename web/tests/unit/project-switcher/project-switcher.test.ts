/**
 * `UI-PARITY-01` wave 1, `R-150b`: the «Проекты ▾» selector of the frame's top strip.
 *
 * The model is pure and read as data (what a choice leads to, what a row says, what the button
 * shows); the markup is read off one static pass of the real widget. The keyboard is `Menu`'s
 * (`tests/unit/ui/menu.test.ts`, `qa_w50/primitives-keyboard.test.ts`), and the hover, focus and
 * press that ask for the list are a browser fact: here the gate is read off the query the widget
 * registers (`enabled`), the way `qa_w50/r66-navigation.test.ts` reads the reads of a screen.
 */

import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it, vi } from 'vitest';

import { ApiError } from '@/shared/api';
import type { ErrorEnvelope, Project, ProjectPage } from '@/shared/api';
import { queryKeys } from '@/shared/api';
import { PROJECT_PAGE_LIMIT } from '@/entities/project';
import {
  ALL_PROJECTS_LABEL,
  GLOBAL_SCREEN_HINT,
  MORE_PROJECTS_LABEL,
  NEW_PROJECT_LABEL,
  ProjectSwitcher,
  ProjectSwitcherLive,
  ProjectSwitcherView,
  RETRY_LABEL,
  buildSwitcherModel,
  chooseProject,
  projectFigures,
  projectRowLabels,
  switcherListOf,
} from '@/widgets/project-switcher';
import type { SwitcherAddress, SwitcherList } from '@/widgets/project-switcher';

import { auditCounts } from '../dashboard/audit-counts';
import { newClient, renderScreen, seedError } from '../screens/harness';

const navigation = vi.hoisted(() => ({ pathname: null as string | null, search: '' }));

vi.mock('next/navigation', async (importOriginal) => ({
  ...(await importOriginal<Record<string, unknown>>()),
  usePathname: () => navigation.pathname,
  useSearchParams: () => new URLSearchParams(navigation.search),
}));

// ----------------------------------------------------------------------------------- fixtures

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

function at(pathname: string | null, search = ''): SwitcherAddress {
  return { pathname, searchParams: new URLSearchParams(search) };
}

function apiError(status: number, code: ErrorEnvelope['error_code'], retryable: boolean): ApiError {
  const envelope: ErrorEnvelope = {
    contract_version: '1.38.0',
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

/** The menu items of a markup, in order: `[tag, href or null, text]`. */
function itemsOf(markup: string): [string, string | null, string][] {
  return [...markup.matchAll(/<(a|button)\b([^>]*role="menuitem"[^>]*)>([\s\S]*?)<\/(?:a|button)>/g)].map((m) => [
    m[1] as string,
    /\bhref="([^"]*)"/.exec(m[2] as string)?.[1] ?? null,
    (m[3] as string).replace(/&amp;/g, '&'),
  ]);
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

  it('«Все проекты» on an optional screen removes the parameter and the dependent ones, and keeps the rest', () => {
    expect(chooseProject(at('/dashboard', `project=${A}&section=AR&view=compact`), null)).toBe('/dashboard?view=compact');
    expect(chooseProject(at('/section-optimisation', `project=${A}`), null)).toBe('/section-optimisation');
  });

  it('choosing the project the address already has changes nothing', () => {
    expect(chooseProject(at('/dashboard', `project=${A}&section=AR`), A)).toBe(`/dashboard?project=${A}&section=AR`);
  });

  it('on a required screen the choice opens the chosen project\'s page, whatever the path says', () => {
    const address = at(`/projects/${A}/versions/${VERSION}`);
    expect(chooseProject(address, B)).toBe(`/projects/${B}`);
    expect(chooseProject(at(`/projects/${A}`), A)).toBe(`/projects/${A}`);
  });

  it('«Все проекты» on a required screen opens the project list', () => {
    expect(chooseProject(at(`/projects/${A}`), null)).toBe('/projects');
  });

  it('on a global screen the choice opens the chosen project\'s page; «Все проекты» opens the list', () => {
    for (const pathname of ['/queue', '/logs', '/workers', '/projects', '/', '/norms', '/admin/users']) {
      expect(chooseProject(at(pathname, `project=${A}`), B), pathname).toBe(`/projects/${B}`);
      expect(chooseProject(at(pathname, `project=${A}`), null), pathname).toBe('/projects');
    }
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
    expect(projectRowLabels([bare])).toEqual(['Склад']);
    expect(projectRowLabels([bare])[0]).not.toMatch(/\d/);
  });

  it('puts the name and the figures on two lines of one label, one line for the name', () => {
    expect(projectRowLabels(PROJECTS)).toEqual([
      'Мост через Неву\nне запускались 2 · нет решений эксперта 5',
      'Школа №7\nне запускались 0 · нет решений эксперта 0',
    ]);
    // A name with its own line breaks and runs of spaces is one line; the stored name is not touched.
    expect(projectRowLabels([project(C, '  Склад\n  №3  ')])).toEqual(['Склад №3']);
  });

  it('renders each row as a link to its choice, with both figures and their words in its text', () => {
    const items = itemsOf(markupOf(at('/dashboard'), ready()));
    expect(items.slice(0, 2)).toEqual([
      ['a', `/dashboard?project=${A}`, 'Мост через Неву\nне запускались 2 · нет решений эксперта 5'],
      ['a', `/dashboard?project=${B}`, 'Школа №7\nне запускались 0 · нет решений эксперта 0'],
    ]);
  });

  it('keeps the contract\'s order and does not sort', () => {
    expect(projectRowLabels([SCHOOL, MOST]).map((label) => label.split('\n')[0])).toEqual(['Школа №7', 'Мост через Неву']);
  });

  it('keeps two projects with the same name and the same figures apart, and keeps a project named like a fixed entry apart', () => {
    const twin = (uid: string, created: string) => ({ ...project(uid, 'Тест', { documents: 1 }), created_at: created });
    const labels = projectRowLabels([twin(A, '2026-11-01T10:00:00Z'), twin(B, '2026-11-02T10:00:00Z'), twin(C, '2026-11-02T11:00:00Z')]);
    expect(new Set(labels).size).toBe(3);
    expect(labels[0]).toContain('создан 2026-11-01');
    expect(labels[1]).toContain('создан 2026-11-02');
    expect(labels[2]).toContain('создан 2026-11-02');
    expect(labels[2]).toContain('№2');
    // No figures: the label is the bare name, which a project can spell as a fixed entry.
    const named = projectRowLabels([project(A, NEW_PROJECT_LABEL), project(B, ALL_PROJECTS_LABEL)]);
    expect(named).not.toContain(NEW_PROJECT_LABEL);
    expect(named).not.toContain(ALL_PROJECTS_LABEL);
    expect(new Set(named).size).toBe(2);
  });
});

// ------------------------------------------------------------------------------------- the menu

describe('the menu: the rows, then «Все проекты», then «Новый проект»', () => {
  it('lists every project, then both fixed entries, in that order', () => {
    const items = itemsOf(markupOf(at('/dashboard'), ready()));
    expect(items.map(([, , text]) => text.split('\n')[0])).toEqual(['Мост через Неву', 'Школа №7', ALL_PROJECTS_LABEL, NEW_PROJECT_LABEL]);
  });

  it('«Новый проект» leads to the project list, where the form is; «Все проекты» is the screen\'s own address without the project', () => {
    const optional = itemsOf(markupOf(at('/dashboard', `project=${A}`), ready())).slice(-2);
    expect(optional).toEqual([
      ['a', '/dashboard', ALL_PROJECTS_LABEL],
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
    expect(markup).toContain('Загрузка проектов…');
    expect(markup).toContain('role="status"');
  });

  it('says there are no projects when the list is empty, and still offers «Новый проект»', () => {
    const markup = markupOf(at('/dashboard'), ready([]));
    expect(markup).toContain('Проектов пока нет.');
    expect(itemsOf(markup).map(([, , text]) => text)).toEqual([ALL_PROJECTS_LABEL, NEW_PROJECT_LABEL]);
  });

  it('never presents the first page as the whole list: it says how many it shows and links to the rest', () => {
    const markup = markupOf(at('/dashboard'), ready(PROJECTS, { more: true }));
    expect(markup).toContain('Показаны первые 2.');
    expect(itemsOf(markup).map(([, href, text]) => [href, text.split('\n')[0]])).toEqual([
      [`/dashboard?project=${A}`, 'Мост через Неву'],
      [`/dashboard?project=${B}`, 'Школа №7'],
      ['/dashboard', ALL_PROJECTS_LABEL],
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

describe('a failed read: «Проекты не загрузились», a retry inside the menu, and the button still works', () => {
  const retryable = apiError(503, 'dependency_unavailable', true);

  it('shows the message as an alert with its correlation id, offers the retry first, and keeps both fixed entries', () => {
    const list = switcherListOf(undefined, retryable);
    expect(list.kind).toBe('error');
    const markup = markupOf(at('/dashboard'), list);
    expect(markup).toContain('Проекты не загрузились');
    expect(markup).toContain('role="alert"');
    expect(markup).toContain('Код обращения: cid-switcher-1');
    expect(itemsOf(markup)).toEqual([
      ['button', null, RETRY_LABEL],
      ['a', '/dashboard', ALL_PROJECTS_LABEL],
      ['a', '/projects', NEW_PROJECT_LABEL],
    ]);
  });

  it('does not offer a retry for a refusal retrying cannot change', () => {
    const list = switcherListOf(undefined, apiError(403, 'permission_denied', false));
    const markup = markupOf(at('/dashboard'), list);
    expect(markup).toContain('Проекты не загрузились');
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

describe('the button: the project\'s name, or «Все проекты», muted on a global screen with its hint', () => {
  it('shows «Все проекты» when the address names no project', () => {
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
    expect(buildSwitcherModel(named, ready(PROJECTS, { more: true })).value).toBe('Проект вне первых 2');
    expect(buildSwitcherModel(named, ready()).value).toBe('Неизвестный проект');
  });

  it('carries the hint «экран общий» only on a global screen, and mutes the button there', () => {
    expect(GLOBAL_SCREEN_HINT).toBe('экран общий');
    for (const pathname of ['/', '/projects', '/queue', '/logs', '/workers', '/norms', '/admin/users']) {
      const model = buildSwitcherModel(at(pathname), ready());
      expect(model.hint, pathname).toBe(GLOBAL_SCREEN_HINT);
      expect(model.triggerLabel, pathname).toBe(`Проекты: Все проекты, ${GLOBAL_SCREEN_HINT}`);
      const markup = markupOf(at(pathname), ready());
      expect(markup, pathname).toContain('data-project-scope="global"');
      expect(markup, pathname).toMatch(/class="[^"]*muted[^"]*" data-project-switcher/);
      expect(markup, pathname).toContain('экран общий');
    }
    for (const pathname of ['/dashboard', '/knowledge-base', '/section-optimisation']) {
      const model = buildSwitcherModel(at(pathname), ready());
      expect(model.hint, pathname).toBeNull();
      expect(model.triggerLabel, pathname).toBe('Проекты: Все проекты');
      expect(markupOf(at(pathname), ready()), pathname).not.toMatch(/muted|экран общий/);
    }
    // A required screen is not muted and has no hint; its project is the path's.
    const required = buildSwitcherModel(at(`/projects/${A}`), ready());
    expect(required.hint).toBeNull();
    expect(required.triggerLabel).toBe('Проекты: Мост через Неву');
    expect(markupOf(at(`/projects/${A}`), ready())).not.toMatch(/muted|экран общий/);
  });

  it('is a menu button named by what it shows: the trigger\'s accessible name is the model\'s', () => {
    const markup = markupOf(at('/dashboard', `project=${A}`), ready());
    expect(markup).toMatch(/<button\b[^>]*aria-haspopup="menu"[^>]*aria-label="Проекты: Мост через Неву"/);
    expect(markup).toContain('data-project-scope="optional"');
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
    client.setQueryData(queryKeys.projects.list(undefined, PROJECT_PAGE_LIMIT), page(PROJECTS));
    const markup = renderScreen(client, createElement(ProjectSwitcherLive, { address: at('/dashboard', `project=${B}`) }));
    expect(markup).toContain('>Школа №7</span>');
    expect(itemsOf(markup).slice(0, 2).map(([, href]) => href)).toEqual([`/dashboard?project=${A}`, `/dashboard?project=${B}`]);
  });

  it('asks for the list on a screen that names a project, and does not on one that names none', () => {
    const enabledFor = (address: SwitcherAddress): boolean | undefined => {
      const client = newClient();
      renderScreen(client, createElement(ProjectSwitcherLive, { address }));
      const queries = client.getQueryCache().getAll();
      expect(queries.map((query) => query.queryKey)).toEqual([queryKeys.projects.list(undefined, PROJECT_PAGE_LIMIT)]);
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

  it('shows the failure of a failed read inside the menu, with the retry', () => {
    const client = newClient();
    seedError(client, queryKeys.projects.list(undefined, PROJECT_PAGE_LIMIT), apiError(503, 'dependency_unavailable', true));
    const markup = renderScreen(client, createElement(ProjectSwitcherLive, { address: at('/dashboard', `project=${A}`) }));
    expect(markup).toContain('Проекты не загрузились');
    expect(markup).toContain('Название недоступно');
    expect(itemsOf(markup)[0]).toEqual(['button', null, RETRY_LABEL]);
  });
});
