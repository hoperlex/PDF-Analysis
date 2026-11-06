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

  it('says its pages beside the number and the history link in the same row', () => {
    const markup = renderWith(newClient(), createElement(DocumentCardGrid, { documents, addresses }));
    expect(markup).toContain('>12 стр.<');
    expect(markup).toContain('>все версии<');
    expect(markup).not.toContain('страниц 12');
  });

  it('says the section and the stage by default, only the stage inside a section’s group, nothing in the unclassified one', () => {
    const both = renderWith(newClient(), createElement(DocumentCardGrid, { documents: [classified], addresses }));
    const stage = renderWith(newClient(), createElement(DocumentCardGrid, { documents: [classified], addresses, classification: 'stage' }));
    const none = renderWith(newClient(), createElement(DocumentCardGrid, { documents: [unclassified], addresses, classification: 'none' }));
    expect(both).toContain('data-section-code="AR"');
    expect(stage).toContain('data-project-stage="P"');
    expect(stage).not.toContain('data-section-code');
    expect(none).not.toContain('data-version-classification');
  });

  it('says how many findings the result run published, beside the chip, and nothing for a document with none', () => {
    const audited = (n: number) => version({
      classification: classification(),
      audit: { state: 'awaiting_decision', partial: false, result_run_id: 'run_01J9ZQ8K7NHVXW3T2R5M6P4Q8F', finding_count: n, undecided_finding_count: 1 },
    });
    const three = renderWith(newClient(), createElement(DocumentCardGrid, { documents: [audited(3)], addresses }));
    const many = renderWith(newClient(), createElement(DocumentCardGrid, { documents: [audited(12)], addresses }));
    const none = renderWith(newClient(), createElement(DocumentCardGrid, { documents: [audited(0)], addresses }));
    expect(three).toMatch(/data-card-findings="3"[^>]*>3 замечания</);
    expect(many).toMatch(/data-card-findings="12"[^>]*>12 замечаний</);
    expect(none).not.toContain('data-card-findings');
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

  it('keeps the card’s other controls above the stretched link, so the history link and the box still work', () => {
    expect(css).toMatch(/\.topEnd,[^{]*\{[^}]*z-index:\s*1;/);
  });
});
