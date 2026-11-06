'use client';

/**
 * The documents of one project — `listDocuments`, on mount.
 *
 * This is the half of `D-16` a user feels. Before it, a project screen read the version
 * the *previous* screen had left in React state, so a reload showed "No version published
 * in this session" over a project full of published work. This asks the server.
 *
 * One item per document, carrying the version that document currently points at, which is
 * what `W18-SEAL` §2 chose the shape to be. The cursor is opaque: handed back exactly as
 * received, never parsed and never built.
 */

import { useQuery } from '@tanstack/react-query';

import type { DocumentAudit, DocumentTagList, DocumentVersionPage, ProjectSection, ProjectUid } from '@/shared/api';
import { listDocumentTags, listDocuments, queryKeys } from '@/shared/api';

/** Page size. Inside the contract's bound and matching the project list's choice. */
export const DOCUMENT_PAGE_LIMIT = 50;

/**
 * `UI-PARITY-DOC-AUDIT` (contract 1.34.0): what the audit of a document adds to a listing. `state` keeps the documents in
 * one audit state (`UI-A-38`, «не запускались» is `not_run`); `order: 'audit'` is the original's section order
 * (`UI-A-49`), decided by the server for the whole listing. Both are the server's, so paging and the end of the list
 * are those of the narrowed, ordered listing.
 */
export interface DocumentListAudit {
  readonly state?: DocumentAudit['state'] | undefined;
  readonly order?: 'published' | 'audit' | undefined;
}

/**
 * Options for one project's documents, ready for `useQuery` or `useQueries`.
 *
 * `W46-DASH` pulled this out of `useDocumentList` so the dashboard's per-project walk
 * (`widgets/dashboard`) can fan out over several projects with `useQueries` — which takes
 * a dynamic array of query configs, not a fixed number of hook calls — while filling the
 * exact same cache entry `useDocumentList` would. Same key, same `queryFn`, one source.
 */
export function documentListQueryOptions(
  projectUid: ProjectUid, cursor?: string, sectionCode?: ProjectSection, includeArchived = false, tag?: string,
  audit: DocumentListAudit = {},
) {
  return {
    queryKey: queryKeys.projects.documents(
      projectUid, cursor, DOCUMENT_PAGE_LIMIT, sectionCode, includeArchived, tag, audit.state, audit.order,
    ),
    queryFn: async (): Promise<DocumentVersionPage> => {
      const response = await listDocuments({
        path: { project_uid: projectUid },
        query: {
          ...(cursor === undefined ? {} : { cursor }),
          limit: DOCUMENT_PAGE_LIMIT,
          // `R-151l`, contract 1.20.0: the server keeps the documents confirmed for this section.
          ...(sectionCode === undefined ? {} : { section_code: sectionCode }),
          // `R-151a`: an archived document is listed only when asked for.
          ...(includeArchived ? { include_archived: true } : {}),
          // `R-151e`: only the documents carrying this tag.
          ...(tag === undefined ? {} : { tag }),
          // `UI-PARITY-DOC-AUDIT`: the server narrows by audit state and orders the whole listing, so both hold across
          // pages (`audit_state`, `order=audit`). Absent, the listing is the one the operation always had.
          ...(audit.state === undefined ? {} : { audit_state: audit.state }),
          ...(audit.order === undefined ? {} : { order: audit.order }),
        },
      });
      return response.data;
    },
  };
}

export function useDocumentList(
  projectUid: ProjectUid, cursor?: string, sectionCode?: ProjectSection, includeArchived = false, tag?: string,
  audit: DocumentListAudit = {},
) {
  return useQuery<DocumentVersionPage>(
    documentListQueryOptions(projectUid, cursor, sectionCode, includeArchived, tag, audit),
  );
}

/** `R-151e`: every tag of the project's documents in use, with counts, for the tag filter. */
export function useDocumentTags(projectUid: ProjectUid) {
  return useQuery<DocumentTagList>({
    queryKey: queryKeys.projects.tags(projectUid),
    queryFn: async () => (await listDocumentTags({ path: { project_uid: projectUid } })).data,
  });
}
