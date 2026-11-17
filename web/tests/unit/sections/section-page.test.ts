/**
 * «Раздел» — one section of one project (`R-151l`), its documents as cards (`R-151s`).
 *
 * The page reads `listDocuments` with `section_code` (contract 1.20.0): its cache entry is keyed by the section,
 * so it never shows another section's or the whole project's page. It refuses a malformed address itself, without
 * a request. Over the cards stands one line (`UIP-S02-01`): the arrow to the object's «Главная», the section, «(N)» with the box,
 * the plaques, the choosing buttons and, at the right, «+ Добавить» and «Обновить»; there is no second line of crumbs.
 */

import { createElement } from 'react';
import { describe, expect, it } from 'vitest';

import { queryKeys } from '@/shared/api';
import { routes } from '@/shared/lib';
import { DOCUMENT_PAGE_LIMIT, documentListQueryOptions } from '@/entities/document-version';
import { SectionDetailPage, objectHomeHref } from '@/_pages/section-detail';

import { newClient, renderWith } from '../screens/harness';
import { PROJECT_UID, classification, otherVersion, page, version } from './fixtures';

// `UI-PARITY-DOC-AUDIT`: the page reads the listing in the server's audit order, a listing of its own in the cache.
const SECTION_KEY = queryKeys.projects.documents(PROJECT_UID, undefined, DOCUMENT_PAGE_LIMIT, 'AR', false, undefined, undefined, 'audit');

function seeded(items: ReturnType<typeof version>[], nextCursor: string | null = null) {
  const client = newClient();
  client.setQueryData(SECTION_KEY, page(items, nextCursor));
  return client;
}

const AR_ONE = version({ classification: classification({ section_code: 'AR' }) });
const AR_TWO = otherVersion('B', { version_ordinal: 3, classification: classification({ section_code: 'AR' }) });

describe('the section page', () => {
  it('keys its read by the section, apart from the project page’s own list', () => {
    const options = documentListQueryOptions(PROJECT_UID, undefined, 'AR', false, undefined, { order: 'audit' });
    expect(options.queryKey).toEqual(SECTION_KEY);
    expect(options.queryKey).not.toEqual(queryKeys.projects.documents(PROJECT_UID, undefined, DOCUMENT_PAGE_LIMIT));
  });

  it('draws each document of the section as a card: number, title, version link and history', () => {
    const markup = renderWith(seeded([AR_ONE, AR_TWO]), createElement(SectionDetailPage, { projectUid: PROJECT_UID, sectionCode: 'AR' }));
    expect(markup).toContain('data-document-cards="2"');
    expect(markup).toContain('>V1<');
    expect(markup).toContain('>V3<');
    expect(markup).toContain(`href="/projects/${PROJECT_UID}/versions/${AR_ONE.version_uid}"`);
    expect(markup).toContain(`href="/projects/${PROJECT_UID}/documents/${AR_TWO.document_uid}"`);
    expect((markup.match(/>все версии</g) ?? []).length).toBe(2);
  });

  it('names the section in the heading, with its code, its name and the dot of its colour, and draws no strip of crumbs', () => {
    const markup = renderWith(seeded([AR_ONE]), createElement(SectionDetailPage, { projectUid: PROJECT_UID, sectionCode: 'AR' }));
    // `UIP-S02-01`: the heading holds the dot, the code and the name; the strip «Объект › АР …» of the document frame is gone.
    expect(markup).toMatch(/<h1[^>]*><span[^>]*data-section-dot="AR"[^>]*><\/span><span[^>]*>АР<\/span><span[^>]*>Архитектурные решения<\/span><\/h1>/);
    expect(markup).not.toContain('data-context-level');
    expect(markup).not.toContain('aria-label="Где вы находитесь"');
    expect(markup).not.toContain('Объекты');
  });

  it('has one line over the cards: the arrow, the heading, the number, the box and the actions, in that order', () => {
    const markup = renderWith(seeded([AR_ONE, AR_TWO]), createElement(SectionDetailPage, { projectUid: PROJECT_UID, sectionCode: 'AR' }));
    const header = markup.slice(markup.indexOf('data-section-header'), markup.indexOf('data-section-page'));
    const at = (needle: string) => header.indexOf(needle);
    expect(at('data-section-back')).toBeGreaterThan(-1);
    const order = ['data-section-back', '<h1', 'data-section-count', 'data-select-all', 'data-audit-tally', 'data-select-not-run', 'data-section-add', '>Обновить<'];
    const present = order.filter((needle) => at(needle) >= 0);
    expect(present.map(at)).toEqual([...present.map(at)].sort((a, b) => a - b));
    expect(present).toContain('data-section-count');
    expect(present).toContain('>Обновить<');
    // the cards come after the line, and the document count is the number in the line, not a plaque of its own
    expect(markup.indexOf('data-section-header')).toBeLessThan(markup.indexOf('data-document-cards'));
    expect(markup).toContain('data-section-count="2"');
    expect(markup).toMatch(/>\(2\)</);
    expect(markup).not.toContain('data-tally="documents"');
    expect(markup).not.toMatch(/>2<\/span> документа/);
  });

  it('leads the arrow to the «Главная» of this object, with the object kept in the address', () => {
    const markup = renderWith(seeded([AR_ONE]), createElement(SectionDetailPage, { projectUid: PROJECT_UID, sectionCode: 'AR' }));
    const arrow = /<a [^>]*data-section-back[^>]*>/.exec(markup)?.[0] ?? '';
    expect(arrow).toContain(`href="/?project=${PROJECT_UID}"`);
    expect(arrow).toContain('aria-label="На главную объекта"');
    expect(objectHomeHref(PROJECT_UID)).toBe(`/?project=${PROJECT_UID}`);
  });

  it('names the object on the arrow once its name is known, read by identity', () => {
    const client = seeded([AR_ONE]);
    client.setQueryData(queryKeys.projects.detail(PROJECT_UID), { project_uid: PROJECT_UID, name: 'Школа', created_at: '2026-09-10T08:00:00.000Z' });
    const markup = renderWith(client, createElement(SectionDetailPage, { projectUid: PROJECT_UID, sectionCode: 'AR' }));
    expect(markup).toContain('aria-label="На главную объекта «Школа»"');
  });

  it('says an empty section is empty, and offers the way back to the project', () => {
    const markup = renderWith(seeded([]), createElement(SectionDetailPage, { projectUid: PROJECT_UID, sectionCode: 'AR' }));
    expect(markup).toContain('В этом разделе пока нет документов.');
    expect(markup).toContain('К разделам объекта');
  });

  it('pages forward when the server has more', () => {
    const markup = renderWith(seeded([AR_ONE], 'next'), createElement(SectionDetailPage, { projectUid: PROJECT_UID, sectionCode: 'AR' }));
    expect(markup).toContain('>Далее<');
    expect(markup).not.toContain('>Назад<');
  });

  it('refuses a malformed project or an unknown section without a request', () => {
    for (const props of [
      { projectUid: 'это-не-идентификатор', sectionCode: 'AR' },
      { projectUid: PROJECT_UID, sectionCode: 'ZZ' },
    ]) {
      const client = newClient();
      const markup = renderWith(client, createElement(SectionDetailPage, props));
      expect(markup).toContain('Это не адрес раздела.');
      expect(client.getQueryCache().getAll()).toHaveLength(0);
    }
  });
});

// ------------------------------------------------------------------ the original's section page, in full

describe('the section page keeps the original’s controls', () => {
  const render = (items = [AR_ONE, AR_TWO]) =>
    renderWith(seeded(items), createElement(SectionDetailPage, { projectUid: PROJECT_UID, sectionCode: 'AR' }));

  it('opens the grid with the Σ card «Оптимизация раздела», a control of the section and not a document', () => {
    const markup = render();
    expect(markup).toContain('data-grid-leading');
    expect(markup).toContain('Оптимизация раздела');
    const escaped = routes.sectionOptimisation('AR', PROJECT_UID).replace(/&/g, '&amp;');
    expect(markup).toContain(`href="${escaped}"`);
    // two documents, two document cards: the Σ card is counted in no figure
    expect(markup).toContain('data-document-cards="2"');
    expect(markup.indexOf('data-grid-leading')).toBeLessThan(markup.indexOf('data-document-uid'));
  });

  it('offers a box on each startable card and one in the line that chooses all, and the start only once something is chosen', () => {
    const markup = render();
    expect((markup.match(/type="checkbox"/g) ?? []).length).toBe(2 + 1 + 1); // two cards, the line's box and «Показать архивные»
    expect(markup).toContain('data-select-all="2"');
    expect(markup).toContain('aria-label="Выбрать все документы раздела: 2"');
    expect(markup).not.toContain('Запустить аудит (');
    expect(markup).not.toContain('Снять выделение');
  });

  it('draws no box for a document whose section is not confirmed, and no box in the line when none can start', () => {
    const markup = render([version()]);
    expect((markup.match(/type="checkbox"/g) ?? []).length).toBe(1);
    expect(markup).not.toContain('data-select-all');
    expect(markup).not.toContain('Выделить необработанные');
  });

  it('offers «Выделить необработанные» only when a startable document was never run', () => {
    const idle = version({
      classification: classification({ section_code: 'AR' }),
      audit: { state: 'not_run', partial: false, finding_count: 0, undecided_finding_count: 0 },
    });
    expect(render([idle, AR_TWO])).toMatch(/<button[^>]*data-select-not-run[^>]*>Выделить необработанные<\/button>/);
    expect(render([idle, AR_TWO])).toContain('title="Документов, которые не запускались: 1"');
    expect(render()).not.toContain('Выделить необработанные');
  });

  it('makes «ждут решения N» a button that chooses those documents, and a plain badge where none waits', () => {
    const waiting = otherVersion('B', {
      classification: classification({ section_code: 'AR' }),
      audit: { state: 'awaiting_decision', partial: false, finding_count: 3, undecided_finding_count: 2 },
    });
    const markup = render([waiting, AR_ONE]);
    expect(markup).toMatch(/<button[^>]*data-tally="awaitingDecision"[^>]*data-tally-select[^>]*>ждут решения <span[^>]*>1<\/span><\/button>/);
    expect(markup).toContain('title="Выбрать документы, которые ждут решения: 1"');
    expect(render()).not.toContain('data-tally-select');
  });

  it('makes «не запускались N» the way to narrow the page to those documents, as the original’s click does', () => {
    const idle = version({
      classification: classification({ section_code: 'AR' }),
      audit: { state: 'not_run', partial: false, finding_count: 0, undecided_finding_count: 0 },
    });
    const markup = render([idle, AR_TWO]);
    const badge = /<a [^>]*data-tally="notRun"[^>]*>/.exec(markup)?.[0] ?? '';
    expect(badge).toContain('filter=not_run');
    expect(badge).toContain('data-tally-link');
  });

  it('carries «Показать архивные» in a row of its own, and «+ Добавить», which is the project’s upload, at the end of the line', () => {
    const markup = render();
    expect(markup).toContain('Показать архивные');
    expect(markup).toMatch(new RegExp(`<a [^>]*data-section-add[^>]*href="/projects/${PROJECT_UID}#upload"[^>]*>\\+ Добавить</a>`));
    expect(markup).not.toContain('Добавить документ');
    expect(markup.indexOf('Показать архивные')).toBeGreaterThan(markup.indexOf('data-section-add'));
  });

  it('says only the stage on a card, the section being the page’s own', () => {
    const markup = render();
    expect(markup).toContain('data-project-stage="P"');
    expect(markup).not.toContain('data-section-code=');
  });

  it('reads its listing with the archive flag and the tag in the key, so a filter is its own listing', () => {
    const options = documentListQueryOptions(PROJECT_UID, undefined, 'AR', true, 'Корпус 1', { order: 'audit' });
    expect(options.queryKey).not.toEqual(SECTION_KEY);
    expect(options.queryKey).toEqual(
      queryKeys.projects.documents(PROJECT_UID, undefined, DOCUMENT_PAGE_LIMIT, 'AR', true, 'Корпус 1', undefined, 'audit'),
    );
  });
});
