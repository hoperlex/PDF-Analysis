/**
 * «Скачать пакет аудита» on «Разбор находок» (`UI-A-76`): what the run's ZIP is made of, what is said when it cannot be
 * made, and that it is offered where the CSV is and only to the session that may export.
 *
 * The archive itself is the evidence-package builder's (`tests/unit/export/evidence-package-names.test.ts` and the
 * comparison suites hold its rules); here the builder is replaced by a recorder, so these tests read exactly which files
 * and which source the page asks it to pack.
 */

import { createElement } from 'react';
import { describe, expect, it } from 'vitest';

import type { ErrorCode, ErrorEnvelope, ExtendedRunReview, RunId, VersionUid } from '@/shared/api';
import { ApiError, EXPORTABLE_RUN_STATES, RUN_STATE_VALUES, csvFileName, isExportableRunState } from '@/shared/api';
import type { DownloadSink } from '@/features/export-run';
import { EvidencePackageError } from '@/features/export-evidence-package';
import type { EvidencePackageOptions } from '@/features/export-evidence-package';
import {
  AUDIT_PACKAGE_TITLE, AuditPackageDownload, AuditPackageStepError, ExportPanel, auditPackageDoneLine, auditPackageFailure,
  buildAuditPackage,
} from '@/widgets/export-panel';
import type { AuditPackageDeps } from '@/widgets/export-panel';

import { mountLive } from '../analysis-settings/live-render';
import { RUN_ID, VERSION_UID, render } from '../review/fixtures';

const RUN = RUN_ID as RunId;
const VERSION = VERSION_UID as VersionUid;

function reading(overrides: Partial<ExtendedRunReview> = {}): ExtendedRunReview {
  return {
    run_id: RUN,
    status: 'completed',
    result: {
      version_uid: VERSION,
      observations: [{ observation_id: 'o1', title: 'Первое', description: 'Описание', source_ids: [] }],
    },
    ...overrides,
  };
}

/** Deps that record what the builder was asked to pack. */
function deps(extended: ExtendedRunReview | Error, overrides: Partial<AuditPackageDeps> = {}) {
  const asked: EvidencePackageOptions[] = [];
  const value: AuditPackageDeps = {
    exportCsv: async () => new Blob(['﻿run_id\r\n']),
    readExtended: async () => { if (extended instanceof Error) throw extended; return extended; },
    build: async (options) => { asked.push(options); return { blob: new Blob(['zip']), fileName: options.fileName }; },
    ...overrides,
  };
  return { value, asked };
}

function refusal(status: number, code: ErrorCode): ApiError {
  const envelope: ErrorEnvelope = {
    contract_version: '1.49.0', error_code: code, message: 'English the client never prints.',
    correlation_id: 'cid-pkg-1', retryable: false, details: {},
  };
  return new ApiError(status, envelope, 'cid-pkg-1');
}

describe('what the package of a run is made of', () => {
  it('packs the server CSV, the four reports of the extended record and the PDF of the run’s version', async () => {
    const { value, asked } = deps(reading());
    const built = await buildAuditPackage({ runId: RUN, versionUid: VERSION, signal: new AbortController().signal, deps: value });
    expect(asked).toHaveLength(1);
    const options = asked[0] as EvidencePackageOptions;
    expect(options.kind).toBe('section-analysis');
    expect(options.runId).toBe(RUN);
    expect(options.fileName).toBe(`audit-package-${RUN}.zip`);
    expect(options.sources).toEqual([{ versionUid: VERSION, side: 'SOURCE' }]);
    expect(options.reports.map((report) => report.name)).toEqual([
      csvFileName(RUN), `analysis-${RUN}.md`, `analysis-${RUN}.html`, `analysis-${RUN}.json`, `analysis-${RUN}-technical.xlsx`,
    ]);
    expect(built.summary).toMatchObject({ extended: 'included', extendedStatus: 'completed', fileName: options.fileName });
  });

  it('packs the CSV and the PDF alone for a run without an extended record, and says so', async () => {
    for (const empty of [reading({ status: 'unavailable', result: null }), reading({ result: { version_uid: VERSION, observations: [] } })]) {
      const { value, asked } = deps(empty);
      const built = await buildAuditPackage({ runId: RUN, versionUid: VERSION, signal: new AbortController().signal, deps: value });
      expect((asked[0] as EvidencePackageOptions).reports.map((report) => report.name)).toEqual([csvFileName(RUN)]);
      expect(built.summary.extended).toBe('absent');
      expect(auditPackageDoneLine(built.summary)).toContain('только CSV находок');
    }
  });

  it('says an unfinished extended record is not final', async () => {
    const { value } = deps(reading({ status: 'running' }));
    const built = await buildAuditPackage({ runId: RUN, versionUid: VERSION, signal: new AbortController().signal, deps: value });
    expect(auditPackageDoneLine(built.summary)).toContain('ещё не окончательная');
  });

  it('refuses a record of another version than the run’s: no report of one document beside the PDF of another', async () => {
    const other = reading({ result: { version_uid: 'ver_01J9ZQ8K7NHVXW3T2R5M6P4Q8C', observations: [{ observation_id: 'o1' }] } });
    const { value, asked } = deps(other);
    const failure = await buildAuditPackage({ runId: RUN, versionUid: VERSION, signal: new AbortController().signal, deps: value })
      .then(() => null, (error: unknown) => error);
    expect(failure).toBeInstanceOf(AuditPackageStepError);
    expect(asked).toHaveLength(0);
    expect(auditPackageFailure(failure).detail).toContain('другой версии документа');
  });

  it('reports each phase it passes, in order, ending with the builder’s', async () => {
    const seen: string[] = [];
    const { value } = deps(reading(), {
      build: async (options) => { options.onProgress?.({ phase: 'sources', completed: 0, total: 1 }); return { blob: new Blob(['z']), fileName: options.fileName }; },
    });
    await buildAuditPackage({
      runId: RUN, versionUid: VERSION, signal: new AbortController().signal, deps: value,
      onProgress: (progress) => { seen.push(`${progress.phase}:${progress.completed}/${progress.total}`); },
    });
    expect(seen).toEqual(['csv:0/1', 'csv:1/1', 'extended:0/1', 'extended:1/1', 'sources:0/1']);
  });
});

describe('when the package cannot be made', () => {
  it('names the CSV when the server refuses it, with the correlation id, and builds nothing', async () => {
    const { value, asked } = deps(reading(), { exportCsv: async () => { throw refusal(403, 'permission_denied'); } });
    const failure = await buildAuditPackage({ runId: RUN, versionUid: VERSION, signal: new AbortController().signal, deps: value })
      .then(() => null, (error: unknown) => error);
    expect(asked).toHaveLength(0);
    const shown = auditPackageFailure(failure);
    expect(shown.title).toBe('Пакет аудита не собран');
    expect(shown.detail).toContain('Не удалось получить CSV находок');
    expect(shown.detail).toContain('Неполный ZIP не скачивается');
    expect(shown.correlationId).toBe('cid-pkg-1');
  });

  it('names the extended record when its read fails, and never packs a package without the record it could not read', async () => {
    const { value, asked } = deps(refusal(503, 'dependency_unavailable'));
    const failure = await buildAuditPackage({ runId: RUN, versionUid: VERSION, signal: new AbortController().signal, deps: value })
      .then(() => null, (error: unknown) => error);
    expect(asked).toHaveLength(0);
    expect(auditPackageFailure(failure).detail).toContain('Не удалось получить запись расширенного анализа');
  });

  it('carries the builder’s own refusal (a source that is not whole, a package over the limit)', () => {
    const shown = auditPackageFailure(new EvidencePackageError('package_too_large', 'Полный пакет превышает 64 МиБ. Пакет не создан; исходные PDF не исключались.'));
    expect(shown.detail).toContain('превышает 64 МиБ');
    expect(shown.detail).toContain('Неполный ZIP не скачивается');
  });

  it('lets a cancellation through as it is, not as a failed step', async () => {
    const controller = new AbortController();
    const { value } = deps(reading(), { exportCsv: async () => { controller.abort(); throw new DOMException('x', 'AbortError'); } });
    const failure = await buildAuditPackage({ runId: RUN, versionUid: VERSION, signal: controller.signal, deps: value })
      .then(() => null, (error: unknown) => error);
    expect(failure).toBeInstanceOf(DOMException);
  });
});

describe('the button', () => {
  function panel(runState: (typeof RUN_STATE_VALUES)[number], overrides: Record<string, unknown> = {}) {
    return render(createElement(ExportPanel, { runId: RUN, runState, providerMode: 'recorded', onExport: () => {}, ...overrides }));
  }

  it.each(EXPORTABLE_RUN_STATES)('is offered beside the CSV for %s when the page names the version', (state) => {
    const markup = panel(state, { auditPackage: { versionUid: VERSION } });
    expect(markup).toContain('data-intent="export-audit-package"');
    expect(markup).toContain('Скачать пакет аудита');
    // It says what the archive holds before the first press.
    expect(markup).toContain('title="ZIP одного прогона: CSV находок');
    expect(AUDIT_PACKAGE_TITLE).toContain('manifest.json');
  });

  it('is not offered to a session that may not export, nor for a run without a result', () => {
    expect(panel('published')).not.toContain('export-audit-package');
    for (const state of RUN_STATE_VALUES.filter((candidate) => !isExportableRunState(candidate))) {
      expect(panel(state, { auditPackage: { versionUid: VERSION } })).not.toContain('export-audit-package');
    }
  });

  it('builds, hands the file to the browser once and says what it holds; a second press while it builds does nothing', async () => {
    const saved: string[] = [];
    const sink: DownloadSink = {
      createObjectUrl: () => 'blob:pkg',
      saveAs: (_url, fileName) => { saved.push(fileName); },
      revokeObjectUrl: () => {},
    };
    const { value, asked } = deps(reading());
    const live = await mountLive(createElement(AuditPackageDownload, { runId: RUN, versionUid: VERSION, sink, deps: value }));
    try {
      expect(await live.press('Скачать пакет аудита')).toBe(true);
      expect(asked).toHaveLength(1);
      expect(saved).toEqual([`audit-package-${RUN}.zip`]);
      expect(live.markup()).toContain('data-audit-package-status');
      expect(live.markup()).toContain('исходный PDF и манифест');
    } finally {
      await live.unmount();
    }
  });

  it('shows the refusal in the page and saves nothing when a part cannot be read', async () => {
    const saved: string[] = [];
    const sink: DownloadSink = { createObjectUrl: () => 'blob:pkg', saveAs: (_url, name) => { saved.push(name); }, revokeObjectUrl: () => {} };
    const { value } = deps(reading(), { exportCsv: async () => { throw refusal(403, 'permission_denied'); } });
    const live = await mountLive(createElement(AuditPackageDownload, { runId: RUN, versionUid: VERSION, sink, deps: value }));
    try {
      await live.press('Скачать пакет аудита');
      expect(saved).toEqual([]);
      expect(live.markup()).toContain('Пакет аудита не собран');
      expect(live.markup()).toContain('Не удалось получить CSV находок');
    } finally {
      await live.unmount();
    }
  });
});
