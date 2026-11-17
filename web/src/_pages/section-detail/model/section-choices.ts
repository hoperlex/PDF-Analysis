/**
 * What the section page's selection controls can choose (`UI-A-35`, `UIP-S02-01`): the startable documents of the WHOLE listing in
 * view, in three sets — all of them, the ones never run («Выделить необработанные») and the ones waiting for a decision (the plaque
 * «ждут решения N»).
 *
 * The listing is paged by the server's cursor, so the whole of it is the page in front of the reader only while it fits one page
 * (`walk.status === 'idle'`) and the walk's own pages once it has read them all (`'complete'`). While the walk is still reading, or
 * after a page failed, **nothing is chosen from a part**: the answer is `null` and the controls wait, say so and offer to try again,
 * never a part of the section offered as the whole. Pure: the same inputs give the same sets, and a test can state each of them.
 */

import type { DocumentVersion } from '@/shared/api';
import { startable } from '@/widgets/project-sections';

import type { ListingWalk } from './use-listing-walk';

export interface SectionChoices {
  /** Every document of the listing that can be started. */
  readonly all: readonly DocumentVersion[];
  /** Of those, the ones whose audit state is «не запускался». */
  readonly notRun: readonly DocumentVersion[];
  /** Of those, the ones whose result run still has a finding without an expert's decision. */
  readonly awaitingDecision: readonly DocumentVersion[];
}

/**
 * The listing in view, whole: the page itself while it is all of the listing (`idle`), the walk's pages once they are all read
 * (`complete`), and `null` while they are being read or one failed. The groups of `UIP-S02-06` are made of the same.
 */
export function wholeListing(pageDocuments: readonly DocumentVersion[], walk: ListingWalk): readonly DocumentVersion[] | null {
  return walk.status === 'idle' ? pageDocuments : walk.status === 'complete' ? walk.items : null;
}

/** The sets over the whole listing, or `null` while it is not known whole (the walk is reading, or failed). */
export function sectionChoices(pageDocuments: readonly DocumentVersion[], walk: ListingWalk): SectionChoices | null {
  const whole = wholeListing(pageDocuments, walk);
  if (whole === null) return null;
  const all = whole.filter(startable);
  return {
    all,
    notRun: all.filter((version) => version.audit?.state === 'not_run'),
    awaitingDecision: all.filter((version) => version.audit?.state === 'awaiting_decision'),
  };
}
