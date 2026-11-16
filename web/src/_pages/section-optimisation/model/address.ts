/**
 * What the address of «Оптимизация разделов» carries (`UI-B-20`): the section (`?section=<code>`), the project the
 * rows are narrowed to (`?project=<project_uid>`) and the tab (`?tab=accepted`, «Спецификация» without it). A link from
 * a section of a project, a reload or a pasted link opens the same view.
 *
 * `?project=all` is the explicit «Все объекты» (`UIP-G-06`): it is read as no project and is not set aside, and it is told
 * from an address that says nothing (`allProjects`), because an address that says nothing opens on the object the account
 * chose last.
 *
 * A value that is not one of the fifteen section codes, or not shaped like a project identity, is not honoured and not
 * guessed at: the page opens on its defaults and says which parameters it set aside.
 */

import type { ProjectSection, ProjectUid } from '@/shared/api';
import { ALL_PROJECTS_PARAM } from '@/shared/lib';
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
  /** `true` when the address says `?project=all`: every object, chosen. Absent otherwise (`projectUid: null` then names none). */
  readonly allProjects?: boolean;
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
  let allProjects = false;
  if (query.project !== undefined && query.project !== '') {
    if (query.project === ALL_PROJECTS_PARAM) allProjects = true;
    else if (looksLikeProjectUid(query.project)) projectUid = query.project as ProjectUid;
    else ignored.push('project');
  }
  let tab: SectionOptimisationTab = 'specification';
  if (query.tab !== undefined && query.tab !== '') {
    if ((SECTION_OPTIMISATION_TABS as readonly string[]).includes(query.tab)) tab = query.tab as SectionOptimisationTab;
    else ignored.push('tab');
  }
  return { tab, sectionCode, projectUid, ignored, ...(allProjects ? { allProjects } : {}) };
}

/**
 * The query string that reopens this view: the section always, the project and the tab when they are not the default.
 * `allProjects` writes the explicit `?project=all` for a view that shows every object by choice, so that a reload does not
 * bring the account's last object back; without a project and without it, the address says nothing about the object.
 */
export function sectionOptimisationSearch({
  tab,
  sectionCode,
  projectUid,
  allProjects = false,
}: Pick<SectionOptimisationAddress, 'tab' | 'sectionCode' | 'projectUid'> & { readonly allProjects?: boolean }): string {
  const params = new URLSearchParams();
  params.set('section', sectionCode);
  if (projectUid !== null) params.set('project', projectUid);
  else if (allProjects) params.set('project', ALL_PROJECTS_PARAM);
  if (tab !== 'specification') params.set('tab', tab);
  return `?${params.toString()}`;
}

/** The object the page was decided on: a project, or «Все объекты» (`allProjects`); neither is an address that says nothing. */
export function objectDecided(address: Pick<SectionOptimisationAddress, 'projectUid' | 'allProjects'>): boolean {
  return address.projectUid !== null || address.allProjects === true;
}

/**
 * The object the page shows (`UIP-G-06`). Once the address or the reader has decided (`decided`), that choice stands, `null`
 * being «Все объекты»; until then the account's last object stands in, so an answer of `getMe` that arrives late is applied to a
 * page nobody has touched and never to one somebody has.
 */
export function shownProject(
  choice: { readonly projectUid: ProjectUid | null; readonly decided: boolean },
  remembered: ProjectUid | null,
): ProjectUid | null {
  return choice.decided ? choice.projectUid : remembered;
}
