/**
 * A comparison-upload PDF is visibly marked as lacking a portal bundle while its ordinary
 * section run remains available through cost approval.
 *
 * Rendered, not read from source (`D-53`): each screen state is rendered through the harness
 * with the field seeded as `comparison_pdf`, as `portal_bundle`, absent, and as a value this
 * client does not know. Only `comparison_pdf` changes anything, and a version without the mark
 * is byte for byte what it was (the absent and the `portal_bundle` markup are compared).
 */

import { createElement } from 'react';
import { describe, expect, it } from 'vitest';

import type { DocumentVersion, VersionUploadKind } from '@/shared/api';
import { VERSION_UPLOAD_KIND_VALUES, queryKeys } from '@/shared/api';
import { RUN_PAGE_LIMIT } from '@/entities/audit-run';
import {
  COMPARISON_ONLY_DETAIL,
  COMPARISON_ONLY_MARK,
  COMPARISON_ONLY_START_NOTE,
  DOCUMENT_PAGE_LIMIT,
  VERSION_PAGE_LIMIT,
  VersionPanel,
  isComparisonOnly,
} from '@/entities/document-version';
import { VersionDetailPage } from '@/_pages/version-detail';
import { DocumentList } from '@/widgets/document-list';
import { ProjectStructureView } from '@/widgets/project-sections';
import { RunList } from '@/widgets/run-list';
import { VersionList } from '@/widgets/version-list';

import { runStatus } from '../review/fixtures';
import { newClient, renderScreen, renderWith, seedError } from '../screens/harness';
import { ApiError } from '@/shared/api';
import { DOCUMENT_UID, PROJECT_UID, VERSION_UID, classification, otherVersion, page, version } from '../sections/fixtures';


const MARK_TEXT = 'PDF без пакета портала';
const MARK = 'data-comparison-only-mark=""';

/** A kind this client has never been told about: it must read as an ordinary version. */
const FUTURE_KIND = 'portal_bundle_v2' as unknown as VersionUploadKind;

const comparison = (over: Partial<DocumentVersion> = {}): DocumentVersion =>
  version({ upload_kind: 'comparison_pdf', ...over });

const countOf = (markup: string, needle: string): number => markup.split(needle).length - 1;

/** The markup of the `<li>` that carries one version's identity. */
function rowOf(markup: string, versionUid: string): string {
  const start = markup.indexOf(`data-version-uid="${versionUid}"`);
  expect(start, `no row for ${versionUid}`).toBeGreaterThan(-1);
  const next = markup.indexOf('data-version-uid="', start + 1);
  return markup.slice(start, next === -1 ? undefined : next);
}

describe('the sentences and the predicate', () => {
  it('says the mark the brief states, in Russian and without a Latin letter', () => {
    expect(COMPARISON_ONLY_MARK).toBe(MARK_TEXT);
    expect(COMPARISON_ONLY_MARK).toContain('PDF');
    expect(COMPARISON_ONLY_START_NOTE).toMatch(/[Ѐ-ӿ]/);
    expect(COMPARISON_ONLY_DETAIL).toMatch(/[Ѐ-ӿ]/);
  });

  it('reads upload_kind and nothing else: only comparison_pdf is comparison-only', () => {
    expect(isComparisonOnly({ upload_kind: 'comparison_pdf' })).toBe(true);
    expect(isComparisonOnly({ upload_kind: 'portal_bundle' })).toBe(false);
    expect(isComparisonOnly({})).toBe(false);
    expect(isComparisonOnly({ upload_kind: FUTURE_KIND })).toBe(false);
  });

  it('covers every value the contract declares', () => {
    // A third value added to the contract must be looked at here, not defaulted in silence.
    expect([...VERSION_UPLOAD_KIND_VALUES].sort()).toEqual(['comparison_pdf', 'portal_bundle']);
  });
});

describe('the version panel', () => {
  const panel = (v: DocumentVersion): string => renderWith(newClient(), createElement(VersionPanel, { version: v }));

  it('carries the mark and the sentence that says what the version is for, for comparison_pdf', () => {
    const markup = panel(comparison());
    expect(markup).toContain(MARK_TEXT);
    expect(countOf(markup, MARK)).toBe(1);
    expect(markup).toContain('data-upload-kind="comparison_pdf"');
    expect(markup).toContain('data-comparison-only-detail=""');
    expect(markup).toContain(COMPARISON_ONLY_DETAIL);
  });

  it('draws the mark as a badge that wraps (the global badge tone, the module layout)', () => {
    const markup = panel(comparison());
    expect(markup).toMatch(/class="am-badge am-badge--degraded [^"]*mark[^"]*"/);
  });

  for (const [name, over] of [
    ['portal_bundle', { upload_kind: 'portal_bundle' as const }],
    ['no field', {}],
    ['an unknown future value', { upload_kind: FUTURE_KIND }],
  ] as const) {
    it(`carries no mark for ${name}`, () => {
      const markup = panel(version(over));
      expect(markup).not.toContain(MARK_TEXT);
      expect(markup).not.toContain(MARK);
      expect(markup).not.toContain('data-comparison-only-detail');
      expect(markup).not.toContain('data-upload-kind');
    });
  }

  it('draws a portal version byte for byte as a version without the field', () => {
    expect(panel(version({ upload_kind: 'portal_bundle' }))).toBe(panel(version()));
  });
});

describe('the lists that draw version rows', () => {
  const PORTAL = version({ display_title: 'Комплект портала' });
  const FLAGGED = otherVersion('C', { upload_kind: 'comparison_pdf', display_title: 'Только для сравнения' });
  const EXPLICIT = otherVersion('D', { upload_kind: 'portal_bundle', display_title: 'Явный пакет портала' });
  const FUTURE = otherVersion('E', { upload_kind: FUTURE_KIND, display_title: 'Будущее значение' });
  const ITEMS = [PORTAL, FLAGGED, EXPLICIT, FUTURE];

  function expectOnlyTheFlaggedRowMarked(markup: string): void {
    expect(countOf(markup, MARK)).toBe(1);
    expect(rowOf(markup, FLAGGED.version_uid)).toContain(MARK_TEXT);
    for (const other of [PORTAL, EXPLICIT, FUTURE]) {
      expect(rowOf(markup, other.version_uid), other.display_title).not.toContain(MARK);
    }
  }

  it("a document's version list marks the comparison row and no other", () => {
    const client = newClient();
    client.setQueryData(queryKeys.versions.list(DOCUMENT_UID, undefined, VERSION_PAGE_LIMIT), page(ITEMS));
    expectOnlyTheFlaggedRowMarked(
      renderScreen(client, createElement(VersionList, { projectUid: PROJECT_UID, documentUid: DOCUMENT_UID })),
    );
  });

  it("the project's document list marks the comparison row and no other", () => {
    const client = newClient();
    client.setQueryData(queryKeys.projects.documents(PROJECT_UID, undefined, DOCUMENT_PAGE_LIMIT), page(ITEMS));
    expectOnlyTheFlaggedRowMarked(
      renderScreen(client, createElement(DocumentList, { projectUid: PROJECT_UID })),
    );
  });

  it('the project structure marks the comparison row in its section and in the unclassified group', () => {
    const classified = otherVersion('F', {
      upload_kind: 'comparison_pdf',
      classification: classification({ version_uid: otherVersion('F').version_uid }),
    });
    const markup = renderScreen(
      newClient(),
      createElement(ProjectStructureView, {
        projectUid: PROJECT_UID,
        items: [PORTAL, FLAGGED, classified],
        hasNextPage: false,
      }),
    );
    expect(countOf(markup, MARK)).toBe(2);
    expect(rowOf(markup, FLAGGED.version_uid)).toContain(MARK_TEXT);
    expect(rowOf(markup, classified.version_uid)).toContain(MARK_TEXT);
    expect(rowOf(markup, PORTAL.version_uid)).not.toContain(MARK);
  });

  it('draws a list of portal versions byte for byte as a list without the field', () => {
    const draw = (items: DocumentVersion[]): string => {
      const client = newClient();
      client.setQueryData(queryKeys.versions.list(DOCUMENT_UID, undefined, VERSION_PAGE_LIMIT), page(items));
      return renderScreen(client, createElement(VersionList, { projectUid: PROJECT_UID, documentUid: DOCUMENT_UID }));
    };
    const bare = [version(), otherVersion('C')];
    const stated = bare.map((v) => ({ ...v, upload_kind: 'portal_bundle' as const }));
    expect(draw(stated)).toBe(draw(bare));
  });
});

describe('ordinary runs on comparison PDFs', () => {
  function runListMarkup(uploadKind?: VersionUploadKind, withRuns = false): string {
    const client = newClient();
    client.setQueryData(queryKeys.runs.list(VERSION_UID, undefined, RUN_PAGE_LIMIT), {
      items: withRuns ? [runStatus()] : [], page: { next_cursor: null },
    });
    return renderScreen(client, createElement(RunList, {
      projectUid: PROJECT_UID, versionUid: VERSION_UID, uploadKind,
    }));
  }

  for (const withRuns of [false, true]) {
    it(`offers cost approval for a comparison PDF with runs=${withRuns}`, () => {
      const markup = runListMarkup('comparison_pdf', withRuns);
      expect(markup).toContain('data-start-run-control');
      expect(markup).toContain('Анализ будет выполнен по исходному PDF');
      expect(markup).not.toContain('data-start-run-disabled');
      if (withRuns) expect(markup).toContain('data-run-count="1"');
    });
  }

  it('keeps the ordinary portal run list unchanged', () => {
    expect(runListMarkup('portal_bundle', true)).toBe(runListMarkup(undefined, true));
  });

  it('does not mount a start while the list is loading or failed', () => {
    const loading = renderScreen(newClient(), createElement(RunList, {
      projectUid: PROJECT_UID, versionUid: VERSION_UID, uploadKind: 'comparison_pdf',
    }));
    expect(loading).not.toContain('data-start-run-control');
    const failed = newClient();
    seedError(failed, queryKeys.runs.list(VERSION_UID, undefined, RUN_PAGE_LIMIT),
      new ApiError(503, { contract_version: '1.14.0', error_code: 'dependency_unavailable',
        message: 'm', correlation_id: 'c', retryable: true }, 'c'));
    expect(renderScreen(failed, createElement(RunList, {
      projectUid: PROJECT_UID, versionUid: VERSION_UID, uploadKind: 'comparison_pdf',
    }))).not.toContain('data-start-run-control');
  });
});

describe('the version screen', () => {
  function screen(v: DocumentVersion): string {
    const client = newClient();
    client.setQueryData(queryKeys.versions.detail(VERSION_UID), v);
    client.setQueryData(queryKeys.runs.list(VERSION_UID, undefined, RUN_PAGE_LIMIT), {
      items: [], page: { next_cursor: null },
    });
    return renderScreen(client, createElement(VersionDetailPage, {
      projectUid: PROJECT_UID, versionUid: VERSION_UID, roles: ['expert'],
    }));
  }

  it('marks a comparison PDF and offers its ordinary run', () => {
    const markup = screen(comparison());
    expect(markup).toContain(MARK_TEXT);
    expect(markup).toContain('data-start-run-control');
    expect(markup).toContain('Сравнить два прогона');
    expect(markup).toContain('href="/stage-comparison"');
    expect(markup).toContain('href="/version-comparison"');
  });

  it('does not offer a run before the version kind is read', () => {
    const client = newClient();
    client.setQueryData(queryKeys.runs.list(VERSION_UID, undefined, RUN_PAGE_LIMIT), {
      items: [], page: { next_cursor: null },
    });
    expect(renderScreen(client, createElement(VersionDetailPage, {
      projectUid: PROJECT_UID, versionUid: VERSION_UID, roles: ['expert'],
    }))).not.toContain('data-start-run-control');
  });
});
