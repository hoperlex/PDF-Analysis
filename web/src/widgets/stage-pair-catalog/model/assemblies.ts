import type { DocumentVersion, StageAssembly } from '@/shared/api';
import { listDocuments } from '@/shared/api';

export function latestDocuments(versions: readonly DocumentVersion[]): DocumentVersion[] {
  const documents = new Map<string, DocumentVersion>();
  for (const version of versions) {
    const prior = documents.get(version.document_uid);
    if (prior === undefined || version.version_ordinal > prior.version_ordinal) documents.set(version.document_uid, version);
  }
  return [...documents.values()];
}

export async function readDocuments(projectUid: string): Promise<DocumentVersion[]> {
  const versions: DocumentVersion[] = [];
  let cursor: string | undefined;
  const seen = new Set<string>();
  do {
    const page = (await listDocuments({ path: { project_uid: projectUid },
      query: { limit: 100, ...(cursor === undefined ? {} : { cursor }) } })).data;
    versions.push(...page.items);
    cursor = page.page.next_cursor ?? undefined;
    if (cursor !== undefined && seen.has(cursor)) throw new Error('Список документов обновился. Откройте его заново.');
    if (cursor !== undefined) seen.add(cursor);
  } while (cursor !== undefined);
  return latestDocuments(versions);
}

export function documentLabel(document: DocumentVersion): string {
  return `${document.display_title ?? document.source_filename ?? document.document_uid} · ${document.classification?.section_code ?? 'раздел не указан'}`;
}

export function revisedMemberCount(assembly: StageAssembly, adds: readonly string[], removes: readonly string[]): number {
  return assembly.members.length + adds.length - removes.length;
}
