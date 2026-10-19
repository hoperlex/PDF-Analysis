'use client';

/**
 * `compareDocumentVersions` for one ordered pair of versions of one set
 * (`W59-VERSION-COMPARE-01`).
 *
 * The older version is always the source and the newer one the target: the caller orders
 * the pair by `version_ordinal` before asking, because the server refuses a reversed pair
 * rather than silently swapping it. A refusal is a successful answer (`outcome: refused`)
 * and is rendered as such; only a transport or server failure is an error here.
 */

import { useQuery } from '@tanstack/react-query';

import type { DocumentUid, ProjectUid, VersionComparison, VersionUid } from '@/shared/api';
import { compareDocumentVersions, queryKeys } from '@/shared/api';

/** Sheets with line differences per answer; the contract allows 1 to 25. */
export const COMPARISON_DIFF_LIMIT = 10;

export type ComparisonMode = VersionComparison['mode'];

export interface VersionComparisonRequest {
  readonly projectUid: ProjectUid;
  readonly documentUid: DocumentUid;
  readonly sourceVersionUid: VersionUid;
  readonly targetVersionUid: VersionUid;
  readonly mode: ComparisonMode;
  readonly diffOffset: number;
}

export function useVersionComparison(request: VersionComparisonRequest | null) {
  return useQuery<VersionComparison>({
    queryKey: queryKeys.versions.comparison(
      request?.sourceVersionUid ?? '',
      request?.targetVersionUid ?? '',
      request?.mode ?? 'version',
      request?.diffOffset ?? 0,
      COMPARISON_DIFF_LIMIT,
    ),
    enabled: request !== null,
    queryFn: async () => {
      if (request === null) throw new Error('no pair chosen');
      const response = await compareDocumentVersions({
        path: {
          project_uid: request.projectUid,
          document_uid: request.documentUid,
          version_uid: request.sourceVersionUid,
        },
        query: {
          target_version_uid: request.targetVersionUid,
          mode: request.mode,
          diff_offset: request.diffOffset,
          diff_limit: COMPARISON_DIFF_LIMIT,
        },
      });
      return response.data;
    },
  });
}
