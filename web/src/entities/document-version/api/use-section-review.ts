'use client';

/**
 * `getVersionSectionReview` — one version's fifteen section choices, their suggestion
 * evidence, whether each has an analysis profile, and the persisted classification.
 *
 * Display input only: nothing read here confirms a section or starts a run. The version
 * screen reads it on mount, once the version itself has told it which document and project
 * the version belongs to — the path is built from the version's own body, not from the
 * address bar, for the reason the screen's back link is.
 */

import { useQuery } from '@tanstack/react-query';

import type { SectionReview } from '@/shared/api';
import { getVersionSectionReview, queryKeys } from '@/shared/api';

import type { VersionAddress } from '../model/classification';

/** Options for one version's review, ready for `useQuery` or a seeded cache. */
export function sectionReviewQueryOptions(address: VersionAddress) {
  return {
    queryKey: queryKeys.versions.sectionReview(address.versionUid),
    queryFn: async (): Promise<SectionReview> => {
      const response = await getVersionSectionReview({
        path: {
          project_uid: address.projectUid,
          document_uid: address.documentUid,
          version_uid: address.versionUid,
        },
      });
      return response.data;
    },
  };
}

/** The review, or an idle query while the version's address is not known yet. */
export function useSectionReview(address: VersionAddress | null) {
  return useQuery<SectionReview>({
    ...sectionReviewQueryOptions(
      address ?? { projectUid: '', documentUid: '', versionUid: '' },
    ),
    enabled: address !== null,
  });
}
