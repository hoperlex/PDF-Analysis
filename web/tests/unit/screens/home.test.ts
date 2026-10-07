/**
 * `W50-HOME-01` — the home page at `/` (`W50-PLAN.md` §3.6).
 *
 * What is held here, each with the reason a screen-wide instrument cannot hold it:
 *
 *   - the greeting by the subject's `displayLabel`, from the props alone (no second `getMe`);
 *   - the role labels from `entities/account`, and an unknown role as a typed fault;
 *   - the administrator's tile, and **the requests the page makes**, for an expert-only and
 *     for an administrator's session — measured by running every query the page built against
 *     a recording `fetch`, so "never asks for `listRegistrations`" is a fact about requests and
 *     not about markup;
 *   - five projects, newest first, out of a cache that holds more;
 *   - the typed error state for a failed read, never the thrown message;
 *   - a 66-character `displayLabel` (a 60-letter last name, a space and `И. О.`) inside an
 *     element whose own rule breaks words — the markup half here; the browser half is the
 *     journey's width reading on the lane stand, quoted in `docs/program/W50-HOME-01.md`;
 *   - every branch rendered by some state, and no English in any of them. The language
 *     guard renders `/` only through the expert-only seed and the projects screen's cache
 *     keys, so the administrator's tile and the recent-projects branches are beyond it; this
 *     file is the coverage for those (`widgets/home-tiles/ui/copy.ts`).
 */

import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';

import type { QueryClient } from '@tanstack/react-query';
import { createElement } from 'react';
import type { ReactElement } from 'react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { HomePage } from '@/_pages/home';
import type { HomePageProps } from '@/_pages/home';
import pageStyles from '@/_pages/home/ui/home-page.module.css';
import { ROLE_LABELS } from '@/entities/account';
import type {
  DashboardSummary,
  ErrorCode,
  ErrorEnvelope,
  Project,
  ProjectPage,
  RegistrationRequestPage,
  Role,
} from '@/shared/api';
import { ApiError, RUN_STATE_VALUES, VERDICT_VALUES, queryKeys } from '@/shared/api';
import { SCREEN_REGISTRY } from '@/shared/config';
import { routes } from '@/shared/lib';
import {
  HOME_TILE_COPY,
  RECENT_PROJECT_LIMIT,
  REGISTRATIONS_SCREEN,
  recentProjects,
  registrationsScreenLink,
  summaryFigures,
} from '@/widgets/home-tiles';
import tileStyles from '@/widgets/home-tiles/ui/home-tiles.module.css';

import { newClient, renderScreen, seedError } from './harness';

// ============================================================================ fixtures

const LABEL = 'Петрова А. С.';
/** The longest name form: a 60-letter last name in one word, a space, and the initials. */
const LONGEST_LABEL = `${'Ж'.repeat(60)} И. О.`;

const EXPERT: readonly Role[] = ['expert'];
const ADMIN: readonly Role[] = ['expert', 'admin'];

const ULID_STEM = '01J9ZQ8K7NHVXW3T2R5M6P4Q8';

/** Seven projects, newest first, as `listProjects` answers. */
const PROJECTS: readonly Project[] = 'ABCDEFG'.split('').map((letter, index) => ({
  project_uid: `prj_${ULID_STEM}${letter}`,
  name: `Проект номер ${7 - index}`,
  created_at: `2026-09-${String(20 - index).padStart(2, '0')}T08:00:00.000Z`,
  document_count: index,
}));

const NO_NEXT = { next_cursor: null } as const;

function projectPage(items: readonly Project[]): ProjectPage {
  return { items: [...items], page: NO_NEXT };
}

function summary(over: Partial<DashboardSummary> = {}): DashboardSummary {
  return {
    documents_by_project: [
      { project_uid: PROJECTS[0]!.project_uid, name: 'Проект номер 7', document_count: 2 },
      { project_uid: PROJECTS[1]!.project_uid, name: 'Проект номер 6', document_count: 3 },
    ],
    findings_by_verdict: VERDICT_VALUES.map((verdict, index) => ({ verdict, count: index + 4 })),
    run_activity: {
      by_state: RUN_STATE_VALUES.map((state, index) => ({ state, count: index })),
    },
    section_breakdown: [{ document_count: 5 }],
    ...over,
  };
}

/** A pending request whose every personal field is a word this file then looks for. */
const APPLICANT = {
  created_user_uid: null,
  decided_at: null,
  decided_by: null,
  display_label: 'Секретова З. Я.',
  first_name: 'Зоя',
  last_name: 'Секретова',
  login: 'applicant@example.org',
  middle_name: 'Яковлевна',
  rejection_reason: 'Причина-которой-тут-не-место',
  request_id: `reg_${ULID_STEM}A`,
  status: 'pending',
  submitted_at: '2026-10-01T10:00:00.000Z',
} as const;

function registrationPage(pendingTotal: number): RegistrationRequestPage {
  return { items: pendingTotal > 0 ? [APPLICANT] : [], page: NO_NEXT, pending_total: pendingTotal };
}

const KEYS = {
  projects: queryKeys.projects.list(undefined, RECENT_PROJECT_LIMIT),
  summary: queryKeys.dashboard.summary(),
  registrations: queryKeys.registrations.list({ status: 'pending', limit: 1 }),
} as const;

const RAW_MESSAGE = 'Сырое сообщение сервера, которого на экране быть не должно';

function apiError(status: number, code: ErrorCode, retryable = false): ApiError {
  const envelope: ErrorEnvelope = {
    contract_version: '1.0.0-draft.1',
    error_code: code,
    message: RAW_MESSAGE,
    correlation_id: 'cid-home-1',
    retryable,
  };
  return new ApiError(status, envelope, 'cid-home-1');
}

function home(roles: readonly Role[], displayLabel = LABEL): ReactElement {
  const props: HomePageProps = { displayLabel, roles };
  return createElement(HomePage, props);
}

function draw(element: ReactElement, client: QueryClient = newClient()): string {
  return renderScreen(client, element);
}

/** A client in which every read the home page makes has answered. */
function loaded(over: { projects?: ProjectPage; summary?: DashboardSummary; pending?: number } = {}) {
  const client = newClient();
  client.setQueryData(KEYS.projects, over.projects ?? projectPage(PROJECTS.slice(0, 5)));
  client.setQueryData(KEYS.summary, over.summary ?? summary());
  client.setQueryData(KEYS.registrations, registrationPage(over.pending ?? 3));
  return client;
}

/** A client in which every read the home page makes has failed. */
function failed(error: unknown = apiError(503, 'dependency_unavailable', true)) {
  const client = newClient();
  for (const key of Object.values(KEYS)) seedError(client, key, error);
  return client;
}

/** The text a reader sees, one string per text node, with markup removed. */
function visibleText(markup: string): string[] {
  return [...markup.replace(/<code>[\s\S]*?<\/code>/g, ' ').matchAll(/>([^<>]+)</g)]
    .map((match) => (match[1] ?? '').replace(/&quot;/g, '"').replace(/&#x27;/g, "'").trim())
    .filter((text) => text.length > 0);
}

/** The `<tag …>` that opens the element carrying `attribute`. */
function openingTag(markup: string, attribute: string): string {
  const match = new RegExp(`<[a-z0-9]+[^>]*${attribute}[^>]*>`).exec(markup);
  expect(match, `no element carries ${attribute}`).not.toBeNull();
  return (match as RegExpExecArray)[0];
}

function declarations(cssPath: string, selector: string): string {
  const css = readFileSync(fileURLToPath(new URL(cssPath, import.meta.url)), 'utf8');
  const escaped = selector.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  return new RegExp(`(?:^|\\n)${escaped}\\s*\\{([^}]*)\\}`).exec(css)?.[1] ?? '';
}

const PAGE_CSS = '../../../src/_pages/home/ui/home-page.module.css';
const TILE_CSS = '../../../src/widgets/home-tiles/ui/home-tiles.module.css';

// ======================================================================= the greeting

describe('the greeting, from the subject the route hands down', () => {
  it('greets by displayLabel in one heading, without doubling the period the name ends with', () => {
    const markup = draw(home(EXPERT));
    expect(markup).toMatch(
      new RegExp(`<h1 class="am-page__title ${pageStyles.greeting}">Здравствуйте, ${LABEL.replace(/\./g, '\\.')}!</h1>`),
    );
    expect(markup).not.toMatch(/\.\./);
  });

  it('reads the account from the props alone: the page asks getMe nothing', () => {
    const client = newClient();
    draw(home(ADMIN), client);
    expect(client.getQueryCache().findAll({ queryKey: queryKeys.account.all() })).toEqual([]);
  });

  it('names the roles with the account entity’s labels', () => {
    expect(draw(home(EXPERT))).toContain(`Роли: ${ROLE_LABELS.expert}.`);
    expect(draw(home(['admin', 'expert']))).toContain(
      `Роли: ${ROLE_LABELS.expert}, ${ROLE_LABELS.admin}.`,
    );
    expect(draw(home(['admin']))).toContain(`Роли: ${ROLE_LABELS.admin}.`);
    expect(draw(home([]))).toContain('Роли не назначены.');
  });
});

describe('an unknown role is a typed fault, never a fallback label', () => {
  const UNKNOWN = ['expert', 'auditor'] as unknown as readonly Role[];

  it('shows the fault in place of the roles and the tiles', () => {
    const client = newClient();
    const markup = draw(home(UNKNOWN), client);
    expect(openingTag(markup, 'data-home-fault="closed-vocabulary"')).toBeTruthy();
    expect(markup).toContain('role="alert"');
    expect(markup).toContain('Учётная запись содержит неизвестную роль.');
    // Neither the value nor a word standing in for it, and no role sentence at all.
    expect(visibleText(markup).join('\n')).not.toContain('auditor');
    expect(markup).not.toContain('Роли:');
    expect(markup).not.toContain(ROLE_LABELS.expert);
    expect(markup).not.toContain('data-home-tile=');
    // The greeting stays: the name is not what is unknown.
    expect(markup).toContain(`Здравствуйте, ${LABEL}!`);
    // And the page asked nothing, the administrator's read least of all.
    expect(client.getQueryCache().getAll()).toEqual([]);
  });

  it('holds when the unknown value sits beside admin', () => {
    const client = newClient();
    const markup = draw(home(['admin', 'superuser'] as unknown as readonly Role[]), client);
    expect(markup).toContain('data-home-fault="closed-vocabulary"');
    expect(client.getQueryCache().findAll({ queryKey: queryKeys.registrations.all() })).toEqual([]);
  });
});

// =============================================== the administrator's tile, and the requests

/**
 * Every request the page makes, read by running each query it built against a `fetch` that
 * records the address. One render builds a query per read the page would make in a browser;
 * running them is what turns "the page holds a query" into "the page asks the API".
 */
async function requestsOf(element: ReactElement): Promise<string[]> {
  vi.stubEnv('NEXT_PUBLIC_API_BASE_URL', 'http://web.test/bff/v1');
  const requested: string[] = [];
  const answers: Record<string, unknown> = {
    '/bff/v1/projects': projectPage(PROJECTS.slice(0, 5)),
    '/bff/v1/dashboard': summary(),
    '/bff/v1/registrations': registrationPage(2),
  };
  vi.stubGlobal(
    'fetch',
    vi.fn(async (input: string, init: RequestInit) => {
      const url = new URL(input);
      requested.push(`${init.method ?? 'GET'} ${url.pathname}${url.search}`);
      return new Response(JSON.stringify(answers[url.pathname] ?? {}), {
        status: 200,
        headers: { 'content-type': 'application/json' },
      });
    }),
  );
  const client = newClient();
  draw(element, client);
  const settled = await Promise.allSettled(
    client.getQueryCache().getAll().map((query) => query.fetch()),
  );
  expect(settled.map((outcome) => outcome.status)).not.toContain('rejected');
  return requested.sort();
}

describe('the administrator’s tile, and what the page asks the API', () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    vi.unstubAllEnvs();
  });

  it('an expert-only session: no tile, and listRegistrations is never requested', async () => {
    const markup = draw(home(EXPERT), loaded());
    expect(markup).not.toContain('data-home-tile="registrations"');
    expect(markup).not.toContain('Заявки на регистрацию');
    expect(await requestsOf(home(EXPERT))).toEqual([
      'GET /bff/v1/dashboard',
      'GET /bff/v1/projects?limit=5',
    ]);
  });

  it('a session holding admin: the tile, and exactly one more request', async () => {
    const markup = draw(home(ADMIN), loaded());
    expect(markup).toContain('data-home-tile="registrations"');
    expect(markup).toContain('Заявки на регистрацию');
    expect(await requestsOf(home(ADMIN))).toEqual([
      'GET /bff/v1/dashboard',
      'GET /bff/v1/projects?limit=5',
      'GET /bff/v1/registrations?limit=1&status=pending',
    ]);
  });

  it('decides by admin alone, and an empty role set is not admin', async () => {
    expect(draw(home(['admin']), loaded())).toContain('data-home-tile="registrations"');
    expect(await requestsOf(home([]))).toEqual([
      'GET /bff/v1/dashboard',
      'GET /bff/v1/projects?limit=5',
    ]);
  });

  it('does not invent a link if the registration screen has no registry row', () => {
    const missing = SCREEN_REGISTRY.filter((screen) => screen.address !== REGISTRATIONS_SCREEN);
    expect(registrationsScreenLink(missing)).toBeNull();
  });

  it('links the live administrator tile to the registered requests screen', () => {
    expect(SCREEN_REGISTRY.map((screen): string => screen.address)).toContain(REGISTRATIONS_SCREEN);
    expect(registrationsScreenLink()).toBe(REGISTRATIONS_SCREEN);
    const markup = draw(home(ADMIN), loaded());
    const tile = markup.slice(markup.indexOf('data-home-tile="registrations"'));
    expect(tile.slice(0, tile.indexOf('</section>'))).toContain(`href="${REGISTRATIONS_SCREEN}"`);
  });
});

describe('the pending count', () => {
  it('is pending_total and nothing about any applicant', () => {
    const markup = draw(home(ADMIN), loaded({ pending: 3 }));
    expect(markup).toContain('data-pending-total="3"');
    const text = visibleText(markup).join('\n');
    for (const field of ['Секретова', 'Зоя', 'Яковлевна', 'applicant@example.org', 'Причина']) {
      expect(markup, field).not.toContain(field);
      expect(text, field).not.toContain(field);
    }
  });

  it('says so when nothing waits', () => {
    const markup = draw(home(ADMIN), loaded({ pending: 0 }));
    expect(markup).toContain(HOME_TILE_COPY.NO_PENDING_REGISTRATIONS_TITLE);
    expect(markup).not.toContain('data-pending-total');
  });

  it('a refusal is the error state, never the count of an earlier answer', () => {
    // A session whose admin role was taken away after sign-in: the cache still holds the
    // earlier answer, and the re-read was refused.
    const client = loaded({ pending: 7 });
    const query = client.getQueryCache().find({ queryKey: KEYS.registrations });
    query!.setState({
      status: 'error',
      error: apiError(403, 'permission_denied'),
      fetchStatus: 'idle',
      errorUpdatedAt: Date.now(),
      fetchFailureCount: 1,
    });
    const markup = draw(home(ADMIN), client);
    const tile = markup.slice(markup.indexOf('data-home-tile="registrations"'));
    const body = tile.slice(0, tile.indexOf('</section>'));
    expect(body).toContain('Вам не разрешено читать заявки на регистрацию.');
    expect(body).toContain('am-state--error');
    expect(body).not.toContain('data-pending-total');
    expect(body).not.toMatch(/>7</);
  });
});

// ==================================================================== recent projects

describe('the five most recent projects', () => {
  it('shows exactly five out of a cache holding seven, newest first, each linked through routes', () => {
    const client = loaded({ projects: projectPage(PROJECTS) });
    const markup = draw(home(EXPERT), client);
    expect(markup).toContain(`data-recent-project-count="${RECENT_PROJECT_LIMIT}"`);
    const links = [...markup.matchAll(/<a href="(\/projects\/prj_[^"]+)">([^<]+)<\/a>/g)];
    expect(links.map((link) => link[2])).toEqual(PROJECTS.slice(0, 5).map((project) => project.name));
    expect(links.map((link) => link[1])).toEqual(
      PROJECTS.slice(0, 5).map((project) => routes.project(project.project_uid)),
    );
    for (const project of PROJECTS.slice(5)) expect(markup).not.toContain(project.name);
    expect(recentProjects(projectPage(PROJECTS))).toEqual(PROJECTS.slice(0, 5));
  });

  it('asks the API for five, under the projects namespace', () => {
    expect(RECENT_PROJECT_LIMIT).toBe(5);
    expect(KEYS.projects).toEqual(['projects', 'list', { cursor: undefined, limit: 5 }]);
  });

  it('says so when there is no project', () => {
    const markup = draw(home(EXPERT), loaded({ projects: projectPage([]) }));
    expect(markup).toContain(HOME_TILE_COPY.NO_PROJECTS_TITLE);
    expect(markup).not.toContain('data-recent-project-count');
  });

  it('lets a long unbroken project name wrap inside its tile', () => {
    const name = 'Ш'.repeat(200);
    const markup = draw(
      home(EXPERT),
      loaded({ projects: projectPage([{ ...PROJECTS[0]!, name }]) }),
    );
    expect(markup).toMatch(new RegExp(`<li class="${tileStyles.project}"><a href="[^"]+">${name}</a>`));
    const rule = declarations(TILE_CSS, '.project');
    expect(rule).toMatch(/overflow-wrap\s*:\s*anywhere/);
    expect(rule).toMatch(/min-width\s*:\s*0/);
  });
});

// ======================================================================= the summary

describe('the summary tile', () => {
  it('shows four figures from the one dashboard read', () => {
    const markup = draw(home(EXPERT), loaded());
    const data = summary();
    const pending = data.findings_by_verdict.find((row) => row.verdict === 'pending')!.count;
    const runs = data.run_activity.by_state.reduce((sum, row) => sum + row.count, 0);
    expect(markup).toContain('data-summary-figure="projects">2<');
    expect(markup).toContain('data-summary-figure="documents">5<');
    expect(markup).toContain(`data-summary-figure="pending-findings">${pending}<`);
    expect(markup).toContain(`data-summary-figure="runs">${runs}<`);
    expect(markup).toContain('href="/dashboard"');
  });

  it('says when the deployment holds no project', () => {
    const markup = draw(home(EXPERT), loaded({ summary: summary({ documents_by_project: [] }) }));
    expect(markup).toContain('Сводка появится вместе с первым проектом.');
    expect(markup).not.toContain('data-summary-figure');
  });

  it('shows no partial count when a breakdown arrives incomplete', () => {
    const whole = summary();
    const incomplete: readonly DashboardSummary[] = [
      { ...whole, findings_by_verdict: whole.findings_by_verdict.slice(1) },
      {
        ...whole,
        findings_by_verdict: [
          ...whole.findings_by_verdict.slice(1),
          { verdict: 'verified' as DashboardSummary['findings_by_verdict'][number]['verdict'], count: 1 },
        ],
      },
      {
        ...whole,
        run_activity: { by_state: [...whole.run_activity.by_state.slice(1), whole.run_activity.by_state[1]!] },
      },
    ];
    for (const answer of incomplete) {
      expect(summaryFigures(answer)).toBeNull();
      const markup = draw(home(EXPERT), loaded({ summary: answer }));
      expect(markup).toContain('data-home-fault="incomplete"');
      expect(markup).toContain(HOME_TILE_COPY.INCOMPLETE_SUMMARY_TITLE);
      expect(markup).not.toContain('data-summary-figure');
    }
  });

  it('a failed getDashboardSummary renders the typed error state, not a raw message', () => {
    for (const [error, title] of [
      [apiError(503, 'dependency_unavailable', true), 'Зависимость, нужная сводке, недоступна.'],
      [apiError(500, 'internal_error'), 'Сводку прочитать не удалось.'],
      [new Error(RAW_MESSAGE), 'Сводку прочитать не удалось.'],
    ] as const) {
      const client = loaded();
      seedError(client, KEYS.summary, error);
      const markup = draw(home(EXPERT), client);
      const tile = markup.slice(markup.indexOf('data-home-tile="summary"'));
      const body = tile.slice(0, tile.indexOf('</section>'));
      expect(body).toContain('am-state--error');
      expect(body).toContain('role="alert"');
      expect(body).toContain(title);
      expect(body).not.toContain(RAW_MESSAGE);
      expect(body).not.toContain(error.message);
      expect(body).not.toContain('data-summary-figure');
    }
  });
});

// ============================================================ the longest name, 780 px

describe('a maximum-length displayLabel does not widen the page', () => {
  it('is the 66 characters the contract allows a name form to reach', () => {
    expect(LONGEST_LABEL).toHaveLength(66);
    expect(LONGEST_LABEL.split(' ')[0]).toHaveLength(60);
  });

  it('sits, whole, in a heading whose own rule breaks words, in a box that may shrink', () => {
    const markup = draw(home(ADMIN, LONGEST_LABEL), loaded());
    expect(markup).toContain(
      `<div class="${pageStyles.heading}"><h1 class="am-page__title ${pageStyles.greeting}">Здравствуйте, ${LONGEST_LABEL}!</h1>`,
    );
    const greeting = declarations(PAGE_CSS, '.greeting');
    expect(greeting).toMatch(/overflow-wrap\s*:\s*anywhere/);
    expect(greeting).toMatch(/min-width\s*:\s*0/);
    expect(declarations(PAGE_CSS, '.heading')).toMatch(/min-width\s*:\s*0/);
  });

  it('lays the tiles out in one column at the 780 px floor, each allowed to shrink', () => {
    const css = readFileSync(fileURLToPath(new URL(PAGE_CSS, import.meta.url)), 'utf8');
    expect(css).toMatch(
      /@media \(max-width: 780px\) \{\s*\.tiles \{\s*grid-template-columns: minmax\(0, 1fr\);/,
    );
    expect(declarations(TILE_CSS, '.tile')).toMatch(/min-width\s*:\s*0/);
  });
});

// ============================================== every branch rendered, none in English

describe('every branch is rendered by some state here, and none carries English', () => {
  const states: readonly { readonly name: string; readonly markup: () => string }[] = [
    { name: 'cold, expert', markup: () => draw(home(EXPERT)) },
    { name: 'cold, administrator', markup: () => draw(home(ADMIN)) },
    { name: 'loaded, administrator', markup: () => draw(home(ADMIN), loaded()) },
    {
      name: 'empty, administrator',
      markup: () =>
        draw(
          home(ADMIN),
          loaded({ projects: projectPage([]), summary: summary({ documents_by_project: [] }), pending: 0 }),
        ),
    },
    { name: 'unavailable, administrator', markup: () => draw(home(ADMIN), failed()) },
    { name: 'refused, administrator', markup: () => draw(home(ADMIN), failed(apiError(403, 'permission_denied'))) },
    { name: 'unsigned, administrator', markup: () => draw(home(ADMIN), failed(apiError(401, 'authentication_required'))) },
    { name: 'thrown, administrator', markup: () => draw(home(ADMIN), failed(new Error(RAW_MESSAGE))) },
    {
      name: 'incomplete summary',
      markup: () =>
        draw(home(EXPERT), loaded({ summary: summary({ findings_by_verdict: [] }) })),
    },
    { name: 'unknown role', markup: () => draw(home(['auditor'] as unknown as readonly Role[])) },
  ];
  const rendered = states.map((state) => ({ name: state.name, markup: state.markup() }));

  it('renders every word the language guard cannot reach', () => {
    const all = rendered.map((state) => state.markup).join('\n');
    const unreached = Object.entries(HOME_TILE_COPY)
      .map(([name, words]) => ({ name, words: name.endsWith('_LOADING') ? `Загрузка: ${words}…` : words }))
      .filter(({ words }) => !all.includes(words))
      .map(({ name }) => name);
    expect(Object.keys(HOME_TILE_COPY).length).toBeGreaterThan(5);
    expect(unreached).toEqual([]);
  });

  it('shows no Latin word but the two the product already prints', () => {
    // `UTC` closes every instant `formatInstant` prints; `API` is the subject of the shared
    // authentication sentence. Correlation ids sit in `<code>` and are removed above.
    const ALLOWED = new Set(['UTC', 'API']);
    for (const { name, markup } of rendered) {
      const latin = visibleText(markup)
        .flatMap((text) => text.match(/[A-Za-z]+/g) ?? [])
        .filter((word) => !ALLOWED.has(word));
      expect({ name, latin }).toEqual({ name, latin: [] });
    }
  });

  it('never prints a thrown message', () => {
    for (const { name, markup } of rendered) {
      expect({ name, raw: markup.includes(RAW_MESSAGE) }).toEqual({ name, raw: false });
    }
  });
});
