'use client';

/**
 * `/section-optimisation` — «Оптимизация разделов» (`R-66`, group «Работа»;
 * `W63-SECTION-FORM7-01`, `UI-B-22`, `UI-B-27`).
 *
 * Two tabs, as in the original: «Спецификация» — `getSectionSpecification` answers, for a section, the
 * combined Form-7 specification of the current versions of every project whose document set an expert confirmed in it
 * (the nine columns of the form with the project, set, version, sheet and page on every row, a project filter and a text
 * search, each row matched against its own project's price list) — and «Принято» — the optimisation proposals whose
 * decision in force is an acceptance, across the section's projects (`listAcceptedOptimisationProposals`). Both are
 * read views: replicating an accepted optimisation into other projects is a later slice, and nothing here writes. The
 * section code only filters; rows are never merged across projects and the totals exist per project and per currency.
 * Only the open tab is mounted, so a closed tab reads nothing.
 *
 * Not `/optimisation`, which is the optimisation of one project and stays registered, outside
 * the menu, until it becomes a tab of the project screen.
 */

import { useId, useRef, useState } from 'react';
import type { KeyboardEvent } from 'react';

import type { ProjectSection, ProjectUid } from '@/shared/api';
import { PageShell } from '@/shared/ui';
import { ANALYSED_SECTION_CODE } from '@/entities/project';
import { SectionAcceptedOptimisations } from '@/widgets/section-accepted-optimisations';
import { SectionSpecificationSection } from '@/widgets/section-specification';

import { SECTION_OPTIMISATION_TABS, SECTION_OPTIMISATION_TAB_LABELS } from '../model/tabs';
import type { SectionOptimisationTab } from '../model/tabs';
import styles from './section-optimisation-page.module.css';

export function SectionOptimisationPage() {
  const base = useId();
  const buttons = useRef<Partial<Record<SectionOptimisationTab, HTMLButtonElement | null>>>({});
  const [tab, setTab] = useState<SectionOptimisationTab>('specification');
  const [sectionCode, setSectionCode] = useState<ProjectSection>(ANALYSED_SECTION_CODE);
  const [projectUid, setProjectUid] = useState<ProjectUid | null>(null);

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
    setTab(next);
    buttons.current[next]?.focus();
  };

  return (
    <PageShell
      title="Оптимизация разделов"
      subtitle="Сводная спецификация раздела по текущим версиям комплектов всех проектов и принятые экспертами оптимизации. Экран только показывает данные: переносить решения между проектами здесь пока нельзя."
    >
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
              onClick={() => setTab(name)}
              onKeyDown={onKeyDown}
            >
              {SECTION_OPTIMISATION_TAB_LABELS[name]}
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
            <SectionSpecificationSection />
          ) : (
            <SectionAcceptedOptimisations
              sectionCode={sectionCode}
              projectUid={projectUid}
              onSection={(code) => {
                setSectionCode(code);
                setProjectUid(null);
              }}
              onProject={setProjectUid}
            />
          )}
        </div>
      </div>
    </PageShell>
  );
}
