/**
 * What the address of «Оптимизация разделов» carries (`UI-B-20`): the section (`?section=<code>`), the project the
 * rows are narrowed to (`?project=<project_uid>`) and the tab (`?tab=accepted`, «Спецификация» without it). A link from
 * a section of a project, a reload or a pasted link opens the same view.
 *
 * A value that is not one of the fifteen section codes, or not shaped like a project identity, is not honoured and not
 * guessed at: the page opens on its defaults and says which parameters it set aside.
 */

import type { ProjectSection, ProjectUid } from '@/shared/api';
import { ANALYSED_SECTION_CODE, findProjectSection, looksLikeProjectUid } from '@/entities/project';

import { SECTION_OPTIMISATION_TABS } from './tabs';
import type { SectionOptimisationTab } from './tabs';

export interface SectionOptimisationAddress {
  readonly tab: SectionOptimisationTab;
  readonly sectionCode: ProjectSection;
  /** The project the rows are narrowed to; `null` shows every project of the section. */
  readonly projectUid: ProjectUid | null;
  /** The parameters of the address that were present and not readable, by name. */
  readonly ignored: readonly ('section' | 'project' | 'tab')[];
}

export const DEFAULT_SECTION_OPTIMISATION_ADDRESS: SectionOptimisationAddress = {
  tab: 'specification',
  sectionCode: ANALYSED_SECTION_CODE,
  projectUid: null,
  ignored: [],
};

export function readSectionOptimisationAddress(query: {
  readonly section?: string | undefined;
  readonly project?: string | undefined;
  readonly tab?: string | undefined;
}): SectionOptimisationAddress {
  const ignored: ('section' | 'project' | 'tab')[] = [];
  let sectionCode: ProjectSection = ANALYSED_SECTION_CODE;
  if (query.section !== undefined && query.section !== '') {
    const found = findProjectSection(query.section);
    if (found === null) ignored.push('section');
    else sectionCode = found.code;
  }
  let projectUid: ProjectUid | null = null;
  if (query.project !== undefined && query.project !== '') {
    if (looksLikeProjectUid(query.project)) projectUid = query.project as ProjectUid;
    else ignored.push('project');
  }
  let tab: SectionOptimisationTab = 'specification';
  if (query.tab !== undefined && query.tab !== '') {
    if ((SECTION_OPTIMISATION_TABS as readonly string[]).includes(query.tab)) tab = query.tab as SectionOptimisationTab;
    else ignored.push('tab');
  }
  return { tab, sectionCode, projectUid, ignored };
}

/** The query string that reopens this view: the section always, the project and the tab when they are not the default. */
export function sectionOptimisationSearch({
  tab,
  sectionCode,
  projectUid,
}: Pick<SectionOptimisationAddress, 'tab' | 'sectionCode' | 'projectUid'>): string {
  const params = new URLSearchParams();
  params.set('section', sectionCode);
  if (projectUid !== null) params.set('project', projectUid);
  if (tab !== 'specification') params.set('tab', tab);
  return `?${params.toString()}`;
}
