/**
 * What the bottom bar's actions of a section act on (`UIP-S02-04`): the chosen documents, read back from the documents the page has
 * shown.
 *
 * The choice holds version uids and card titles only (`BatchSelection`, the project-sections widget's); an action over documents needs the
 * document's identity and what it is in the listing (archived or not). The page has read that listing, so the chosen versions are looked
 * up in the documents it has shown, never fetched again. Pure: the same inputs give the same targets.
 */

import type { DocumentVersion } from '@/shared/api';
import { documentCardTitle } from '@/entities/document-version';
import type { ArchiveTarget } from '@/features/manage-document';

export interface BulkTargets {
  /** Documents of the choice that are not archived yet, in the order they were chosen: what «В архив (N)» sends. */
  readonly archivable: readonly ArchiveTarget[];
}

/**
 * The actions' targets from the chosen version uids. A uid the page never showed is not a chosen card — a card is chosen only while it is
 * drawn (the box, the header's «Выбрать все» over the listing the walk read) — so it is left out and no action is made up for it.
 */
export function bulkTargets(chosen: ReadonlySet<string>, known: ReadonlyMap<string, DocumentVersion>): BulkTargets {
  const archivable: ArchiveTarget[] = [];
  for (const versionUid of chosen) {
    const version = known.get(versionUid);
    if (version === undefined) continue;
    if (version.archived_at === undefined) archivable.push({ documentUid: version.document_uid, title: documentCardTitle(version) });
  }
  return { archivable };
}
