'use client';

/**
 * The several-files upload of `R-151b`: each file to its own explicit target, one after another.
 *
 * Sequential, so each refusal lands beside its file and the stand admits the uploads in the reader's order. Each
 * file's idempotency key is minted once per intent (`manyFileSignature`: the file and its target) and reused on a
 * retry, so pressing «Загрузить» again after a failure never publishes a file twice. The same two commands the
 * single-file forms send, and the same invalidations.
 */

import { useRef, useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';

import type { ProjectUid } from '@/shared/api';
import { newIdempotencyKey, queryKeys, uploadDocument, uploadDocumentVersion } from '@/shared/api';
import { classifyUploadFailure } from '@/entities/document-version';

import type { ManyFile, ManyOutcome } from './upload-many';
import { manyFileSignature, sendable } from './upload-many';

export interface UploadManyApi {
  readonly outcomes: ReadonlyMap<string, ManyOutcome>;
  readonly sending: boolean;
  readonly send: (files: readonly ManyFile[]) => Promise<void>;
  readonly reset: () => void;
}

export function useUploadMany(projectUid: ProjectUid): UploadManyApi {
  const queryClient = useQueryClient();
  const [outcomes, setOutcomes] = useState<ReadonlyMap<string, ManyOutcome>>(new Map());
  const [sending, setSending] = useState(false);
  const keys = useRef(new Map<string, string>());

  const put = (id: string, outcome: ManyOutcome) => setOutcomes((map) => new Map(map).set(id, outcome));

  async function send(files: readonly ManyFile[]): Promise<void> {
    setSending(true);
    for (const item of sendable(files, outcomes)) {
      const signature = manyFileSignature(projectUid, item);
      const idempotencyKey = keys.current.get(signature) ?? newIdempotencyKey();
      keys.current.set(signature, idempotencyKey);
      put(item.id, { kind: 'sending' });
      try {
        const version = item.target.kind === 'new'
          ? (await uploadDocument({ path: { project_uid: projectUid }, body: { file: item.file }, idempotencyKey })).data
          : (await uploadDocumentVersion({
            path: { project_uid: projectUid, document_uid: item.target.documentUid },
            body: { file: item.file },
            idempotencyKey,
          })).data;
        queryClient.setQueryData(queryKeys.versions.detail(version.version_uid), version);
        if (item.target.kind === 'version') {
          void queryClient.invalidateQueries({ queryKey: queryKeys.versions.lists(version.document_uid) });
        }
        put(item.id, { kind: 'published', version });
      } catch (error) {
        put(item.id, { kind: 'refused', failure: classifyUploadFailure(error) });
      }
    }
    void queryClient.invalidateQueries({ queryKey: queryKeys.projects.all() });
    void queryClient.invalidateQueries({ queryKey: queryKeys.dashboard.summary() });
    setSending(false);
  }

  return { outcomes, sending, send, reset: () => setOutcomes(new Map()) };
}
