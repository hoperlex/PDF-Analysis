'use client';

/**
 * «Оптимизация разделов» — a section's combined Form-7 specification across projects
 * (`W63-SECTION-FORM7-01`), the body of the page's «Форма 7» tab.
 *
 * **What is chosen here.** The search text, and the columns: the original's nine graphs of the form (default), or the same
 * table with the match against the project's price list added (`UI-B-23`). The section and the project are the page's, chosen in
 * the row of the tabs as the original chooses its project there (`UI-B-24`); this widget reads them (`sectionCode`,
 * `projectUid`) and never writes them but through `onSelectProject`, the button of a project's panel that narrows the section
 * to it. All of them are filters over the one read, `getSectionSpecification`: the section code is not an object, a document
 * or a proposal, and nothing here ever writes. The search narrows the rows and never a project's totals.
 *
 * **What is shown** is `SectionSpecificationAnswer`: each project with its sets, its own price list and its own totals, the
 * current versions nobody classified, and the Form-7 rows grouped under their project, each with set, version, sheet and
 * page and, on request, the match against that project's price list. Rows come a page at a time.
 */

import { useState } from 'react';

import type { ProjectSection as ContractProjectSection, ProjectUid } from '@/shared/api';
import { failureMessage } from '@/shared/api/failure-message';
import { ErrorState, LoadingState } from '@/shared/ui';
import { ANALYSED_SECTION_CODE } from '@/entities/project';
import { useSectionSpecification } from '@/entities/section-specification';

import { SectionSpecificationAnswer } from './section-specification-answer';
import type { SectionSpecificationColumns } from './section-specification-answer';
import styles from './section-specification.module.css';

/**
 * The ids of the section and project selects. The selects are drawn by the page, in the row of the tabs (`UI-B-24`), but these are
 * the handles the browser journey (`section-form7`) has always pressed them by; they stay authored here, with the screen's
 * other controls, so the journey's handles and the page's selects cannot drift apart.
 */
export const SECTION_SELECT_ID = 'section-specification-section';
export const PROJECT_SELECT_ID = 'section-specification-project';

export interface SectionSpecificationSectionProps {
  /** The section read; АР when absent. */
  readonly sectionCode?: ContractProjectSection | undefined;
  /** The project the rows are narrowed to; every project of the section when absent. */
  readonly projectUid?: ProjectUid | null | undefined;
  /** Narrow the section to one project (the button of a project's panel). */
  readonly onSelectProject?: ((projectUid: ProjectUid) => void) | undefined;
}

export function SectionSpecificationSection({
  sectionCode = ANALYSED_SECTION_CODE,
  projectUid = null,
  onSelectProject,
}: SectionSpecificationSectionProps) {
  const [draft, setDraft] = useState('');
  const [query, setQuery] = useState('');
  const [offset, setOffset] = useState(0);
  const [columns, setColumns] = useState<SectionSpecificationColumns>('form7');
  // A page of rows belongs to the section and project it was read under; another one starts from the first page.
  const scope = `${sectionCode}|${projectUid ?? ''}`;
  const [seenScope, setSeenScope] = useState(scope);
  if (seenScope !== scope) {
    setSeenScope(scope);
    setOffset(0);
  }
  const specification = useSectionSpecification({ sectionCode, projectUid, query, offset });
  const answer = specification.data;
  const failure = specification.error === null ? null : failureMessage(specification.error);

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
        {/* `UI-B-23`: the original has the form's nine graphs only; the match against the price list is ours, kept one click away. */}
        <label className={styles.options}>
          <input
            type="checkbox"
            checked={columns === 'priced'}
            data-section-columns-toggle=""
            onChange={(event) => setColumns(event.target.checked ? 'priced' : 'form7')}
          />
          Показать сопоставление с прайс-листом
        </label>
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
          columns={columns}
          onPage={specification.isPlaceholderData ? null : setOffset}
          onSelectProject={onSelectProject === undefined ? null : (uid) => onSelectProject(uid as ProjectUid)}
        />
      ) : null}
    </section>
  );
}
