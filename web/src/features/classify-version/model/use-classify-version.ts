'use client';

/**
 * `classifyDocumentVersion` (`W59-SECTION-UI-01`): an expert confirms one version's project
 * stage (`P`/`R`) and one of the fifteen sections.
 *
 * **No idempotency key, and none is needed.** The command is a write-once on durable state:
 * an exact repeat answers the stored row and keeps the first confirmer, and a different
 * stage or section is `409 conflict` (`version_already_classified`) and changes nothing.
 * `retry: false` all the same — nothing here repeats a write on its own, and the form sends
 * one request per confirmation (`./single-flight.ts`).
 *
 * **What a success changes, and so what is told.** The answer is written into the review's
 * entry and into the version's own (`versions.detail`, whose infinite stale time would
 * otherwise keep the unclassified body), and the review is read again. The document's first
 * page of versions and every project read (`projects.all()`, which holds the project
 * structure) are invalidated, because both render the badge. The dashboard is invalidated
 * too: its section breakdown groups by the document's legacy `section` today and a
 * classification does not write that field, but the backend half of this window
 * (`W59-SECTION-SEAL-01`) is still being written, and one extra read of an aggregate is the
 * cheaper of the two ways to be wrong (integrator ruling for this lane).
 *
 * **What a conflict changes.** Nothing on the server — so the review and the version are
 * read again, and the screen shows the classification that is actually stored.
 */

import { useMutation, useQueryClient } from '@tanstack/react-query';

import type {
  DocumentVersion,
  ProjectSection as SectionCode,
  ProjectStage,
  SectionReview,
  VersionClassification,
} from '@/shared/api';
import { classifyDocumentVersion, queryKeys } from '@/shared/api';
import type { VersionAddress } from '@/entities/document-version';
import { VERSION_PAGE_LIMIT, classificationFailure } from '@/entities/document-version';

export interface ClassifyVersionCommand extends VersionAddress {
  readonly stage: ProjectStage;
  readonly section: SectionCode;
}

export function useClassifyVersion() {
  const client = useQueryClient();
  return useMutation<VersionClassification, unknown, ClassifyVersionCommand>({
    mutationFn: async ({ projectUid, documentUid, versionUid, stage, section }) =>
      (
        await classifyDocumentVersion({
          path: { project_uid: projectUid, document_uid: documentUid, version_uid: versionUid },
          body: { project_stage: stage, section_code: section },
        })
      ).data,
    retry: false,
    onSuccess: (classification, { documentUid, versionUid }) => {
      client.setQueryData<SectionReview>(queryKeys.versions.sectionReview(versionUid), (review) =>
        review === undefined ? review : { ...review, classification },
      );
      client.setQueryData<DocumentVersion>(queryKeys.versions.detail(versionUid), (version) =>
        version === undefined ? version : { ...version, classification },
      );
      void client.invalidateQueries({ queryKey: queryKeys.versions.sectionReview(versionUid) });
      void client.invalidateQueries({
        queryKey: queryKeys.versions.list(documentUid, undefined, VERSION_PAGE_LIMIT),
      });
      void client.invalidateQueries({ queryKey: queryKeys.projects.all() });
      void client.invalidateQueries({ queryKey: queryKeys.dashboard.summary() });
    },
    onError: (error, { versionUid }) => {
      if (classificationFailure(error).kind !== 'already_classified') return;
      void client.invalidateQueries({ queryKey: queryKeys.versions.sectionReview(versionUid) });
      void client.invalidateQueries({ queryKey: queryKeys.versions.detail(versionUid) });
    },
  });
}
