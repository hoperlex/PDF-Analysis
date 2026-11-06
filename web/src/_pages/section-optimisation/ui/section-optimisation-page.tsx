'use client';

/**
 * `/section-optimisation` — «Оптимизация разделов» (`R-66`, group «Работа»;
 * `W63-SECTION-FORM7-01`, `UI-B-20`, `UI-B-22`, `UI-B-27`).
 *
 * Two tabs, as in the original: «Спецификация» — `getSectionSpecification` answers, for a section, the
 * combined Form-7 specification of the current versions of every project whose document set an expert confirmed in it
 * (the nine columns of the form with the project, set, version, sheet and page on every row, a project filter and a text
 * search, each row matched against its own project's price list) — and «Принято» — the optimisation proposals whose
 * decision in force is an acceptance, across the section's projects (`listAcceptedOptimisationProposals`). Both are
 * read views: replicating an accepted optimisation into other projects is a later slice, and nothing here writes. The
 * section code only filters; rows are never merged across projects and the totals exist per project and per currency.
 *
 * **The address.** `?section=<code>&project=<project_uid>&tab=accepted` opens the page on that section, narrowed to that
 * project, on that tab (`UI-B-20`); the page keeps the address in step with the choices, and carries the section and the
 * project from one tab to the other. A parameter the address carries that is not a section code or a project identity is
 * set aside and said so. Only the open tab is mounted, so a closed tab shows nothing of its own; each tab does carry the
 * server's number for the section and project chosen («Форма 7 · Спецификация N», «Принято N»), read here without
 * opening it. The two reads are the tabs' own first reads -- the same query keys, so an open tab and its number are one
 * request -- and the number of a tab whose read has not answered, was refused or was stopped at a bound is left off.
 *
 * Not `/optimisation`, which is the optimisation of one project and stays registered, outside
 * the menu, until it becomes a tab of the project screen.
 */

import Link from 'next/link';
import { useId, useRef, useState } from 'react';
import type { KeyboardEvent } from 'react';

import type { ProjectSection, ProjectUid } from '@/shared/api';
import { routes } from '@/shared/lib';
import { PageShell } from '@/shared/ui';
import { useAcceptedOptimisationProposals } from '@/entities/optimisation-proposal';
import { useSectionSpecification } from '@/entities/section-specification';
import { SectionAcceptedOptimisations } from '@/widgets/section-accepted-optimisations';
import { SectionSpecificationSection } from '@/widgets/section-specification';

import { DEFAULT_SECTION_OPTIMISATION_ADDRESS, sectionOptimisationSearch } from '../model/address';
import type { SectionOptimisationAddress } from '../model/address';
import { SECTION_OPTIMISATION_TABS, sectionOptimisationTabText } from '../model/tabs';
import type { SectionOptimisationTab, SectionOptimisationTabCounts } from '../model/tabs';
import styles from './section-optimisation-page.module.css';

export interface SectionOptimisationPageProps {
  /** The tab, section and project the address named; the defaults when absent. */
  readonly initial?: SectionOptimisationAddress | undefined;
}

const IGNORED_TEXT = {
  section: 'раздел',
  project: 'проект',
  tab: 'вкладка',
} as const;

export function SectionOptimisationPage({ initial = DEFAULT_SECTION_OPTIMISATION_ADDRESS }: SectionOptimisationPageProps) {
  const base = useId();
  const buttons = useRef<Partial<Record<SectionOptimisationTab, HTMLButtonElement | null>>>({});
  const [tab, setTab] = useState<SectionOptimisationTab>(initial.tab);
  const [filter, setFilter] = useState<{ readonly sectionCode: ProjectSection; readonly projectUid: ProjectUid | null }>({
    sectionCode: initial.sectionCode,
    projectUid: initial.projectUid,
  });

  // The tabs' numbers. `row_count` counts every row in scope apart from the text search, and only a `ready` answer has
  // one worth showing: a section the server stopped at a bound (`section_too_large`) lists no rows.
  const specification = useSectionSpecification({
    sectionCode: filter.sectionCode,
    projectUid: filter.projectUid,
    query: '',
    offset: 0,
  });
  const accepted = useAcceptedOptimisationProposals({ sectionCode: filter.sectionCode, projectUid: filter.projectUid });
  const counts: SectionOptimisationTabCounts = {
    specification:
      specification.data !== undefined && specification.data.section_code === filter.sectionCode && specification.data.state === 'ready'
        ? specification.data.row_count
        : null,
    accepted: accepted.data?.total ?? null,
  };

  function keep(next: { readonly tab: SectionOptimisationTab; readonly sectionCode: ProjectSection; readonly projectUid: ProjectUid | null }) {
    // A reload or a pasted link opens the same view: the address follows every choice, without a new history entry.
    if (typeof window !== 'undefined') window.history.replaceState(null, '', sectionOptimisationSearch(next));
  }

  function chooseTab(next: SectionOptimisationTab) {
    setTab(next);
    keep({ tab: next, ...filter });
  }

  function chooseFilter(next: { readonly sectionCode: ProjectSection; readonly projectUid: ProjectUid | null }) {
    setFilter(next);
    keep({ tab, ...next });
  }

  const onKeyDown = (event: KeyboardEvent<HTMLButtonElement>) => {
    const at = SECTION_OPTIMISATION_TABS.indexOf(tab);
    const last = SECTION_OPTIMISATION_TABS.length - 1;
    const next =
      event.key === 'ArrowRight'
        ? SECTION_OPTIMISATION_TABS[at === last ? 0 : at + 1]
        : event.key === 'ArrowLeft'
          ? SECTION_OPTIMISATION_TABS[at === 0 ? last : at - 1]
          : event.key === 'Home'
            ? SECTION_OPTIMISATION_TABS[0]
            : event.key === 'End'
              ? SECTION_OPTIMISATION_TABS[last]
              : undefined;
    if (next === undefined) return;
    event.preventDefault();
    chooseTab(next);
    buttons.current[next]?.focus();
  };

  return (
    <PageShell
      title="Оптимизация разделов"
      subtitle="Сводная спецификация раздела по текущим версиям комплектов всех проектов и принятые экспертами оптимизации. Экран только показывает данные: переносить решения между проектами здесь пока нельзя."
    >
      {initial.ignored.length === 0 ? null : (
        <p className={styles.notice} data-address-ignored={initial.ignored.join(' ')}>
          Из адреса не прочитано: {initial.ignored.map((name) => IGNORED_TEXT[name]).join(', ')}. Экран открыт с выбором по умолчанию.
        </p>
      )}
      {/*
        * The original's «←» on this screen leads back to the section's projects. The way back here is where the reader came
        * from: the project's section page when the address names a project, and the dashboard (the section table) when it names none.
        */}
      <p className={styles.back} data-section-optimisation-back={filter.projectUid === null ? 'dashboard' : 'section'}>
        {filter.projectUid === null ? (
          <Link href="/dashboard">← К дашборду</Link>
        ) : (
          <Link href={routes.projectSection(filter.projectUid, filter.sectionCode)}>← К разделу проекта</Link>
        )}
      </p>
      <div className={styles.tabs}>
        <div role="tablist" aria-label="Вкладки оптимизации раздела" className={styles.tablist}>
          {SECTION_OPTIMISATION_TABS.map((name) => (
            <button
              key={name}
              ref={(element) => {
                buttons.current[name] = element;
              }}
              type="button"
              role="tab"
              id={`${base}-tab-${name}`}
              aria-selected={name === tab}
              aria-controls={`${base}-panel`}
              tabIndex={name === tab ? 0 : -1}
              className={styles.tab}
              data-section-optimisation-tab={name}
              onClick={() => chooseTab(name)}
              onKeyDown={onKeyDown}
            >
              {sectionOptimisationTabText(name, counts)}
            </button>
          ))}
        </div>
        <div
          role="tabpanel"
          id={`${base}-panel`}
          aria-labelledby={`${base}-tab-${tab}`}
          tabIndex={0}
          className={styles.panel}
          data-section-optimisation-panel={tab}
        >
          {tab === 'specification' ? (
            <SectionSpecificationSection
              initialSectionCode={filter.sectionCode}
              initialProjectUid={filter.projectUid}
              onFilterChange={chooseFilter}
            />
          ) : (
            <SectionAcceptedOptimisations
              sectionCode={filter.sectionCode}
              projectUid={filter.projectUid}
              onSection={(sectionCode) => chooseFilter({ sectionCode, projectUid: null })}
              onProject={(projectUid) => chooseFilter({ sectionCode: filter.sectionCode, projectUid })}
            />
          )}
        </div>
      </div>
    </PageShell>
  );
}
