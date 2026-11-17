/**
 * The groups of a section's documents (`UIP-S02-06`, owner ruling Г11): a group is a value of the document (`DocumentVersion.group`, set by
 * `UIP-G-10`), not an entity — it is there as long as a document is in it, it has no record of its own, no order of its own and no
 * name that can be changed apart from its documents. The section page draws the cards by group only when at least one document of the
 * section has one; with none, nothing here applies and the grid is the plain one.
 *
 * **Whole or nothing.** A group's number is the count of the documents of the listing in view, so the groups are made of the whole
 * listing (the page that fits one page, or the walk's pages read to their end — {@link wholeListing}) and never of the page in front
 * of the reader: a part of the section drawn as groups would give numbers that are not the groups'.
 *
 * **The order of the groups is one function** ({@link orderGroupNames}). Alphabetical for now — the owner has not ruled on a
 * manual order (Г11 is open on it) — so that his ruling changes this one place and nothing around it.
 *
 * Pure: the same documents give the same groups.
 */

import type { DocumentVersion } from '@/shared/api';

/** What the group of the documents that have none is called on the screen; it is not a name a group can have. */
export const NO_GROUP_LABEL = 'Без группы';

/** The longest group name the server stores (`UIP-G-10`: 1 to 40 characters). */
export const GROUP_NAME_MAX_LENGTH = 40;

export interface DocumentGroup {
  /** The group's name, or `null` for the documents that have no group («Без группы»). */
  readonly name: string | null;
  /** The group's documents, in the order the listing had them. */
  readonly documents: readonly DocumentVersion[];
}

/** The group of one document, or `null` when it has none (an absent value, or one that is only spaces, is «Без группы»). */
export function groupOf(version: DocumentVersion): string | null {
  const group = version.group?.trim();
  return group === undefined || group === '' ? null : group;
}

// Numbers inside a name count as numbers («Корпус 2» before «Корпус 10»); case is no difference; a tie falls to the code points, so the order is total.
const COLLATOR = new Intl.Collator('ru', { numeric: true, sensitivity: 'base' });

/**
 * The order the named groups stand in, the one place that decides it: alphabetical, numbers by value. «Без группы» is not a name and
 * is not here; it stands last wherever the groups are drawn.
 */
export function orderGroupNames(names: readonly string[]): readonly string[] {
  return [...names].sort((a, b) => COLLATOR.compare(a, b) || (a < b ? -1 : a > b ? 1 : 0));
}

/**
 * The listing's documents by group, or `null` when none of them has a group (the section is then drawn as one plain grid, with no
 * headings). The named groups come in {@link orderGroupNames} order, «Без группы» last and only when a document is in it.
 */
export function groupDocuments(documents: readonly DocumentVersion[]): readonly DocumentGroup[] | null {
  const named = new Map<string, DocumentVersion[]>();
  const ungrouped: DocumentVersion[] = [];
  for (const version of documents) {
    const name = groupOf(version);
    if (name === null) {
      ungrouped.push(version);
      continue;
    }
    const members = named.get(name);
    if (members === undefined) named.set(name, [version]);
    else members.push(version);
  }
  if (named.size === 0) return null;
  const groups: DocumentGroup[] = orderGroupNames([...named.keys()]).map((name) => ({ name, documents: named.get(name) ?? [] }));
  if (ungrouped.length > 0) groups.push({ name: null, documents: ungrouped });
  return groups;
}
