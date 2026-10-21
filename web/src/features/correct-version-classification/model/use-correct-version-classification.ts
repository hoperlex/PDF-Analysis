'use client';

/**
 * `correctVersionClassification` (`CLASSIFICATION-CORRECTION-01`): an expert corrects one
 * version's project stage and/or section with a reason, based on the revision the screen
 * showed (`expected_revision`).
 *
 * **No idempotency key, and none is needed.** `expected_revision` is the optimistic-concurrency
 * token that also makes a retry safe: an exact repeat answers the stored revision, a stale one
 * is `409 classification_revision_stale` and changes nothing. `retry: false` all the same --
 * nothing here repeats a write on its own, and the form sends one request per correction
 * (`../model/single-flight.ts`).
 *
 * **What a success changes, and so what is told.** A classification is read in many places, so
 * the list of reads told is the whole list, not the panel's own:
 *
 *   - the version's own review (it carries the history) and detail, and every page of the
 *     document's version list;
 *   - every comparison -- the pair guard answers differently once a side changes stage or
 *     section;
 *   - the project structure and the document lists (`projects.all()`), which render the badges;
 *   - the dashboard's section breakdown;
 *   - every optimisation read (`optimisation.all()`): the priced specification, the passes and
 *     the section Form-7 view admit a version by its current classification.
 *
 * The answer is not written into a cache: when the request was an exact repeat it can be an
 * older revision than the current one, and the review is read again either way.
 *
 * **What a conflict changes.** Nothing on the server. On `classification_revision_stale` and
 * `version_not_classified` the review and the version are read again, so the screen shows the
 * classification that is actually stored.
 */

import { useMutation, useQueryClient } from '@tanstack/react-query';

import type {
  ProjectSection as SectionCode,
  ProjectStage,
  VersionClassification,
} from '@/shared/api';
import { correctVersionClassification, queryKeys } from '@/shared/api';
import type { VersionAddress } from '@/entities/document-version';
import { correctionFailure } from '@/entities/document-version';

export interface CorrectVersionClassificationCommand extends VersionAddress {
  readonly stage: ProjectStage;
  readonly section: SectionCode;
  /** The expert's words. Trimmed before it is sent; the server holds the same rules. */
  readonly reason: string;
  /** The revision the screen was showing: the current one the correction is based on. */
  readonly expectedRevision: number;
}

export function useCorrectVersionClassification() {
  const client = useQueryClient();
  return useMutation<VersionClassification, unknown, CorrectVersionClassificationCommand>({
    mutationFn: async ({ projectUid, documentUid, versionUid, stage, section, reason, expectedRevision }) =>
      (
        await correctVersionClassification({
          path: { project_uid: projectUid, document_uid: documentUid, version_uid: versionUid },
          body: {
            project_stage: stage,
            section_code: section,
            reason: reason.trim(),
            expected_revision: expectedRevision,
          },
        })
      ).data,
    retry: false,
    onSuccess: (_classification, { documentUid, versionUid }) => {
      void client.invalidateQueries({ queryKey: queryKeys.versions.sectionReview(versionUid) });
      void client.invalidateQueries({ queryKey: queryKeys.versions.detail(versionUid) });
      void client.invalidateQueries({ queryKey: queryKeys.versions.lists(documentUid) });
      void client.invalidateQueries({ queryKey: queryKeys.versions.comparisons() });
      void client.invalidateQueries({ queryKey: queryKeys.projects.all() });
      void client.invalidateQueries({ queryKey: queryKeys.dashboard.summary() });
      void client.invalidateQueries({ queryKey: queryKeys.optimisation.all() });
    },
    onError: (error, { versionUid }) => {
      const kind = correctionFailure(error).kind;
      if (kind !== 'stale' && kind !== 'not_classified') return;
      void client.invalidateQueries({ queryKey: queryKeys.versions.sectionReview(versionUid) });
      void client.invalidateQueries({ queryKey: queryKeys.versions.detail(versionUid) });
    },
  });
}
