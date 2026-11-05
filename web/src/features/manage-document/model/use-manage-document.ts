'use client';

/**
 * Archive, restore and rename one document (`R-151a`, contract 1.22.0).
 *
 * The original deletes and renames folders; ours archives (a reversible flag that hides the document from lists and
 * keeps every version, run and decision) and renames (the display title changes, `document_uid` stays). Each command
 * is keyed: one idempotency key per intent, reused on a retry. On success every read that shows the document is
 * re-read: the project's lists, the document's versions and the dashboard.
 */

import { useRef } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';

import type { DocumentUid, DocumentVersion, ProjectUid } from '@/shared/api';
import { newIdempotencyKey, queryKeys, renameDocument, setDocumentArchived } from '@/shared/api';

export interface DocumentAddress {
  readonly projectUid: ProjectUid;
  readonly documentUid: DocumentUid;
}

/** One key per intent: the same intent again (a retry) keeps its key, another intent mints a new one. */
function useIntentKeys() {
  const keys = useRef(new Map<string, string>());
  return (intent: string): string => {
    const known = keys.current.get(intent);
    if (known !== undefined) return known;
    const key = newIdempotencyKey();
    keys.current.set(intent, key);
    return key;
  };
}

function useRefresh(documentUid: DocumentUid) {
  const client = useQueryClient();
  return (version: DocumentVersion) => {
    client.setQueryData(queryKeys.versions.detail(version.version_uid), version);
    void client.invalidateQueries({ queryKey: queryKeys.projects.all() });
    void client.invalidateQueries({ queryKey: queryKeys.versions.lists(documentUid) });
    void client.invalidateQueries({ queryKey: queryKeys.dashboard.summary() });
  };
}

export function useSetDocumentArchived({ projectUid, documentUid }: DocumentAddress) {
  const keyOf = useIntentKeys();
  const refresh = useRefresh(documentUid);
  return useMutation<DocumentVersion, unknown, { readonly archived: boolean }>({
    mutationFn: async ({ archived }) => (await setDocumentArchived({
      path: { project_uid: projectUid, document_uid: documentUid },
      body: { archived },
      idempotencyKey: keyOf(`archive:${documentUid}:${archived}`),
    })).data,
    retry: false,
    onSuccess: refresh,
  });
}

export function useRenameDocument({ projectUid, documentUid }: DocumentAddress) {
  const keyOf = useIntentKeys();
  const refresh = useRefresh(documentUid);
  return useMutation<DocumentVersion, unknown, { readonly displayTitle: string }>({
    mutationFn: async ({ displayTitle }) => (await renameDocument({
      path: { project_uid: projectUid, document_uid: documentUid },
      body: { display_title: displayTitle },
      idempotencyKey: keyOf(`rename:${documentUid}:${displayTitle}`),
    })).data,
    retry: false,
    onSuccess: refresh,
  });
}

/** The title as the server will store it, or why it cannot be sent: trimmed, 1 to 400 characters. */
export function titleProblem(value: string): string | null {
  const title = value.trim();
  if (title === '') return 'Название не может быть пустым.';
  if (title.length > 400) return 'Название длиннее 400 символов.';
  return null;
}
