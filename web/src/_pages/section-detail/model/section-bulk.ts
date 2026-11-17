/**
 * What the bottom bar's actions of a section act on (`UIP-S02-04`, `UIP-S02-05`): the chosen documents, read back from the documents the
 * page has shown.
 *
 * The choice holds version uids and card titles only (`BatchSelection`, the project-sections widget's); an action over documents needs the
 * document's identity and what it is in the listing (archived or not). The page has read that listing, so the chosen versions are looked
 * up in the documents it has shown, never fetched again. Pure: the same inputs give the same targets.
 */

import type { DocumentVersion, VersionUid } from '@/shared/api';
import { documentCardTitle } from '@/entities/document-version';
import type { ArchiveTarget } from '@/features/manage-document';
import { splitAuditPackages } from '@/widgets/export-panel';
import type { AuditPackagesDocument, AuditPackagesSplit } from '@/widgets/export-panel';

export interface BulkTargets {
  /** Documents of the choice that are not archived yet, in the order they were chosen: what «В архив (N)» sends. */
  readonly archivable: readonly ArchiveTarget[];
  /**
   * `UIP-S02-05`: the chosen documents split by whether they have a result run: the ones that get an audit package, and the ones skipped
   * (the package is of a result; a version with none gets none). Archived documents are in it: their results are still theirs.
   */
  readonly packages: AuditPackagesSplit;
}

/**
 * The actions' targets from the chosen version uids. A uid the page never showed is not a chosen card — a card is chosen only while it is
 * drawn (the box, the header's «Выбрать все» over the listing the walk read) — so it is left out and no action is made up for it.
 */
export function bulkTargets(chosen: ReadonlySet<string>, known: ReadonlyMap<string, DocumentVersion>): BulkTargets {
  const archivable: ArchiveTarget[] = [];
  const documents: AuditPackagesDocument[] = [];
  for (const versionUid of chosen) {
    const version = known.get(versionUid);
    if (version === undefined) continue;
    const title = documentCardTitle(version);
    if (version.archived_at === undefined) archivable.push({ documentUid: version.document_uid, title });
    documents.push({ documentUid: version.document_uid, versionUid: version.version_uid as VersionUid, title, runId: version.audit?.result_run_id });
  }
  return { archivable, packages: splitAuditPackages(documents) };
}
