/**
 * «Скачать пакеты аудита» over the chosen documents of a section (`UIP-S02-05`): one ZIP holding the audit package of each of them.
 *
 * Each package is the very one «Скачать пакет аудита» builds on «Разбор» for a run (`buildAuditPackage`: the server's CSV, the extended
 * review's record when it has one, the version's PDF checked against its digest, `manifest.json`), built in the browser, one document after
 * another, and kept inside the common ZIP as the file it made, under the name the single download gives it, so each can be opened and
 * checked by itself. The common archive adds `index.json`: which document each package belongs to, which chosen documents were left out
 * and why, and each file's size and SHA-256. Nothing is built on the server and no new operation is asked of it.
 *
 * **The rule of the package stays:** every file of every package is in the archive, or there is no archive. A document whose package cannot
 * be built stops the whole ZIP and is named; it is not left out quietly. What is left out is only what has no package to build: a document
 * with no result run (`audit.result_run_id` absent), listed as skipped in the line after the download and in `index.json`. A version with no
 * result never gets a package of its own.
 *
 * **The limit** (an open question for the owner, so a safe one, said in words): at most {@link AUDIT_PACKAGES_LIMIT} documents with a
 * result at a time, and the packages together at most {@link EVIDENCE_BUNDLE_MAX_BYTES} bytes, because the archive is built in the memory
 * of the browser. Over either, nothing is built.
 */

import type { DocumentUid, RunId, VersionUid } from '@/shared/api';
import type { ErrorStateProps } from '@/shared/ui';
import { EVIDENCE_BUNDLE_MAX_BYTES, EvidencePackageError, buildEvidenceBundle } from '@/features/export-evidence-package';
import type { EvidencePackageProgress } from '@/features/export-evidence-package';

import type { AuditPackageDeps, AuditPackageProgress, AuditPackageSummary } from './audit-package';
import { auditPackageFailure, auditPackageProgressLine, buildAuditPackage } from './audit-package';

/** The most documents with a result one common ZIP is built for. The owner has not set it; this is the safe figure until he does. */
export const AUDIT_PACKAGES_LIMIT = 20;

/** What the button's tooltip says the common ZIP holds. */
export const AUDIT_PACKAGES_TITLE =
  'Один ZIP с пакетом аудита каждого выбранного документа, у которого есть результат (такой же, как «Скачать пакет аудита» на «Разборе»), '
  + 'и index.json со списком пакетов и пропущенных документов. Документы без результата пропускаются и перечисляются. '
  + `За один раз — не больше ${AUDIT_PACKAGES_LIMIT} документов. Если пакет любого документа получить не удалось, ZIP не создаётся.`;

/** One chosen document, as the section page knows it. Its identity is its uids; the title only names it to the reader. */
export interface AuditPackagesDocument {
  readonly documentUid: DocumentUid;
  /** The document's current version: the one PDF of its package. */
  readonly versionUid: VersionUid;
  readonly title: string;
  /** The version's result run (`DocumentAudit.result_run_id`); absent when the version has no result. */
  readonly runId: RunId | undefined;
}

export interface PackableDocument extends AuditPackagesDocument {
  readonly runId: RunId;
}

export interface AuditPackagesSplit {
  /** Documents with a result, in the order they were chosen: each gets a package. */
  readonly packable: readonly PackableDocument[];
  /** Documents with no result: listed as skipped. */
  readonly skipped: readonly AuditPackagesDocument[];
}

export function splitAuditPackages(documents: readonly AuditPackagesDocument[]): AuditPackagesSplit {
  const packable: PackableDocument[] = [];
  const skipped: AuditPackagesDocument[] = [];
  for (const document of documents) {
    if (document.runId === undefined) skipped.push(document);
    else packable.push({ ...document, runId: document.runId });
  }
  return { packable, skipped };
}

/**
 * Why the button cannot be pressed, in words, or `null` when it can: nothing to build a package of, or more than the limit. The same
 * words are what the bar says beside the button, so the limit is read before the press and not found out by it.
 */
export function auditPackagesRefusal(split: AuditPackagesSplit): string | null {
  if (split.packable.length === 0) return 'У выбранных документов нет результата аудита: пакеты собирать не из чего.';
  if (split.packable.length > AUDIT_PACKAGES_LIMIT) {
    return `Пакеты аудита собираются не больше чем для ${AUDIT_PACKAGES_LIMIT} документов с результатом за раз: выбрано ${split.packable.length}. Уберите лишние из выбора.`;
  }
  return null;
}

export interface AuditPackagesSummary {
  readonly fileName: string;
  /** The packages in the archive, in the order they were chosen. */
  readonly packed: ReadonlyArray<{ readonly document: PackableDocument; readonly entryName: string; readonly package: AuditPackageSummary }>;
  /** The chosen documents with no result, which have no package. */
  readonly skipped: readonly AuditPackagesDocument[];
}

export type AuditPackagesProgress =
  | { readonly kind: 'document'; readonly index: number; readonly total: number; readonly title: string; readonly step: AuditPackageProgress }
  | { readonly kind: 'archive'; readonly step: EvidencePackageProgress };

export interface AuditPackagesDeps {
  /** One document's package; production builds it from the server. */
  readonly buildPackage: typeof buildAuditPackage;
  /** The common ZIP of the finished packages. */
  readonly bundle: typeof buildEvidenceBundle;
  /** Passed on to each package's own builder. */
  readonly package?: AuditPackageDeps | undefined;
}

const REAL_DEPS: AuditPackagesDeps = { buildPackage: buildAuditPackage, bundle: buildEvidenceBundle };

export type AuditPackagesRefusalKind = 'nothing' | 'too_many';

/** Nothing was built because there is nothing to build or too much: said before any request. */
export class AuditPackagesRefused extends Error {
  readonly kind: AuditPackagesRefusalKind;
  readonly detail: string;
  constructor(kind: AuditPackagesRefusalKind, detail: string) {
    super(`audit packages refused: ${kind}`);
    this.name = 'AuditPackagesRefused';
    this.kind = kind;
    this.detail = detail;
  }
}

/** The package of one document could not be built: which document, and what the single builder threw. */
export class AuditPackagesDocumentError extends Error {
  readonly document: AuditPackagesDocument;
  readonly reason: unknown;
  constructor(document: AuditPackagesDocument, reason: unknown) {
    super('audit package of a document failed');
    this.name = 'AuditPackagesDocumentError';
    this.document = document;
    this.reason = reason;
  }
}

export interface BuildAuditPackagesArgs {
  readonly documents: readonly AuditPackagesDocument[];
  /** The common ZIP's name. */
  readonly fileName: string;
  readonly signal: AbortSignal;
  readonly onProgress?: ((progress: AuditPackagesProgress) => void) | undefined;
  /** Injected by tests. Production reads the server. */
  readonly deps?: AuditPackagesDeps | undefined;
}

export async function buildAuditPackages(args: BuildAuditPackagesArgs): Promise<{ blob: Blob; summary: AuditPackagesSummary }> {
  const { signal } = args;
  const deps = args.deps ?? REAL_DEPS;
  const split = splitAuditPackages(args.documents);
  const refusal = auditPackagesRefusal(split);
  if (refusal !== null) throw new AuditPackagesRefused(split.packable.length === 0 ? 'nothing' : 'too_many', refusal);

  const files: Array<{ name: string; content: Blob; mediaType: string }> = [];
  const packed: Array<AuditPackagesSummary['packed'][number]> = [];
  let bytes = 0;
  for (const [position, document] of split.packable.entries()) {
    let built: Awaited<ReturnType<typeof buildAuditPackage>>;
    try {
      built = await deps.buildPackage({
        runId: document.runId,
        versionUid: document.versionUid,
        signal,
        deps: deps.package,
        onProgress: (step) => {
          args.onProgress?.({ kind: 'document', index: position + 1, total: split.packable.length, title: document.title, step });
        },
      });
    } catch (error) {
      if (signal.aborted || error instanceof DOMException && error.name === 'AbortError') throw error;
      throw new AuditPackagesDocumentError(document, error);
    }
    // The archive is built in memory beside what it holds: stop before the next package is read once the packages together are too many bytes.
    bytes += built.blob.size;
    if (bytes > EVIDENCE_BUNDLE_MAX_BYTES) {
      throw new EvidencePackageError(
        'package_too_large',
        `Пакеты выбранных документов вместе больше ${EVIDENCE_BUNDLE_MAX_BYTES / 1024 / 1024} МиБ. Архив не создан; выберите меньше документов.`,
      );
    }
    files.push({ name: built.summary.fileName, content: built.blob, mediaType: 'application/zip' });
    packed.push({ document, entryName: built.summary.fileName, package: built.summary });
  }

  const bundle = await deps.bundle({
    fileName: args.fileName,
    files,
    index: {
      kind: 'audit-packages',
      expert_review_required: true,
      packages: packed.map((item) => ({
        document_uid: item.document.documentUid,
        version_uid: item.document.versionUid,
        run_id: item.document.runId,
        title: item.document.title,
        entry_name: item.entryName,
        extended_review: item.package.extended,
      })),
      skipped: split.skipped.map((item) => ({
        document_uid: item.documentUid,
        version_uid: item.versionUid,
        title: item.title,
        reason: 'no_result_run',
      })),
      all_requested_packages_included: true,
    },
    signal,
    onProgress: (step) => { args.onProgress?.({ kind: 'archive', step }); },
  });
  return { blob: bundle.blob, summary: { fileName: bundle.fileName, packed, skipped: split.skipped } };
}

/** «Документ 2 из 5 «Название»: Получение исходного PDF · 0 из 1». */
export function auditPackagesProgressLine(progress: AuditPackagesProgress): string {
  if (progress.kind === 'archive') {
    const phase = progress.step.phase === 'packaging' ? 'Сборка общего ZIP' : 'Подготовка общего ZIP';
    return `${phase} · ${progress.step.completed} из ${progress.step.total}`;
  }
  return `Документ ${progress.index} из ${progress.total} «${progress.title}»: ${auditPackageProgressLine(progress.step)}`;
}

/** The sentence after a finished download: what the archive holds, and how many chosen documents have no package. */
export function auditPackagesDoneLine(summary: AuditPackagesSummary): string {
  const count = summary.packed.length;
  const packages = count === 1 ? '1 пакет аудита' : `${count} пакетов аудита`;
  const head = `${summary.fileName}: ${packages} и index.json.`;
  if (summary.skipped.length === 0) return head;
  return `${head} Пропущено документов без результата аудита: ${summary.skipped.length} — они перечислены ниже и в index.json.`;
}

/** What the panel says when no archive was built; nothing is saved, and the document that stopped it is named. */
export function auditPackagesFailure(error: unknown): ErrorStateProps {
  const title = 'Пакеты аудита не собраны';
  if (error instanceof AuditPackagesRefused) return { title, detail: error.detail };
  if (error instanceof AuditPackagesDocumentError) {
    const inner = auditPackageFailure(error.reason);
    return {
      title,
      detail: `Документ «${error.document.title}»: ${inner.detail ?? ''} Общий ZIP не создан.`,
      correlationId: inner.correlationId ?? null,
    };
  }
  const single = auditPackageFailure(error);
  return { ...single, title };
}
