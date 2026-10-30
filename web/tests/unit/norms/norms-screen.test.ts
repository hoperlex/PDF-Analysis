/**
 * `W55A-WEB-NORMS` — «Нормы» as a reader meets it: the refusal before any snapshot is current,
 * a search and its results, a server refusal of a search, the sealed stub, and what an expert
 * and an administrator each see. Rendered in one static pass over seeded caches (no DOM), and
 * read off the markup and off the query cache — a query in the cache is a request the screen
 * would send.
 */

import { createElement } from 'react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

const jar = vi.hoisted(() => ({ value: null as string | null }));

vi.mock('next/headers', () => ({
  cookies: async () => ({
    get: (name: string) => (jar.value === null ? undefined : { name, value: jar.value }),
  }),
}));

import type { ErrorCode, ErrorEnvelope } from '@/shared/api';
import { ApiError, queryKeys } from '@/shared/api';
import { NormsPage } from '@/_pages/norms';
import { NORM_EVENT_PAGE_LIMIT, NORM_SEARCH_PAGE_LIMIT, NORM_SNAPSHOT_LIMIT } from '@/entities/norms';
import { forgetEverySession, openSession } from '@/app/bff/session/store';
import NormsRoute from '@/app/norms/page';
import NormDocumentRoute from '@/app/norms/document/page';

import { newClient, renderScreen, seedError } from '../screens/harness';
import {
  CURRENT_SNAPSHOT_ID, NORM_DOCUMENT_ID, NORM_EVENTS, NORM_HITS, NORM_QUERY, NORM_SNAPSHOTS,
  QUALIFIED_SNAPSHOT_ID,
} from './fixtures';

const SNAPSHOTS = queryKeys.norms.snapshots(undefined, NORM_SNAPSHOT_LIMIT);
const EVENTS = queryKeys.norms.events(undefined, NORM_EVENT_PAGE_LIMIT);
const SEARCH = queryKeys.norms.search(NORM_QUERY, undefined, NORM_SEARCH_PAGE_LIMIT);
const LAST = { next_cursor: null };

function refusal(status: number, code: ErrorCode, details: Record<string, string> = {}): ApiError {
  const envelope: ErrorEnvelope = {
    contract_version: '1.11.0',
    error_code: code,
    message: 'English the client never prints.',
    correlation_id: 'cid-norms-2',
    retryable: code === 'dependency_unavailable',
    details,
  };
  return new ApiError(status, envelope, 'cid-norms-2');
}

function clientWith(seed: (client: ReturnType<typeof newClient>) => void) {
  const client = newClient();
  seed(client);
  return client;
}

/** The second segment of every key the render put in the cache: what the screen asks for. */
function asked(client: ReturnType<typeof newClient>): string[] {
  return client.getQueryCache().getAll().map((query) => String(query.queryKey[1])).sort();
}

/** The search field's own tag, whatever order React writes its attributes in. */
function searchField(markup: string): string {
  return /<input[^>]*name="q"[^>]*>/.exec(markup)?.[0] ?? '';
}

function render(client: ReturnType<typeof newClient>, roles: readonly string[], query: string | null = null): string {
  return renderScreen(client, createElement(NormsPage, { roles, query }));
}

describe('before any snapshot is current, «Нормы» renders the refusal, never an empty list', () => {
  it('the snapshot list read whole with none current is the refusal, and no search is sent', () => {
    const client = clientWith((c) => c.setQueryData(SNAPSHOTS, { items: NORM_SNAPSHOTS.slice(1), page: LAST }));
    const markup = render(client, ['expert'], NORM_QUERY);
    expect(markup).toContain('data-norms-refusal="no_current_snapshot"');
    expect(markup).toContain('Текущий снимок норм не назначен');
    expect(markup).toContain('это отказ, а не пустой результат');
    expect(markup).not.toContain('Ничего не найдено');
    expect(markup).not.toMatch(/data-norm-hits=/);
    // The form says it cannot search now, and the screen sends nothing it knows is refused.
    expect(searchField(markup)).toContain('disabled=""');
    expect(asked(client)).toEqual(['snapshots']);
  });

  it('an empty snapshot list is the same refusal (the state before the corpus is loaded)', () => {
    const client = clientWith((c) => c.setQueryData(SNAPSHOTS, { items: [], page: LAST }));
    const markup = render(client, ['expert']);
    expect(markup).toContain('data-norms-refusal="no_current_snapshot"');
  });

  it('the server refusing a search (no current snapshot) renders the refusal, not an empty result', () => {
    const client = clientWith((c) => {
      c.setQueryData(SNAPSHOTS, { items: NORM_SNAPSHOTS, page: LAST });
      seedError(c, SEARCH, refusal(422, 'required_norm_unavailable', { reference_kind: 'norms_snapshot' }));
    });
    const markup = render(client, ['expert'], NORM_QUERY);
    expect(markup).toContain('data-norms-refusal="no_current_snapshot"');
    expect(markup).not.toContain('Ничего не найдено');
  });

  it('can fail: a current snapshot is not refused', () => {
    const client = clientWith((c) => c.setQueryData(SNAPSHOTS, { items: NORM_SNAPSHOTS, page: LAST }));
    const markup = render(client, ['expert'], NORM_QUERY);
    expect(markup).not.toContain('data-norms-refusal');
    expect(markup).toContain('data-norm-current="current"');
    expect(searchField(markup)).toMatch(/^<input/);
    expect(searchField(markup)).not.toContain('disabled=""');
    expect(asked(client)).toEqual(['search', 'snapshots']);
  });

  it('the sealed stub (503) is a failed read with its correlation id, not a refusal and not empty', () => {
    const client = clientWith((c) => seedError(c, SNAPSHOTS, refusal(503, 'dependency_unavailable', { dependency: 'norms_search' })));
    const markup = render(client, ['admin']);
    expect(markup).toContain('data-norms-snapshots-failure="dependency_unavailable"');
    expect(markup).toContain('Снимки норм не прочитаны');
    expect(markup).toContain('cid-norms-2');
    expect(markup).not.toContain('data-norms-refusal');
    expect(markup).not.toContain('English the client never prints');
  });
});

describe('a search and its results', () => {
  const loaded = () => clientWith((c) => {
    c.setQueryData(SNAPSHOTS, { items: NORM_SNAPSHOTS, page: LAST });
    c.setQueryData(SEARCH, { items: NORM_HITS, page: LAST });
  });

  it('names each result’s document, clause and page, marks the matched spans and says where the text came from', () => {
    const markup = render(loaded(), ['expert'], NORM_QUERY);
    expect(markup).toContain('data-norm-hits="2"');
    expect(markup).toContain('СП 54.13330.2022');
    expect(markup).toContain('п. 5.1 · ');
    expect(markup).toContain('<span data-norm-page="12">стр. 12</span>');
    expect(markup).toContain('<mark class="');
    expect(markup).toMatch(/<mark[^>]*>Высота<\/mark>/);
    expect(markup).toMatch(/<mark[^>]*>помещений<\/mark>/);
    expect(markup).toContain('Источник текста: КонсультантПлюс');
    expect(markup).toContain('Источник текста: не указан');
    // The search text is shown back in the field it came from.
    expect(markup).toContain(`value="${NORM_QUERY}"`);
  });

  it('«Открыть» opens the result’s document at the result’s PDF page', () => {
    const markup = render(loaded(), ['expert'], NORM_QUERY);
    expect(markup).toContain(`href="/norms/document?id=${NORM_DOCUMENT_ID}&amp;page=12"`);
    expect(markup).toContain(`href="/norms/document?id=${NORM_DOCUMENT_ID}&amp;page=13"`);
    expect(markup).toMatch(/>Открыть<\/a>/);
  });

  it('a search the timeout cancelled says it was too broad; a refused request says so', () => {
    const tooBroad = clientWith((c) => {
      c.setQueryData(SNAPSHOTS, { items: NORM_SNAPSHOTS, page: LAST });
      seedError(c, SEARCH, refusal(422, 'validation_failed', { constraint: 'norms_search_too_broad' }));
    });
    const broad = render(tooBroad, ['expert'], NORM_QUERY);
    expect(broad).toContain('data-norms-search-failure="search_too_broad"');
    expect(broad).toContain('Запрос слишком широкий');
    expect(broad).not.toContain('Ничего не найдено');
    const invalid = clientWith((c) => {
      c.setQueryData(SNAPSHOTS, { items: NORM_SNAPSHOTS, page: LAST });
      seedError(c, SEARCH, refusal(422, 'validation_failed'));
    });
    expect(render(invalid, ['expert'], NORM_QUERY)).toContain('data-norms-search-failure="validation_failed"');
  });

  it('a cold landing searches nothing: no address search, no request', () => {
    const client = loaded();
    const markup = render(client, ['expert'], null);
    expect(markup).not.toContain('data-norm-hits');
    expect(asked(client)).toEqual(['search', 'snapshots']); // the seeded search key only
    const cold = newClient();
    render(cold, ['expert'], null);
    expect(asked(cold)).toEqual(['snapshots']);
  });
});

describe('administrator controls are an administrator’s', () => {
  const seeded = () => clientWith((c) => {
    c.setQueryData(SNAPSHOTS, { items: NORM_SNAPSHOTS, page: LAST });
    c.setQueryData(EVENTS, { items: NORM_EVENTS, page: LAST });
  });

  it('an expert sees which snapshot search reads, and no list, no control and no history — nor asks for one', () => {
    const client = seeded();
    client.removeQueries({ queryKey: EVENTS });
    const markup = render(client, ['expert']);
    expect(markup).toContain('data-norm-current="current"');
    expect(markup).not.toContain('data-norms-administration');
    expect(markup).not.toContain('Сделать текущим');
    expect(markup).not.toContain('data-norm-snapshot=');
    expect(markup).not.toContain('История назначений');
    expect(asked(client)).toEqual(['snapshots']);
  });

  it('an administrator sees every snapshot, «Сделать текущим» only on a qualifying non-current one, and the history', () => {
    const client = seeded();
    const markup = render(client, ['admin']);
    expect(markup).toContain('data-norms-administration');
    expect(markup.match(/data-norm-snapshot="/g)).toHaveLength(NORM_SNAPSHOTS.length);
    expect(markup.match(/>Сделать текущим<\/button>/g)).toHaveLength(1);
    const qualifiedRow = markup.slice(markup.indexOf(`data-norm-snapshot="${QUALIFIED_SNAPSHOT_ID}"`));
    expect(qualifiedRow.slice(0, qualifiedRow.indexOf('</li>'))).toContain('Сделать текущим');
    const currentRow = markup.slice(markup.indexOf(`data-norm-snapshot="${CURRENT_SNAPSHOT_ID}"`));
    expect(currentRow.slice(0, currentRow.indexOf('</li>'))).not.toContain('Сделать текущим');
    // Each unqualified row says which half of the qualification is missing.
    expect(markup).toContain('поисковый индекс построен не полностью');
    expect(markup).toContain('не у всех документов подтверждена привязка к исходному PDF');
    expect(markup).toContain('data-norm-events="2"');
    expect(markup).toContain('Назначен первый текущий снимок');
    expect(asked(client)).toEqual(['events', 'snapshots']);
  });

  it('no control is offered while the current snapshot is beyond the page read', () => {
    const client = clientWith((c) => c.setQueryData(SNAPSHOTS, { items: NORM_SNAPSHOTS.slice(1), page: { next_cursor: 'Y3Vyc29y' } }));
    const markup = render(client, ['admin']);
    expect(markup).toContain('data-norm-current="beyond"');
    expect(markup).not.toContain('>Сделать текущим</button>');
  });
});

describe('who the routes let in (R-80)', () => {
  const ACCOUNT = {
    login: 'petrova@example.org',
    displayLabel: 'Петрова А. С.',
    initials: 'ПА',
    isDefaultCredential: false,
    profileComplete: true,
  };

  beforeEach(() => forgetEverySession());
  afterEach(() => {
    forgetEverySession();
    jar.value = null;
  });

  async function landing(route: (props: object) => Promise<unknown>, searchParams: object): Promise<string> {
    try {
      await route({ searchParams: Promise.resolve(searchParams) });
    } catch (thrown) {
      return String((thrown as { digest?: unknown }).digest ?? '').split(';')[2] ?? '';
    }
    return 'opened';
  }

  it('a role-less session is sent to /403 from both addresses, before any read', async () => {
    jar.value = openSession({ ...ACCOUNT, roles: [] }, 'a-credential', 3600);
    expect(await landing(NormsRoute, {})).toMatch(/^\/403\?from=%2Fnorms$/);
    expect(await landing(NormDocumentRoute, { id: NORM_DOCUMENT_ID })).toMatch(/^\/403\?from=%2Fnorms%2Fdocument/);
  });

  it('a guest is sent to sign in; an expert and an administrator open both', async () => {
    expect(await landing(NormsRoute, {})).toBe('/login?next=%2Fnorms');
    for (const roles of [['expert'], ['admin']] as const) {
      jar.value = openSession({ ...ACCOUNT, roles }, 'a-credential', 3600);
      expect(await landing(NormsRoute, { q: 'СП 54' })).toBe('opened');
      expect(await landing(NormDocumentRoute, { id: NORM_DOCUMENT_ID, page: '12' })).toBe('opened');
    }
  });
});
