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
 * **What is shown** is `SectionSpecificationAnswer`: each project with its sets, its own price
 * list and its own totals, the current versions nobody classified, and the Form-7 rows with
 * project, set, version, sheet and page on every line and the match against that project's
 * price list. Rows come a page at a time.
 */

import { useEffect, useState } from 'react';

import type { ProjectSection as ContractProjectSection, ProjectUid } from '@/shared/api';
import { failureMessage } from '@/shared/api/failure-message';
import { ErrorState, LoadingState } from '@/shared/ui';
import { ANALYSED_SECTION_CODE, projectSectionTitle, sectionsInStructureOrder } from '@/entities/project';
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

export function SectionSpecificationSection() {
  const [sectionCode, setSectionCode] = useState<ContractProjectSection>(ANALYSED_SECTION_CODE);
  const [projectUid, setProjectUid] = useState<ProjectUid | null>(null);
  const [draft, setDraft] = useState('');
  const [query, setQuery] = useState('');
  const [offset, setOffset] = useState(0);
  const [members, setMembers] = useState<readonly Member[]>([]);
  const specification = useSectionSpecification({ sectionCode, projectUid, query, offset });
  const answer = specification.data;
  const failure = specification.error === null ? null : failureMessage(specification.error);

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
  }

  function chooseProject(uid: ProjectUid | null) {
    setProjectUid(uid);
    setOffset(0);
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
            data-section-project-filter={members.length}
          >
            <option value="">Все проекты раздела</option>
            {members.map((member) => (
              <option key={member.projectUid} value={member.projectUid}>
                {member.name}
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
