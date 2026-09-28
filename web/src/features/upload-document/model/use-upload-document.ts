'use client';

/**
 * The upload command.
 *
 * One PDF, sent as the contract's `multipart/form-data` body by the generated client.
 * Nothing here builds a `FormData`, a URL or a boundary: that is the transport's job and
 * there is one implementation of it.
 *
 * On success the published version is written into the version cache under the frozen
 * key, and the project detail is invalidated so the document count is re-read rather
 * than incremented locally — a count the browser maintains is a second source of truth.
 *
 * `W46-WIRE`: the dashboard's one read is invalidated too. An upload changes two of its
 * four panels the moment the server accepts it — `documents_by_project` (this project now
 * has one more) and `section_breakdown` (the upload names a section or it does not, and
 * either way a row's count moves) — and there is no cheaper way to keep that screen honest
 * than asking the server again.
 */

import { useMutation, useQueryClient } from '@tanstack/react-query';

import type { DocumentVersion, ProjectUid } from '@/shared/api';
import { queryKeys, uploadDocument } from '@/shared/api';

export interface UploadDocumentCommand {
  readonly projectUid: ProjectUid;
  readonly file: File;
  /** Optional display label. Never an identity, and neither is the file name. */
  readonly displayTitle?: string | undefined;
  /** Minted once per intent by the caller and reused on every retry. */
  readonly idempotencyKey: string;
}

export function useUploadDocument() {
  const queryClient = useQueryClient();

  return useMutation<DocumentVersion, unknown, UploadDocumentCommand>({
    mutationFn: async ({ projectUid, file, displayTitle, idempotencyKey }) => {
      const title = displayTitle?.trim() ?? '';
      const response = await uploadDocument({
        path: { project_uid: projectUid },
        body: { file, ...(title === '' ? {} : { display_title: title }) },
        idempotencyKey,
      });
      return response.data;
    },
    onSuccess: (version) => {
      queryClient.setQueryData(queryKeys.versions.detail(version.version_uid), version);
      void queryClient.invalidateQueries({
        queryKey: queryKeys.projects.detail(version.project_uid),
      });
      void queryClient.invalidateQueries({ queryKey: queryKeys.projects.all() });
      void queryClient.invalidateQueries({ queryKey: queryKeys.dashboard.summary() });
    },
  });
}
