/**
 * A project's storage structure: section → the documents in it → each document's current
 * version with its stage (`W59-SECTION-UI-01`).
 *
 * **Where the grouping comes from.** `listDocuments` answers one `DocumentVersion` per
 * document — the version the document currently points at — and since `W59-SECTION-SEAL-01`
 * that body carries the version's expert-confirmed `classification` when it has one. So the
 * structure is built from the one read the project screen already makes, with no second
 * request per document: a document sits under the section confirmed for its **current**
 * version, and in «Не классифицировано» while that version has none. Nothing here reads a
 * file name, a suggestion or the document's legacy `section`; those are not a classification.
 *
 * **Order.** The fifteen sections in the order of the owner's poll answer `S-5`
 * (`PROJECT_STRUCTURE_ORDER` in `entities/project`), every one of them present even when it
 * holds nothing, then the unclassified group. Within a group the server's order is kept.
 */

import type { DocumentVersion } from '@/shared/api';
import type { ProjectSection } from '@/entities/project';
import { sectionsInStructureOrder } from '@/entities/project';

export interface SectionGroup {
  readonly section: ProjectSection;
  /** The documents whose current version is confirmed for this section, in server order. */
  readonly documents: readonly DocumentVersion[];
}

export interface ProjectStructure {
  /** All fifteen sections, in `S-5` order. */
  readonly sections: readonly SectionGroup[];
  /** The documents whose current version has no confirmed classification yet. */
  readonly unclassified: readonly DocumentVersion[];
}

export function projectStructure(items: readonly DocumentVersion[]): ProjectStructure {
  return {
    sections: sectionsInStructureOrder().map((section) => ({
      section,
      documents: items.filter((item) => item.classification?.section_code === section.code),
    })),
    unclassified: items.filter((item) => item.classification === undefined),
  };
}
