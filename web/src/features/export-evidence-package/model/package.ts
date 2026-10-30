/** Read-only report/source custody. Every requested PDF is included or the whole export fails. */
import type { DocumentVersion, VersionUid } from '@/shared/api';
import { getDocumentVersion, streamDocumentVersionContent } from '@/shared/api';

export interface EvidencePackageReport {
  readonly name: string;
  readonly content: string | ArrayBuffer | Blob;
  readonly mediaType?: string;
}
export interface EvidencePackageSource {
  readonly versionUid: VersionUid;
  readonly side?: 'OLD' | 'NEW' | 'SOURCE';
}
export interface EvidencePackageProgress {
  readonly phase: 'preparing' | 'sources' | 'packaging';
  readonly completed: number;
  readonly total: number;
  readonly currentVersionUid?: string;
}
export interface EvidencePackageOptions {
  readonly fileName: string;
  readonly kind: 'section-analysis' | 'stage-v3';
  readonly runId: string;
  readonly reports: readonly EvidencePackageReport[];
  readonly sources: readonly EvidencePackageSource[];
  readonly signal?: AbortSignal;
  readonly onProgress?: (progress: EvidencePackageProgress) => void;
}
export type EvidencePackageErrorCode = 'invalid_request' | 'package_too_large' | 'source_metadata_invalid'
  | 'source_incomplete' | 'source_integrity_error' | 'source_read_failed' | 'crypto_unavailable';
export class EvidencePackageError extends Error {
  readonly code: EvidencePackageErrorCode;
  constructor(code: EvidencePackageErrorCode, message: string) {
    super(message);
    this.name = 'EvidencePackageError';
    this.code = code;
  }
}

const MAX_BYTES = 64 * 1024 * 1024;
const MAX_REPORTS = 32;
const MAX_SOURCES = 128;
const encoder = new TextEncoder();
interface Entry { readonly name: string; readonly data: ArrayBuffer; readonly mediaType: string }
interface SourcePlan {
  readonly versionUid: VersionUid;
  readonly roles: Array<'OLD' | 'NEW' | 'SOURCE'>;
  readonly metadata: DocumentVersion;
  readonly entryName: string;
}
function cancelled(signal?: AbortSignal): void {
  if (signal?.aborted) throw new DOMException('Экспорт пакета отменён.', 'AbortError');
}
function tooLarge(): never {
  throw new EvidencePackageError('package_too_large', 'Полный пакет превышает 64 МиБ. Пакет не создан; исходные PDF не исключались.');
}
function progress(options: EvidencePackageOptions, value: EvidencePackageProgress): void {
  cancelled(options.signal);
  options.onProgress?.(value);
}
function safeName(value: string, label: string): string {
  if (typeof value !== 'string' || !value.trim() || value === '.' || value === '..'
    || /[\\/\u0000-\u001f\u007f]/u.test(value) || encoder.encode(value).length > 200) {
    throw new EvidencePackageError('invalid_request', `${label}: требуется короткое имя файла без пути.`);
  }
  return value;
}
function utf8(value: string): ArrayBuffer {
  if (value.length > MAX_BYTES) tooLarge();
  const bytes = encoder.encode(value);
  if (bytes.length > MAX_BYTES) tooLarge();
  return bytes.buffer as ArrayBuffer;
}
async function sha256(data: ArrayBuffer, signal?: AbortSignal): Promise<string> {
  cancelled(signal);
  if (!globalThis.crypto?.subtle) {
    throw new EvidencePackageError('crypto_unavailable', 'Браузер не предоставляет SHA-256. Для проверенного пакета откройте приложение через HTTPS.');
  }
  const result = await globalThis.crypto.subtle.digest('SHA-256', data);
  cancelled(signal);
  return Array.from(new Uint8Array(result), (byte) => byte.toString(16).padStart(2, '0')).join('');
}
async function reportBytes(report: EvidencePackageReport, signal?: AbortSignal): Promise<ArrayBuffer> {
  cancelled(signal);
  if (typeof report.content === 'string') return utf8(report.content);
  if (report.content instanceof ArrayBuffer) {
    if (report.content.byteLength > MAX_BYTES) tooLarge();
    return report.content.slice(0); // caller cannot change bytes after their hash has been recorded.
  }
  if (report.content instanceof Blob) {
    if (report.content.size > MAX_BYTES) tooLarge();
    const data = await report.content.arrayBuffer();
    cancelled(signal);
    return data;
  }
  throw new EvidencePackageError('invalid_request', 'Неподдерживаемый формат отчёта в пакете.');
}
function archiveSize(entries: readonly Entry[]): number {
  return entries.reduce((sum, entry) => sum + entry.data.byteLength + 76 + encoder.encode(entry.name).length * 2, 22);
}
function guardSize(entries: readonly Entry[], extraBytes = 0): void {
  if (archiveSize(entries) + extraBytes > MAX_BYTES) tooLarge();
}

/** ZIP STORE/CRC32 adapted from entities/audit-run/lib/extended-xlsx.ts in this repository.
 * The implementation is copied locally rather than importing another feature/entity's internals.
 * Names are UTF-8, bytes remain exact, entries are unencrypted, dates are deterministic. */
const CRC_TABLE = new Uint32Array(256);
for (let index = 0; index < 256; index += 1) {
  let value = index;
  for (let bit = 0; bit < 8; bit += 1) value = value & 1 ? 0xEDB88320 ^ (value >>> 1) : value >>> 1;
  CRC_TABLE[index] = value >>> 0;
}
async function yieldToCancel(signal?: AbortSignal): Promise<void> {
  await new Promise<void>((resolve) => { setTimeout(resolve, 0); });
  cancelled(signal);
}
async function checksum(data: Uint8Array, signal?: AbortSignal): Promise<number> {
  let value = 0xFFFFFFFF;
  for (let start = 0; start < data.length; start += 1024 * 1024) {
    const end = Math.min(start + 1024 * 1024, data.length);
    for (let index = start; index < end; index += 1) {
      const byte = data[index] ?? 0;
      value = (value >>> 8) ^ (CRC_TABLE[(value ^ byte) & 0xFF] ?? 0);
    }
    await yieldToCancel(signal);
  }
  return (value ^ 0xFFFFFFFF) >>> 0;
}
async function archive(entries: readonly Entry[], options: EvidencePackageOptions): Promise<Blob> {
  guardSize(entries);
  const records: Array<{ name: Uint8Array; data: Uint8Array; crc: number; offset: number }> = [];
  for (const entry of entries) {
    const data = new Uint8Array(entry.data);
    records.push({ name: encoder.encode(entry.name), data, crc: await checksum(data, options.signal), offset: 0 });
  }
  const localSize = records.reduce((size, part) => size + 30 + part.name.length + part.data.length, 0);
  const centralSize = records.reduce((size, part) => size + 46 + part.name.length, 0);
  const buffer = new ArrayBuffer(localSize + centralSize + 22);
  const output = new Uint8Array(buffer);
  const view = new DataView(buffer);
  let offset = 0;
  let completed = 0;
  for (const part of records) {
    cancelled(options.signal);
    part.offset = offset;
    view.setUint32(offset, 0x04034B50, true); view.setUint16(offset + 4, 20, true);
    view.setUint16(offset + 6, 0x0800, true); view.setUint16(offset + 12, 33, true);
    view.setUint32(offset + 14, part.crc, true); view.setUint32(offset + 18, part.data.length, true);
    view.setUint32(offset + 22, part.data.length, true); view.setUint16(offset + 26, part.name.length, true);
    output.set(part.name, offset + 30);
    const dataOffset = offset + 30 + part.name.length;
    for (let start = 0; start < part.data.length; start += 1024 * 1024) {
      output.set(part.data.subarray(start, Math.min(start + 1024 * 1024, part.data.length)), dataOffset + start);
      await yieldToCancel(options.signal);
    }
    offset = dataOffset + part.data.length;
    completed += 1;
    progress(options, { phase: 'packaging', completed, total: entries.length });
  }
  for (const part of records) {
    cancelled(options.signal);
    view.setUint32(offset, 0x02014B50, true); view.setUint16(offset + 4, 20, true); view.setUint16(offset + 6, 20, true);
    view.setUint16(offset + 8, 0x0800, true); view.setUint16(offset + 14, 33, true);
    view.setUint32(offset + 16, part.crc, true); view.setUint32(offset + 20, part.data.length, true);
    view.setUint32(offset + 24, part.data.length, true); view.setUint16(offset + 28, part.name.length, true);
    view.setUint32(offset + 42, part.offset, true); output.set(part.name, offset + 46);
    offset += 46 + part.name.length;
  }
  view.setUint32(offset, 0x06054B50, true); view.setUint16(offset + 8, records.length, true);
  view.setUint16(offset + 10, records.length, true); view.setUint32(offset + 12, centralSize, true);
  view.setUint32(offset + 16, localSize, true);
  cancelled(options.signal);
  return new Blob([buffer], { type: 'application/zip' });
}

export async function buildEvidencePackage(options: EvidencePackageOptions): Promise<{ blob: Blob; fileName: string }> {
  cancelled(options.signal);
  if (!['section-analysis', 'stage-v3'].includes(options.kind) || typeof options.runId !== 'string'
    || !options.runId.trim() || options.runId.length > 160 || !Array.isArray(options.reports) || options.reports.length < 1
    || options.reports.length > MAX_REPORTS || !Array.isArray(options.sources)
    || options.sources.length < 1 || options.sources.length > MAX_SOURCES * 3) {
    throw new EvidencePackageError('invalid_request', 'Для полного пакета нужны идентификатор запуска, отчёты и исходные версии PDF.');
  }
  const desiredName = safeName(options.fileName, 'Имя пакета');
  const fileName = desiredName.toLowerCase().endsWith('.zip') ? desiredName : `${desiredName}.zip`;
  const requested = new Map<VersionUid, Set<'OLD' | 'NEW' | 'SOURCE'>>();
  for (const source of options.sources) {
    if (typeof source.versionUid !== 'string' || !source.versionUid.trim() || source.versionUid.length > 160
      || source.side !== undefined && !['OLD', 'NEW', 'SOURCE'].includes(source.side)) {
      throw new EvidencePackageError('invalid_request', 'Не указан действительный идентификатор исходной версии PDF.');
    }
    const roles = requested.get(source.versionUid) ?? new Set<'OLD' | 'NEW' | 'SOURCE'>();
    roles.add(source.side ?? 'SOURCE'); requested.set(source.versionUid, roles);
  }
  if (requested.size > MAX_SOURCES) {
    throw new EvidencePackageError('invalid_request', 'В одном пакете допускается не более 128 исходных PDF.');
  }
  const entries: Entry[] = [];
  const reportManifest: Array<{ entry_name: string; media_type: string; byte_size: number; sha256: string }> = [];
  const reportNames = new Set<string>();
  const sourcePlans: SourcePlan[] = [];
  const preparingTotal = options.reports.length + requested.size;
  let prepared = 0;
  progress(options, { phase: 'preparing', completed: 0, total: preparingTotal });
  try {
    for (const report of options.reports) {
      const name = safeName(report.name, 'Имя отчёта');
      if (report.mediaType !== undefined && (typeof report.mediaType !== 'string'
        || report.mediaType.length > 160 || /[\u0000-\u001f\u007f]/u.test(report.mediaType))) {
        throw new EvidencePackageError('invalid_request', 'Некорректный тип файла отчёта.');
      }
      const normalizedName = name.normalize('NFC').toLowerCase();
      if (reportNames.has(normalizedName)) throw new EvidencePackageError('invalid_request', 'Имена отчётов в пакете повторяются.');
      reportNames.add(normalizedName);
      const data = await reportBytes(report, options.signal);
      const entry = { name: `reports/${name}`, data, mediaType: report.mediaType ?? 'application/octet-stream' };
      entries.push(entry); guardSize(entries);
      reportManifest.push({ entry_name: entry.name, media_type: entry.mediaType,
        byte_size: data.byteLength, sha256: await sha256(data, options.signal) });
      prepared += 1;
      progress(options, { phase: 'preparing', completed: prepared, total: preparingTotal });
    }
    let sourceBytes = 0;
    for (const [versionUid, roles] of requested) {
      const response = await getDocumentVersion({ path: { version_uid: versionUid } },
        options.signal === undefined ? undefined : { signal: options.signal });
      cancelled(options.signal);
      const metadata = response.data;
      if (response.status !== 200 || metadata.version_uid !== versionUid || metadata.media_type !== 'application/pdf'
        || !Number.isSafeInteger(metadata.byte_size) || metadata.byte_size <= 0
        || typeof metadata.sha256 !== 'string' || !/^[a-fA-F0-9]{64}$/u.test(metadata.sha256)) {
        throw new EvidencePackageError('source_metadata_invalid', `Метаданные исходной версии ${versionUid} не позволяют проверить полный PDF.`);
      }
      sourceBytes += metadata.byte_size;
      guardSize(entries, sourceBytes);
      sourcePlans.push({ versionUid, roles: [...roles].sort(), metadata,
        entryName: `sources/${String(sourcePlans.length + 1).padStart(3, '0')}.pdf` });
      prepared += 1;
      progress(options, { phase: 'preparing', completed: prepared, total: preparingTotal, currentVersionUid: versionUid });
    }
    const sourceManifest: Array<Record<string, unknown>> = [];
    let sourceCompleted = 0;
    progress(options, { phase: 'sources', completed: 0, total: sourcePlans.length });
    for (const source of sourcePlans) {
      progress(options, { phase: 'sources', completed: sourceCompleted, total: sourcePlans.length, currentVersionUid: source.versionUid });
      const response = await streamDocumentVersionContent({ path: { version_uid: source.versionUid } },
        options.signal === undefined ? undefined : { signal: options.signal });
      cancelled(options.signal);
      if (response.status !== 200 || !(response.data instanceof Blob) || response.data.size !== source.metadata.byte_size) {
        throw new EvidencePackageError('source_incomplete', `Полный PDF версии ${source.versionUid} не получен. Пакет не создан.`);
      }
      const data = await response.data.arrayBuffer();
      const sha = await sha256(data, options.signal);
      if (data.byteLength !== source.metadata.byte_size || sha !== source.metadata.sha256.toLowerCase()) {
        throw new EvidencePackageError('source_integrity_error', `Размер или SHA-256 исходной версии ${source.versionUid} не совпадает с метаданными. Пакет не создан.`);
      }
      entries.push({ name: source.entryName, data, mediaType: 'application/pdf' }); guardSize(entries);
      sourceManifest.push({ version_uid: source.versionUid, side_roles: source.roles,
        document_uid: source.metadata.document_uid, project_uid: source.metadata.project_uid,
        page_count: source.metadata.page_count, source_filename: source.metadata.source_filename ?? null,
        entry_name: source.entryName, byte_size: data.byteLength, sha256: sha,
        verified_against_version_metadata: true });
      sourceCompleted += 1;
      progress(options, { phase: 'sources', completed: sourceCompleted, total: sourcePlans.length, currentVersionUid: source.versionUid });
    }
    const manifest = { format: 'auditmanager-evidence-package-v1', kind: options.kind, run_id: options.runId,
      created_at: new Date().toISOString(), expert_review_required: true,
      reports: reportManifest, sources: sourceManifest,
      all_requested_reports_included: true, all_requested_sources_included: true,
      requested_source_roles: options.sources.map((source) => ({ version_uid: source.versionUid, side: source.side ?? 'SOURCE' })),
      source_reads: ['getDocumentVersion', 'streamDocumentVersionContent'],
      archive: { method: 'ZIP_STORE', maximum_bytes: MAX_BYTES, entry_count: entries.length + 1 } };
    entries.push({ name: 'manifest.json', data: utf8(JSON.stringify(manifest, null, 2)), mediaType: 'application/json' });
    guardSize(entries);
    progress(options, { phase: 'packaging', completed: 0, total: entries.length });
    const blob = await archive(entries, options);
    cancelled(options.signal);
    return { blob, fileName };
  } catch (error) {
    cancelled(options.signal);
    if (error instanceof EvidencePackageError || error instanceof DOMException && error.name === 'AbortError') throw error;
    throw new EvidencePackageError('source_read_failed', 'Не удалось прочитать все обязательные файлы. Пакет не создан; повторите экспорт после восстановления доступа.');
  }
}
