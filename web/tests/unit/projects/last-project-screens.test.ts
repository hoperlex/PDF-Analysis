/**
 * `UIP-G-06`: the screens of the class that follows the object, other than the three that have their own files
 * (`dashboard/dashboard-project`, `knowledge-base/knowledge-base-project`, `dispatcher/project-scope`), open on the account's
 * last object when their address names none, and the address beats it.
 *
 *   - «Оптимизация разделов» (`/section-optimisation`): the address reader tells `?project=all` from an address that says
 *     nothing; the page opens on the last object only until the address or the reader has decided;
 *   - the retired `/optimisation`: redirects to the object's «Оптимизация» tab, and waits for the account's answer;
 *   - «Сравнение версий» and «Сравнение стадий»: the object of the chooser.
 */

import { PathnameContext, SearchParamsContext } from 'next/dist/shared/lib/hooks-client-context.shared-runtime';
import { AppRouterContext } from 'next/dist/shared/lib/app-router-context.shared-runtime';
import type { AppRouterInstance } from 'next/dist/shared/lib/app-router-context.shared-runtime';
import { QueryClientProvider } from '@tanstack/react-query';
import { createElement } from 'react';
import type { ReactElement } from 'react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('@/shared/api', async (importOriginal) => {
  const actual = await importOriginal<Record<string, unknown>>();
  return { ...actual, getMe: vi.fn() };
});

import { OPTIMISATION_MOVED_TO, OptimisationPage, optimisationTarget } from '@/_pages/optimisation';
import {
  DEFAULT_SECTION_OPTIMISATION_ADDRESS,
  SectionOptimisationPage,
  objectDecided,
  readSectionOptimisationAddress,
  sectionOptimisationSearch,
  shownProject,
} from '@/_pages/section-optimisation';
import { StageComparePage } from '@/_pages/stage-compare';
import { VersionComparePage } from '@/_pages/version-compare';
import { getMe, queryKeys } from '@/shared/api';
import type { Account } from '@/shared/api';
import { PROJECT_PAGE_LIMIT } from '@/entities/project';

import { mountLive } from '../analysis-settings/live-render';
import type { LiveRender } from '../analysis-settings/live-render';
import { newClient, renderScreen } from '../screens/harness';
import { PROJECT_UID as P1, uid } from '../version-compare/fixtures';
import { seedComparison } from '../version-compare/seed';

const A = 'prj_01J9ZQ8K7NHVXW3T2R5M6P4Q8B';
const B = 'prj_01J9ZQ8K7NHVXW3T2R5M6P4Q8C';
const P2 = uid('prj', 2);

const me = vi.mocked(getMe);
const account = (lastProject: string | null | undefined): Account =>
  ({ user_uid: 'usr_01J9ZQ8K7NHVXW3T2R5M6P4Q8B', roles: ['expert'], ...(lastProject === undefined ? {} : { last_project_uid: lastProject }) }) as unknown as Account;

beforeEach(() => {
  me.mockReset();
  me.mockImplementation((async () => ({ data: account(null), status: 200, correlationId: 'cid-me' })) as unknown as typeof getMe);
});

// ------------------------------------------------------------------------------ the address of «Оптимизация разделов»

describe('«Оптимизация разделов»: ?project=all is «Все объекты», chosen', () => {
  it('reads ?project=all as no project, not set aside, and says it was chosen', () => {
    expect(readSectionOptimisationAddress({ project: 'all' })).toEqual({ ...DEFAULT_SECTION_OPTIMISATION_ADDRESS, allProjects: true });
    expect(readSectionOptimisationAddress({ section: 'KJ', project: 'all', tab: 'accepted' })).toEqual({
      tab: 'accepted',
      sectionCode: 'KJ',
      projectUid: null,
      ignored: [],
      allProjects: true,
    });
  });

  it('an address that says nothing, or names an object, is read as it was: no allProjects', () => {
    expect(readSectionOptimisationAddress({})).toEqual(DEFAULT_SECTION_OPTIMISATION_ADDRESS);
    expect(readSectionOptimisationAddress({})).not.toHaveProperty('allProjects');
    expect(readSectionOptimisationAddress({ project: A })).not.toHaveProperty('allProjects');
    expect(readSectionOptimisationAddress({ project: A }).projectUid).toBe(A);
  });

  it('still sets a project that is neither an identity nor «all» aside', () => {
    expect(readSectionOptimisationAddress({ project: 'ALL' })).toMatchObject({ projectUid: null, ignored: ['project'] });
    expect(readSectionOptimisationAddress({ project: 'prj_nope' }).ignored).toEqual(['project']);
  });

  it('writes the explicit choice as ?project=all, and nothing for a page that has chosen nothing', () => {
    expect(sectionOptimisationSearch({ tab: 'specification', sectionCode: 'AR', projectUid: null, allProjects: true })).toBe('?section=AR&project=all');
    expect(sectionOptimisationSearch({ tab: 'accepted', sectionCode: 'KJ', projectUid: null, allProjects: true })).toBe('?section=KJ&project=all&tab=accepted');
    expect(sectionOptimisationSearch({ tab: 'specification', sectionCode: 'AR', projectUid: null })).toBe('?section=AR');
    expect(sectionOptimisationSearch({ tab: 'specification', sectionCode: 'AR', projectUid: null, allProjects: false })).toBe('?section=AR');
  });

  it('an object beats the flag: the address never says both', () => {
    expect(sectionOptimisationSearch({ tab: 'specification', sectionCode: 'AR', projectUid: A, allProjects: true })).toBe(`?section=AR&project=${A}`);
  });

  it('what it writes it reads back', () => {
    for (const projectUid of [null, A]) {
      const written = sectionOptimisationSearch({ tab: 'accepted', sectionCode: 'KJ', projectUid, allProjects: projectUid === null });
      const params = new URLSearchParams(written);
      const read = readSectionOptimisationAddress({ section: params.get('section') ?? undefined, project: params.get('project') ?? undefined, tab: params.get('tab') ?? undefined });
      expect(read).toMatchObject({ tab: 'accepted', sectionCode: 'KJ', projectUid, ignored: [] });
      expect(read.allProjects === true).toBe(projectUid === null);
    }
  });
});

describe('«Оптимизация разделов»: the page opens on the account\'s last object until the address or the reader has decided', () => {
  function pageWith(lastProject: string | null | undefined, query: Parameters<typeof readSectionOptimisationAddress>[0]): string {
    const client = newClient();
    if (lastProject !== undefined) client.setQueryData(queryKeys.account.me(), account(lastProject));
    return renderScreen(client, createElement(SectionOptimisationPage, { initial: readSectionOptimisationAddress(query) }));
  }
  const back = (markup: string): string | null => /data-section-optimisation-back="([^"]*)"/.exec(markup)?.[1] ?? null;

  it('narrows to the last object for an address that says nothing about the object', () => {
    const markup = pageWith(A, { section: 'KJ' });
    expect(back(markup)).toBe('section');
    // `UIP-S11-01`: the arrow of the header, whose name says where it leads.
    expect(/<a [^>]*data-section-optimisation-back="section"[^>]*>←<\/a>/.exec(markup)?.[0]).toContain(`href="/projects/${A}/sections/KJ"`);
  });

  it('is beaten by ?project=<uid>, and by ?project=all, which stays on every object', () => {
    expect(pageWith(A, { section: 'KJ', project: B })).toContain(`/projects/${B}/sections/KJ`);
    const all = pageWith(A, { section: 'KJ', project: 'all' });
    expect(back(all)).toBe('dashboard');
    expect(all).not.toContain('data-address-ignored');
  });

  it('stays on every object when the account chose none, has not answered, or did not say', () => {
    expect(back(pageWith(null, { section: 'KJ' }))).toBe('dashboard');
    expect(back(pageWith(undefined, { section: 'KJ' }))).toBe('dashboard');
    expect(back(pageWith(A, {}))).toBe('section');
  });

  it('a late answer of getMe applies to a page nobody has decided, and never to one that was', () => {
    // untouched: the account's object stands in as it arrives; before it arrives, every object
    expect(shownProject({ projectUid: null, decided: false }, null)).toBeNull();
    expect(shownProject({ projectUid: null, decided: false }, A)).toBe(A);
    // decided «Все объекты» (the address, or the reader's choice): the account's object does not override it
    expect(shownProject({ projectUid: null, decided: true }, A)).toBeNull();
    // decided on an object: that object
    expect(shownProject({ projectUid: B, decided: true }, A)).toBe(B);
    expect(shownProject({ projectUid: B, decided: false }, A)).toBe(A);
  });

  it('an address has decided the object when it names one or says ?project=all, and not when it says nothing', () => {
    expect(objectDecided(readSectionOptimisationAddress({}))).toBe(false);
    expect(objectDecided(readSectionOptimisationAddress({ section: 'KJ', tab: 'accepted' }))).toBe(false);
    expect(objectDecided(readSectionOptimisationAddress({ project: A }))).toBe(true);
    expect(objectDecided(readSectionOptimisationAddress({ project: 'all' }))).toBe(true);
    // a project the address spells wrongly is set aside and decides nothing
    expect(objectDecided(readSectionOptimisationAddress({ project: 'prj_nope' }))).toBe(false);
  });

  it('reads the last object\'s specification and offers no list of projects (`UIP-S11-01`: the object is the top strip\'s)', () => {
    const client = newClient();
    client.setQueryData(queryKeys.account.me(), account(A));
    const markup = renderScreen(client, createElement(SectionOptimisationPage, { initial: readSectionOptimisationAddress({ section: 'KJ' }) }));
    expect(markup).not.toContain('data-section-project-filter');
    const reads = client.getQueryCache().getAll().map((query) => query.queryKey as readonly unknown[]);
    expect(reads.some((key) => key[1] === 'section-specification' && (key[3] as { projectUid: string | null }).projectUid === A)).toBe(true);
    expect(reads.some((key) => key[1] === 'section-specification' && (key[3] as { projectUid: string | null }).projectUid === null)).toBe(false);
  });
});

// ----------------------------------------------------------------------------------------------- the retired /optimisation

describe('the retired /optimisation address follows the object', () => {
  it('leads to the object\'s «Оптимизация» tab, and to the list where there is no object', () => {
    expect(optimisationTarget(A)).toBe(`/projects/${A}?tab=optimisation`);
    expect(optimisationTarget(null)).toBe(OPTIMISATION_MOVED_TO);
    expect(OPTIMISATION_MOVED_TO).toBe('/projects');
  });

  it('says where it leads, in the markup: the last object\'s tab, or the list', () => {
    const known = newClient();
    known.setQueryData(queryKeys.account.me(), account(A));
    const withObject = renderScreen(known, createElement(OptimisationPage));
    expect(withObject).toContain(`href="/projects/${A}?tab=optimisation"`);
    expect(withObject).toContain('Открываю вкладку «Оптимизация» объекта.');
    expect(withObject).toContain('вкладке объекта');

    const none = newClient();
    none.setQueryData(queryKeys.account.me(), account(null));
    const withoutObject = renderScreen(none, createElement(OptimisationPage));
    expect(withoutObject).toContain('href="/projects"');
    expect(withoutObject).toContain('Открываю список объектов.');
    expect(withoutObject).not.toContain('tab=optimisation');
  });

  describe('the redirect itself', () => {
    let live: LiveRender | null = null;
    afterEach(async () => {
      await live?.unmount();
      live = null;
    });

    const replace = vi.fn();
    const router = { replace, push: vi.fn(), prefetch: vi.fn(), back: vi.fn(), forward: vi.fn(), refresh: vi.fn() } as unknown as AppRouterInstance;

    const mount = (client: ReturnType<typeof newClient>, address: string): Promise<LiveRender> =>
      mountLive(
        createElement(
          QueryClientProvider,
          { client },
          createElement(
            AppRouterContext.Provider,
            { value: router },
            createElement(
              PathnameContext.Provider,
              { value: '/optimisation' },
              createElement(SearchParamsContext.Provider, { value: new URLSearchParams(address) }, createElement(OptimisationPage)),
            ),
          ),
        ),
      );

    async function settled(view: LiveRender): Promise<void> {
      for (let round = 0; round < 5; round += 1) {
        await view.settle(() => new Promise<void>((done) => setTimeout(done, 0)));
      }
    }

    beforeEach(() => replace.mockReset());

    it('waits for the account\'s answer, then goes to the last object\'s tab', async () => {
      let answer: (value: unknown) => void = () => undefined;
      me.mockImplementation((() => new Promise((resolve) => { answer = resolve; })) as unknown as typeof getMe);
      live = await mount(newClient(), '');
      await settled(live);
      expect(replace).not.toHaveBeenCalled();
      answer({ data: account(A), status: 200, correlationId: 'cid-me' });
      await settled(live);
      expect(replace.mock.calls).toEqual([[`/projects/${A}?tab=optimisation`]]);
    });

    it('goes to the list for an account with no last object, and for one whose answer failed', async () => {
      live = await mount(newClient(), '');
      await settled(live);
      expect(replace.mock.calls.at(-1)).toEqual(['/projects']);
      await live.unmount();

      replace.mockReset();
      me.mockRejectedValue(new Error('down'));
      live = await mount(newClient(), '');
      await settled(live);
      expect(replace.mock.calls.at(-1)).toEqual(['/projects']);
    });

    it('goes to the object of the address at once, and to the list for ?project=all, without asking the account', async () => {
      me.mockImplementation((async () => ({ data: account(A), status: 200, correlationId: 'cid-me' })) as unknown as typeof getMe);
      live = await mount(newClient(), `project=${B}`);
      await settled(live);
      expect(replace.mock.calls).toEqual([[`/projects/${B}?tab=optimisation`]]);
      await live.unmount();

      replace.mockReset();
      live = await mount(newClient(), 'project=all');
      await settled(live);
      expect(replace.mock.calls).toEqual([['/projects']]);
      expect(me).not.toHaveBeenCalled();
    });
  });
});

// ------------------------------------------------------------------------------------------------- the comparison screens

describe('the comparison screens work in the object the screen is on', () => {
  const projects = [
    { project_uid: P1, name: 'Корпус 1', created_at: '2026-10-01T00:00:00Z', document_count: 3 },
    { project_uid: P2, name: 'Корпус 2', created_at: '2026-10-02T00:00:00Z', document_count: 1 },
  ];

  function screenOf(page: ReactElement, query: string, lastProject: string | null, modules: 'versions' | 'versions,stages'): string {
    const client = newClient();
    seedComparison(client, { modules, projects: false, overview: 'none' });
    client.setQueryData(queryKeys.projects.list(undefined, PROJECT_PAGE_LIMIT), { items: projects, page: { next_cursor: null } });
    client.setQueryData(queryKeys.account.me(), account(lastProject));
    return renderScreen(client, createElement(SearchParamsContext.Provider, { value: new URLSearchParams(query) }, page));
  }

  function chooserOf(page: ReactElement, query: string, lastProject: string | null, modules: 'versions' | 'versions,stages'): string[] {
    const markup = screenOf(page, query, lastProject, modules);
    // the chooser is the first select of the screen; the workspace below it has selects of its own
    const chooser = /<select[\s\S]*?<\/select>/.exec(markup)?.[0] ?? '';
    return [...chooser.matchAll(/<option value="([^"]*)"[^>]*\bselected\b/g)].map((match) => match[1] as string);
  }

  /** `UIP-S16-01`: «Сравнение стадий» has no chooser; the object the workspace opens on is the top strip's. */
  function workspaceOf(query: string, lastProject: string | null): string | null {
    return /data-stage-workspace="([^"]*)"/.exec(screenOf(createElement(StageComparePage), query, lastProject, 'versions,stages'))?.[1] ?? null;
  }

  it('«Сравнение версий»: the last object when the address names none', () => {
    expect(chooserOf(createElement(VersionComparePage), '', P2, 'versions')).toEqual([P2]);
  });

  it('«Сравнение версий»: the address beats it, and ?project=all leaves the choice empty', () => {
    expect(chooserOf(createElement(VersionComparePage), `project=${P1}`, P2, 'versions')).toEqual([P1]);
    expect(chooserOf(createElement(VersionComparePage), 'project=all', P2, 'versions')).toEqual(['']);
  });

  it('«Сравнение версий»: no last object leaves the choice empty, as before', () => {
    expect(chooserOf(createElement(VersionComparePage), '', null, 'versions')).toEqual(['']);
  });

  it('«Сравнение стадий»: the last object when the address names none', () => {
    expect(workspaceOf('', P2)).toBe(P2);
  });

  it('«Сравнение стадий»: the address beats it, and ?project=all opens no workspace', () => {
    expect(workspaceOf(`project=${P1}`, P2)).toBe(P1);
    expect(workspaceOf('project=all', P2)).toBeNull();
  });

  it('«Сравнение стадий»: no last object opens no workspace and asks for the top strip', () => {
    expect(workspaceOf('', null)).toBeNull();
    expect(screenOf(createElement(StageComparePage), '', null, 'versions,stages')).toContain('Выберите объект в верхней строке');
  });
});
