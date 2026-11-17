/**
 * Density of the lists (UI parity, `UI-A-10`, `UI-A-24`, `UI-A-45`): a project, a version and a document card are
 * each a compact block of the original's shape instead of a bordered stack of paragraphs.
 *
 * What is held: the project row states the project's audit from its own counters (and the plain count of documents
 * when it has none), the opaque identity is the link's address and tooltip and not a second line; a version row is a
 * line of number, title and badges over a line of facts; a document card says its stage and, when asked, not its
 * section, and a Σ card opens the grid.
 */

import { readFileSync } from 'node:fs';
import { join } from 'node:path';

import { createElement } from 'react';
import { describe, expect, it } from 'vitest';

import type { DocumentVersion, Project, ProjectPage } from '@/shared/api';
import { queryKeys } from '@/shared/api';
import { DocumentCardGrid, VersionRow } from '@/entities/document-version';
import { PROJECT_PAGE_LIMIT } from '@/entities/project';
import { ProjectList } from '@/widgets/project-list';

import { WEB_ROOT } from '../../guards/lib/repo';
import { parseRules } from '../styles/contrast';
import { withoutMedia } from '../styles/css-reads';
import { auditCounts } from '../dashboard/audit-counts';
import { newClient, renderWith } from '../screens/harness';
import { PROJECT_UID, classification, otherVersion, version } from '../sections/fixtures';

const LIST_KEY = queryKeys.projects.list(undefined, PROJECT_PAGE_LIMIT);

function listOf(items: Project[]): string {
  const client = newClient();
  const data: ProjectPage = { items, page: { next_cursor: null } as ProjectPage['page'] };
  client.setQueryData(LIST_KEY, data);
  return renderWith(client, createElement(ProjectList, {}));
}

const BASE: Project = { project_uid: PROJECT_UID, name: 'Школа', created_at: '2026-09-10T08:00:00.000Z', document_count: 4 };

describe('a project in the list', () => {
  it('states its audit from its own counters: documents, not started, awaiting a decision, checked', () => {
    const markup = listOf([{ ...BASE, audit_counts: auditCounts(4, { not_run: 2, awaiting_decision: 1, checked: 1, no_expert_decision: 3 }) }]);
    expect(markup).toContain('data-audit-tally="4"');
    expect(markup).toContain('data-tally="notRun"');
    expect(markup).toContain('data-tally="awaitingDecision"');
    expect(markup).toContain('data-tally="checked"');
  });

  it('keeps the plain count of documents for a project that carries no counters', () => {
    const markup = listOf([BASE]);
    expect(markup).not.toContain('data-audit-tally');
    expect(markup).toContain('документов 4');
  });

  it('puts the opaque identity in the link’s address and tooltip, not on a line of its own', () => {
    const markup = listOf([BASE]);
    expect(markup).toContain(`href="/projects/${PROJECT_UID}"`);
    expect(markup).toContain(`title="${PROJECT_UID}"`);
    expect(markup).not.toContain(`<code>${PROJECT_UID}</code>`);
  });

  it('is one row per project, with no state block round it', () => {
    const markup = listOf([BASE]);
    expect(markup).not.toContain('am-state');
    expect((markup.match(/data-project-uid=/g) ?? [])).toHaveLength(1);
  });
});

describe('a version in the list', () => {
  const v = version({ version_ordinal: 3, display_title: 'Комплект АР', classification: classification() });
  const markup = renderWith(newClient(), createElement(VersionRow, {
    version: v, href: '/v', secondary: { href: '/d', label: 'Все версии документа' },
  }));

  it('is a line of number, title and badges, with the history link at its end', () => {
    expect(markup).toContain('>V3<');
    expect(markup).toContain('>Комплект АР<');
    expect(markup).toContain('data-version-classification="P:AR"');
    expect(markup.indexOf('Все версии документа')).toBeGreaterThan(markup.indexOf('data-version-classification'));
  });

  it('keeps the facts and the identity on the second line, and does not say the number twice', () => {
    expect(markup).toContain('страниц 8');
    expect(markup).toContain(`<code>${v.version_uid}</code>`);
    expect(markup).not.toContain('Версия 3 ·');
  });
});

describe('a document card', () => {
  const documents = [version({ page_count: 12, classification: classification() }), otherVersion('B')];
  const [classified, unclassified] = documents as [DocumentVersion, DocumentVersion];
  const addresses = () => ({ href: '/v', documentHref: '/d' });
  const facts = (markup: string) => [...markup.matchAll(/data-card-fact="([a-z]+)"/g)].map((match) => match[1]);

  it('is one line of name, number of version and box, and the number leads to the document’s versions', () => {
    const markup = renderWith(newClient(), createElement(DocumentCardGrid, { documents, addresses }));
    expect(markup).toMatch(/<p class="[^"]*"><a [^>]*title="Комплект АР\n[^"]*"[^>]*href="\/v">Комплект АР<\/a><\/p>/);
    expect(markup).toMatch(/<a [^>]*title="Все версии документа"[^>]*href="\/d">V1<\/a>/);
    // not drawn any more: «все версии» in a row of its own, the pages beside the number, the stage badge (they are read, below)
    expect(markup).not.toMatch(/<a [^>]*>все версии<\/a>/);
    expect(markup).not.toContain('am-badge--active');
  });

  it('keeps the pages, the stage, the section and the tags in words a screen reader reads and the tooltip carries, and in no line', () => {
    const tagged = version({ page_count: 12, classification: classification(), tags: ['Корпус 1', 'Корпус 2'] });
    const markup = renderWith(newClient(), createElement(DocumentCardGrid, { documents: [tagged], addresses }));
    expect(facts(markup)).toEqual(['pages', 'stage', 'section', 'tags', 'versions']);
    expect(markup).toContain('>все версии<');
    expect(markup).toContain('>12 стр.<');
    expect(markup).toContain('>Стадия: П<');
    expect(markup).toContain('>Метки: Корпус 1, Корпус 2<');
    expect(markup).toContain('12 стр.\nСтадия: П\nАрхитектурные решения (АР)\nМетки: Корпус 1, Корпус 2\nV1: все версии документа"');
    expect(markup).toContain('data-version-classification="P:AR"');
    expect(markup).not.toContain('страниц 12');
  });

  it('says the section and the stage by default, only the stage inside a section’s group, nothing in the unclassified one', () => {
    const both = renderWith(newClient(), createElement(DocumentCardGrid, { documents: [classified], addresses }));
    const stage = renderWith(newClient(), createElement(DocumentCardGrid, { documents: [classified], addresses, classification: 'stage' }));
    const none = renderWith(newClient(), createElement(DocumentCardGrid, { documents: [unclassified], addresses, classification: 'none' }));
    expect(both).toContain('data-section-code="AR"');
    expect(stage).toContain('data-project-stage="P"');
    expect(stage).not.toContain('data-section-code');
    expect(facts(none)).toEqual(['pages', 'versions']);
    expect(none).not.toContain('data-version-classification');
    // a version with no confirmed section says so, as the badge did, except in the group that is that very case
    const unconfirmed = renderWith(newClient(), createElement(DocumentCardGrid, { documents: [unclassified], addresses }));
    expect(unconfirmed).toContain('>Раздел не подтверждён<');
  });

  it('says how many findings the result run published in its first mark, and a zero for a result with none', () => {
    const audited = (n: number) => version({
      classification: classification(),
      audit: { state: 'awaiting_decision', partial: false, result_run_id: 'run_01J9ZQ8K7NHVXW3T2R5M6P4Q8F', finding_count: n, undecided_finding_count: 1 },
    });
    const three = renderWith(newClient(), createElement(DocumentCardGrid, { documents: [audited(3)], addresses }));
    const many = renderWith(newClient(), createElement(DocumentCardGrid, { documents: [audited(12)], addresses }));
    const clean = renderWith(newClient(), createElement(DocumentCardGrid, {
      documents: [version({ classification: classification(), audit: { state: 'clean', partial: false, finding_count: 0, undecided_finding_count: 0 } })], addresses,
    }));
    expect(three).toMatch(/data-card-findings="3"[^>]*><span[^>]*>Замечания<\/span><span[^>]*>3<\/span><span[^>]*aria-hidden="true">·<\/span>/);
    expect(many).toMatch(/data-card-findings="12"[^>]*><span[^>]*>Замечания<\/span><span[^>]*>12<\/span>/);
    expect(clean).toMatch(/data-card-findings="0"[^>]*data-card-mark-state="done"|data-card-mark-state="done"[^>]*data-card-findings="0"/);
  });

  it('opens the grid with a Σ card that is not a document', () => {
    const markup = renderWith(newClient(), createElement(DocumentCardGrid, {
      documents, addresses, leading: createElement('span', null, 'Оптимизация раздела'),
    }));
    expect(markup).toContain('data-document-cards="2"');
    expect(markup.indexOf('data-grid-leading')).toBeLessThan(markup.indexOf('data-document-uid'));
    expect((markup.match(/data-document-uid=/g) ?? [])).toHaveLength(2);
  });
});

describe('a document card as a whole target', () => {
  const css = readFileSync(join(WEB_ROOT, 'src/entities/document-version/ui/document-cards.module.css'), 'utf8');

  it('stretches the title link over the card, as the original’s card opens its version', () => {
    expect(css).toMatch(/\.title a::after\s*\{[^}]*position:\s*absolute;[^}]*inset:\s*0;/);
    expect(css).toMatch(/\.card\s*\{[^}]*position:\s*relative;/);
  });

  it('keeps the card’s other controls above the stretched link, so the number of the version and the box still work', () => {
    expect(css).toMatch(/\.ordinal,\s*\.select\s*\{[^}]*z-index:\s*1;/);
    const marks = readFileSync(join(WEB_ROOT, 'src/entities/document-version/ui/audit-chip.module.css'), 'utf8');
    expect(marks).toMatch(/\.marks a\.mark,[^{]*\{[^}]*z-index:\s*1;/);
  });
});

describe('the density of a document card (UIP-S02-02)', () => {
  const css = readFileSync(join(WEB_ROOT, 'src/entities/document-version/ui/document-cards.module.css'), 'utf8');
  /** The declarations of every base rule (outside `@media`) whose selector list names `selector`, in source order, as the cascade merges them. */
  const rule = (selector: string): string => {
    const merged = new Map<string, string>();
    for (const found of parseRules(withoutMedia(css), 'module')) {
      if (!found.selector.split(',').some((part) => part.trim() === selector)) continue;
      for (const [property, value] of found.declarations) merged.set(property, value);
    }
    return [...merged].map(([k, v]) => `${k}: ${v}`).join('; ');
  };

  it('takes the card’s size from the tokens of UIP-G-14: the grid’s column floor is the width less a gap, the card’s height at least the token', () => {
    expect(rule('.grid')).toContain('minmax(min(100%, calc(var(--am-card-doc-width) - var(--am-gap-md))), 1fr)');
    expect(rule('.card')).toContain('min-height: var(--am-card-doc-height)');
    // the Σ card is a cell of the same grid and the same size
    expect(rule('.leading')).toContain('min-height: var(--am-card-doc-height)');
  });

  it('draws the name on one line, cut with an ellipsis, in a 24 px target, and the line is 24 px high', () => {
    expect(rule('.title a')).toContain('white-space: nowrap');
    expect(rule('.title a')).toContain('text-overflow: ellipsis');
    expect(rule('.title a')).toContain('min-height: var(--am-target-min)');
    expect(rule('.select')).toContain('min-height: var(--am-target-min)');
    expect(rule('.select')).toContain('min-width: var(--am-target-min)');
  });

  it('makes the cards a container, so a mark reads the width of its own card to say its word', () => {
    expect(rule('.card')).toContain('container-type: inline-size');
    const marks = readFileSync(join(WEB_ROOT, 'src/entities/document-version/ui/audit-chip.module.css'), 'utf8');
    expect(marks).toMatch(/@container \(min-width: 17rem\)\s*\{\s*\.label\s*\{/);
  });

  it('is one column on a phone', () => {
    expect(css).toMatch(/@media \(max-width: 590px\)\s*\{\s*\.grid\s*\{\s*grid-template-columns:\s*minmax\(0, 1fr\);/);
  });
});
