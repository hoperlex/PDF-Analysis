/**
 * The screens that show a document's audit state (`UI-PARITY-DOC-AUDIT`, contract 1.34.0).
 *
 * The section page reads the listing in the server's audit order (`order=audit`) and, under `?filter=not_run`, only the
 * documents that were never analysed (`audit_state=not_run`); each card carries the chip of its state; the dashboard's
 * «Не запускались» is a link to that narrowed page while a project is followed. The listing is the cache entry the page
 * reads, so each case seeds the entry under the key the page builds -- a page that asked for another listing would show a
 * spinner here.
 */

import { createElement } from 'react';
import { describe, expect, it } from 'vitest';

import type { DashboardSummary, DocumentAudit } from '@/shared/api';
import { PROJECT_SECTION_VALUES, RUN_STATE_VALUES, queryKeys } from '@/shared/api';
import { DOCUMENT_PAGE_LIMIT, DocumentCardGrid } from '@/entities/document-version';
import { SectionDetailPage } from '@/_pages/section-detail';
import { ProjectSections } from '@/widgets/project-sections';
import { Dashboard } from '@/widgets/dashboard';

import { sectionAudit } from '../dashboard/audit-counts';
import { newClient, renderWith } from '../screens/harness';
import { PROJECT_UID, classification, otherVersion, page, version } from '../sections/fixtures';

const RUN = 'run_01J9ZQ8K7NHVXW3T2R5M6P4Q8F';

function audit(overrides: Partial<DocumentAudit>): DocumentAudit {
  return { state: 'not_run', partial: false, finding_count: 0, undecided_finding_count: 0, ...overrides };
}

/** The key the section page builds: the section, the audit order, and the state under a filter. */
function sectionKey(state?: string) {
  return queryKeys.projects.documents(PROJECT_UID, undefined, DOCUMENT_PAGE_LIMIT, 'AR', false, undefined, state, 'audit');
}

const CHECKED = version({
  display_title: 'Проверенный', classification: classification({ section_code: 'AR' }),
  audit: audit({ state: 'checked', result_run_id: RUN, finding_count: 4 }),
});
const WAITING = otherVersion('B', {
  display_title: 'Ожидающий', classification: classification({ section_code: 'AR' }),
  audit: audit({ state: 'awaiting_decision', partial: true, result_run_id: RUN, finding_count: 3, undecided_finding_count: 2 }),
});
const NEVER = otherVersion('C', {
  display_title: 'Не тронутый', classification: classification({ section_code: 'AR' }), audit: audit({ state: 'not_run' }),
});
const NO_AUDIT = otherVersion('D', { display_title: 'Без сведений', classification: classification({ section_code: 'AR' }) });

function sectionPage(client: ReturnType<typeof newClient>, filter?: string) {
  return renderWith(client, createElement(SectionDetailPage, { projectUid: PROJECT_UID, sectionCode: 'AR', filter }));
}

describe('the card of a document', () => {
  const grid = (documents: Parameters<typeof DocumentCardGrid>[0]['documents']) =>
    renderWith(newClient(), createElement(DocumentCardGrid, {
      documents,
      addresses: () => ({ href: '/projects', documentHref: '/projects' }),
      reviewAddress: (runId) => `/projects/${PROJECT_UID}/runs/${runId}/review`,
    }));

  it('carries the chip of its audit state, in the order the server gave', () => {
    const markup = grid([CHECKED, WAITING, NEVER]);
    const states = [...markup.matchAll(/data-audit-state="([a-z_]+)"/g)].map((match) => match[1]);
    expect(states).toEqual(['checked', 'awaiting_decision', 'not_run']);
    expect(markup).toContain('>Проверен экспертом<');
    expect(markup).toContain('>Ждёт решения: 2<');
    expect(markup).toContain('>Не запускался<');
    expect(markup).toContain('title="3 замечания, без решения эксперта: 2"');
  });

  it('links the chip of a document that was run to «Разбор» of its result run, and a never-run one links nowhere', () => {
    const markup = grid([CHECKED, NEVER]);
    expect(markup).toContain(`href="/projects/${PROJECT_UID}/runs/${RUN}/review"`);
    const never = markup.slice(markup.indexOf('Не тронутый'));
    expect(never).not.toContain('/review"');
  });

  it('marks a partial result beside its state', () => {
    const markup = grid([WAITING, NEVER]);
    expect((markup.match(/data-audit-partial="true"/g) ?? []).length).toBe(1);
    expect((markup.match(/>частично</g) ?? []).length).toBe(1);
  });

  it('draws no chip for an item whose answer carried no audit', () => {
    const markup = grid([NO_AUDIT]);
    expect(markup).not.toContain('data-audit-state');
    expect(markup).not.toContain('Не запускался');
  });
});

describe('the section page', () => {
  it('reads the listing in the audit order and shows the chips', () => {
    const client = newClient();
    client.setQueryData(sectionKey(), page([CHECKED, WAITING, NEVER]));
    const markup = sectionPage(client);
    expect(markup).toContain('data-document-cards="3"');
    expect(markup).toContain('data-audit-state="checked"');
    expect(markup).not.toContain('data-section-filter');
    expect(markup).not.toContain('Показать все');
  });

  it('under ?filter=not_run reads the narrowed listing, says what it shows and offers «Показать все»', () => {
    const client = newClient();
    client.setQueryData(sectionKey('not_run'), page([NEVER, NO_AUDIT].slice(0, 1)));
    const markup = sectionPage(client, 'not_run');
    expect(markup).toContain('data-section-filter="not_run"');
    expect(markup).toContain('Показаны документы, которые не анализировались: 1');
    expect(markup).not.toContain('на этой странице');
    expect(markup).toMatch(new RegExp(`<a [^>]*data-show-all[^>]*href="/projects/${PROJECT_UID}/sections/AR"`));
    expect(markup).toContain('>Показать все<');
  });

  it('says when the narrowed list goes on past this page, so a page is not taken for the whole', () => {
    const client = newClient();
    client.setQueryData(sectionKey('not_run'), page([NEVER], 'next'));
    const markup = sectionPage(client, 'not_run');
    expect(markup).toContain('Показаны документы, которые не анализировались: 1 на этой странице');
    expect(markup).toContain('>Далее<');
  });

  it('says an empty narrowed list is empty because everything was analysed, with the way to the whole section', () => {
    const client = newClient();
    client.setQueryData(sectionKey('not_run'), page([]));
    const markup = sectionPage(client, 'not_run');
    expect(markup).toContain('В этом разделе нет документов, которые не анализировались.');
    expect(markup).toContain('>Показать все<');
    expect(markup).not.toContain('В этом разделе пока нет документов.');
  });

  it('takes any other value of filter for no filter, and reads the unnarrowed listing', () => {
    for (const filter of ['clean', '', 'not_run,clean']) {
      const client = newClient();
      client.setQueryData(sectionKey(), page([CHECKED]));
      const markup = sectionPage(client, filter);
      expect(markup, filter).toContain('data-document-cards="1"');
      expect(markup).not.toContain('data-section-filter');
    }
  });
});

describe('the project’s sections', () => {
  it('reads the listing in the audit order and keeps the server’s order inside each group', () => {
    const client = newClient();
    client.setQueryData(
      queryKeys.projects.documents(PROJECT_UID, undefined, DOCUMENT_PAGE_LIMIT, undefined, false, undefined, undefined, 'audit'),
      page([CHECKED, WAITING, NEVER]),
    );
    client.setQueryData(queryKeys.projects.tags(PROJECT_UID), { items: [] });
    const markup = renderWith(client, createElement(ProjectSections, { projectUid: PROJECT_UID }));
    const states = [...markup.matchAll(/data-audit-state="([a-z_]+)"/g)].map((match) => match[1]);
    expect(states).toEqual(['checked', 'awaiting_decision', 'not_run']);
    expect(markup).toContain(`href="/projects/${PROJECT_UID}/runs/${RUN}/review"`);
  });
});

describe('the dashboard’s «Не запускались»', () => {
  function summary(notRunOfAr: number): DashboardSummary {
    return {
      documents_by_project: [{ project_uid: PROJECT_UID, name: 'Проект', document_count: 9 }],
      findings_by_verdict: [
        { verdict: 'pending', count: 1 }, { verdict: 'accepted', count: 2 },
        { verdict: 'rejected', count: 3 }, { verdict: 'needs_manual_review', count: 4 },
      ],
      run_activity: { by_state: RUN_STATE_VALUES.map((state) => ({ state, count: 1 })) },
      section_breakdown: [
        ...PROJECT_SECTION_VALUES.map((section) => ({
          section, document_count: 9,
          ...sectionAudit(9, section === 'AR' ? { not_run: notRunOfAr, no_expert_decision: notRunOfAr } : {}),
        })),
        { document_count: 9, ...sectionAudit(9) },
      ],
      awaiting_decision_findings: 0,
    };
  }

  function dashboard(data: DashboardSummary, projectUid?: string) {
    const client = newClient();
    client.setQueryData(queryKeys.dashboard.summary(projectUid as never), data);
    return renderWith(client, createElement(Dashboard, projectUid === undefined ? {} : { projectUid: projectUid as never }));
  }

  it('links the figure of a section to that section’s page narrowed to the documents never run', () => {
    const markup = dashboard(summary(4), PROJECT_UID);
    const href = `/projects/${PROJECT_UID}/sections/AR?filter=not_run`;
    expect(markup).toContain(`href="${href}"`);
    expect(markup).toMatch(new RegExp(`<a [^>]*data-not-run-link[^>]*href="${href.replace(/[?]/g, '\\?')}"[^>]*>4</a>`));
  });

  it('links a section that has some, and leaves a zero a plain number', () => {
    const markup = dashboard(summary(0), PROJECT_UID);
    expect((markup.match(/data-not-run-link/g) ?? []).length).toBe(PROJECT_SECTION_VALUES.length - 1);
    expect(markup).not.toContain('/sections/AR?filter=not_run');
  });

  it('draws no link across all projects: there is no one section page to open', () => {
    const markup = dashboard(summary(4));
    expect(markup).not.toContain('data-not-run-link');
    expect(markup).not.toContain('filter=not_run');
  });
});
