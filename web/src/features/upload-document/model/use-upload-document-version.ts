'use client';

/**
 * The next-version upload command (`W59-VERSION-UPLOAD-01`).
 *
 * One portal bundle, sent by the generated client as `uploadDocumentVersion`'s
 * `multipart/form-data` body — the same transport as `uploadDocument`, and nothing here builds
 * a `FormData`, a URL or a boundary either. The body is the bundle and nothing else: a further
 * version takes no title (the document keeps its own) and no section.
 *
 * On success the new version is written into the version cache under the frozen key, and
 * every read it changes is asked again rather than patched locally: the document's version
 * list (a new first row), the project's document list and structure (the document's current
 * version moved, so its row and its section grouping read another version), the project
 * detail and listing, and the dashboard, whose panels count versions and sections.
 */

import { useMutation, useQueryClient } from '@tanstack/react-query';

import type { DocumentUid, DocumentVersion, ProjectUid } from '@/shared/api';
import { queryKeys, uploadDocumentVersion } from '@/shared/api';

export interface UploadDocumentVersionCommand {
  readonly projectUid: ProjectUid;
  readonly documentUid: DocumentUid;
  readonly file: File;
  /** Minted once per intent by the caller and reused on every retry. */
  readonly idempotencyKey: string;
}

export function useUploadDocumentVersion() {
  const queryClient = useQueryClient();

  return useMutation<DocumentVersion, unknown, UploadDocumentVersionCommand>({
    mutationFn: async ({ projectUid, documentUid, file, idempotencyKey }) => {
      const response = await uploadDocumentVersion({
        path: { project_uid: projectUid, document_uid: documentUid },
        body: { file },
        idempotencyKey,
      });
      return response.data;
    },
    onSuccess: (version) => {
      queryClient.setQueryData(queryKeys.versions.detail(version.version_uid), version);
      void queryClient.invalidateQueries({
        queryKey: queryKeys.versions.lists(version.document_uid),
      });
      void queryClient.invalidateQueries({ queryKey: queryKeys.projects.all() });
      void queryClient.invalidateQueries({ queryKey: queryKeys.dashboard.summary() });
    },
  });
}
