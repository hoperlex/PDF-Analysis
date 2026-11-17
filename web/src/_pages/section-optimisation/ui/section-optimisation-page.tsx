'use client';

/**
 * `/section-optimisation` — «Оптимизация раздела» (`R-66`, group «Работа»;
 * `W63-SECTION-FORM7-01`, `UI-B-20`, `UI-B-22`, `UI-B-27`, `UIP-S11-01`).
 *
 * Two tabs, as in the original: «Спецификация» — `getSectionSpecification` answers, for a section, the
 * combined Form-7 specification of the current versions of every project whose document set an expert confirmed in it
 * (the nine columns of the form with the project, set, version, sheet and page on every row and a text
 * search, each row matched against its own project's price list) — and «Принято» — the optimisation proposals whose
 * decision in force is an acceptance, across the section's projects (`listAcceptedOptimisationProposals`). Both are
 * read views: replicating an accepted optimisation into other projects is a later slice, and nothing here writes. The
 * section code only filters; rows are never merged across projects and the totals exist per project and per currency.
 *
 * **The header** (`UIP-S11-01`) is the original's: «←», the section's badge, «Уровень раздела», «Оптимизация раздела», the list of
 * sections (ours: one screen for all fifteen) and one line of what the screen holds; the long paragraph is behind «ⓘ».
 *
 * **The object** (`UIP-G-06`, `UIP-S11-01`; the registry class is `optional`) is the one of the top strip, and there is no list of
 * projects on this screen. The address says it first (`?project=<uid>`, `?project=all` for «Все объекты»), and an address that
 * says nothing opens on the object the account chose last (`getMe`), and on every object where there is none. The screen reads it
 * from the live address (`useCurrentProject`), so a choice in the top strip moves the scope of both tabs without a reload. Where
 * no router is mounted (a one-pass render, which has no address) the address the route read (`initial`) stands.
 *
 * **The address.** `?section=<code>&project=<project_uid>&tab=accepted` opens the page on that section, narrowed to that
 * project, on that tab (`UI-B-20`); the page keeps the address in step with the choices, and carries the section and the
 * project from one tab to the other. A parameter the address carries that is not a section code or a project identity is
 * set aside and said so. Only the open tab is mounted, so a closed tab shows nothing of its own; each tab does carry the
 * server's number for the section and project chosen («Форма 7 · Спецификация N», «Принято N»), read here without
 * opening it. The two reads are the tabs' own first reads -- the same query keys, so an open tab and its number are one
 * request -- and the number of a tab whose read has not answered, was refused or was stopped at a bound is left off.
 *
 * **The row of the tabs** holds the tabs and, at its end, the filter «Документ» (`UIP-S11-06`): «Все документы раздела» and the
 * documents the scope lists, «АР-1 · v2». The choice narrows both tabs and the numbers on them, goes into the address
 * (`?document=<document_uid>`) and is forgotten when the section or the object changes — a document names nothing in another
 * object or section. The documents are the sources of the scope's unnarrowed read, which is the tabs' own first read while no document
 * is chosen. The «Форма 7» tab shows the form's nine graphs with the rows grouped under a row per
 * project that folds («+» and «−» unfold and fold them all), as the original draws it (`UI-B-23`).
 *
 * Not `/optimisation`, which is the optimisation of one project and stays registered, outside
 * the menu, until it becomes a tab of the project screen.
 */

import { usePathname, useSearchParams } from 'next/navigation';
import { useEffect, useId, useRef, useState } from 'react';
import type { KeyboardEvent } from 'react';

import type { DocumentUid, ProjectSection, ProjectUid } from '@/shared/api';
import { useAcceptedOptimisationProposals } from '@/entities/optimisation-proposal';
import { useAddressProject, useCurrentProject } from '@/entities/project';
import { useSectionSpecification } from '@/entities/section-specification';
import { SectionAcceptedOptimisations } from '@/widgets/section-accepted-optimisations';
import { SectionSpecificationSection } from '@/widgets/section-specification';

import {
  DEFAULT_SECTION_OPTIMISATION_ADDRESS, objectDecided, readDocumentParam, sectionOptimisationSearch, shownProject,
} from '../model/address';
import type { SectionOptimisationAddress } from '../model/address';
import { SECTION_OPTIMISATION_TABS, sectionOptimisationTabText } from '../model/tabs';
import type { SectionOptimisationTab, SectionOptimisationTabCounts } from '../model/tabs';
import { DocumentFilter, documentFilterOptions, withSelectedDocument } from './document-filter';
import { SectionHeader } from './section-header';
import styles from './section-optimisation-page.module.css';

export interface SectionOptimisationPageProps {
  /** The tab, section and project the address named; the defaults when absent. */
  readonly initial?: SectionOptimisationAddress | undefined;
}

const IGNORED_TEXT = {
  section: 'раздел',
  project: 'объект',
  tab: 'вкладка',
  document: 'документ',
} as const;

/** This screen's registry address: it stands in for the address where no router is mounted, so the class (`optional`) is known. */
const SECTION_OPTIMISATION_ADDRESS = '/section-optimisation';

/** Rewrite the address to `search` without a new history entry, where there is a browser history to write to. */
function rewriteAddress(search: string): void {
  if (typeof window === 'undefined' || typeof window.history?.replaceState !== 'function') return;
  window.history.replaceState(null, '', search);
}

export function SectionOptimisationPage({ initial = DEFAULT_SECTION_OPTIMISATION_ADDRESS }: SectionOptimisationPageProps) {
  const base = useId();
  const buttons = useRef<Partial<Record<SectionOptimisationTab, HTMLButtonElement | null>>>({});
  const [tab, setTab] = useState<SectionOptimisationTab>(initial.tab);
  const [sectionCode, setSectionCode] = useState<ProjectSection>(initial.sectionCode);
  // The document of the scope (`UIP-S11-06`): the address the route read, or, where a router is mounted, the live one — the route
  // passes the parameters it knows, and `?document=` is read here whatever it passed. Held by identity, never by its title.
  const addressParams = useSearchParams();
  const [addressedDocument] = useState(() =>
    readDocumentParam(addressParams === null ? (initial.documentUid ?? null) : addressParams.get('document')),
  );
  const [documentUid, setDocumentUid] = useState<DocumentUid | null>(addressedDocument.documentUid);

  // The object is the top strip's (`UIP-S11-01`): the live address, and where it says nothing the account's last object, through
  // `useCurrentProject`, so a choice in the strip changes the scope of both tabs with no reload. Where no router is mounted the
  // address the route read stands: an object it decided, or the account's last one (`shownProject`) until it has.
  const routed = usePathname() !== null;
  const live = useCurrentProject(SECTION_OPTIMISATION_ADDRESS);
  // The button of a project's panel narrows the screen to that object the way the top strip does: by the address, kept for next time.
  const [, chooseObject, rememberFailure] = useAddressProject(SECTION_OPTIMISATION_ADDRESS);
  const liveProject = live.projectUid as ProjectUid | null;
  const projectUid = routed
    ? liveProject
    : shownProject({ projectUid: initial.projectUid, decided: objectDecided(initial) }, liveProject);
  // «Все объекты» was chosen, in the address, and the address says it as `?project=all`; an address that says nothing says nothing.
  const allProjects = projectUid === null && (routed ? live.source === 'all' : initial.allProjects === true);

  // A document names nothing in another section or another object: it is forgotten when either changes. The object that arrives late
  // from the account (`pending` to the last object) is no change — nobody had chosen a document under another object.
  const scopeKey = live.pending ? null : `${sectionCode}|${projectUid ?? ''}`;
  const [seenScope, setSeenScope] = useState<string | null>(scopeKey);
  if (scopeKey !== null && seenScope !== scopeKey) {
    setSeenScope(scopeKey);
    if (seenScope !== null) setDocumentUid(null);
  }

  // The tabs' numbers. `row_count` counts every row in scope apart from the text search, and only a `ready` answer has
  // one worth showing: a section the server stopped at a bound (`section_too_large`) lists no rows.
  const specification = useSectionSpecification({ sectionCode, projectUid, documentUid, query: '', offset: 0 });
  const accepted = useAcceptedOptimisationProposals({ sectionCode, projectUid, documentUid });
  const counts: SectionOptimisationTabCounts = {
    specification:
      specification.data !== undefined && specification.data.section_code === sectionCode && specification.data.state === 'ready'
        ? specification.data.row_count
        : null,
    accepted: accepted.data?.total ?? null,
  };

  // The documents of the scope: the unnarrowed read, which is the tabs' own first read (one request) while no document is chosen, and a
  // read of its own once one is. The chosen document is always offered, named by the narrowed answer when the list lacks it.
  const scopeRead = useSectionSpecification({ sectionCode, projectUid, documentUid: null, query: '', offset: 0 });
  const documentOptions = withSelectedDocument(
    documentFilterOptions(scopeRead.data, sectionCode),
    documentUid,
    documentFilterOptions(specification.data, sectionCode),
  );

  function keep(next: {
    readonly tab: SectionOptimisationTab;
    readonly sectionCode: ProjectSection;
    readonly projectUid: ProjectUid | null;
    readonly allProjects: boolean;
    readonly documentUid: DocumentUid | null;
  }) {
    // A reload or a pasted link opens the same view: the address follows every choice, without a new history entry.
    rewriteAddress(sectionOptimisationSearch(next));
  }

  // The top strip rewrites the address in its own way (it drops the section and the tab, which mean something inside one object):
  // when the object moves under the page, the page writes back what it shows, so a reload opens the same view. The object that
  // arrives late from the account (`pending` to the last object) is no move: nobody has chosen anything yet.
  const objectKey = live.pending ? null : (projectUid ?? '');
  const seenObject = useRef<string | null>(objectKey);
  useEffect(() => {
    if (objectKey === null) return;
    if (seenObject.current !== null && seenObject.current !== objectKey) keep({ tab, sectionCode, projectUid, allProjects, documentUid });
    seenObject.current = objectKey;
    // Only a change of the object writes the address here; the rest is written by the choices themselves.
  }, [objectKey]);

  function chooseTab(next: SectionOptimisationTab) {
    setTab(next);
    keep({ tab: next, sectionCode, projectUid, allProjects, documentUid });
  }

  function chooseSection(next: ProjectSection) {
    setSectionCode(next);
    setDocumentUid(null);
    keep({ tab, sectionCode: next, projectUid, allProjects, documentUid: null });
  }

  function chooseDocument(next: DocumentUid | null) {
    setDocumentUid(next);
    keep({ tab, sectionCode, projectUid, allProjects, documentUid: next });
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

  // What the address carried that could not be read, by name: the route's own, and the document, which the page reads itself.
  const ignored = addressedDocument.ignored && !initial.ignored.includes('document') ? [...initial.ignored, 'document' as const] : initial.ignored;

  return (
    <section className="am-page" data-screen="section-optimisation">
      <SectionHeader sectionCode={sectionCode} projectUid={projectUid} onSection={chooseSection} />
      <div className="am-page__body">
        {ignored.length === 0 ? null : (
          <p className={styles.notice} data-address-ignored={ignored.join(' ')}>
            Из адреса не прочитано: {ignored.map((name) => IGNORED_TEXT[name]).join(', ')}. Экран открыт с выбором по умолчанию.
          </p>
        )}
        {rememberFailure === null ? null : (
          <p className="am-note" role="alert" data-remember-failure="">
            Объект выбран, но не запомнен: {rememberFailure.detail}
            {rememberFailure.correlationId === null ? null : ` Код обращения: ${rememberFailure.correlationId}`}
          </p>
        )}
        <div className={styles.tabs}>
          {/* `UI-B-24`: as the original's toolbar, the tabs on the left. The section is chosen in the header, the object in the top strip. */}
          <div className={styles.toolbar}>
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
            <DocumentFilter options={documentOptions} value={documentUid} onChange={chooseDocument} />
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
                sectionCode={sectionCode}
                projectUid={projectUid}
                documentUid={documentUid}
                onSelectProject={chooseObject}
              />
            ) : (
              <SectionAcceptedOptimisations sectionCode={sectionCode} projectUid={projectUid} documentUid={documentUid} />
            )}
          </div>
        </div>
      </div>
    </section>
  );
}
