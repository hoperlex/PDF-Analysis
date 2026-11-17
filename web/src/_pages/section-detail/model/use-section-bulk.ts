'use client';

/**
 * The actions of the section's bottom bar over the chosen documents (`UIP-S02-04`): the state each one holds and the way it gives the
 * choice back. Only the expert's bar has them: `BatchSelection.selection` is `undefined` for anyone else and the bar is not drawn.
 *
 * **«В архив (N)»** sends one archive command per document (`useArchiveDocuments`, the feature's) and at its end leaves the choice
 * with the documents that were refused, so the same button retries exactly those; the bar keeps the one message of the pass until it is
 * dismissed, even when nothing is chosen any more.
 */

import { useEffect, useMemo, useState } from 'react';

import type { DocumentVersion, ProjectUid } from '@/shared/api';
import type { ArchiveProgress, ArchiveReport, ArchiveSend } from '@/features/manage-document';
import { useArchiveDocuments } from '@/features/manage-document';
import type { BatchSelection } from '@/widgets/project-sections';

import type { ListingWalk } from './use-listing-walk';
import { bulkTargets } from './section-bulk';

/** What the bar is given to act on: the project, the documents the page has read and, for a test, the commands to send. */
export interface SectionBulkScope {
  readonly projectUid: ProjectUid;
  /** The cards in front of the reader. */
  readonly pageDocuments: readonly DocumentVersion[];
  /** The listing read to its end, or `idle` when the page is all of it. */
  readonly walk: ListingWalk;
  /** Injected by tests. Production sends `setDocumentArchived`. */
  readonly sendArchive?: ArchiveSend | undefined;
}

/** «В архив (N)»: what the bar draws of it. */
export interface SectionArchiveView {
  /** The chosen documents it would send: the ones not archived yet. */
  readonly count: number;
  readonly pending: boolean;
  readonly progress: ArchiveProgress | null;
  readonly report: ArchiveReport | null;
  readonly onArchive: () => void;
  readonly onDismiss: () => void;
}

export interface SectionBulk {
  readonly archive: SectionArchiveView;
}

/**
 * Every version the page has shown, by uid: the documents in front of the reader and the whole listing once it was read, with the
 * ones shown on an earlier page kept, because a card chosen there stays chosen when the reader goes on.
 */
function useShownDocuments(pageDocuments: readonly DocumentVersion[], walk: ListingWalk): ReadonlyMap<string, DocumentVersion> {
  const whole = walk.status === 'complete' ? walk.items : undefined;
  const [remembered, setRemembered] = useState<ReadonlyMap<string, DocumentVersion>>(new Map());
  useEffect(() => {
    setRemembered((held) => {
      let next: Map<string, DocumentVersion> | null = null;
      for (const version of [...pageDocuments, ...(whole ?? [])]) {
        if (held.get(version.version_uid) === version) continue;
        next ??= new Map(held);
        next.set(version.version_uid, version);
      }
      return next ?? held;
    });
  }, [pageDocuments, whole]);
  return useMemo(() => {
    const shown = new Map(remembered);
    for (const version of [...pageDocuments, ...(whole ?? [])]) shown.set(version.version_uid, version);
    return shown;
  }, [remembered, pageDocuments, whole]);
}

export function useSectionBulk(scope: SectionBulkScope, selection: BatchSelection): SectionBulk {
  const shown = useShownDocuments(scope.pageDocuments, scope.walk);
  const targets = useMemo(
    () => bulkTargets(selection.selection?.selected ?? new Set<string>(), shown),
    [selection.selection?.selected, shown],
  );
  const archive = useArchiveDocuments(scope.projectUid, scope.sendArchive);

  const onArchive = (): void => {
    const sent = targets.archivable;
    void archive.archive(sent).then((report) => {
      if (report === null) return;
      // The choice stays with the documents the server refused, so the same button retries exactly those.
      const refused = new Set(report.failed.map((failure) => failure.target.documentUid));
      const left = [...shown.values()].filter((version) => refused.has(version.document_uid));
      if (left.length === 0) selection.clear();
      else selection.choose(left);
    });
  };

  return {
    archive: {
      count: targets.archivable.length,
      pending: archive.pending,
      progress: archive.progress,
      report: archive.report,
      onArchive,
      onDismiss: archive.dismiss,
    },
  };
}
