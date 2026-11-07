/**
 * Parity pass 4, project and document screens: `UI-A-36` (the project page's «Σ Итого») and `UI-A-45` (the audit chip in
 * the version rows of the document page).
 *
 * What is held: the total is the sum of the server's figures of the fifteen sections and nothing the page counted, it is
 * absent whenever a section's figures are, and stands before «Не классифицировано», which is not in it; a version row
 * draws the chip of the audit it carries and none for a version that carries none, the current version's chip reaches the
 * document screen through its section's listing under the keys the section strip already reads.
 */

import { createElement } from 'react';
import { describe, expect, it } from 'vitest';

import type { DocumentAudit, DocumentUid, SectionDocumentCount } from '@/shared/api';
import { queryKeys } from '@/shared/api';
import { DOCUMENT_PAGE_LIMIT, VERSION_PAGE_LIMIT, VersionRow } from '@/entities/document-version';
import { PROJECT_SECTIONS } from '@/entities/project';
import { ProjectStructureView, sectionFigures, totalFigures } from '@/widgets/project-sections';
import { VersionList } from '@/widgets/version-list';

import { sectionAudit } from '../dashboard/audit-counts';
import { newClient, renderWith } from '../screens/harness';
import { DOCUMENT_UID, PROJECT_UID, classification, otherVersion, page, version } from './fixtures';

const RUN = 'run_01J9ZQ8K7NHVXW3T2R5M6P4Q8F';

function audit(overrides: Partial<DocumentAudit>): DocumentAudit {
  return { state: 'not_run', partial: false, finding_count: 0, undecided_finding_count: 0, ...overrides };
}

/** Fifteen section rows, each with its own figures, and the unclassified row. */
function rows(): SectionDocumentCount[] {
  return [
    ...PROJECT_SECTIONS.map((section, index) => ({
      section: section.code,
      document_count: index + 2,
      ...sectionAudit(index + 2, { not_run: 1, awaiting_decision: 1, no_expert_decision: 2, checked: index }, index),
    })),
    { document_count: 7, ...sectionAudit(7) },
  ] as SectionDocumentCount[];
}

describe('UI-A-36: «Σ Итого» on the project page', () => {
  const sum = (pick: (row: SectionDocumentCount) => number): number =>
    rows().filter((row) => row.section !== undefined).reduce((total, row) => total + pick(row), 0);
  const AR = version({ classification: classification() });
  const view = (figures: ReturnType<typeof sectionFigures> | undefined): string =>
    renderWith(newClient(), createElement(ProjectStructureView, {
      projectUid: PROJECT_UID, items: [AR], hasNextPage: false, figures,
    }));

  it('sums the server’s figures of the fifteen sections, without «Не классифицировано»', () => {
    const total = totalFigures(sectionFigures(rows()));
    expect(total).toEqual({
      documents: sum((row) => row.document_count),
      notRun: sum((row) => row.audit_counts?.not_run ?? 0),
      awaitingDecision: sum((row) => row.audit_counts?.awaiting_decision ?? 0),
      checked: sum((row) => row.audit_counts?.checked ?? 0),
      clean: 0,
      findings: sum((row) => row.finding_count),
    });
    expect(total?.documents).not.toBe(sum((row) => row.document_count) + 7);
  });

  it('draws the total after the sections and before the unclassified group, as one card', () => {
    const markup = view(sectionFigures(rows()));
    expect(markup.match(/data-section-total=/g) ?? []).toHaveLength(1);
    expect(markup).toContain(`data-section-total="" data-section-documents="${sum((row) => row.document_count)}"`);
    expect(markup).toContain('Итого по разделам');
    const at = markup.indexOf('data-section-total');
    expect(at).toBeGreaterThan(markup.indexOf(`data-section-group="${PROJECT_SECTIONS.at(-1)?.code}"`));
    expect(at).toBeLessThan(markup.indexOf('data-section-group="unclassified"'));
    // The total says its figures through the tally line, as a section does.
    expect(markup.slice(at)).toContain(`data-audit-tally="${sum((row) => row.document_count)}"`);
  });

  it('is absent while the server’s figures are, and when one section has none: never a smaller number', () => {
    expect(view(undefined)).not.toContain('data-section-total');
    const without = rows().filter((row) => row.section !== 'KM');
    expect(totalFigures(sectionFigures(without))).toBeUndefined();
    expect(view(sectionFigures(without))).not.toContain('data-section-total');
  });

  it('is not a section group, so the sections’ own count and order are unchanged', () => {
    const markup = view(sectionFigures(rows()));
    expect((markup.match(/data-section-group="/g) ?? [])).toHaveLength(PROJECT_SECTIONS.length + 1);
  });
});

describe('UI-A-45: the audit chip in a version row', () => {
  const run = audit({ state: 'awaiting_decision', result_run_id: RUN, finding_count: 3, undecided_finding_count: 2 });
  const render = (element: ReturnType<typeof createElement>): string => renderWith(newClient(), element);

  it('draws the chip of the audit the version carries, linked to «Разбор» of its result run', () => {
    const markup = render(createElement(VersionRow, {
      version: version({ audit: run }), href: '/v', reviewAddress: (runId: string) => `/review/${runId}`,
    }));
    expect(markup).toContain('data-audit-state="awaiting_decision"');
    expect(markup).toContain(`href="/review/${RUN}"`);
  });

  it('draws no chip for a version that carries no audit: it says nothing about its runs', () => {
    const markup = render(createElement(VersionRow, { version: version(), href: '/v' }));
    expect(markup).not.toContain('data-audit-state');
  });

  it('puts the chip after the badges of the row, in its first line', () => {
    const markup = render(createElement(VersionRow, {
      version: version({ audit: run, classification: classification() }), href: '/v',
    }));
    expect(markup.indexOf('data-audit-state')).toBeGreaterThan(markup.indexOf('data-version-classification'));
    expect(markup.indexOf('data-audit-state')).toBeLessThan(markup.indexOf('страниц'));
  });

  describe('on the document screen', () => {
    const current = version({ version_ordinal: 2, classification: classification(), audit: run });
    const older = version({
      version_uid: `${current.version_uid.slice(0, -1)}Z`, version_ordinal: 1, classification: classification(),
    });
    const seeded = () => {
      const client = newClient();
      client.setQueryData(queryKeys.versions.list(DOCUMENT_UID as DocumentUid, undefined, VERSION_PAGE_LIMIT), page([current, older]));
      return client;
    };
    const sectionKey = queryKeys.projects.documents(PROJECT_UID, undefined, DOCUMENT_PAGE_LIMIT, 'AR', false, undefined, undefined, 'audit');

    it('gets the current version’s chip from its section’s listing, and none for the older version', () => {
      const client = seeded();
      client.setQueryData(sectionKey, page([otherVersion('B'), current]));
      const markup = renderWith(client, createElement(VersionList, { projectUid: PROJECT_UID, documentUid: DOCUMENT_UID as DocumentUid, sectionCode: 'AR' }));
      expect(markup.match(/data-audit-state=/g) ?? []).toHaveLength(1);
      const row = markup.slice(markup.indexOf(`data-version-uid="${current.version_uid}"`), markup.indexOf(`data-version-uid="${older.version_uid}"`));
      expect(row).toContain('data-audit-state="awaiting_decision"');
    });

    it('draws no chip while the section’s listing is unread, or when the version has no confirmed section', () => {
      const unread = renderWith(seeded(), createElement(VersionList, { projectUid: PROJECT_UID, documentUid: DOCUMENT_UID as DocumentUid, sectionCode: 'AR' }));
      expect(unread).not.toContain('data-audit-state');
      const unclassified = renderWith(seeded(), createElement(VersionList, { projectUid: PROJECT_UID, documentUid: DOCUMENT_UID as DocumentUid }));
      expect(unclassified).not.toContain('data-audit-state');
    });
  });
});
