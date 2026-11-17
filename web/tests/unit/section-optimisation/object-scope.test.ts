/**
 * `UIP-S11-01`: «Оптимизация раздела» has no list of projects. The object is the one of the top strip (`UIP-G-06`): the address says
 * it first (`?project=<uid>`, `?project=all`), an address that says nothing opens on the account's last object, and a choice in the
 * strip changes the scope of both tabs WITHOUT a reload — the same page instance, a new address.
 *
 * Two instruments, because each sees what the other cannot. A live mount presses on the real page under a mounted address and
 * watches the requests, which is how «the object reaches the request» and «a change of the object asks again, in the same
 * instance» are proved (the section the page was opened on is kept across the change, which a reload would lose). The header's arrow
 * is read off the same mount.
 */

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AppRouterContext } from 'next/dist/shared/lib/app-router-context.shared-runtime';
import type { AppRouterInstance } from 'next/dist/shared/lib/app-router-context.shared-runtime';
import { PathnameContext, SearchParamsContext } from 'next/dist/shared/lib/hooks-client-context.shared-runtime';
import { createElement } from 'react';
import type { ReactElement } from 'react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('@/shared/api', async (importOriginal) => {
  const actual = await importOriginal<Record<string, unknown>>();
  return {
    ...actual,
    getMe: vi.fn(),
    getSectionSpecification: vi.fn(),
    listAcceptedOptimisationProposals: vi.fn(),
    setMyLastProject: vi.fn(),
  };
});

// The live tree has no CSS object model: the section's dot sets a custom property on its `style`, which the hand-written node of
// `live-render.ts` cannot take. The dot is a mark of colour and says nothing of the object, so it stands out of this mount.
vi.mock('@/entities/project', async (importOriginal) => {
  const actual = await importOriginal<Record<string, unknown>>();
  return { ...actual, SectionDot: () => null };
});

import { SectionOptimisationPage, readSectionOptimisationAddress } from '@/_pages/section-optimisation';
import { getMe, getSectionSpecification, listAcceptedOptimisationProposals, setMyLastProject } from '@/shared/api';
import type { Account } from '@/shared/api';

import { mountLive } from '../analysis-settings/live-render';
import type { LiveRender } from '../analysis-settings/live-render';
import { SECTION_DOCUMENT_A, sectionAnswer } from '../section-specification/fixtures';
import { ACCEPTED_PROJECT_A, ACCEPTED_PROJECT_B, acceptedPage } from './fixtures';

const A = ACCEPTED_PROJECT_A;
const B = ACCEPTED_PROJECT_B;

const me = vi.mocked(getMe);
const specification = vi.mocked(getSectionSpecification);
const acceptedList = vi.mocked(listAcceptedOptimisationProposals);
const remember = vi.mocked(setMyLastProject);

const account = (lastProject: string | null): Account =>
  ({ user_uid: 'usr_01J9ZQ8K7NHVXW3T2R5M6P4Q8B', roles: ['expert'], last_project_uid: lastProject }) as unknown as Account;

/** One project of the section, so «Показать только этот объект» is the one button of its text. */
const oneProject = () => {
  const answer = sectionAnswer();
  const project = answer.projects[0]!;
  return sectionAnswer({
    projects: [project],
    source_count: project.sources.length,
    excluded: [],
    excluded_count: 0,
    row_count: 4,
    rows: { ...answer.rows!, items: answer.rows!.items.slice(0, 4), total: 4 },
  });
};

interface Reads {
  readonly specification: readonly (string | null)[];
  readonly accepted: readonly (string | null)[];
}

/** The document each request carried, in order; `null` for a request that named none. */
function documentsRead(calls: readonly (readonly unknown[])[]): readonly (string | null)[] {
  return calls.map((call) => ((call[0] as { query?: { document_uid?: string } }).query?.document_uid ?? null));
}

/** The project each request carried, in order; `null` for a request that named none. */
function reads(): Reads {
  const of = (calls: readonly (readonly unknown[])[]) =>
    calls.map((call) => ((call[0] as { query?: { project_uid?: string } }).query?.project_uid ?? null));
  return { specification: of(specification.mock.calls), accepted: of(acceptedList.mock.calls) };
}

/** The sections each specification request carried. */
const sectionsRead = (): readonly string[] =>
  specification.mock.calls.map((call) => (call[0] as { path: { section_code: string } }).path.section_code);

describe('the object of the screen is the top strip’s (`UIP-S11-01`)', () => {
  let live: LiveRender | null = null;
  const router = { replace: vi.fn(), push: vi.fn(), prefetch: vi.fn(), back: vi.fn(), forward: vi.fn(), refresh: vi.fn() } as unknown as AppRouterInstance;
  const replaceState = vi.fn();

  beforeEach(() => {
    vi.mocked(router.replace).mockReset();
    replaceState.mockReset();
    me.mockReset();
    me.mockImplementation((async () => ({ data: account(null), status: 200, correlationId: 'cid-me' })) as unknown as typeof getMe);
    specification.mockReset();
    // The answer echoes the section it was asked for, as the server's does: an answer of another section lists no document of this one.
    specification.mockImplementation((async (input: { path: { section_code: string } }) => ({
      data: { ...oneProject(), section_code: input.path.section_code },
      status: 200,
      correlationId: 'cid-spec',
    })) as unknown as typeof getSectionSpecification);
    acceptedList.mockReset();
    acceptedList.mockImplementation((async () => ({ data: acceptedPage(), status: 200, correlationId: 'cid-acc' })) as unknown as typeof listAcceptedOptimisationProposals);
    remember.mockReset();
    remember.mockImplementation((async () => ({ data: undefined, status: 204, correlationId: 'cid-remember' })) as unknown as typeof setMyLastProject);
  });

  afterEach(async () => {
    await live?.unmount();
    live = null;
  });

  const freshClient = (): QueryClient =>
    new QueryClient({ defaultOptions: { queries: { retry: false, refetchOnMount: false, gcTime: Infinity, staleTime: 30_000 } } });

  /** The page under the address a router would have mounted. The page is opened on КЖ by the address the route read. */
  const page = (client: QueryClient, query: string): ReactElement =>
    createElement(
      QueryClientProvider,
      { client },
      createElement(
        AppRouterContext.Provider,
        { value: router },
        createElement(
          PathnameContext.Provider,
          { value: '/section-optimisation' },
          createElement(
            SearchParamsContext.Provider,
            { value: new URLSearchParams(query) },
            createElement(SectionOptimisationPage, { initial: readSectionOptimisationAddress({ section: 'KJ' }) }),
          ),
        ),
      ),
    );

  async function settled(view: LiveRender): Promise<void> {
    for (let round = 0; round < 5; round += 1) {
      await view.settle(() => new Promise<void>((done) => setTimeout(done, 0)));
    }
  }

  const arrow = (view: LiveRender): string => /<a [^>]*data-section-optimisation-back="[^"]*"[^>]*>←<\/a>/.exec(view.markup())?.[0] ?? '';

  it('reads the object of the address for both tabs, and the arrow leads to that object’s section', async () => {
    const client = freshClient();
    live = await mountLive(page(client, `project=${A}`));
    await settled(live);
    expect(reads().specification).toEqual([A]);
    expect(reads().accepted).toEqual([A]);
    expect(arrow(live)).toContain(`href="/projects/${A}/sections/KJ"`);
    expect(live.markup()).not.toContain('data-section-project-filter');
  });

  it('moves to the object of a new address in the SAME page, with no reload: both tabs ask again, the section is kept', async () => {
    const client = freshClient();
    live = await mountLive(page(client, `project=${A}`));
    await settled(live);
    (globalThis as unknown as { window: Record<string, unknown> }).window.history = { replaceState };
    await live.update(page(client, `project=${B}`));
    await settled(live);
    expect(reads().specification).toEqual([A, B]);
    expect(reads().accepted).toEqual([A, B]);
    expect(sectionsRead()).toEqual(['KJ', 'KJ']);
    expect(arrow(live)).toContain(`href="/projects/${B}/sections/KJ"`);
    // The top strip drops the section from the address; the page writes back what it shows, once, so a reload opens the same view.
    expect(replaceState).toHaveBeenCalledTimes(1);
    expect(replaceState).toHaveBeenCalledWith(null, '', `?section=KJ&project=${B}`);
  });

  it('«Все объекты» is `?project=all`: the next requests name no object, and the arrow leads to the dashboard', async () => {
    const client = freshClient();
    live = await mountLive(page(client, `project=${A}`));
    await settled(live);
    (globalThis as unknown as { window: Record<string, unknown> }).window.history = { replaceState };
    await live.update(page(client, 'project=all'));
    await settled(live);
    expect(reads().specification).toEqual([A, null]);
    expect(reads().accepted).toEqual([A, null]);
    expect(arrow(live)).toContain('href="/dashboard"');
    expect(replaceState).toHaveBeenCalledWith(null, '', '?section=KJ&project=all');
  });

  it('opens on the account’s last object where the address says nothing, and the address that names one beats it', async () => {
    me.mockImplementation((async () => ({ data: account(A), status: 200, correlationId: 'cid-me' })) as unknown as typeof getMe);
    const client = freshClient();
    live = await mountLive(page(client, ''));
    await settled(live);
    // The first read is for «Все объекты», drawn while the account is on its way; it moves to the last object when that arrives.
    expect(reads().specification.at(-1)).toBe(A);
    expect(arrow(live)).toContain(`href="/projects/${A}/sections/KJ"`);
    (globalThis as unknown as { window: Record<string, unknown> }).window.history = { replaceState };
    await live.update(page(client, `project=${B}`));
    await settled(live);
    expect(reads().specification.at(-1)).toBe(B);
    expect(arrow(live)).toContain(`href="/projects/${B}/sections/KJ"`);
  });

  it('writes nothing to the address when the account’s object arrives late: nobody has chosen anything', async () => {
    me.mockImplementation((async () => ({ data: account(A), status: 200, correlationId: 'cid-me' })) as unknown as typeof getMe);
    const client = freshClient();
    live = await mountLive(page(client, ''));
    (globalThis as unknown as { window: Record<string, unknown> }).window.history = { replaceState };
    await settled(live);
    expect(replaceState).not.toHaveBeenCalled();
  });

  it('«Показать только этот объект» narrows by the address, the way the top strip does, and keeps the choice for next time', async () => {
    const client = freshClient();
    live = await mountLive(page(client, 'project=all'));
    await settled(live);
    expect(await live.press('Показать только этот объект')).toBe(true);
    await settled(live);
    expect(router.replace).toHaveBeenCalledTimes(1);
    const target = String(vi.mocked(router.replace).mock.calls[0]?.[0]);
    expect(target.startsWith('/section-optimisation?')).toBe(true);
    expect(new URLSearchParams(target.split('?')[1]).get('project')).toMatch(/^prj_/);
    expect(remember).toHaveBeenCalledTimes(1);
  });

  it('narrows both tabs to the document chosen in the row of the tabs, writes it to the address, and forgets it when the object changes', async () => {
    const client = freshClient();
    live = await mountLive(page(client, `project=${A}`));
    await settled(live);
    (globalThis as unknown as { window: Record<string, unknown> }).window.history = { replaceState };
    expect(documentsRead(specification.mock.calls)).toEqual([null]);

    expect(await live.change('Документ', SECTION_DOCUMENT_A)).toBe(true);
    await settled(live);
    // Both tabs' reads carry the document, for the same object and section; the list of documents stays the unnarrowed read.
    expect(documentsRead(specification.mock.calls).at(-1)).toBe(SECTION_DOCUMENT_A);
    expect(reads().specification.at(-1)).toBe(A);
    expect(documentsRead(acceptedList.mock.calls)).toEqual([null, SECTION_DOCUMENT_A]);
    expect(sectionsRead().at(-1)).toBe('KJ');
    expect(replaceState).toHaveBeenLastCalledWith(null, '', `?section=KJ&project=${A}&document=${SECTION_DOCUMENT_A}`);

    // The object moves in the top strip: the document is forgotten, both tabs ask again for the whole object, the address says so.
    const before = specification.mock.calls.length;
    await live.update(page(client, `project=${B}&document=${SECTION_DOCUMENT_A}`));
    await settled(live);
    expect(specification.mock.calls.length).toBeGreaterThan(before);
    expect(documentsRead(specification.mock.calls).at(-1)).toBeNull();
    expect(reads().specification.at(-1)).toBe(B);
    expect(documentsRead(acceptedList.mock.calls).at(-1)).toBeNull();
    expect(replaceState).toHaveBeenLastCalledWith(null, '', `?section=KJ&project=${B}`);
  });

  it('forgets the document when the section changes too, and «Все документы раздела» lifts it', async () => {
    const client = freshClient();
    live = await mountLive(page(client, `project=${A}`));
    await settled(live);
    (globalThis as unknown as { window: Record<string, unknown> }).window.history = { replaceState };
    await live.change('Документ', SECTION_DOCUMENT_A);
    await settled(live);
    expect(documentsRead(specification.mock.calls).at(-1)).toBe(SECTION_DOCUMENT_A);
    await live.change('Раздел', 'AR');
    await settled(live);
    expect(sectionsRead().at(-1)).toBe('AR');
    expect(documentsRead(specification.mock.calls).at(-1)).toBeNull();
    expect(replaceState).toHaveBeenLastCalledWith(null, '', `?section=AR&project=${A}`);
    // And choosing «Все документы раздела» (the empty value) lifts a document that was chosen.
    await live.change('Документ', SECTION_DOCUMENT_A);
    await settled(live);
    expect(documentsRead(specification.mock.calls).at(-1)).toBe(SECTION_DOCUMENT_A);
    await live.change('Документ', '');
    await settled(live);
    expect(documentsRead(specification.mock.calls).at(-1)).toBeNull();
    expect(replaceState).toHaveBeenLastCalledWith(null, '', `?section=AR&project=${A}`);
  });
});
