/**
 * `UI-A-47` (contract 1.40.0): a document whose current version has a run in flight says «Идёт аудит» beside its audit chip.
 *
 * The server names the run (`audit.active_run`: its id and one of `queued`, `running`, `validating`) in the statement that
 * reads the audit, and changes none of the four audit words. These cases pin the mark's words (the product's own words for a
 * run's state), its link to the run page of the version's own project, that the four-state chip is exactly what it was beside
 * it, and that a document with no run in flight, or an answer with no audit at all, draws nothing in its place.
 */

import { createElement } from 'react';
import { describe, expect, it } from 'vitest';

import type { DocumentAudit } from '@/shared/api';
import { queryKeys } from '@/shared/api';
import { STATE_LABELS } from '@/shared/ui';
import {
  ACTIVE_RUN_LABEL,
  AuditChip,
  DOCUMENT_PAGE_LIMIT,
  DocumentCardGrid,
  VersionRow,
  activeRunHref,
  activeRunMark,
} from '@/entities/document-version';
import { SectionDetailPage } from '@/_pages/section-detail';

import { newClient, renderScreen, renderWith } from '../screens/harness';
import { PROJECT_UID, classification, otherVersion, page, version } from '../sections/fixtures';

const RESULT = 'run_01J9ZQ8K7NHVXW3T2R5M6P4Q8F';
const ACTIVE = 'run_01J9ZQ8K7NHVXW3T2R5M6P4Q9G';

function audit(overrides: Partial<DocumentAudit>): DocumentAudit {
  return { state: 'not_run', partial: false, finding_count: 0, undecided_finding_count: 0, ...overrides };
}

const RERUN = version({
  display_title: 'Повторный аудит',
  classification: classification({ section_code: 'AR' }),
  audit: audit({ state: 'checked', result_run_id: RESULT, finding_count: 2, active_run: { run_id: ACTIVE, state: 'queued' } }),
});
const FIRST = otherVersion('B', {
  display_title: 'Первый аудит',
  classification: classification({ section_code: 'AR' }),
  audit: audit({ state: 'not_run', active_run: { run_id: ACTIVE.replace('9G', '9H'), state: 'running' } }),
});
const CHECKING = otherVersion('C', {
  display_title: 'На проверке',
  classification: classification({ section_code: 'AR' }),
  audit: audit({ state: 'awaiting_decision', result_run_id: RESULT, finding_count: 3, undecided_finding_count: 1, active_run: { run_id: ACTIVE.replace('9G', '9J'), state: 'validating' } }),
});
const QUIET = otherVersion('D', {
  display_title: 'Без прогона',
  classification: classification({ section_code: 'AR' }),
  audit: audit({ state: 'checked', result_run_id: RESULT, finding_count: 1 }),
});
const NO_AUDIT = otherVersion('E', { display_title: 'Без сведений', classification: classification({ section_code: 'AR' }) });

describe('the mark of a run in flight', () => {
  it('says «Идёт аудит» and the run’s state in the product’s own words for it', () => {
    expect(ACTIVE_RUN_LABEL).toBe('Идёт аудит');
    expect(
      (['queued', 'running', 'validating'] as const).map((state) => activeRunMark(audit({ active_run: { run_id: ACTIVE, state } }))?.text),
    ).toEqual(['Идёт аудит: в очереди', 'Идёт аудит: выполняется', 'Идёт аудит: проверяется']);
    expect(STATE_LABELS).toMatchObject({ queued: 'в очереди', running: 'выполняется', validating: 'проверяется' });
  });

  it('is nothing when the server names no run, and nothing when the answer carried no audit', () => {
    expect(activeRunMark(audit({}))).toBeNull();
    expect(activeRunMark(undefined)).toBeNull();
    expect(activeRunHref(version())).toBeUndefined();
    expect(activeRunHref(version({ audit: audit({ state: 'checked', result_run_id: RESULT }) }))).toBeUndefined();
  });

  it('links to the run page of the version’s own project', () => {
    expect(activeRunHref(RERUN)).toBe(`/projects/${PROJECT_UID}/runs/${ACTIVE}`);
  });
});

describe('the audit chip', () => {
  const chip = (audit_: DocumentAudit | undefined, runHref?: string, reviewHref?: string) =>
    renderScreen(newClient(), createElement(AuditChip, { audit: audit_, reviewHref, runHref }));

  it('draws the mark beside the four-state chip and leaves that chip exactly as it was', () => {
    const withRun = chip(RERUN.audit, `/projects/${PROJECT_UID}/runs/${ACTIVE}`, `/projects/${PROJECT_UID}/runs/${RESULT}/review`);
    const without = chip(
      audit({ state: 'checked', result_run_id: RESULT, finding_count: 2 }), undefined, `/projects/${PROJECT_UID}/runs/${RESULT}/review`,
    );
    expect(withRun).toContain('data-audit-state="checked"');
    expect(withRun).toContain('>Проверен экспертом<');
    expect(withRun).toContain(`href="/projects/${PROJECT_UID}/runs/${RESULT}/review"`);
    expect(withRun).toContain('data-audit-active-run="queued"');
    expect(withRun).toContain('>Идёт аудит: в очереди<');
    expect(withRun).toContain(`href="/projects/${PROJECT_UID}/runs/${ACTIVE}"`);
    expect(without).not.toContain('data-audit-active-run');
    // What the chip said before is a prefix of what it says now: the mark is added after it.
    const chipOnly = without.replace(/<\/span>$/, '');
    expect(withRun.startsWith(chipOnly)).toBe(true);
  });

  it('draws the mark without a link when no address was given, and never invents one', () => {
    const markup = chip(FIRST.audit);
    expect(markup).toContain('data-audit-active-run="running"');
    expect(markup).toContain('>Идёт аудит: выполняется<');
    expect(markup).not.toContain('/runs/');
  });

  it('draws nothing for a document with no run in flight or for an answer with no audit', () => {
    expect(chip(QUIET.audit)).not.toContain('Идёт аудит');
    expect(chip(undefined)).toBe('');
  });
});

describe('the cards and the rows', () => {
  const grid = (documents: Parameters<typeof DocumentCardGrid>[0]['documents']) =>
    renderWith(newClient(), createElement(DocumentCardGrid, {
      documents,
      addresses: () => ({ href: '/projects', documentHref: '/projects' }),
      reviewAddress: (runId) => `/projects/${PROJECT_UID}/runs/${runId}/review`,
    }));

  it('puts the mark on each card whose version has a run in flight, linked to that run, and on no other', () => {
    const markup = grid([RERUN, FIRST, CHECKING, QUIET, NO_AUDIT]);
    const marks = [...markup.matchAll(/data-audit-active-run="([a-z]+)"/g)].map((match) => match[1]);
    expect(marks).toEqual(['queued', 'running', 'validating']);
    expect(markup).toContain(`href="/projects/${PROJECT_UID}/runs/${ACTIVE}"`);
    expect(markup).toContain(`href="/projects/${PROJECT_UID}/runs/${ACTIVE.replace('9G', '9H')}"`);
    expect(markup).toContain(`href="/projects/${PROJECT_UID}/runs/${ACTIVE.replace('9G', '9J')}"`);
    expect((markup.match(/>Идёт аудит: /g) ?? []).length).toBe(3);
    // The four states are the ones the server gave, the mark changes none: a first run in flight is still «Не запускался».
    const states = [...markup.matchAll(/data-audit-state="([a-z_]+)"/g)].map((match) => match[1]);
    expect(states).toEqual(['checked', 'not_run', 'awaiting_decision', 'checked']);
    expect(markup).toContain('>Не запускался<');
  });

  it('puts the same mark on a version row', () => {
    const row = (v: typeof RERUN) =>
      renderScreen(newClient(), createElement(VersionRow, { version: v, href: '/projects/x', reviewAddress: (runId: string) => `/r/${runId}/review` }));
    expect(row(CHECKING)).toContain('>Идёт аудит: проверяется<');
    expect(row(CHECKING)).toContain(`href="/projects/${PROJECT_UID}/runs/${ACTIVE.replace('9G', '9J')}"`);
    expect(row(QUIET)).not.toContain('Идёт аудит');
    expect(row(NO_AUDIT)).not.toContain('Идёт аудит');
  });

  it('is on the section page, read from the one listing the page already makes', () => {
    const client = newClient();
    client.setQueryData(
      queryKeys.projects.documents(PROJECT_UID, undefined, DOCUMENT_PAGE_LIMIT, 'AR', false, undefined, undefined, 'audit'),
      page([RERUN, QUIET]),
    );
    const markup = renderWith(client, createElement(SectionDetailPage, { projectUid: PROJECT_UID, sectionCode: 'AR', filter: undefined }));
    expect(markup).toContain('data-document-cards="2"');
    expect(markup.match(/data-audit-active-run=/g)?.length).toBe(1);
    expect(markup).toContain('>Идёт аудит: в очереди<');
  });
});
