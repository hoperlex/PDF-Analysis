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

import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { renderToStaticMarkup } from 'react-dom/server';
import { createElement } from 'react';
import { describe, expect, it } from 'vitest';

import { ApiError, queryKeys } from '@/shared/api';
import type { DocumentAudit, DocumentVersion } from '@/shared/api';
import { DOCUMENT_PAGE_LIMIT } from '@/entities/document-version';
import { SectionBatchBar, SectionDetailPage, SectionHeader, SectionSelectionBar } from '@/_pages/section-detail';
import type { ListingWalk } from '@/_pages/section-detail';
import { auditTally } from '@/entities/document-version';
import { findProjectSection } from '@/entities/project';
import type { ProjectSection } from '@/entities/project';
import type { BatchSelection } from '@/widgets/project-sections';

import { WEB_ROOT } from '../../guards/lib/repo';
import { parseRules } from '../styles/contrast';
import { newClient, renderWith, seedError } from '../screens/harness';
import { PROJECT_UID, classification, otherVersion, page, version } from './fixtures';

/** The declarations of every rule whose selector list names `selector`, the later rule winning, as the cascade has it. */
function declared(css: string, selector: string): ReadonlyMap<string, string> {
  const merged = new Map<string, string>();
  for (const rule of parseRules(css, 'module')) {
    if (!rule.selector.split(',').some((part) => part.trim() === selector)) continue;
    for (const [property, value] of rule.declarations) merged.set(property, value);
  }
  return merged;
}

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
    expect(markup).not.toContain('data-listing-walk');
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
    expect(markup).toContain('data-listing-walk="pending"');
    expect(markup).toContain('Читаю все страницы раздела');
    // `UIP-DEBT-02`: the walk is one, and so is the line that says it is being read — the groups and the choosing share it.
    expect(markup.match(/Читаю все страницы раздела/g)).toHaveLength(1);
    expect(markup.match(/data-listing-walk=/g)).toHaveLength(1);
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
      contract_version: '1.60.0', error_code: 'dependency_unavailable',
      message: 'Сообщение об отказе.', correlation_id: correlation, retryable: false,
    }, correlation));
    const markup = render(client);
    expect(markup).toContain('data-listing-walk="failed"');
    expect(markup).toContain('Не удалось прочитать все страницы раздела: группы не показаны, выбрать документы целиком пока нельзя.');
    expect(markup).toContain('>Повторить</button>');
    // `UIP-DEBT-02`: one line and one «Повторить» for the one walk, not one for the groups and one for the choosing.
    expect(markup.match(/Не удалось прочитать все страницы раздела/g)).toHaveLength(1);
    expect(markup.match(/>Повторить<\/button>/g)).toHaveLength(1);
    expect(markup.match(/data-listing-walk=/g)).toHaveLength(1);
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
    expect(markup).toContain('data-select-all="2"');
    expect(markup).toContain('title="Документов, которые не запускались: 1"');
    expect(markup).not.toContain('data-listing-walk');
    expect(documentKeys(client)).toHaveLength(1);
  });

  it('draws no row at all where no document can be started', () => {
    const client = newClient();
    client.setQueryData(key(undefined), page([version()], null));
    const markup = render(client);
    expect(markup).not.toContain('data-select-all');
    expect(markup).not.toContain('data-listing-walk');
  });
});

describe('a session that cannot start an audit', () => {
  it('draws no choice; it still reads the whole listing, for the groups (`UIP-S02-06`), which every reader is shown', () => {
    const client = newClient();
    client.setQueryData(queryKeys.account.me(), { roles: ['admin'] });
    client.setQueryData(key(undefined), page(FIRST_PAGE, 'c2'));
    const markup = render(client);
    expect(markup).not.toContain('data-select-all');
    expect(markup).not.toContain('Выделить необработанные');
    expect(markup).not.toContain('data-tally-select');
    // the number and the plaques are still read: a viewer sees the section's figures
    expect(markup).toContain('data-section-count="2"');
    // `UIP-S02-06`: this test said «reads no page beyond the one in view» while only «Выбрать все» needed the whole listing. The groups are
    // made of the whole listing and are shown to everyone, so the second page is read for a viewer too (here it is being read).
    expect(documentKeys(client)).toHaveLength(2);
    expect(markup).toContain('data-listing-walk="pending"');
    expect(markup.match(/Читаю все страницы раздела/g)).toHaveLength(1);
  });

  it('is told, when a page could not be read, that the groups are not shown and nothing of choosing, with one «Повторить»', () => {
    const client = newClient();
    client.setQueryData(queryKeys.account.me(), { roles: ['admin'] });
    client.setQueryData(key(undefined), page(FIRST_PAGE, 'c2'));
    const correlation = '0f0e9d8c-7b6a-4948-b726-150413021100';
    seedError(client, key('c2'), new ApiError(503, {
      contract_version: '1.60.0', error_code: 'dependency_unavailable',
      message: 'Сообщение об отказе.', correlation_id: correlation, retryable: false,
    }, correlation));
    const markup = render(client);
    expect(markup).toContain('Не удалось прочитать все страницы раздела: группы не показаны.');
    expect(markup).not.toContain('выбрать документы целиком');
    expect(markup.match(/>Повторить<\/button>/g)).toHaveLength(1);
  });
});

describe('the header and the row over the cards on their own', () => {
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

  it('keeps the start out of the row over the cards: the row has the words about the reading and the panel, and no button to start', () => {
    expect(bar({ status: 'complete', items: WHOLE }, 5)).not.toContain('Запустить');
    expect(bar({ status: 'pending' }, 5)).toContain('data-listing-walk="pending"');
    expect(bar({ status: 'pending' }, 5)).not.toContain('Запустить');
  });
});

// ------------------------------------------------------------------ the bar at the bottom (UIP-S02-03)

describe('the bottom bar of the chosen documents', () => {
  const chosen = (chosenCount: number, over: Partial<BatchSelection> = {}): BatchSelection => ({
    selection: { selected: new Set<string>(), onToggle: () => undefined },
    chosenCount, batch: null, choose: () => undefined, clear: () => undefined, openBatch: () => undefined, closeBatch: () => undefined, ...over,
  });
  const bar = (selection: BatchSelection) => renderToStaticMarkup(createElement(SectionSelectionBar, { selection }));

  it('says how many are chosen and offers to start all of them and to clear the choice, in that order', () => {
    const markup = bar(chosen(5));
    expect(markup).toContain('role="region"');
    expect(markup).toContain('aria-label="Выбранные документы"');
    expect(markup).toMatch(/<span[^>]*role="status"[^>]*>Выбрано: 5<\/span>/);
    expect(markup).toMatch(/<button type="button"[^>]*data-batch-start[^>]*>Запустить все \(5\)<\/button>/);
    expect(markup).toMatch(/<button type="button"[^>]*data-clear-selection[^>]*>Снять выделение<\/button>/);
    expect(markup.indexOf('Выбрано: 5')).toBeLessThan(markup.indexOf('Запустить все'));
    expect(markup.indexOf('Запустить все')).toBeLessThan(markup.indexOf('Снять выделение'));
    expect(markup).toContain('data-batch-selection="5"');
  });

  it('is drawn only while something is chosen', () => {
    expect(bar(chosen(0))).toBe('');
  });

  it('is drawn for whoever may start an audit and for no one else, nor while the batch panel holds the choice', () => {
    // `selection` is `undefined` for a session that cannot start an audit, and while the panel is open
    expect(bar(chosen(5, { selection: undefined }))).toBe('');
  });

  it('is the last thing of the page and the page keeps room under the cards while it is drawn', () => {
    const page = readFileSync(join(WEB_ROOT, 'src/_pages/section-detail/ui/section-detail-page.tsx'), 'utf8');
    const body = page.slice(page.indexOf('{body}'));
    // `UIP-S02-04`: it is given what its actions act on (`scope`); it is still the one bar, at the end of the page.
    expect(body).toMatch(/<SectionSelectionBar selection=\{batch\} scope=\{\{ projectUid, /);
    expect(body.slice(body.indexOf('<SectionSelectionBar'))).not.toMatch(/<DocumentCardGrid|<Section(?:Header|BatchBar)/);
    expect(page).toContain("batch.chosenCount > 0 ? `am-section ${styles.reserve}` : 'am-section'");
    const css = readFileSync(join(WEB_ROOT, 'src/_pages/section-detail/ui/section-detail-page.module.css'), 'utf8');
    expect(declared(css, '.reserve').get('padding-bottom')).toBe('var(--am-gap-lg)');
  });

  it('sticks to the bottom of the area, under the sticky strip, with tokens only', () => {
    const css = readFileSync(join(WEB_ROOT, 'src/_pages/section-detail/ui/section-selection-bar.module.css'), 'utf8');
    const rule = declared(css, '.bar');
    expect(rule.get('position')).toBe('sticky');
    expect(rule.get('bottom')).toBe('0');
    // the strip at the top is 9 (`.am-app__utility`); a dialog is in the top layer
    expect(Number(rule.get('z-index'))).toBeLessThan(9);
    expect(Number(rule.get('z-index'))).toBeGreaterThan(0);
    for (const property of ['padding', 'margin-top', 'gap']) expect(rule.get(property), property).toMatch(/^var\(--am-gap/);
  });

  it('can fail: a bar that is not sticky, or sits above the strip, is read as such', () => {
    const wrong = declared('.bar { position: static; bottom: 0; z-index: 40; }', '.bar');
    expect(wrong.get('position')).not.toBe('sticky');
    expect(Number(wrong.get('z-index'))).toBeGreaterThan(9);
  });
});
