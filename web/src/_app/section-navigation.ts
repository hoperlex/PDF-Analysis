/**
 * The «Разделы» group of the side menu, as data (`UI-A-04`, owner ruling `R-151l`).
 *
 * The original's menu has a parent «Разделы» with one sub-item per discipline of the current object, each with a
 * count badge, leading to that discipline's page. Here the object is the **current project** (`R-150c`: the project
 * the address names), the page is the section page (`/projects/[project_uid]/sections/[section_code]`), and the
 * counts are the ones the dashboard's section panel shows: `getDashboardSummary` for that project, whose
 * `section_breakdown` counts a document in the section an expert confirmed for its current version and leaves the
 * archived ones out. This module adds no read of its own; `use-section-navigation.ts` asks the dashboard's.
 *
 * **Every section of the project is listed** (`R-153g`), in the order of the project structure (`S-5`), the ones with
 * no document too: the menu shows the project's whole structure, so a reader sees which sections are still empty
 * instead of wondering where they went. (Until `R-153g` only the sections that held documents were listed.) An empty
 * section is an entry like the others, with a count of 0 that the menu draws muted, no red badge, and a link to its
 * section page, which says that the section holds no document yet.
 *
 * **A reading that is not whole is not a list.** `section_breakdown` carries each of the fifteen sections exactly
 * once, zeros included. A response short of that, with a section this build does not know, or naming one twice, is
 * reported as `failed` rather than as a shorter menu, the same rule `summarizeSectionBreakdown` holds for the
 * dashboard (`W46-WIRE`, `Y5-a`): a row the server did not send is not a zero. A list that is `ready` therefore holds
 * all fifteen entries, which is why the group has no note for an empty list (it was `SECTIONS_EMPTY_NOTE` until
 * `R-153g`): that case cannot occur.
 *
 * The labels are the section page's own: the Cyrillic mark a designer writes on a title block (`АР`) and, as the
 * link's name and tooltip, the section's name. The Latin code reaches the markup only as a data attribute.
 *
 * **The red badge (`UI-A-05`).** Beside the count, a section whose documents wait for an expert shows how many:
 * `audit_counts.awaiting_decision` of the same row, the documents of the section whose result run has a finding
 * nobody has decided (`docs/program/UI-PARITY-METRICS.md` §2, `R-150o`). It is the server's figure, in the answer the
 * group already reads, so there is no second read; a row that carries no counts has no figure (`null`), which draws no
 * badge, and zero draws none either.
 *
 * **The group's own figures (`D-360`).** The original's parent row «Разделы» carries the summed red count and, in grey, how
 * many projects the sub-menu holds, so both are seen while it is folded. The same here: {@link sectionsSummary} sums the
 * entries' red figures and their documents (the original's "project" is our document), and the group's button draws
 * them beside its name (`frame-navigation.tsx`). Nothing is read for it: the sums are over the entries the group lists,
 * which are all of the project's sections (`R-153g`), so a project with no document has a sum of 0.
 */

import type { SectionDocumentCount } from '@/shared/api';
import type { ProjectSectionCode } from '@/entities/project';
import { PROJECT_SECTIONS, findProjectSection, sectionsInStructureOrder } from '@/entities/project';
import { routes } from '@/shared/lib';

import { UNCHECKED_BADGE_LABEL, uncheckedClause } from './menu-badges';

/** One sub-item: a section of the current project, with the documents it holds (`R-153g`: none, too). */
export interface SectionNavigationEntry {
  readonly code: ProjectSectionCode;
  /** The Cyrillic mark shown in the menu: `АР`, `КЖ`, `ЭОМ`. */
  readonly abbr: string;
  /** The section's name, for the link's accessible name and tooltip. */
  readonly name: string;
  /** Documents in the section, from the server's count. 0 for a section with none: the menu draws it muted. */
  readonly count: number;
  /**
   * `UI-A-05`: the documents of the section no expert has checked (`audit_counts.awaiting_decision`); `null` when the
   * row carried no counts. A figure of at least 1 is the red badge.
   */
  readonly awaitingDecision: number | null;
  readonly href: string;
  /** The section page being shown: the link carries `aria-current="page"`. */
  readonly current: boolean;
}

/** What the group has to say: still reading, could not be read whole, or the list (always all of the sections). */
export type SectionNavigation =
  | { readonly status: 'loading' }
  | { readonly status: 'failed' }
  | { readonly status: 'ready'; readonly entries: readonly SectionNavigationEntry[] };

/** The group's name in the menu. */
export const SECTIONS_GROUP_LABEL = 'Разделы';

/** What the grey number on the group's button counts (the original's «Всего проектов (без ИРД)»). */
export const SECTIONS_DOCUMENTS_LABEL = 'Документов в разделах';

/** The words of a group that has no list to show. */
export const SECTIONS_LOADING_NOTE = 'Разделы проекта загружаются…';
export const SECTIONS_FAILED_NOTE = 'Разделы проекта не удалось прочитать.';

/**
 * The accessible name of a sub-item: the mark, the name and the count, which the visible badge shortens to a number,
 * and, when there is a red badge, what it counts.
 */
export function sectionEntryLabel(entry: Pick<SectionNavigationEntry, 'abbr' | 'name' | 'count' | 'awaitingDecision'>): string {
  const base = `${entry.abbr} ${entry.name}, документов: ${entry.count}`;
  const unchecked = uncheckedClause(entry.awaitingDecision);
  return unchecked === null ? base : `${base}, ${unchecked}`;
}

/**
 * The group for `projectUid` from the dashboard's `section_breakdown` rows of that project, with the entry whose
 * page is `pathname` marked current: one entry for each of the project's sections, in structure order, the empty ones
 * included (`R-153g`).
 */
export function sectionNavigationOf(
  rows: readonly SectionDocumentCount[],
  projectUid: string,
  pathname: string | null,
): SectionNavigation {
  const counts = new Map<ProjectSectionCode, number>();
  const awaiting = new Map<ProjectSectionCode, number | null>();
  for (const row of rows) {
    if (row.section === undefined) continue; // the «Без раздела» bucket is not a section
    if (findProjectSection(row.section) === null || counts.has(row.section)) return { status: 'failed' };
    counts.set(row.section, row.document_count);
    // A row that carries no counts has no figure: unknown is not zero, and neither draws a badge.
    awaiting.set(row.section, row.audit_counts !== undefined ? row.audit_counts.awaiting_decision : null);
  }
  if (counts.size !== PROJECT_SECTIONS.length) return { status: 'failed' };
  const entries = sectionsInStructureOrder().flatMap((section): SectionNavigationEntry[] => {
    // The reading is whole (`counts.size` is the sections' number, checked above), so every code has its count.
    const count = counts.get(section.code) ?? 0;
    const href = routes.projectSection(projectUid, section.code);
    return [{
      code: section.code,
      abbr: section.abbr,
      name: section.name,
      count,
      awaitingDecision: awaiting.get(section.code) ?? null,
      href,
      current: pathname === href,
    }];
  });
  return { status: 'ready', entries };
}

/** The figures of the whole group: the documents it lists and, of them, the red count (`null` when no entry had one). */
export interface SectionsSummary {
  readonly documents: number;
  readonly awaitingDecision: number | null;
}

/**
 * The group's figures from its entries. An entry with no red figure adds nothing to the red sum, and when none of them
 * has one the sum is unknown (`null`), not zero.
 */
export function sectionsSummary(entries: readonly Pick<SectionNavigationEntry, 'count' | 'awaitingDecision'>[]): SectionsSummary {
  let documents = 0;
  let awaiting: number | null = null;
  for (const entry of entries) {
    documents += entry.count;
    if (entry.awaitingDecision !== null) awaiting = (awaiting ?? 0) + entry.awaitingDecision;
  }
  return { documents, awaitingDecision: awaiting };
}

/**
 * What the group's button counts, as a sentence: `Не проверено экспертом: 3. Документов в разделах: 7`; the first clause
 * only when the red figure is above zero. It follows the group's name in the button's accessible name.
 */
export function sectionsSummaryLabel(summary: SectionsSummary): string {
  const documents = `${SECTIONS_DOCUMENTS_LABEL}: ${summary.documents}`;
  return summary.awaitingDecision !== null && summary.awaitingDecision > 0
    ? `${UNCHECKED_BADGE_LABEL}: ${summary.awaitingDecision}. ${documents}`
    : documents;
}
