/**
 * `UI-A-35`, `UIP-S02-01`: the box «выбрать все», «Выделить необработанные» and the plaque «ждут решения N» in the section's header
 * choose across the whole listing in view.
 *
 * They chose the cards of the page in front of the reader — up to fifty — and said nothing of the rest. The listing is paged by
 * the server's cursor, so a section of more pages is read to its end through the same listing the document page's «N из M» walks;
 * the controls carry the count over all of it, wait while pages are read, say so when one cannot be read, and carry the page's own
 * narrowing (`?filter=not_run`) instead of reading the section unfiltered. A section that fits one page reads nothing more.
 *
 * Rendered, not read from source (`D-53`): one pass over a seeded cache, which is enough for the walk to follow the cursors
 * the seeded pages name.
 */

import { renderToStaticMarkup } from 'react-dom/server';
import { createElement } from 'react';
import { describe, expect, it } from 'vitest';

import { ApiError, queryKeys } from '@/shared/api';
import type { DocumentAudit, DocumentVersion } from '@/shared/api';
import { DOCUMENT_PAGE_LIMIT } from '@/entities/document-version';
import { SectionBatchBar, SectionDetailPage, SectionHeader } from '@/_pages/section-detail';
import type { ListingWalk } from '@/_pages/section-detail';
import { auditTally } from '@/entities/document-version';
import { findProjectSection } from '@/entities/project';
import type { ProjectSection } from '@/entities/project';
import type { BatchSelection } from '@/widgets/project-sections';

import { newClient, renderWith, seedError } from '../screens/harness';
import { PROJECT_UID, classification, otherVersion, page, version } from './fixtures';

const key = (cursor: string | undefined, state?: DocumentAudit['state']) =>
  queryKeys.projects.documents(PROJECT_UID, cursor, DOCUMENT_PAGE_LIMIT, 'AR', false, undefined, state, 'audit');

const audit = (state: DocumentAudit['state']): DocumentAudit => ({ state, partial: false, finding_count: 0, undecided_finding_count: 0 });
const inAr = (suffix: string, state: DocumentAudit['state']): DocumentVersion =>
  otherVersion(suffix, { classification: classification({ section_code: 'AR' }), audit: audit(state) });

const FIRST_PAGE = [inAr('A', 'not_run'), inAr('B', 'checked')];
const SECOND_PAGE = [inAr('C', 'not_run'), inAr('D', 'not_run'), inAr('E', 'clean')];

function render(client = newClient(), filter?: string): string {
  return renderWith(client, createElement(SectionDetailPage, { projectUid: PROJECT_UID, sectionCode: 'AR', filter }));
}

function seededTwoPages() {
  const client = newClient();
  client.setQueryData(key(undefined), page(FIRST_PAGE, 'c2'));
  client.setQueryData(key('c2'), page(SECOND_PAGE, null));
  return client;
}

function documentKeys(client: ReturnType<typeof newClient>): readonly string[] {
  return client.getQueryCache().getAll().map((query) => JSON.stringify(query.queryKey)).filter((text) => text.includes('"documents"'));
}

describe('a section of more than one page', () => {
  it('counts the controls over every page, not the fifty in view', () => {
    const markup = render(seededTwoPages());
    expect(markup).toContain('data-batch-scope="section"');
    expect(markup).toContain('data-select-all="5"');
    expect(markup).toContain('aria-label="Выбрать все документы раздела: 5"');
    expect(markup).toContain('title="Документов, которые не запускались: 3"');
    // The cards in view are the first page's; only the choice reaches further.
    expect(markup).toContain('data-document-cards="2"');
  });

  it('waits while a page is being read, and says so, and chooses nothing yet', () => {
    const client = newClient();
    client.setQueryData(key(undefined), page(FIRST_PAGE, 'c2'));
    const markup = render(client);
    expect(markup).toContain('data-batch-walk="pending"');
    expect(markup).toContain('Читаю все страницы раздела');
    expect(markup).toContain('data-select-all="waiting"');
    expect(markup).toMatch(/<input[^>]*aria-label="Выбрать все документы раздела"[^>]*disabled=""/);
    expect(markup).toMatch(/<button[^>]*disabled=""[^>]*>Выделить необработанные<\/button>/);
    expect(markup).not.toContain('Выбрать все документы раздела:');
  });

  it('says a page it could not read is the reason it chose nothing, and offers to try again', () => {
    const client = newClient();
    client.setQueryData(key(undefined), page(FIRST_PAGE, 'c2'));
    const correlation = '0f0e9d8c-7b6a-4948-b726-150413021100';
    seedError(client, key('c2'), new ApiError(503, {
      contract_version: '1.56.0', error_code: 'dependency_unavailable',
      message: 'Сообщение об отказе.', correlation_id: correlation, retryable: false,
    }, correlation));
    const markup = render(client);
    expect(markup).toContain('data-batch-walk="failed"');
    expect(markup).toContain('Не удалось прочитать все страницы раздела');
    expect(markup).toContain('>Повторить</button>');
    expect(markup).toContain('data-select-all="waiting"');
    expect(markup).not.toContain('Выбрать все документы раздела:');
  });

  it('follows the narrowing of the page: the walk of «не запускались» is the listing «не запускались», not the section', () => {
    const client = newClient();
    client.setQueryData(key(undefined, 'not_run'), page([inAr('A', 'not_run')], 'c2'));
    client.setQueryData(key('c2', 'not_run'), page([inAr('C', 'not_run'), inAr('D', 'not_run')], null));
    const markup = render(client, 'not_run');
    expect(markup).toContain('data-select-all="3"');
    // Every document read is under the narrowed key; the unfiltered listing was not asked for.
    expect(documentKeys(client).every((text) => text.includes('not_run'))).toBe(true);
  });
});

describe('a section that fits one page', () => {
  it('counts the page, reads no further page and says it is the page', () => {
    const client = newClient();
    client.setQueryData(key(undefined), page(FIRST_PAGE, null));
    const markup = render(client);
    expect(markup).toContain('data-batch-scope="page"');
    expect(markup).toContain('data-select-all="2"');
    expect(markup).toContain('title="Документов, которые не запускались: 1"');
    expect(markup).not.toContain('data-batch-walk');
    expect(documentKeys(client)).toHaveLength(1);
  });

  it('draws no row at all where no document can be started', () => {
    const client = newClient();
    client.setQueryData(key(undefined), page([version()], null));
    expect(render(client)).not.toContain('data-batch-controls');
  });
});

describe('a session that cannot start an audit', () => {
  it('reads no page beyond the one in view and draws no choice', () => {
    const client = newClient();
    client.setQueryData(queryKeys.account.me(), { roles: ['admin'] });
    client.setQueryData(key(undefined), page(FIRST_PAGE, 'c2'));
    const markup = render(client);
    expect(markup).not.toContain('data-batch-controls');
    expect(markup).not.toContain('data-select-all');
    expect(markup).not.toContain('Выделить необработанные');
    expect(markup).not.toContain('data-tally-select');
    // the number and the plaques are still read: a viewer sees the section's figures
    expect(markup).toContain('data-section-count="2"');
    expect(documentKeys(client)).toHaveLength(1);
  });
});

describe('the header and the start row on their own', () => {
  const selection: BatchSelection = {
    selection: { selected: new Set<string>(), onToggle: () => undefined },
    chosenCount: 0, batch: null, choose: () => undefined, clear: () => undefined, openBatch: () => undefined, closeBatch: () => undefined,
  };
  const SECTION = findProjectSection('AR') as ProjectSection;
  const header = (walk: ListingWalk, chosen = 0, chosenIds: readonly string[] = []) =>
    renderToStaticMarkup(createElement(SectionHeader, {
      projectUid: PROJECT_UID, section: SECTION, documents: FIRST_PAGE, walk,
      tally: auditTally(walk.status === 'complete' ? walk.items : FIRST_PAGE), partial: false,
      selection: { ...selection, selection: { selected: new Set(chosenIds), onToggle: () => undefined }, chosenCount: chosen },
      addHref: '/x#upload', refreshing: false, onRefresh: () => undefined,
    }));
  const bar = (walk: ListingWalk, chosen = 0) =>
    renderToStaticMarkup(createElement(SectionBatchBar, {
      projectUid: PROJECT_UID, selection: { ...selection, chosenCount: chosen }, pageDocuments: FIRST_PAGE, walk,
    }));
  const WHOLE = [...FIRST_PAGE, ...SECOND_PAGE];

  it('counts a completed walk, whole', () => {
    const markup = header({ status: 'complete', items: WHOLE });
    expect(markup).toContain('data-select-all="5"');
    expect(markup).toContain('title="Документов, которые не запускались: 3"');
  });

  it('chooses the documents that wait for a decision from the whole listing, and says how many', () => {
    const waiting = inAr('F', 'awaiting_decision');
    const markup = header({ status: 'complete', items: [...WHOLE, waiting] });
    expect(markup).toContain('title="Выбрать документы, которые ждут решения: 1"');
    expect(markup).toContain('aria-pressed="false"');
  });

  it('shows the box on, the plaque pressed and «Снять выделение» once every one of them is chosen', () => {
    const waiting = inAr('F', 'awaiting_decision');
    const everyone = [...WHOLE, waiting];
    const none = header({ status: 'complete', items: everyone }, 0);
    expect(none).not.toContain('Снять выделение');
    expect(none).not.toMatch(/<input[^>]*type="checkbox"[^>]*checked=""/);
    const all = header({ status: 'complete', items: everyone }, 6, everyone.map((version) => version.version_uid));
    expect(all).toMatch(/<input[^>]*type="checkbox"[^>]*checked=""/);
    expect(all).toContain('>Снять выделение<');
    const only = header({ status: 'complete', items: everyone }, 1, [waiting.version_uid]);
    expect(only).toContain('aria-pressed="true"');
    expect(only).not.toMatch(/<input[^>]*type="checkbox"[^>]*checked=""/);
  });

  it('leaves out «Выделить необработанные» when the whole listing has none', () => {
    const markup = header({ status: 'complete', items: [inAr('B', 'checked'), inAr('E', 'clean')] });
    expect(markup).toContain('data-select-all="2"');
    expect(markup).not.toContain('Выделить необработанные');
  });

  it('starts the chosen ones from the row, and says nothing of starting while none is chosen', () => {
    expect(bar({ status: 'complete', items: WHOLE }, 5)).toContain('Запустить аудит (5)');
    expect(bar({ status: 'complete', items: WHOLE }, 0)).not.toContain('Запустить аудит');
  });
});
