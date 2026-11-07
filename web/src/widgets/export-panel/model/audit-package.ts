/**
 * «Скачать пакет аудита» (UI-A-76): the ZIP of one run on «Разбор находок».
 *
 * The original packs the audit's results into an archive «для обсуждения в любой нейронке». Here the archive is the
 * evidence package the comparisons already build in the browser (`features/export-evidence-package`, kind
 * `section-analysis`), so its rules are that builder's and are not restated: every requested file is in it, checked
 * against its digest, or there is no archive.
 *
 * What a run's package holds, and where each part comes from (none of it is built here):
 *
 *   - `reports/<run>-findings.csv`: the server's CSV of the run's published findings, byte for byte (`exportRunCsv`), the
 *     very file «Скачать CSV» saves: the findings with the experts' verdicts and latest comments, `provider_mode` and
 *     `run_state` in its own columns. The browser never builds a CSV; it only packs this one.
 *   - `reports/analysis-<run>.{md,html,json,xlsx}`: the extended review's record of the run (`getExtendedRunReview`), in
 *     the four formats the run page offers, only when the run has such a record with observations. A run without one
 *     says so in the line that follows the download; the package is then the CSV, the PDF and the manifest.
 *   - `sources/001.pdf`: the PDF of the run's version, read whole and checked against the version's byte size and SHA-256.
 *   - `manifest.json`: the builder's: each file's name, size and SHA-256, `expert_review_required: true`.
 *
 * The workbook of «Скачать Excel» is not in it: the server refuses it for a version without verifiable sheet labels and
 * for citations that do not verify, and a package refused for that would lose the CSV that has neither condition.
 */

import type { ExtendedRunReview, RunId, VersionUid } from '@/shared/api';
import { csvFileName, exportRunCsv, getExtendedRunReview } from '@/shared/api';
import { failureMessage } from '@/shared/api/failure-message';
import { formatExtendedRunReport } from '@/entities/audit-run';
import type { ExtendedReportFormat } from '@/entities/audit-run';
import { EvidencePackageError, buildEvidencePackage } from '@/features/export-evidence-package';
import type { EvidencePackageProgress, EvidencePackageReport } from '@/features/export-evidence-package';
import type { ErrorStateProps } from '@/shared/ui';

/** What the button's tooltip says the package holds. */
export const AUDIT_PACKAGE_TITLE =
  'ZIP одного прогона: CSV находок с вердиктами и комментариями экспертов, отчёты расширенного анализа (MD, HTML, JSON, '
  + 'технический XLSX) — если у прогона есть такая запись, исходный PDF версии и manifest.json с SHA-256 каждого файла. '
  + 'Если любой файл получить не удалось, ZIP не создаётся.';

const EXTENDED_FORMATS: readonly ExtendedReportFormat[] = ['md', 'html', 'json', 'xlsx'];

type Step = 'csv' | 'extended' | 'mismatch';

/** A step before the builder failed: which one, and what it threw. */
export class AuditPackageStepError extends Error {
  readonly step: Step;
  readonly reason: unknown;
  constructor(step: Step, reason: unknown) {
    super(`audit package step failed: ${step}`);
    this.name = 'AuditPackageStepError';
    this.step = step;
    this.reason = reason;
  }
}

export interface AuditPackageProgress {
  readonly phase: 'csv' | 'extended' | EvidencePackageProgress['phase'];
  readonly completed: number;
  readonly total: number;
}

/** What the finished package holds, said back to the person after the download. */
export interface AuditPackageSummary {
  readonly fileName: string;
  /** The names under `reports/`, in the order they were packed. */
  readonly reports: readonly string[];
  /** The extended review's record was packed (`included`) or the run has none with observations (`absent`). */
  readonly extended: 'included' | 'absent';
  /** The record's state when it was packed, `null` when absent. */
  readonly extendedStatus: ExtendedRunReview['status'] | null;
}

export interface AuditPackageDeps {
  readonly exportCsv: (runId: RunId, signal: AbortSignal) => Promise<Blob>;
  readonly readExtended: (runId: RunId, signal: AbortSignal) => Promise<ExtendedRunReview>;
  readonly build: typeof buildEvidencePackage;
}

const REAL_DEPS: AuditPackageDeps = {
  exportCsv: async (runId, signal) => (await exportRunCsv({ path: { run_id: runId } }, { signal })).data,
  readExtended: async (runId, signal) => (await getExtendedRunReview({ path: { run_id: runId } }, { signal })).data,
  build: buildEvidencePackage,
};

export interface BuildAuditPackageArgs {
  readonly runId: RunId;
  /** The run's version, from the run's own reading; the one PDF of the package. */
  readonly versionUid: VersionUid;
  readonly signal: AbortSignal;
  readonly onProgress?: ((progress: AuditPackageProgress) => void) | undefined;
  /** Injected by tests. Production reads the server. */
  readonly deps?: AuditPackageDeps | undefined;
}

function object(value: unknown): Record<string, unknown> | null {
  return typeof value === 'object' && value !== null && !Array.isArray(value) ? value as Record<string, unknown> : null;
}

/**
 * The extended review's reading when it holds observations of this run's version, or `null` when it holds none. A record
 * that names another version than the run's is refused: it would put a report of one document beside the PDF of another.
 */
function recordOf(reading: ExtendedRunReview, versionUid: VersionUid): ExtendedRunReview | null {
  const result = object(reading.result);
  if (result === null || !Array.isArray(result.observations) || result.observations.length === 0) return null;
  const named = result.version_uid;
  if (typeof named === 'string' && named !== '' && named !== versionUid) throw new AuditPackageStepError('mismatch', named);
  return reading;
}

export async function buildAuditPackage(args: BuildAuditPackageArgs): Promise<{ blob: Blob; summary: AuditPackageSummary }> {
  const { runId, versionUid, signal } = args;
  const deps = args.deps ?? REAL_DEPS;
  const say = (progress: AuditPackageProgress) => { args.onProgress?.(progress); };
  const reports: EvidencePackageReport[] = [];

  say({ phase: 'csv', completed: 0, total: 1 });
  try {
    reports.push({ name: csvFileName(runId), content: await deps.exportCsv(runId, signal), mediaType: 'text/csv;charset=utf-8' });
  } catch (error) {
    if (signal.aborted) throw error;
    throw new AuditPackageStepError('csv', error);
  }
  say({ phase: 'csv', completed: 1, total: 1 });

  say({ phase: 'extended', completed: 0, total: 1 });
  let record: ExtendedRunReview | null;
  try {
    record = recordOf(await deps.readExtended(runId, signal), versionUid);
    if (record !== null) {
      // Snapshot this one reading in every format; a later poll cannot change what is packed.
      for (const format of EXTENDED_FORMATS) {
        const report = formatExtendedRunReport(record, format);
        reports.push({ name: report.fileName, content: report.content, mediaType: report.mediaType });
      }
    }
  } catch (error) {
    if (signal.aborted || error instanceof AuditPackageStepError) throw error;
    throw new AuditPackageStepError('extended', error);
  }
  say({ phase: 'extended', completed: 1, total: 1 });

  const built = await deps.build({
    fileName: `audit-package-${runId}.zip`,
    kind: 'section-analysis',
    runId,
    reports,
    sources: [{ versionUid, side: 'SOURCE' }],
    signal,
    onProgress: (next) => { say({ phase: next.phase, completed: next.completed, total: next.total }); },
  });
  return {
    blob: built.blob,
    summary: {
      fileName: built.fileName,
      reports: reports.map((report) => report.name),
      extended: record === null ? 'absent' : 'included',
      extendedStatus: record === null ? null : record.status,
    },
  };
}

const PHASE_LABEL: Readonly<Record<AuditPackageProgress['phase'], string>> = {
  csv: 'Получение CSV находок',
  extended: 'Получение отчёта расширенного анализа',
  preparing: 'Подготовка пакета',
  sources: 'Получение исходного PDF',
  packaging: 'Сборка ZIP',
};

/** «Получение исходного PDF · 0 из 1». */
export function auditPackageProgressLine(progress: AuditPackageProgress): string {
  return `${PHASE_LABEL[progress.phase]} · ${progress.completed} из ${progress.total}`;
}

/** The sentence after a finished download: what the archive holds, and what it does not. */
export function auditPackageDoneLine(summary: AuditPackageSummary): string {
  const files = summary.reports.length;
  const head = `${summary.fileName}: ${files === 1 ? '1 файл отчёта' : `${files} файлов отчётов`}, исходный PDF и манифест.`;
  if (summary.extended === 'absent') {
    return `${head} Записи расширенного анализа с наблюдениями у прогона нет, поэтому из отчётов в пакете только CSV находок.`;
  }
  return summary.extendedStatus === 'completed' || summary.extendedStatus === 'partial'
    ? `${head} Отчёты расширенного анализа — предварительные, не решения эксперта.`
    : `${head} Запись расширенного анализа ещё не окончательная; в пакете она в том виде, как была прочитана.`;
}

/** What the panel says when no package was built; every part that failed names itself, and no partial archive is saved. */
export function auditPackageFailure(error: unknown): ErrorStateProps {
  const title = 'Пакет аудита не собран';
  const tail = 'Неполный ZIP не скачивается; повторите попытку.';
  if (error instanceof AuditPackageStepError) {
    if (error.step === 'mismatch') {
      return { title, detail: `Запись расширенного анализа относится к другой версии документа, чем прогон. ${tail}` };
    }
    const reason = error.reason;
    if (error.step === 'extended' && reason instanceof Error && reason.message.startsWith('Технический XLSX:')) {
      return { title, detail: `${reason.message} ${tail}` };
    }
    const message = failureMessage(reason);
    const what = error.step === 'csv' ? 'CSV находок' : 'запись расширенного анализа';
    return { title, detail: `Не удалось получить ${what}: ${message.detail} ${tail}`, correlationId: message.correlationId };
  }
  if (error instanceof EvidencePackageError) return { title, detail: `${error.message} ${tail}` };
  const message = failureMessage(error);
  return { title, detail: `${message.detail} ${tail}`, correlationId: message.correlationId };
}
