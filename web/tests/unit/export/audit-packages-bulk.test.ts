/**
 * `UIP-S02-05`, `Г12-B`: «Скачать пакеты аудита» in the bottom bar of a section — the audit packages of the chosen documents in one ZIP,
 * built in the browser.
 *
 * Each package is the single builder's (`tests/unit/export/audit-package.test.ts` holds its rules), so here that builder is replaced by a
 * recorder and the common archive is the real one, read back byte by byte: what the archive holds, which documents were left out and
 * why, the limit in words, and that a document that cannot be packed stops the whole ZIP instead of dropping out of it.
 */

import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { QueryClientProvider } from '@tanstack/react-query';
import { afterEach, describe, expect, it } from 'vitest';

import type { DocumentVersion, RunId, VersionUid } from '@/shared/api';
import { ApiError } from '@/shared/api';
import type { DownloadSink } from '@/features/export-run';
import {
  EVIDENCE_BUNDLE_MAX_BYTES, EvidencePackageError, buildEvidenceBundle,
} from '@/features/export-evidence-package';
import type { EvidenceBundleOptions } from '@/features/export-evidence-package';
import { SectionSelectionBar, SectionSelectionBarView, bulkTargets } from '@/_pages/section-detail';
import type { SectionBulk } from '@/_pages/section-detail';
import {
  AUDIT_PACKAGES_LIMIT, AUDIT_PACKAGES_TITLE, AuditPackagesDocumentError, AuditPackagesRefused, auditPackagesDoneLine,
  auditPackagesFailure, auditPackagesProgressLine, auditPackagesRefusal, buildAuditPackages, splitAuditPackages,
} from '@/widgets/export-panel';
import type { AuditPackageSummary, AuditPackagesDeps, AuditPackagesDocument, AuditPackagesProgress } from '@/widgets/export-panel';
import type { BatchSelection } from '@/widgets/project-sections';

import type { LiveRender } from '../analysis-settings/live-render';
import { mountLive } from '../analysis-settings/live-render';
import { newClient } from '../screens/harness';
import { PROJECT_UID, apiError, classification, otherVersion } from '../sections/fixtures';

const runOf = (suffix: string): RunId => `run_01J9ZQ8K7NHVXW3T2R5M6P4Q${suffix}` as RunId;

const withResult = (suffix: string): DocumentVersion => otherVersion(suffix, {
  classification: classification({ section_code: 'AR' }),
  audit: { state: 'checked', partial: false, finding_count: 3, undecided_finding_count: 0, result_run_id: runOf(suffix) },
});
const withoutResult = (suffix: string): DocumentVersion => otherVersion(suffix, {
  classification: classification({ section_code: 'AR' }),
  audit: { state: 'not_run', partial: false, finding_count: 0, undecided_finding_count: 0 },
});

const A = withResult('A');
const B = withoutResult('B');
const C = withResult('C');

const asDocument = (version: DocumentVersion): AuditPackagesDocument => ({
  documentUid: version.document_uid,
  versionUid: version.version_uid as VersionUid,
  title: version.display_title ?? '',
  runId: version.audit?.result_run_id,
});

// ------------------------------------------------------------------ a reader for the archive the builder writes (STORE, one pass)

function crc32(data: Uint8Array): number {
  let value = 0xFFFFFFFF;
  for (const byte of data) {
    value ^= byte;
    for (let bit = 0; bit < 8; bit += 1) value = value & 1 ? 0xEDB88320 ^ (value >>> 1) : value >>> 1;
  }
  return (value ^ 0xFFFFFFFF) >>> 0;
}

/** Every entry of the archive by name, read from its central directory, each checked against its CRC-32. */
async function entriesOf(blob: Blob): Promise<Map<string, Uint8Array>> {
  const bytes = new Uint8Array(await blob.arrayBuffer());
  const view = new DataView(bytes.buffer);
  const end = bytes.length - 22;
  expect(view.getUint32(end, true)).toBe(0x06054B50);
  const count = view.getUint16(end + 10, true);
  let at = view.getUint32(end + 16, true);
  const entries = new Map<string, Uint8Array>();
  for (let index = 0; index < count; index += 1) {
    expect(view.getUint32(at, true)).toBe(0x02014B50);
    const crc = view.getUint32(at + 16, true);
    const size = view.getUint32(at + 24, true);
    const nameLength = view.getUint16(at + 28, true);
    const local = view.getUint32(at + 42, true);
    const name = new TextDecoder().decode(bytes.subarray(at + 46, at + 46 + nameLength));
    const start = local + 30 + view.getUint16(local + 26, true) + view.getUint16(local + 28, true);
    const data = bytes.slice(start, start + size);
    expect(crc32(data), `crc of ${name}`).toBe(crc);
    entries.set(name, data);
    at += 46 + nameLength + view.getUint16(at + 30, true) + view.getUint16(at + 32, true);
  }
  return entries;
}

const text = (bytes: Uint8Array | undefined): string => new TextDecoder().decode(bytes);

async function sha256Hex(bytes: Uint8Array): Promise<string> {
  const digest = await globalThis.crypto.subtle.digest('SHA-256', bytes as Uint8Array<ArrayBuffer>);
  return Array.from(new Uint8Array(digest), (byte) => byte.toString(16).padStart(2, '0')).join('');
}

// ------------------------------------------------------------------ the single builder, replaced

const summaryOf = (runId: string): AuditPackageSummary => ({
  fileName: `audit-package-${runId}.zip`, reports: [`${runId}-findings.csv`], extended: 'absent', extendedStatus: null,
});

/** A builder of one package that records what it was asked for and returns bytes named after the run. */
function recorder(over: Partial<Record<string, Error>> = {}) {
  const asked: Array<{ runId: string; versionUid: string }> = [];
  const buildPackage: AuditPackagesDeps['buildPackage'] = async (args) => {
    asked.push({ runId: args.runId, versionUid: args.versionUid });
    args.onProgress?.({ phase: 'csv', completed: 0, total: 1 });
    const failure = over[args.runId];
    if (failure !== undefined) throw failure;
    return { blob: new Blob([`package of ${args.runId}`]), summary: summaryOf(args.runId) };
  };
  return { asked, buildPackage };
}

const signal = (): AbortSignal => new AbortController().signal;

// ------------------------------------------------------------------ what is chosen

describe('what is packed and what is left out', () => {
  it('gives a package to every chosen document with a result, in the order chosen, and skips the ones with none', () => {
    const split = splitAuditPackages([C, B, A].map(asDocument));
    expect(split.packable.map((document) => document.runId)).toEqual([runOf('C'), runOf('A')]);
    expect(split.skipped.map((document) => document.documentUid)).toEqual([B.document_uid]);
  });

  it('reads the chosen versions back to their result runs from the documents the page showed', () => {
    const known = new Map([A, B, C].map((version) => [version.version_uid, version] as const));
    const { packages } = bulkTargets(new Set([A.version_uid, B.version_uid]), known);
    expect(packages.packable.map((document) => document.versionUid)).toEqual([A.version_uid]);
    expect(packages.skipped.map((document) => document.title)).toEqual([B.display_title]);
    // an archived document keeps its result, so it keeps its package
    const archived = { ...A, archived_at: '2026-11-17T09:00:00Z' };
    expect(bulkTargets(new Set([A.version_uid]), new Map([[A.version_uid, archived]])).packages.packable).toHaveLength(1);
  });

  it('says in words why a choice cannot be packed: no result among them, or more than the limit', () => {
    expect(auditPackagesRefusal(splitAuditPackages([B].map(asDocument)))).toContain('нет результата аудита');
    expect(auditPackagesRefusal(splitAuditPackages([A, B].map(asDocument)))).toBeNull();
    const many = Array.from({ length: AUDIT_PACKAGES_LIMIT }, (_, n) => asDocument(withResult(`${n}`)));
    expect(auditPackagesRefusal(splitAuditPackages(many))).toBeNull();
    const over = auditPackagesRefusal(splitAuditPackages([...many, asDocument(C)]));
    expect(over).toContain(`не больше чем для ${AUDIT_PACKAGES_LIMIT} документов`);
    expect(over).toContain(`выбрано ${AUDIT_PACKAGES_LIMIT + 1}`);
  });

  it('counts only the documents with a result against the limit: the skipped ones cost nothing', () => {
    const many = Array.from({ length: AUDIT_PACKAGES_LIMIT }, (_, n) => asDocument(withResult(`${n}`)));
    const skipped = Array.from({ length: 30 }, (_, n) => asDocument(withoutResult(`S${n}`)));
    expect(auditPackagesRefusal(splitAuditPackages([...many, ...skipped]))).toBeNull();
  });
});

// ------------------------------------------------------------------ the common archive

describe('the common ZIP', () => {
  it('holds the package of each document with a result, as the file the single builder made, and an index of what it holds', async () => {
    const { asked, buildPackage } = recorder();
    const { blob, summary } = await buildAuditPackages({
      documents: [A, B, C].map(asDocument), fileName: 'audit-packages-AR.zip', signal: signal(), deps: { buildPackage, bundle: buildEvidenceBundle },
    });
    // one package per document with a result, sequentially, for the run and the version of that document
    expect(asked).toEqual([{ runId: runOf('A'), versionUid: A.version_uid }, { runId: runOf('C'), versionUid: C.version_uid }]);
    expect(summary.fileName).toBe('audit-packages-AR.zip');
    expect(summary.packed.map((item) => item.entryName)).toEqual([`audit-package-${runOf('A')}.zip`, `audit-package-${runOf('C')}.zip`]);
    expect(summary.skipped.map((document) => document.documentUid)).toEqual([B.document_uid]);

    const entries = await entriesOf(blob);
    expect([...entries.keys()]).toEqual([`audit-package-${runOf('A')}.zip`, `audit-package-${runOf('C')}.zip`, 'index.json']);
    expect(text(entries.get(`audit-package-${runOf('A')}.zip`))).toBe(`package of ${runOf('A')}`);
    expect(text(entries.get(`audit-package-${runOf('C')}.zip`))).toBe(`package of ${runOf('C')}`);

    const index = JSON.parse(text(entries.get('index.json'))) as Record<string, unknown> & {
      files: Array<{ entry_name: string; byte_size: number; sha256: string }>;
      packages: Array<Record<string, unknown>>;
      skipped: Array<Record<string, unknown>>;
    };
    expect(index).toMatchObject({ format: 'auditmanager-audit-packages-v1', kind: 'audit-packages', expert_review_required: true, all_requested_packages_included: true });
    expect(index.packages.map((item) => [item.document_uid, item.version_uid, item.run_id, item.entry_name])).toEqual([
      [A.document_uid, A.version_uid, runOf('A'), `audit-package-${runOf('A')}.zip`],
      [C.document_uid, C.version_uid, runOf('C'), `audit-package-${runOf('C')}.zip`],
    ]);
    expect(index.skipped).toEqual([{ document_uid: B.document_uid, version_uid: B.version_uid, title: B.display_title, reason: 'no_result_run' }]);
    // each file's size and digest are measured from the bytes the archive holds
    for (const file of index.files) {
      const bytes = entries.get(file.entry_name) as Uint8Array;
      expect(file.byte_size).toBe(bytes.length);
      expect(file.sha256).toBe(await sha256Hex(bytes));
    }
  });

  it('is not built, and not one package is read, when nothing chosen has a result or more than the limit is chosen', async () => {
    const { asked, buildPackage } = recorder();
    const run = (documents: readonly AuditPackagesDocument[]) =>
      buildAuditPackages({ documents, fileName: 'x.zip', signal: signal(), deps: { buildPackage, bundle: buildEvidenceBundle } })
        .then(() => null, (error: unknown) => error);
    const none = await run([B].map(asDocument));
    expect(none).toBeInstanceOf(AuditPackagesRefused);
    expect((none as AuditPackagesRefused).kind).toBe('nothing');
    const many = Array.from({ length: AUDIT_PACKAGES_LIMIT + 1 }, (_, n) => asDocument(withResult(`${n}`)));
    const over = await run(many);
    expect(over).toBeInstanceOf(AuditPackagesRefused);
    expect((over as AuditPackagesRefused).kind).toBe('too_many');
    expect(asked).toHaveLength(0);
    expect(auditPackagesFailure(over).detail).toContain(`не больше чем для ${AUDIT_PACKAGES_LIMIT} документов`);
  });

  it('is not built when the package of one document cannot be, and names that document: no archive without a file of it', async () => {
    const refusal = apiError(403, 'permission_denied');
    const { asked, buildPackage } = recorder({ [runOf('C')]: refusal });
    let bundled = 0;
    const bundle: AuditPackagesDeps['bundle'] = async (options) => { bundled += 1; return buildEvidenceBundle(options); };
    const failure = await buildAuditPackages({
      documents: [A, C].map(asDocument), fileName: 'x.zip', signal: signal(), deps: { buildPackage, bundle },
    }).then(() => null, (error: unknown) => error);
    expect(asked).toHaveLength(2);
    expect(bundled).toBe(0);
    expect(failure).toBeInstanceOf(AuditPackagesDocumentError);
    const shown = auditPackagesFailure(failure);
    expect(shown.title).toBe('Пакеты аудита не собраны');
    expect(shown.detail).toContain(`«${C.display_title}»`);
    expect(shown.detail).toContain('Общий ZIP не создан');
    expect(shown.detail).not.toContain(`«${A.display_title}»`);
  });

  it('carries the correlation id of the document’s refusal, and lets a cancellation through as it is', async () => {
    const withId = new ApiError(503, {
      contract_version: '1.59.0', error_code: 'dependency_unavailable', message: 'English.', correlation_id: 'cid-bulk-1', retryable: false,
    }, 'cid-bulk-1');
    const failed = await buildAuditPackages({
      documents: [asDocument(A)], fileName: 'x.zip', signal: signal(), deps: { buildPackage: recorder({ [runOf('A')]: withId }).buildPackage, bundle: buildEvidenceBundle },
    }).then(() => null, (error: unknown) => error);
    expect(auditPackagesFailure(failed).correlationId).toBeTruthy();

    const controller = new AbortController();
    const cancelled = await buildAuditPackages({
      documents: [asDocument(A)], fileName: 'x.zip', signal: controller.signal,
      deps: { buildPackage: async () => { controller.abort(); throw new DOMException('x', 'AbortError'); }, bundle: buildEvidenceBundle },
    }).then(() => null, (error: unknown) => error);
    expect(cancelled).toBeInstanceOf(DOMException);
  });

  it('stops before the next package when the packages together are more than the archive may hold', async () => {
    const big: AuditPackagesDeps['buildPackage'] = async (args) => ({
      // only its size is read; the bytes are never allocated
      blob: { size: EVIDENCE_BUNDLE_MAX_BYTES / 2 + 1 } as Blob,
      summary: summaryOf(args.runId),
    });
    let asked = 0;
    const counting: AuditPackagesDeps['buildPackage'] = async (args) => { asked += 1; return big(args); };
    const failure = await buildAuditPackages({
      documents: [A, C, withResult('D')].map(asDocument), fileName: 'x.zip', signal: signal(), deps: { buildPackage: counting, bundle: buildEvidenceBundle },
    }).then(() => null, (error: unknown) => error);
    expect(failure).toBeInstanceOf(EvidencePackageError);
    expect((failure as EvidencePackageError).code).toBe('package_too_large');
    expect(asked).toBe(2);
    expect(auditPackagesFailure(failure).detail).toContain('Архив не создан');
  });

  it('says which document it is on, and each phase of it, then the archive', async () => {
    const seen: string[] = [];
    const { buildPackage } = recorder();
    await buildAuditPackages({
      documents: [A, C].map(asDocument), fileName: 'x.zip', signal: signal(), deps: { buildPackage, bundle: buildEvidenceBundle },
      onProgress: (progress: AuditPackagesProgress) => { seen.push(auditPackagesProgressLine(progress)); },
    });
    expect(seen.slice(0, 2)).toEqual([
      'Документ 1 из 2 «Документ A»: Получение CSV замечаний · 0 из 1',
      'Документ 2 из 2 «Документ C»: Получение CSV замечаний · 0 из 1',
    ]);
    expect(seen.at(-1)).toMatch(/^Сборка общего ZIP · \d+ из 3$/);
  });

  it('says what it holds, and how many documents had no result, in one sentence', () => {
    const packed = [A, C].map((version) => ({ document: { ...asDocument(version), runId: version.audit?.result_run_id as RunId }, entryName: 'e.zip', package: summaryOf('r') }));
    expect(auditPackagesDoneLine({ fileName: 'audit-packages-AR.zip', packed, skipped: [] })).toBe('audit-packages-AR.zip: 2 пакетов аудита и index.json.');
    expect(auditPackagesDoneLine({ fileName: 'a.zip', packed: packed.slice(0, 1), skipped: [asDocument(B)] }))
      .toContain('Пропущено документов без результата аудита: 1');
  });
});

describe('the bundle writer on its own', () => {
  const file = (name: string, content = 'x') => ({ name, content: new Blob([content]) });
  const options = (over: Partial<EvidenceBundleOptions> = {}): EvidenceBundleOptions => ({ fileName: 'b.zip', files: [file('a.zip')], index: {}, ...over });

  it('refuses names that repeat, a name with a path and the name of its own index', async () => {
    for (const files of [[file('a.zip'), file('A.ZIP')], [file('../a.zip')], [file('index.json')]]) {
      const failure = await buildEvidenceBundle(options({ files })).then(() => null, (error: unknown) => error);
      expect(failure).toBeInstanceOf(EvidencePackageError);
      expect((failure as EvidencePackageError).code).toBe('invalid_request');
    }
  });

  it('refuses a file larger than the archive may hold, before it reads it', async () => {
    class Huge extends Blob { override get size(): number { return EVIDENCE_BUNDLE_MAX_BYTES + 1; } }
    const failure = await buildEvidenceBundle(options({ files: [{ name: 'a.zip', content: new Huge(['x']) }] })).then(() => null, (error: unknown) => error);
    expect((failure as EvidencePackageError).code).toBe('package_too_large');
    expect((failure as EvidencePackageError).message).toContain('256 МиБ');
  });

  it('lets the caller say what each file is but never what the archive’s format is', async () => {
    const { blob } = await buildEvidenceBundle(options({ index: { kind: 'x', format: 'something-else', files: 'nope' } }));
    const index = JSON.parse(text((await entriesOf(blob)).get('index.json'))) as { kind: string; format: string; files: unknown[] };
    expect(index.kind).toBe('x');
    expect(index.format).toBe('auditmanager-audit-packages-v1');
    expect(Array.isArray(index.files)).toBe(true);
  });

  it('stops when it is cancelled', async () => {
    const controller = new AbortController();
    controller.abort();
    const failure = await buildEvidenceBundle(options({ signal: controller.signal })).then(() => null, (error: unknown) => error);
    expect(failure).toBeInstanceOf(DOMException);
  });
});

// ------------------------------------------------------------------ the button in the bar

describe('the button in the bottom bar', () => {
  const noop = (): void => undefined;
  const selection = (count: number, over: Partial<BatchSelection> = {}): BatchSelection => ({
    selection: { selected: new Set<string>(), onToggle: noop },
    chosenCount: count, batch: null, choose: noop, clear: noop, openBatch: noop, closeBatch: noop, ...over,
  });
  const bulk = (over: Partial<SectionBulk['packages']> = {}): SectionBulk => ({
    archive: { count: 0, pending: false, progress: null, report: null, onArchive: noop, onDismiss: noop },
    packages: {
      count: 2, skippedCount: 1, refusal: null, pending: false, status: null, summary: null, error: null,
      onDownload: noop, onCancel: noop, onDismiss: noop, ...over,
    },
  });
  const bar = (chosen: BatchSelection, packages?: SectionBulk) =>
    renderToStaticMarkup(createElement(SectionSelectionBarView, { selection: chosen, bulk: packages }));

  it('is «Скачать пакеты аудита», says what the archive holds before the press, and stands between «Запустить все» and «Снять выделение»', () => {
    const markup = bar(selection(3), bulk());
    expect(markup).toMatch(/<button type="button"[^>]*data-audit-packages[^>]*>Скачать пакеты аудита<\/button>/);
    expect(markup).toContain(`title="${AUDIT_PACKAGES_TITLE}"`);
    expect(markup.indexOf('Запустить все')).toBeLessThan(markup.indexOf('Скачать пакеты аудита'));
    expect(markup.indexOf('Скачать пакеты аудита')).toBeLessThan(markup.indexOf('Снять выделение'));
    expect(markup).not.toContain('data-audit-packages-refusal');
  });

  it('is not drawn to a session that cannot act, nor without the actions, nor when no chosen document has a result', () => {
    expect(bar(selection(3, { selection: undefined }), bulk())).toBe('');
    expect(bar(selection(3))).not.toContain('Скачать пакеты аудита');
    const none = bar(selection(3), bulk({ count: 0, skippedCount: 3, refusal: 'У выбранных документов нет результата аудита: пакеты собирать не из чего.' }));
    expect(none).not.toContain('Скачать пакеты аудита');
    expect(none).not.toContain('data-audit-packages-refusal');
    // it can fail: the same bar with one document that has a result draws it
    expect(bar(selection(3), bulk({ count: 1 }))).toContain('Скачать пакеты аудита');
  });

  it('is held, with the limit said in words beside it and in its tooltip, when too many are chosen', () => {
    const refusal = `Пакеты аудита собираются не больше чем для ${AUDIT_PACKAGES_LIMIT} документов с результатом за раз: выбрано 23. Уберите лишние из выбора.`;
    const markup = bar(selection(23), bulk({ count: 23, refusal }));
    expect(markup).toMatch(/<button[^>]*disabled=""[^>]*data-audit-packages[^>]*>/);
    expect(markup).toContain(`title="${refusal}"`);
    expect(markup).toMatch(/<p[^>]*data-audit-packages-refusal[^>]*>Пакеты аудита собираются не больше чем для 20/);
  });

  it('shows the document it is on and a way to stop, while it builds', () => {
    const markup = bar(selection(3), bulk({ pending: true, status: 'Документ 1 из 2 «Документ A»: Получение CSV замечаний · 0 из 1' }));
    expect(markup).toMatch(/<button[^>]*disabled=""[^>]*data-audit-packages[^>]*>Собираю пакеты…<\/button>/);
    expect(markup).toMatch(/<button[^>]*data-audit-packages-cancel[^>]*>Отменить<\/button>/);
    expect(markup).toMatch(/<p[^>]*role="status"[^>]*data-audit-packages-progress[^>]*>Документ 1 из 2 «Документ A»/);
  });

  it('lists the skipped documents after the download, and keeps the message when nothing is chosen any more', () => {
    const summary = { fileName: 'audit-packages-AR.zip', packed: [], skipped: [asDocument(B)] };
    const markup = bar(selection(0), bulk({ status: 'audit-packages-AR.zip: 1 пакет аудита и index.json.', summary }));
    expect(markup).toContain('data-audit-packages-status="done"');
    expect(markup).toContain(`data-audit-packages-skipped-document="${B.document_uid}"`);
    expect(markup).toContain('нет результата аудита');
    expect(markup).toMatch(/<button[^>]*data-audit-packages-dismiss[^>]*>Закрыть<\/button>/);
    expect(markup).not.toContain('Выбрано:');
    expect(bar(selection(0), bulk())).toBe('');
  });

  it('shows why no archive was built, with the same refusal block the single download uses', () => {
    const markup = bar(selection(2), bulk({ error: { title: 'Пакеты аудита не собраны', detail: 'Документ «Документ A»: нет. Общий ZIP не создан.', correlationId: 'cid-1' } }));
    expect(markup).toContain('data-audit-packages-error');
    expect(markup).toContain('role="alert"');
    expect(markup).toContain('Общий ZIP не создан');
  });
});

describe('pressing «Скачать пакеты аудита»', () => {
  let live: LiveRender | null = null;
  afterEach(async () => {
    await live?.unmount();
    live = null;
  });

  function chosen(versions: readonly DocumentVersion[]): BatchSelection {
    return {
      selection: { selected: new Set(versions.map((version) => version.version_uid)), onToggle: () => undefined },
      chosenCount: versions.length, batch: null, choose: () => undefined, clear: () => undefined, openBatch: () => undefined, closeBatch: () => undefined,
    };
  }

  function mount(versions: readonly DocumentVersion[], deps: AuditPackagesDeps, sink: DownloadSink, pageDocuments = versions) {
    return mountLive(createElement(QueryClientProvider, { client: newClient() }, createElement(SectionSelectionBar, {
      selection: chosen(versions),
      scope: { projectUid: PROJECT_UID, sectionCode: 'AR', pageDocuments, walk: { status: 'idle' }, packages: { sink, deps } },
    })));
  }

  const sinkOf = (saved: string[]): DownloadSink => ({ createObjectUrl: () => 'blob:bundle', saveAs: (_url, name) => { saved.push(name); }, revokeObjectUrl: () => undefined });
  const bundleOf = (asked: EvidenceBundleOptions[]): AuditPackagesDeps['bundle'] => async (options) => {
    asked.push(options);
    return { blob: new Blob(['bundle']), fileName: options.fileName };
  };

  it('builds the packages of the chosen documents with a result, hands one file to the browser and lists the skipped one', async () => {
    const saved: string[] = [];
    const asked: EvidenceBundleOptions[] = [];
    const { buildPackage, asked: packed } = recorder();
    live = await mount([A, B, C], { buildPackage, bundle: bundleOf(asked) }, sinkOf(saved));
    expect(await live.press('Скачать пакеты аудита')).toBe(true);
    expect(packed.map((item) => item.runId)).toEqual([runOf('A'), runOf('C')]);
    expect(saved).toEqual(['audit-packages-AR.zip']);
    expect(asked[0]?.files.map((item) => item.name)).toEqual([`audit-package-${runOf('A')}.zip`, `audit-package-${runOf('C')}.zip`]);
    expect(live.markup()).toContain('audit-packages-AR.zip: 2 пакетов аудита и index.json.');
    expect(live.markup()).toContain(`data-audit-packages-skipped-document="${B.document_uid}"`);
    // the choice is left as it is: nothing of the documents changed
    expect(live.markup()).toContain('Выбрано: 3');
    expect(await live.press('Закрыть')).toBe(true);
    expect(live.markup()).not.toContain('data-audit-packages-status');
  });

  it('holds the button and sends nothing when more documents than the limit are chosen', async () => {
    const many = Array.from({ length: AUDIT_PACKAGES_LIMIT + 1 }, (_, n) => withResult(`${n}`));
    const saved: string[] = [];
    const { buildPackage, asked } = recorder();
    live = await mount(many, { buildPackage, bundle: bundleOf([]) }, sinkOf(saved));
    expect(live.markup()).toContain('data-audit-packages-refusal');
    expect(live.markup()).toContain(`не больше чем для ${AUDIT_PACKAGES_LIMIT} документов`);
    expect(await live.press('Скачать пакеты аудита')).toBe(false);
    expect(asked).toHaveLength(0);
    expect(saved).toEqual([]);
  });

  it('draws no button when none of the chosen documents has a result: there is nothing to build a package of', async () => {
    live = await mount([B], { buildPackage: recorder().buildPackage, bundle: bundleOf([]) }, sinkOf([]));
    expect(live.markup()).toContain('Запустить все (1)');
    expect(live.markup()).not.toContain('Скачать пакеты аудита');
    expect(live.markup()).not.toContain('data-audit-packages-refusal');
  });

  it('shows the document it is on while it builds, and a press of «Отменить» stops it with nothing saved', async () => {
    const saved: string[] = [];
    const buildPackage: AuditPackagesDeps['buildPackage'] = (args) => new Promise((_resolve, reject) => {
      args.onProgress?.({ phase: 'sources', completed: 0, total: 1 });
      args.signal.addEventListener('abort', () => { reject(new DOMException('x', 'AbortError')); });
    });
    live = await mount([A, C], { buildPackage, bundle: bundleOf([]) }, sinkOf(saved));
    await live.press('Скачать пакеты аудита');
    expect(live.markup()).toContain('Собираю пакеты…');
    expect(live.markup()).toContain('Документ 1 из 2 «Документ A»: Получение исходного PDF · 0 из 1');
    expect(await live.press('Отменить')).toBe(true);
    expect(live.markup()).toContain('Сборка пакетов отменена. Архив не скачивался.');
    expect(live.markup()).toContain('>Скачать пакеты аудита<');
    expect(saved).toEqual([]);
  });

  it('saves nothing and names the document when the package of one cannot be built', async () => {
    const saved: string[] = [];
    const { buildPackage } = recorder({ [runOf('C')]: apiError(403, 'permission_denied') });
    live = await mount([A, C], { buildPackage, bundle: bundleOf([]) }, sinkOf(saved));
    await live.press('Скачать пакеты аудита');
    expect(saved).toEqual([]);
    expect(live.markup()).toContain('Пакеты аудита не собраны');
    expect(live.markup()).toContain(`«${C.display_title}»`);
    expect(live.markup()).toContain('Общий ZIP не создан');
  });

  it('does not start a second build while one runs', async () => {
    let release: () => void = () => undefined;
    const gate = new Promise<void>((resolve) => { release = resolve; });
    const asked: string[] = [];
    const buildPackage: AuditPackagesDeps['buildPackage'] = async (args) => {
      asked.push(args.runId);
      await gate;
      return { blob: new Blob(['p']), summary: summaryOf(args.runId) };
    };
    live = await mount([A, C], { buildPackage, bundle: bundleOf([]) }, sinkOf([]));
    await live.pressRepeatedly('Скачать пакеты аудита', 2);
    expect(asked).toEqual([runOf('A')]);
    await live.settle(async () => { release(); await gate; });
    expect(asked).toEqual([runOf('A'), runOf('C')]);
  });
});
