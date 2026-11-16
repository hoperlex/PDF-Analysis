'use client';

/**
 * Archive, restore and rename one document (`R-151a`, contract 1.22.0); set its free tags (`R-151e`) and its group (`UIP-G-10`).
 *
 * The original deletes and renames folders; ours archives (a reversible flag that hides the document from lists and
 * keeps every version, run and decision) and renames (the display title changes, `document_uid` stays). Each command
 * is keyed: one idempotency key per intent, reused on a retry. On success every read that shows the document is
 * re-read: the project's lists, the document's versions and the dashboard.
 */

import { useRef } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';

import type { DocumentUid, DocumentVersion, ProjectUid } from '@/shared/api';
import {
  newIdempotencyKey, queryKeys, renameDocument, setDocumentArchived, setDocumentGroup, setDocumentTags,
} from '@/shared/api';

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

/** `R-151e`: replace a document's free tags with a whole new set. */
export function useSetDocumentTags({ projectUid, documentUid }: DocumentAddress) {
  const keyOf = useIntentKeys();
  const refresh = useRefresh(documentUid);
  return useMutation<DocumentVersion, unknown, { readonly tags: readonly string[] }>({
    mutationFn: async ({ tags }) => (await setDocumentTags({
      path: { project_uid: projectUid, document_uid: documentUid },
      body: { tags: [...tags] },
      idempotencyKey: keyOf(`tags:${documentUid}:${tags.join('\u0000')}`),
    })).data,
    retry: false,
    onSuccess: refresh,
  });
}

/**
 * `UIP-G-10` (owner ruling Г11): put a document into one group, move it to another, or take it out (`null`, or a blank text).
 * The group is a value of the document, not an entity: the server trims it and holds it to 1 to 40 characters. The reads that show
 * the group are re-read as for the tags.
 */
export function useSetDocumentGroup({ projectUid, documentUid }: DocumentAddress) {
  const keyOf = useIntentKeys();
  const refresh = useRefresh(documentUid);
  return useMutation<DocumentVersion, unknown, { readonly group: string | null }>({
    mutationFn: async ({ group }) => (await setDocumentGroup({
      path: { project_uid: projectUid, document_uid: documentUid },
      body: { group },
      idempotencyKey: keyOf(`group:${documentUid}:${group ?? ''}`),
    })).data,
    retry: false,
    onSuccess: refresh,
  });
}

/** A tag as the server stores it (trimmed, spaces collapsed), or why it cannot be added. */
export function tagProblem(value: string, current: readonly string[]): string | null {
  const tag = value.split(/\s+/).filter(Boolean).join(' ');
  if (tag === '') return 'Метка не может быть пустой.';
  if (tag.length > 40) return 'Метка длиннее 40 символов.';
  if (current.some((known) => known.toLocaleLowerCase('ru') === tag.toLocaleLowerCase('ru'))) return 'Такая метка уже есть.';
  if (current.length >= 10) return 'У документа не больше 10 меток.';
  return null;
}

export function cleanTag(value: string): string {
  return value.split(/\s+/).filter(Boolean).join(' ');
}
