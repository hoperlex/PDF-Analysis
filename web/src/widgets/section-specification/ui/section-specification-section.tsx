'use client';

/**
 * «Оптимизация разделов» — a section's combined Form-7 specification across projects
 * (`W63-SECTION-FORM7-01`), the body of `/section-optimisation`.
 *
 * **What is chosen.** The section, in the order of the owner's poll answer `S-5` (АР first),
 * and — optionally — one project of it and a search text. All three are filters over the
 * same read, `getSectionSpecification`: the section code is not an object, a document or a
 * proposal, and nothing here ever writes. A project filter offers the projects the section
 * lists when it is not narrowed; the search narrows the rows and never a project's totals.
 *
 * **Where it starts.** On the section and project the page's address names (`UI-B-20`, optional
 * `initialSectionCode` and `initialProjectUid`); without them, on АР and every project, as before.
 * The project an address names has no unfiltered answer yet, so the project select may not list it:
 * it is offered anyway, named from the answer once the narrowed read lists it (or from its own
 * read, `getProject`, before that), and never silently dropped. `onFilterChange` reports each new
 * section and project, so the page can keep the choice across its tabs.
 *
 * **What is shown** is `SectionSpecificationAnswer`: each project with its sets, its own price
 * list and its own totals, the current versions nobody classified, and the Form-7 rows with
 * project, set, version, sheet and page on every line and the match against that project's
 * price list. Rows come a page at a time.
 */

import { useEffect, useState } from 'react';

import type { ProjectSection as ContractProjectSection, ProjectUid } from '@/shared/api';
import { failureMessage } from '@/shared/api/failure-message';
import { ErrorState, LoadingState } from '@/shared/ui';
import { ANALYSED_SECTION_CODE, projectSectionTitle, sectionsInStructureOrder, useProject } from '@/entities/project';
import { useSectionSpecification } from '@/entities/section-specification';

import { SectionSpecificationAnswer } from './section-specification-answer';
import styles from './section-specification.module.css';

/** The projects an unnarrowed answer listed, kept so the filter can still offer them. */
interface Member {
  readonly projectUid: ProjectUid;
  readonly name: string;
}

export interface SectionPickerProps {
  readonly selected: ContractProjectSection;
  readonly onSelect: (code: ContractProjectSection) => void;
}

/** The section picker: the fifteen sections in `S-5` order. Rendered by the static harness. */
export function SectionPicker({ selected, onSelect }: SectionPickerProps) {
  return (
    <div className="am-form__field">
      <label htmlFor="section-specification-section"><strong>Раздел</strong></label>
      <select
        id="section-specification-section"
        value={selected}
        onChange={(event) => onSelect(event.target.value as ContractProjectSection)}
        data-section-picker={sectionsInStructureOrder().length}
      >
        {sectionsInStructureOrder().map((section) => (
          <option key={section.code} value={section.code}>
            {projectSectionTitle(section)}
          </option>
        ))}
      </select>
    </div>
  );
}

export interface SectionSpecificationSectionProps {
  /** The section to open on (`UI-B-20`); АР when absent. */
  readonly initialSectionCode?: ContractProjectSection | undefined;
  /** The project to open narrowed to; every project of the section when absent. */
  readonly initialProjectUid?: ProjectUid | null | undefined;
  /** Told after every change of section or project, so a page can carry the choice to another tab. */
  readonly onFilterChange?: ((filter: { readonly sectionCode: ContractProjectSection; readonly projectUid: ProjectUid | null }) => void) | undefined;
}

/** A project option as the select shows it: `name` is `null` while nothing in hand names the project. */
export interface ProjectFilterOption {
  readonly projectUid: ProjectUid;
  readonly name: string | null;
}

/**
 * The project options the select shows: the projects an unnarrowed answer listed, and the selected project when that
 * list lacks it (an address opened on a project has no unnarrowed answer yet), named by `selectedName` when the
 * narrowed answer lists it and by `null` otherwise — the option then reads the project itself (`ProjectOptionName`).
 */
export function projectFilterOptions(
  members: readonly Member[],
  selected: ProjectUid | null,
  selectedName: string | null,
): readonly ProjectFilterOption[] {
  if (selected === null || members.some((member) => member.projectUid === selected)) return members;
  return [...members, { projectUid: selected, name: selectedName }];
}

/**
 * The name of a project the lists do not hold, from its own read (`getProject`); its identity — the only label that is
 * true before anything is read — while that is on its way or refused. Mounted only for a project the address names, so
 * a screen opened without one reads no project.
 */
export function ProjectOptionName({ projectUid }: { readonly projectUid: ProjectUid }) {
  const project = useProject(projectUid);
  return <>{project.data?.name ?? projectUid}</>;
}

export function SectionSpecificationSection({
  initialSectionCode,
  initialProjectUid,
  onFilterChange,
}: SectionSpecificationSectionProps) {
  const [sectionCode, setSectionCode] = useState<ContractProjectSection>(initialSectionCode ?? ANALYSED_SECTION_CODE);
  const [projectUid, setProjectUid] = useState<ProjectUid | null>(initialProjectUid ?? null);
  const [draft, setDraft] = useState('');
  const [query, setQuery] = useState('');
  const [offset, setOffset] = useState(0);
  const [members, setMembers] = useState<readonly Member[]>([]);
  const specification = useSectionSpecification({ sectionCode, projectUid, query, offset });
  const answer = specification.data;
  const failure = specification.error === null ? null : failureMessage(specification.error);
  // The narrowed answer lists the project it is narrowed to, so it names it; before it arrives the option reads the project.
  const answeredName =
    answer === undefined || projectUid === null
      ? null
      : (answer.projects.find((project) => project.project_uid === projectUid)?.name ?? null);
  const options = projectFilterOptions(members, projectUid, answeredName);

  // The unnarrowed answer is the only one that lists every project of the section.
  useEffect(() => {
    if (answer !== undefined && answer.section_code === sectionCode && answer.project_filter === null) {
      setMembers(answer.projects.map((project) => ({ projectUid: project.project_uid, name: project.name })));
    }
  }, [answer, sectionCode]);

  function chooseSection(code: ContractProjectSection) {
    setSectionCode(code);
    setProjectUid(null);
    setMembers([]);
    setOffset(0);
    onFilterChange?.({ sectionCode: code, projectUid: null });
  }

  function chooseProject(uid: ProjectUid | null) {
    setProjectUid(uid);
    setOffset(0);
    onFilterChange?.({ sectionCode, projectUid: uid });
  }

  return (
    <section className={styles.section} aria-label="Сводная спецификация раздела" data-section-specification="">
      <p className={styles.rule}>
        Строки спецификации (форма 7) текущих версий комплектов, которые эксперт подтвердил для
        выбранного раздела, из всех проектов. Раздел только отбирает комплекты: каждая строка
        остаётся строкой своего проекта, комплекта и листа и сопоставляется с прайс-листом своего
        проекта. Цена и сумма показаны только для строки, однозначно сопоставленной с позицией в той же
        единице измерения и с числовым количеством; итоги считаются по проектам и валютам отдельно.
      </p>
      <form
        className={`am-form ${styles.filters}`}
        aria-label="Отбор строк раздела"
        onSubmit={(event) => {
          event.preventDefault();
          setQuery(draft.trim());
          setOffset(0);
        }}
      >
        <SectionPicker selected={sectionCode} onSelect={chooseSection} />
        <div className="am-form__field">
          <label htmlFor="section-specification-project"><strong>Проект</strong></label>
          <select
            id="section-specification-project"
            value={projectUid ?? ''}
            onChange={(event) => chooseProject(event.target.value === '' ? null : (event.target.value as ProjectUid))}
            data-section-project-filter={options.length}
          >
            <option value="">Все проекты раздела</option>
            {options.map((member) => (
              <option key={member.projectUid} value={member.projectUid}>
                {member.name ?? <ProjectOptionName projectUid={member.projectUid} />}
              </option>
            ))}
          </select>
        </div>
        <div className="am-form__field">
          <label htmlFor="section-specification-query"><strong>Поиск по строкам</strong></label>
          <input
            id="section-specification-query"
            type="search"
            value={draft}
            maxLength={200}
            placeholder="Наименование, позиция, примечание"
            onChange={(event) => setDraft(event.target.value)}
          />
        </div>
        <button type="submit" className="am-button">Найти</button>
        <button
          type="button"
          className="am-button am-button--quiet"
          onClick={() => {
            setDraft('');
            setQuery('');
            setOffset(0);
          }}
          disabled={draft === '' && query === ''}
        >
          Сбросить поиск
        </button>
        <button type="button" className="am-button am-button--quiet" onClick={() => void specification.refetch()}>
          Обновить
        </button>
      </form>
      {specification.isPending ? <LoadingState what="сводной спецификации раздела" /> : null}
      {failure !== null ? (
        <div data-section-failure={failure.kind}>
          <ErrorState
            title="Сводная спецификация раздела не прочитана"
            detail={failure.detail}
            correlationId={failure.correlationId}
            onRetry={() => void specification.refetch()}
          />
        </div>
      ) : null}
      {answer !== undefined && failure === null ? (
        <SectionSpecificationAnswer
          answer={answer}
          onPage={specification.isPlaceholderData ? null : setOffset}
          onSelectProject={(uid) => chooseProject(uid as ProjectUid)}
        />
      ) : null}
    </section>
  );
}
