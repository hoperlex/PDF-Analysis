'use client';

/**
 * What a stage pair's documents are called (`UI-B-85`): the original's catalog and selectors name the documents by their title and
 * section, never by an identifier. The pair carries only `document_uid`s, so the names come from the project's document list, read
 * once for the whole screen (every page, the latest version of each document) and shared by the catalog, the pair and run selectors
 * and the suggestions. Until it has answered — or if it cannot — a document is shown by its identifier, the old text, and the
 * screen does not wait for it.
 */

import { useQuery } from '@tanstack/react-query';

import type { DocumentUid, DocumentVersion, ProjectUid } from '@/shared/api';
import { listDocuments } from '@/shared/api';

import { STAGE_PAIR_KEYS } from './catalog';

export interface StageDocumentName {
  /** The title the reader gave or the uploaded file's name; empty when the document has neither. */
  readonly title: string;
  readonly section: string | undefined;
  readonly stage: 'P' | 'R' | undefined;
}

export type StageDocumentNames = ReadonlyMap<string, StageDocumentName>;

const MAX_PAGES = 50;

/** The latest version of each document, as a name. Pure, so a test reads it without a query. */
export function namesOf(versions: readonly DocumentVersion[]): StageDocumentNames {
  const latest = new Map<string, DocumentVersion>();
  for (const version of versions) {
    const prior = latest.get(version.document_uid);
    if (prior === undefined || version.version_ordinal > prior.version_ordinal) latest.set(version.document_uid, version);
  }
  return new Map(
    [...latest].map(([uid, version]) => [
      uid,
      {
        title: version.display_title ?? version.source_filename ?? '',
        section: version.classification?.section_code,
        stage: version.classification?.project_stage as 'P' | 'R' | undefined,
      },
    ]),
  );
}

/** «название · раздел», or the identifier while the name is unknown. */
export function documentCaption(names: StageDocumentNames | undefined, uid: DocumentUid): string {
  const name = names?.get(uid);
  if (name === undefined || name.title === '') return uid;
  return name.section === undefined ? name.title : `${name.title} · ${name.section}`;
}

async function readAll(projectUid: string): Promise<StageDocumentNames> {
  const versions: DocumentVersion[] = [];
  let cursor: string | undefined;
  for (let pages = 0; pages < MAX_PAGES; pages += 1) {
    const page = (await listDocuments({ path: { project_uid: projectUid }, query: { limit: 100, ...(cursor === undefined ? {} : { cursor }) } })).data;
    versions.push(...page.items);
    cursor = page.page.next_cursor ?? undefined;
    if (cursor === undefined) break;
  }
  return namesOf(versions);
}

export function useStageDocumentNames(projectUid: ProjectUid | null) {
  return useQuery<StageDocumentNames>({
    queryKey: STAGE_PAIR_KEYS.documents(projectUid ?? ''),
    queryFn: () => readAll(projectUid!),
    enabled: projectUid !== null,
    retry: false,
  });
}
