/**
 * The project screen's storage structure (`W59-SECTION-UI-01`): section → documents →
 * the current version with its stage, built from the one `listDocuments` read.
 *
 * It replaced `R-18`'s fourteen-tab stub, so the claims that stub was careful NOT to make are
 * now the claims under test, and each is made only from the contract's own field: a document
 * stands under the section an expert confirmed for its current version, in «Не
 * классифицировано» while there is none — never under a section its file name or its legacy
 * `section` suggests.
 */

import { createElement } from 'react';
import { describe, expect, it } from 'vitest';

import { queryKeys } from '@/shared/api';
import { DOCUMENT_PAGE_LIMIT } from '@/entities/document-version';
import { PROJECT_STRUCTURE_ORDER } from '@/entities/project';
import { ProjectDetailPage } from '@/_pages/project-detail';
import { ProjectSections, ProjectStructureView, projectStructure } from '@/widgets/project-sections';

import { newClient, renderScreen, renderWith } from '../screens/harness';
import { PROJECT_UID, classification, otherVersion, page, version } from './fixtures';

const AR_P = version({ classification: classification() });
const KJ_R = otherVersion('C', {
  classification: classification({ project_stage: 'R', section_code: 'KJ' }),
});
const KJ_P = otherVersion('E', {
  classification: classification({ project_stage: 'P', section_code: 'KJ' }),
});
// Its legacy `section` says АИ; that is not a classification, so it stays unclassified.
const UNCLASSIFIED = otherVersion('D', { section: 'AI' });
const ITEMS = [AR_P, KJ_R, UNCLASSIFIED, KJ_P];

/** The `data-section-group` values in markup order. */
function groupOrder(markup: string): string[] {
  return [...markup.matchAll(/data-section-group="([A-Za-z]+)"/g)].map((m) => m[1] as string);
}

/** The markup of one group's `<li>`. */
function group(markup: string, code: string): string {
  const start = markup.indexOf(`data-section-group="${code}"`);
  expect(start, `no group ${code}`).toBeGreaterThan(-1);
  const end = markup.indexOf('data-section-group="', start + 1);
  return markup.slice(start, end === -1 ? undefined : end);
}

describe('the grouping', () => {
  it('puts each document under the section confirmed for its current version, in server order', () => {
    const structure = projectStructure(ITEMS);
    const byCode = new Map(structure.sections.map((g) => [g.section.code, g.documents]));
    expect(byCode.get('AR')).toEqual([AR_P]);
    expect(byCode.get('KJ')).toEqual([KJ_R, KJ_P]);
    expect(structure.unclassified).toEqual([UNCLASSIFIED]);
  });

  it('never reads the legacy section: a document classified nowhere stays unclassified', () => {
    const structure = projectStructure([UNCLASSIFIED]);
    expect(structure.sections.every((g) => g.documents.length === 0)).toBe(true);
    expect(structure.unclassified).toHaveLength(1);
  });

  it('keeps all fifteen sections in the S-5 order, empty ones included, and loses no document', () => {
    const structure = projectStructure(ITEMS);
    expect(structure.sections.map((g) => g.section.code)).toEqual([...PROJECT_STRUCTURE_ORDER]);
    const placed = structure.sections.reduce((n, g) => n + g.documents.length, 0) + structure.unclassified.length;
    expect(placed).toBe(ITEMS.length);
  });
});

describe('the structure as a reader sees it', () => {
  const markup = renderWith(
    newClient(),
    createElement(ProjectStructureView, { projectUid: PROJECT_UID, items: ITEMS, hasNextPage: false }),
  );

  it('lists fifteen sections in the S-5 order, then «Не классифицировано»', () => {
    expect(groupOrder(markup)).toEqual([...PROJECT_STRUCTURE_ORDER, 'unclassified']);
    expect(markup).toContain('Не классифицировано');
  });

  it('names each section by its Cyrillic mark and name, never by its Latin code', () => {
    expect(group(markup, 'AR')).toContain('АР</span> Архитектурные решения');
    expect(group(markup, 'PS')).toContain('ПЗ</span> Пояснительная записка');
    expect(group(markup, 'OV')).toContain('Отопление, вентиляция и кондиционирование');
  });

  it('counts the documents of each group and says when one is empty', () => {
    expect(group(markup, 'KJ')).toContain('data-section-documents="2"');
    expect(group(markup, 'KJ')).toContain('документов: 2');
    expect(group(markup, 'GP')).toContain('data-section-documents="0"');
    expect(group(markup, 'GP')).toContain('документов нет');
    expect(group(markup, 'unclassified')).toContain('data-section-documents="1"');
  });

  it('carries the stage on every classified row, and «Раздел не подтверждён» on the rest', () => {
    const kj = group(markup, 'KJ');
    expect(kj).toContain('Стадия: Р');
    expect(kj).toContain('Стадия: П');
    expect(group(markup, 'AR')).toContain('data-version-classification="P:AR"');
    expect(group(markup, 'unclassified')).toContain('Раздел не подтверждён');
    expect(group(markup, 'unclassified')).not.toContain('Стадия:');
  });

  it('links every row to its version and to its document, as the flat list did', () => {
    expect(markup).toContain(`href="/projects/${PROJECT_UID}/versions/${KJ_R.version_uid}"`);
    expect(markup).toContain(`href="/projects/${PROJECT_UID}/documents/${KJ_R.document_uid}"`);
    expect((markup.match(/Все версии документа/g) ?? []).length).toBe(ITEMS.length);
  });

  it('opens an unclassified document at its version’s stage-and-section panel', () => {
    expect(group(markup, 'unclassified')).toContain(
      `href="/projects/${PROJECT_UID}/versions/${UNCLASSIFIED.version_uid}#version-classification"`,
    );
    expect(group(markup, 'AR')).not.toContain('#version-classification');
  });

  it('says when the structure is one page of several', () => {
    const paged = renderWith(
      newClient(),
      createElement(ProjectStructureView, { projectUid: PROJECT_UID, items: ITEMS, hasNextPage: true }),
    );
    expect(paged).toContain('data-structure-page="partial"');
    expect(markup).not.toContain('data-structure-page');
  });
});

describe('the project screen', () => {
  const key = queryKeys.projects.documents(PROJECT_UID, undefined, DOCUMENT_PAGE_LIMIT);

  it('groups the one listDocuments read and keeps the upload under it', () => {
    const client = newClient();
    client.setQueryData(key, page(ITEMS));
    const screen = renderScreen(client, createElement(ProjectDetailPage, { projectUid: PROJECT_UID }));
    expect(screen).toContain('<h2>Разделы проекта</h2>');
    expect(screen).toContain('data-project-structure=""');
    expect(screen).toContain('id="upload-file"');
    expect(screen.indexOf('data-project-structure')).toBeLessThan(screen.indexOf('id="upload-file"'));
    // One read, and no other query was asked for by the structure.
    const keys = client.getQueryCache().getAll().map((q) => JSON.stringify(q.queryKey));
    expect(keys.filter((k) => k.startsWith('["projects","documents"'))).toEqual([JSON.stringify(key)]);
    expect(keys.some((k) => k.startsWith('["versions"'))).toBe(false);
  });

  it('no longer renders the stub: no tabs, no placeholder, no «Раздел пока недоступен»', () => {
    const client = newClient();
    client.setQueryData(key, page(ITEMS));
    const screen = renderScreen(client, createElement(ProjectDetailPage, { projectUid: PROJECT_UID }));
    expect(screen).not.toContain('Раздел пока недоступен');
    expect(screen).not.toContain('data-open-section');
    expect(screen).not.toContain('aria-current="true"');
  });

  it('says an empty project is empty, rather than drawing fifteen empty sections', () => {
    const client = newClient();
    client.setQueryData(key, page([]));
    const markup = renderWith(client, createElement(ProjectSections, { projectUid: PROJECT_UID }));
    expect(markup).toContain('В этом проекте пока нет документов.');
    expect(markup).not.toContain('data-section-group=');
  });

  it('shows the pager when the server has another page', () => {
    const client = newClient();
    client.setQueryData(key, page(ITEMS, 'opaque-cursor'));
    const markup = renderWith(client, createElement(ProjectSections, { projectUid: PROJECT_UID }));
    expect(markup).toContain('>Дальше</button>');
    expect(markup).toContain('data-structure-page="partial"');
  });
});
