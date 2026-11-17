/**
 * What the queue's panel «Добавить документы» offers (`UIP-S13-03`): the documents of the chosen object that can be put in the
 * queue now, and the arithmetic of the choice. Pure: the same documents give the same list.
 *
 * A document is offered when it can be run at all (a version confirmed for a section and not admitted for comparison only: the
 * rule the section page's boxes use, `startable`) **and has no run in flight** (`audit.active_run` is absent): one that is
 * already queued or running is in the list below, not here, and a second run of it would only wait behind the first. A document
 * the listing does not tell the audit of (`audit` absent) is offered: nothing says it is busy.
 */

import type { DocumentVersion, VersionUid } from '@/shared/api';
import { documentCardTitle, sectionTitleOf } from '@/entities/document-version';
import type { BatchEntry } from '@/features/start-run';
import { startable } from '@/widgets/project-sections';

/** The documents of `listing` that can be added to the queue, in the listing's order. */
export function addableDocuments(listing: readonly DocumentVersion[]): readonly DocumentVersion[] {
  return listing.filter((version) => startable(version) && version.audit?.active_run === undefined);
}

/** What the panel says of a document's section: its title, or none for a document with no confirmed section (it is not offered). */
export function addableSection(version: DocumentVersion): string | null {
  return version.classification === undefined ? null : sectionTitleOf(version.classification.section_code);
}

/** The entry the batch panel starts for a document: its version and the name the panel calls it by. */
export function addableEntry(version: DocumentVersion): BatchEntry {
  return { versionUid: version.version_uid as VersionUid, title: documentCardTitle(version) };
}

/** The choice as the batch's entries, in the order the documents are listed (not in the order they were ticked). */
export function chosenEntries(documents: readonly DocumentVersion[], chosen: ReadonlySet<string>): readonly BatchEntry[] {
  return documents.filter((version) => chosen.has(version.version_uid)).map(addableEntry);
}
