'use client';

import { useQuery } from '@tanstack/react-query';

import type { DocumentUid, ProjectSection, ProjectUid, SectionSpecification } from '@/shared/api';
import { getSectionSpecification, queryKeys } from '@/shared/api';

/** Rows per page. Inside the contract's bound (1..200). */
export const SECTION_ROW_LIMIT = 50;

/** What the expert narrowed the section by. Each is a filter; none is an identity. */
export interface SectionSpecificationRequest {
  readonly sectionCode: ProjectSection;
  /** One project of the section, or `null` for every project that has a set in it. */
  readonly projectUid: ProjectUid | null;
  /**
   * `UIP-S11-05`: one document set of the section, or `null`/absent for every set. The server answers `404` for a
   * document that is unknown, of another project than {@link projectUid}, or confirmed in another section.
   */
  readonly documentUid?: DocumentUid | null;
  /** The text rows are searched for, trimmed; `''` for none. */
  readonly query: string;
  readonly offset: number;
}

/**
 * `getSectionSpecification` (`W63-SECTION-FORM7-01`): the section's combined Form-7
 * specification, project by project, one page of rows at a time.
 *
 * The answer is always a `SectionSpecification`: a bound that stops the read, a set without a
 * published run or a saved text and a project without a price list are states in it, not
 * failures. A failure is what the transport refuses (`404` for an unknown project or document filter).
 * An empty search, project or document is not sent at all.
 */
export function sectionSpecificationQueryOptions(request: SectionSpecificationRequest) {
  const { sectionCode, projectUid, query, offset } = request;
  const documentUid = request.documentUid ?? null;
  const text = query.trim();
  return {
    queryKey: queryKeys.optimisation.sectionSpecification(sectionCode, {
      projectUid,
      documentUid,
      q: text === '' ? null : text,
      offset,
      limit: SECTION_ROW_LIMIT,
    }),
    queryFn: async (): Promise<SectionSpecification> =>
      (
        await getSectionSpecification({
          path: { section_code: sectionCode },
          query: {
            offset,
            limit: SECTION_ROW_LIMIT,
            ...(projectUid === null ? {} : { project_uid: projectUid }),
            ...(documentUid === null ? {} : { document_uid: documentUid }),
            ...(text === '' ? {} : { q: text }),
          },
        })
      ).data,
  } as const;
}

/**
 * The previous page of the **same** section, project, document and search stays on screen
 * while the next loads; another section's answer never stands in for this one's. The answer
 * echoes the project filter and the search but not the document, so the document of the
 * previous query is read from its key.
 */
export function useSectionSpecification(request: SectionSpecificationRequest) {
  return useQuery<SectionSpecification>({
    ...sectionSpecificationQueryOptions(request),
    // Prices come from every project's current price list, which other screens change; the
    // application's thirty-second freshness would show the cache of a visit made before an
    // upload, so this read is asked again whenever the screen mounts.
    staleTime: 0,
    placeholderData: (previous, previousQuery) =>
      previous !== undefined &&
      previous.section_code === request.sectionCode &&
      previous.project_filter === request.projectUid &&
      previous.query === (request.query.trim() === '' ? null : request.query.trim()) &&
      documentOfKey(previousQuery?.queryKey) === (request.documentUid ?? null)
        ? previous
        : undefined,
  });
}

/** The document filter a section specification query was asked with, read from its key. */
function documentOfKey(key: readonly unknown[] | undefined): DocumentUid | null | undefined {
  const filter = (key as ReturnType<typeof queryKeys.optimisation.sectionSpecification> | undefined)?.[3];
  return filter?.documentUid;
}
