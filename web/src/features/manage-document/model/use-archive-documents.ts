'use client';

/**
 * «В архив (N)» over several documents (`UIP-S02-04`): the keys, the cache and the state of one pass of {@link archiveDocuments}.
 *
 * Plain component state, as `useUploadMany`: a pass is a loop of keyed commands with a result per document, which a single
 * mutation cannot say. Each document has its own idempotency key for the intent «archive it»; a document the server refused keeps
 * its key, so pressing the button again for it is a retry of the same command, and a document that was archived gives its key
 * up, so archiving it once more after it came back is a new command and not a replay of the old answer. When the pass is over,
 * every read that shows the documents is re-read once.
 */

import { useCallback, useRef, useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';

import type { DocumentVersion, ProjectUid } from '@/shared/api';
import { failureMessage, newIdempotencyKey, queryKeys, setDocumentArchived } from '@/shared/api';

import type { ArchiveProgress, ArchiveReport, ArchiveSend, ArchiveTarget } from './bulk-archive';
import { archiveDocuments } from './bulk-archive';

export interface UseArchiveDocuments {
  /** Send the archive command for each target; resolves with what the pass did, or `null` when it did not start (one is running, or no targets). */
  readonly archive: (targets: readonly ArchiveTarget[]) => Promise<ArchiveReport | null>;
  readonly pending: boolean;
  readonly progress: ArchiveProgress | null;
  /** What the last pass did, until it is dismissed or the next pass starts. */
  readonly report: ArchiveReport | null;
  readonly dismiss: () => void;
}

export function useArchiveDocuments(projectUid: ProjectUid, send?: ArchiveSend | undefined): UseArchiveDocuments {
  const client = useQueryClient();
  const keys = useRef(new Map<string, string>());
  const running = useRef(false);
  const [pending, setPending] = useState(false);
  const [progress, setProgress] = useState<ArchiveProgress | null>(null);
  const [report, setReport] = useState<ArchiveReport | null>(null);

  const archive = useCallback(async (targets: readonly ArchiveTarget[]): Promise<ArchiveReport | null> => {
    if (running.current || targets.length === 0) return null;
    running.current = true;
    setPending(true);
    setReport(null);
    setProgress({ done: 0, total: new Set(targets.map((target) => target.documentUid)).size });
    const command: ArchiveSend = send ?? (async (target, idempotencyKey) => (await setDocumentArchived({
      path: { project_uid: projectUid, document_uid: target.documentUid },
      body: { archived: true },
      idempotencyKey,
    })).data);
    const intent = (target: ArchiveTarget): string => `archive:${target.documentUid}:true`;
    try {
      const result = await archiveDocuments({
        targets,
        send: command,
        keyOf: (target) => {
          const known = keys.current.get(intent(target));
          if (known !== undefined) return known;
          const key = newIdempotencyKey();
          keys.current.set(intent(target), key);
          return key;
        },
        reasonOf: (error) => failureMessage(error).detail,
        onStep: (step, archived: DocumentVersion | null) => {
          setProgress(step);
          if (archived !== null) client.setQueryData(queryKeys.versions.detail(archived.version_uid), archived);
        },
      });
      for (const target of result.archived) {
        keys.current.delete(intent(target));
        void client.invalidateQueries({ queryKey: queryKeys.versions.lists(target.documentUid) });
      }
      if (result.archived.length > 0) {
        void client.invalidateQueries({ queryKey: queryKeys.projects.all() });
        void client.invalidateQueries({ queryKey: queryKeys.dashboard.summary() });
      }
      setReport(result);
      return result;
    } finally {
      running.current = false;
      setPending(false);
      setProgress(null);
    }
  }, [client, projectUid, send]);

  const dismiss = useCallback(() => { setReport(null); }, []);

  return { archive, pending, progress, report, dismiss };
}
