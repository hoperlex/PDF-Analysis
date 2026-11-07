'use client';

/**
 * «Принято» on «Оптимизация разделов» (`UI-B-27`, contract 1.35.0): the optimisation proposals whose decision in force
 * is an acceptance, across the projects of a section — the original's «библиотека опыта».
 *
 * **What is listed.** `listAcceptedOptimisationProposals`, newest acceptance first, a page at a time. A proposal an
 * expert rejected, sent back, decided and then withdrew, or never decided is not here; a proposal accepted again after
 * a withdrawal is. The section and the project are filters, not parents: a section nothing was accepted in is an empty
 * page, said as such. Each row names its project and document set and leads to the document's «Оптимизация» tab, on the
 * pass the proposal belongs to (`UI-B-02`). Every price and the saving are the API's exact text; a saving the API
 * leaves out is said to be not computed, never shown as zero.
 *
 * **Filters.** The section is chosen from the fifteen in the structure's order; the project from the projects the
 * installation lists, and a project the address names is offered even when the first page of projects lacks it (it is
 * read on its own), so an address never opens on a selection the control cannot show.
 */

import Link from 'next/link';
import { useState } from 'react';

import type { AcceptedOptimisationProposal, AcceptedOptimisationProposalPage, ProjectSection, ProjectUid } from '@/shared/api';
import { failureMessage } from '@/shared/api/failure-message';
import { formatInstant, routes } from '@/shared/lib';
import type { TableColumn } from '@/shared/ui';
import { EmptyState, ErrorState, LoadingState, Table } from '@/shared/ui';
import { findProjectSection, projectSectionTitle, sectionsInStructureOrder, useProject, useProjectList } from '@/entities/project';
import { CarriedMark } from '@/entities/expert-decision';
import { formatAmount, formatDecimal, useAcceptedOptimisationProposals } from '@/entities/optimisation-proposal';

import styles from './section-accepted-optimisations.module.css';

export interface ProjectOption {
  readonly projectUid: ProjectUid;
  readonly name: string;
}

/** «16 000 руб.», or why there is no figure. Never `0` for an absent saving. */
export function acceptedSaving(row: AcceptedOptimisationProposal): string {
  return row.saving === null ? 'не рассчитана' : formatAmount(row.saving, row.currency);
}

/** The quantity with its unit, or that it is not a number. */
export function acceptedQuantity(row: AcceptedOptimisationProposal): string {
  return row.quantity === null ? `не число (${row.unit})` : `${formatDecimal(row.quantity)} ${row.unit}`;
}

/** The section by its title; a code this build does not know is left as the server sent it. */
export function acceptedSectionTitle(code: string | undefined): string | null {
  if (code === undefined) return null;
  const section = findProjectSection(code);
  return section === null ? code : projectSectionTitle(section);
}

const COLUMNS: readonly TableColumn<AcceptedOptimisationProposal>[] = [
  {
    key: 'place',
    header: 'Проект и комплект',
    cell: (row) => (
      <>
        <Link href={routes.documentOptimisation(row.project_uid, row.document_uid, row.optimisation_pass_id)}>
          {row.project_name}
        </Link>
        <span className={styles.place}>
          {[row.document_name, acceptedSectionTitle(row.section)].filter((part) => part !== null).join(' · ')}
        </span>
        <span className={styles.place}>
          страница {row.page_number}
          {row.row_position === null ? '' : `, позиция ${row.row_position}`}
        </span>
      </>
    ),
  },
  { key: 'row', header: 'Позиция спецификации', cell: (row) => row.row_text },
  {
    key: 'change',
    header: 'Принятая замена',
    cell: (row) => (
      <>
        <span className={styles.change}>{row.matched_name}</span>
        <span className={styles.change}>
          → {row.proposed_name} · {row.proposed_vendor}
        </span>
        <span className={styles.place}>
          {formatAmount(row.current_unit_price, row.currency)} → {formatAmount(row.proposed_unit_price, row.currency)} за{' '}
          {row.unit}
        </span>
      </>
    ),
  },
  { key: 'quantity', header: 'Количество', cell: acceptedQuantity },
  { key: 'saving', header: 'Экономия', cell: acceptedSaving },
  {
    key: 'decision',
    header: 'Решение',
    cell: (row) => (
      <>
        {row.actor_label}, <time dateTime={row.decided_at}>{formatInstant(row.decided_at)}</time>
        {/* `D-335`: an acceptance carried over from an earlier version's pass says so, «↩ Перенесено из V2». */}
        {row.carried_from === null ? null : (
          <>
            {' '}
            <CarriedMark carriedFrom={row.carried_from} />
          </>
        )}
        {row.comment === null ? null : <span className={styles.comment}>{row.comment}</span>}
      </>
    ),
  },
];

export interface SectionAcceptedFiltersProps {
  readonly sectionCode: ProjectSection;
  readonly projectUid: ProjectUid | null;
  readonly projects: readonly ProjectOption[];
  readonly onSection: (code: ProjectSection) => void;
  readonly onProject: (uid: ProjectUid | null) => void;
}

/** The section and project selects. Rendered by the static harness. */
export function SectionAcceptedFilters({ sectionCode, projectUid, projects, onSection, onProject }: SectionAcceptedFiltersProps) {
  return (
    <form className={`am-form ${styles.filters}`} aria-label="Отбор принятых оптимизаций" onSubmit={(event) => event.preventDefault()}>
      <div className="am-form__field">
        <label htmlFor="section-accepted-section">
          <strong>Раздел</strong>
        </label>
        <select
          id="section-accepted-section"
          value={sectionCode}
          onChange={(event) => onSection(event.target.value as ProjectSection)}
          data-accepted-section-picker={sectionsInStructureOrder().length}
        >
          {sectionsInStructureOrder().map((section) => (
            <option key={section.code} value={section.code}>
              {projectSectionTitle(section)}
            </option>
          ))}
        </select>
      </div>
      <div className="am-form__field">
        <label htmlFor="section-accepted-project">
          <strong>Проект</strong>
        </label>
        <select
          id="section-accepted-project"
          value={projectUid ?? ''}
          onChange={(event) => onProject(event.target.value === '' ? null : (event.target.value as ProjectUid))}
          data-accepted-project-filter={projects.length}
        >
          <option value="">Все проекты раздела</option>
          {projects.map((project) => (
            <option key={project.projectUid} value={project.projectUid}>
              {project.name}
            </option>
          ))}
        </select>
      </div>
    </form>
  );
}

export interface SectionAcceptedListProps {
  readonly page: AcceptedOptimisationProposalPage;
  readonly hasPrevious: boolean;
  readonly onPrevious: () => void;
  readonly onNext: (cursor: string) => void;
}

/** The answer: the count, the rows, the pager — or the empty page said in words. Rendered by the static harness. */
export function SectionAcceptedList({ page, hasPrevious, onPrevious, onNext }: SectionAcceptedListProps) {
  const next = page.page.next_cursor;
  if (page.items.length === 0 && !hasPrevious) {
    return (
      <EmptyState
        title="Нет принятых экспертом оптимизаций."
        detail="Непроверенные, отклонённые и возвращённые на доработку предложения сюда намеренно не включаются. Принятое появится здесь после решения эксперта на вкладке «Оптимизация» комплекта."
      />
    );
  }
  return (
    <div data-accepted-count={page.total}>
      <p className={styles.summary}>Принято предложений: {page.total}</p>
      <Table columns={COLUMNS} rows={page.items} rowKey={(row) => row.optimisation_proposal_id} caption="Принятые оптимизации раздела" />
      <p className={styles.pager}>
        <button type="button" className="am-button am-button--quiet" disabled={!hasPrevious} onClick={onPrevious}>
          Назад
        </button>
        <button type="button" className="am-button am-button--quiet" disabled={next === null} onClick={() => next !== null && onNext(next)}>
          Далее
        </button>
      </p>
    </div>
  );
}

export interface SectionAcceptedOptimisationsProps {
  readonly sectionCode: ProjectSection;
  readonly projectUid: ProjectUid | null;
  readonly onSection: (code: ProjectSection) => void;
  readonly onProject: (uid: ProjectUid | null) => void;
}

/**
 * The project options: the first page of projects, and the selected project even when that page lacks it (read on its
 * own by `getProject`; until it answers, its identity is the only honest label).
 */
export function projectOptions(
  listed: readonly { readonly project_uid: ProjectUid; readonly name: string }[],
  selected: ProjectUid | null,
  selectedName: string | null,
): readonly ProjectOption[] {
  const options = listed.map((project) => ({ projectUid: project.project_uid, name: project.name }));
  if (selected !== null && !options.some((option) => option.projectUid === selected)) {
    options.push({ projectUid: selected, name: selectedName ?? selected });
  }
  return options;
}

export function SectionAcceptedOptimisations({ sectionCode, projectUid, onSection, onProject }: SectionAcceptedOptimisationsProps) {
  const [cursors, setCursors] = useState<readonly string[]>([]);
  const cursor = cursors.at(-1);
  const accepted = useAcceptedOptimisationProposals({ sectionCode, projectUid, ...(cursor === undefined ? {} : { cursor }) });
  const listed = useProjectList();
  const selected = useProject(projectUid);
  const options = projectOptions(listed.data?.items ?? [], projectUid, selected.data?.name ?? null);
  const failure = accepted.error === null ? null : failureMessage(accepted.error);
  const page = accepted.data;

  function restart<T>(change: (value: T) => void) {
    return (value: T) => {
      setCursors([]);
      change(value);
    };
  }

  return (
    <section className={styles.section} aria-label="Принятые оптимизации раздела" data-section-accepted="">
      <p className={styles.rule}>
        Предложения оптимизации, по которым действующее решение — «принято», по проектам выбранного раздела, сначала недавние.
        Раздел и проект только отбирают записи; каждая строка остаётся предложением своего проекта и прохода, и по ссылке открывается
        вкладка «Оптимизация» его комплекта.
      </p>
      <SectionAcceptedFilters
        sectionCode={sectionCode}
        projectUid={projectUid}
        projects={options}
        onSection={restart(onSection)}
        onProject={restart(onProject)}
      />
      {accepted.isPending ? <LoadingState what="принятых оптимизаций" /> : null}
      {failure !== null ? (
        <div data-accepted-failure={failure.kind}>
          <ErrorState
            title="Принятые оптимизации не прочитаны"
            detail={failure.detail}
            correlationId={failure.correlationId}
            onRetry={() => void accepted.refetch()}
          />
        </div>
      ) : null}
      {page !== undefined && failure === null ? (
        <SectionAcceptedList
          page={page}
          hasPrevious={cursors.length > 0}
          onPrevious={() => setCursors((held) => held.slice(0, -1))}
          onNext={(next) => setCursors((held) => [...held, next])}
        />
      ) : null}
    </section>
  );
}
