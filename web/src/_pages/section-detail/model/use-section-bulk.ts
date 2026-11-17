'use client';

/**
 * The actions of the section's bottom bar over the chosen documents (`UIP-S02-04`, `UIP-S02-05`): the state each one holds and the way
 * it gives the choice back. Only the expert's bar has them: `BatchSelection.selection` is `undefined` for anyone else and the bar is not
 * drawn.
 *
 * **«В архив (N)»** sends one archive command per document (`useArchiveDocuments`, the feature's) and at its end leaves the choice
 * with the documents that were refused, so the same button retries exactly those; the bar keeps the one message of the pass until it is
 * dismissed, even when nothing is chosen any more.
 *
 * **«Скачать пакеты аудита»** builds, in the browser, the audit package of each chosen document that has a result and hands one ZIP
 * of them over (`useAuditPackages`, the export panel's); the choice is left as it is, because nothing of the documents changed. Documents
 * with no result are skipped and listed; more documents than the limit, or none with a result, is refused in words before any request.
 */

import { useEffect, useMemo, useState } from 'react';

import type { DocumentVersion, ProjectUid } from '@/shared/api';
import type { ErrorStateProps } from '@/shared/ui';
import type { DownloadSink } from '@/features/export-run';
import type { ArchiveProgress, ArchiveReport, ArchiveSend } from '@/features/manage-document';
import { useArchiveDocuments } from '@/features/manage-document';
import type { AuditPackagesDeps, AuditPackagesDocument, AuditPackagesSummary } from '@/widgets/export-panel';
import { auditPackagesRefusal, useAuditPackages } from '@/widgets/export-panel';
import type { BatchSelection } from '@/widgets/project-sections';

import type { ListingWalk } from './use-listing-walk';
import { bulkTargets } from './section-bulk';

/** What the bar is given to act on: the project, the documents the page has read and, for a test, the commands to send. */
export interface SectionBulkScope {
  readonly projectUid: ProjectUid;
  /** The section's code, which names the common ZIP of the packages. */
  readonly sectionCode: string;
  /** The cards in front of the reader. */
  readonly pageDocuments: readonly DocumentVersion[];
  /** The listing read to its end, or `idle` when the page is all of it. */
  readonly walk: ListingWalk;
  /** Injected by tests. Production sends `setDocumentArchived`. */
  readonly sendArchive?: ArchiveSend | undefined;
  /** Injected by tests. Production hands the file to the browser and builds the packages from the server. */
  readonly packages?: { readonly sink?: DownloadSink | undefined; readonly deps?: AuditPackagesDeps | undefined } | undefined;
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

/** «Скачать пакеты аудита»: what the bar draws of it. */
export interface SectionPackagesView {
  /** The chosen documents that get a package: the ones with a result. */
  readonly count: number;
  /** The chosen documents with no result, which are skipped. */
  readonly skippedCount: number;
  /** Why the button cannot be pressed, in words (nothing with a result, or more than the limit), or `null`. */
  readonly refusal: string | null;
  readonly pending: boolean;
  /** The phase while it builds, what the archive holds, or that it was cancelled. */
  readonly status: string | null;
  /** What the last archive holds: the skipped documents are listed from it. */
  readonly summary: AuditPackagesSummary | null;
  readonly error: ErrorStateProps | null;
  readonly onDownload: () => void;
  readonly onCancel: () => void;
  readonly onDismiss: () => void;
}

export interface SectionBulk {
  readonly archive: SectionArchiveView;
  readonly packages: SectionPackagesView;
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
  const packs = useAuditPackages({ sink: scope.packages?.sink, deps: scope.packages?.deps });

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

  const onDownload = (): void => {
    const documents: readonly AuditPackagesDocument[] = [...targets.packages.packable, ...targets.packages.skipped];
    packs.download(documents, `audit-packages-${scope.sectionCode}.zip`);
  };

  return {
    packages: {
      count: targets.packages.packable.length,
      skippedCount: targets.packages.skipped.length,
      refusal: auditPackagesRefusal(targets.packages),
      pending: packs.isPending,
      status: packs.status,
      summary: packs.summary,
      error: packs.error,
      onDownload,
      onCancel: packs.cancel,
      onDismiss: packs.dismiss,
    },
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
