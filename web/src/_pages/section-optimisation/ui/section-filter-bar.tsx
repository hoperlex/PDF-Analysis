'use client';

/**
 * The section and project selects of «Оптимизация разделов», in the row of the tabs (`UI-B-24`).
 *
 * The original chooses the project of its section summary in the toolbar beside the tabs, one select for every tab; the
 * selects were inside each tab's own form, so the choice was made twice and lost between tabs. They are the page's now: the
 * page holds the section and the project, and both tabs read them.
 *
 * The projects offered are the ones an unnarrowed read of the section listed. An address that names a project has no
 * unnarrowed answer yet, so the project is offered anyway: named from the narrowed answer once that lists it, from its own
 * read (`getProject`) before that, by its identity until either answers — and never silently dropped.
 */

import type { ProjectSection, ProjectUid } from '@/shared/api';
import { projectSectionTitle, sectionsInStructureOrder, useProject } from '@/entities/project';

import styles from './section-optimisation-page.module.css';

/** A project the section lists. */
export interface SectionMember {
  readonly projectUid: ProjectUid;
  readonly name: string;
}

/** A project option as the select shows it: `name` is `null` while nothing in hand names the project. */
export interface ProjectFilterOption {
  readonly projectUid: ProjectUid;
  readonly name: string | null;
}

/**
 * The project options the select shows: the projects an unnarrowed answer listed, and the selected project when that
 * list lacks it, named by `selectedName` when the narrowed answer lists it and by `null` otherwise — the option then reads
 * the project itself (`ProjectOptionName`).
 */
export function projectFilterOptions(
  members: readonly SectionMember[],
  selected: ProjectUid | null,
  selectedName: string | null,
): readonly ProjectFilterOption[] {
  if (selected === null || members.some((member) => member.projectUid === selected)) return members;
  return [...members, { projectUid: selected, name: selectedName }];
}

/**
 * The name of a project the lists do not hold, from its own read (`getProject`); its identity — the only label that is
 * true before anything is read — while that is on its way or refused. Mounted only for a project the address names, so a
 * screen opened without one reads no project.
 */
export function ProjectOptionName({ projectUid }: { readonly projectUid: ProjectUid }) {
  const project = useProject(projectUid);
  return <>{project.data?.name ?? projectUid}</>;
}

export interface SectionFilterBarProps {
  readonly sectionCode: ProjectSection;
  readonly projectUid: ProjectUid | null;
  readonly options: readonly ProjectFilterOption[];
  readonly onSection: (code: ProjectSection) => void;
  readonly onProject: (uid: ProjectUid | null) => void;
}

export function SectionFilterBar({ sectionCode, projectUid, options, onSection, onProject }: SectionFilterBarProps) {
  return (
    <form className={styles.filterBar} aria-label="Раздел и проект" onSubmit={(event) => event.preventDefault()} data-section-filter-bar="">
      <label className={styles.filterField}>
        <span>Раздел</span>
        {/* The literal id is what the PC-01 journey's write half addresses (`section-form7-without-members`), and its
            conformance test finds the handle by this text in web/src; `SECTION_SELECT_ID` names the same value. */}
        <select
          id="section-specification-section"
          value={sectionCode}
          onChange={(event) => onSection(event.target.value as ProjectSection)}
          data-section-picker={sectionsInStructureOrder().length}
        >
          {sectionsInStructureOrder().map((section) => (
            <option key={section.code} value={section.code}>
              {projectSectionTitle(section)}
            </option>
          ))}
        </select>
      </label>
      <label className={styles.filterField}>
        <span>Проект</span>
        <select
          id="section-specification-project"
          value={projectUid ?? ''}
          onChange={(event) => onProject(event.target.value === '' ? null : (event.target.value as ProjectUid))}
          data-section-project-filter={options.length}
        >
          <option value="">Все проекты раздела</option>
          {options.map((option) => (
            <option key={option.projectUid} value={option.projectUid}>
              {option.name ?? <ProjectOptionName projectUid={option.projectUid} />}
            </option>
          ))}
        </select>
      </label>
    </form>
  );
}
