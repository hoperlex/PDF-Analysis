'use client';

/**
 * `/knowledge-base` — what this installation has decided, and what it decided it about.
 *
 * `R-23` makes the knowledge base required and working inside the alpha, and `R-24` gave
 * it a contract operation rather than a client-side walk over every run. This screen is
 * the reason that ruling was taken: before `listDecisions` a page like this had to fetch
 * every run, then every run's findings, then every finding's history, and could only start
 * once it already knew the identities.
 *
 * Composition only: the shell from `shared/ui`, the query from the `expert-decision`
 * entity, the list from a widget (reached through the lazy wrapper beside this file,
 * `W50-LAZY-01`). No projection is computed here — `ADR-0012` puts the
 * knowledge-base view on the server, and a count assembled in this file would be a second
 * answer to a question the server already answers.
 *
 * The journal is paged (50 per page, newest first): «Далее» and «Назад» walk the server's
 * opaque cursors with a stack, and changing either filter returns to the first page.
 *
 * **The object comes from the address, and where it is silent, from the account** (`UI-PARITY-01`,
 * «Project context», `UIP-G-06`; the screen's registry class is `optional`). `useCurrentProject` reads
 * `?project=<uid>`, then the explicit `?project=all`, then the object the account chose last, and it is
 * sent as `project_uid`; it is one of the journal's filters, so it is in the cache key, and — like a
 * filter change — a change of object returns to the first page. No object is «Все объекты». The screen
 * says which of the two it shows, and how many entries match (`total` of the page, not the length of the
 * page on screen).
 *
 * **One top row** (`UIP-S12-03`, `Г9-B`, `Г12-B`): on the left the group «Эксперт» -- the cards «Отклонено», «Принято», «Все» and, only
 * while the journal holds such a decision, «Не решено» (`UI-B-32`: each card sets the `verdict` and carries the server's count of it,
 * `useDecisionVerdictTotals`: `total` of `listDecisions` read with `limit=1`, under the same project and category; the page counts
 * nothing itself, and a count the server has not answered is drawn «—», not a zero); on the right «Фильтры ▾» (the type, the view and
 * the category, in the browser's own disclosure) and «Память решений». The screen opens on «Отклонено», and «Все» is a chosen card
 * (`?verdict=all`, `model/address.ts`). There is no list of verdicts beside the cards: it said the same thing twice.
 *
 * **The second group, «Заказчик и проектировщик»** (`UIP-S12-04`, `Г12-B`) stands beside the first, and only while the journal holds a
 * designer's execution status at all (`R-151g`: the expert sets it by hand in «Разбор»; most journals hold none, and then the group
 * has nothing to say and is not drawn). «Приняли в работу» counts the statuses «Учтено» and «По согласованию», «Исправили замечание»
 * counts «Внесено»; the numbers are the server's, as the first group's (`useDecisionStatusTotals`, `limit=1`), and a card sets the
 * `execution_status` filter of the list (`?execution=`). The two groups are one choice: one card is pressed, never two, and the verdict
 * is not a filter while a card of this group is. «Отклонено» of the designer is in neither card (the owner has not ruled where it goes).
 *
 * **«Память решений»** (`D-495`, `DECISION-MEMORY-01`) is a button of its own beside «Фильтры ▾», not one of the types: the copy of what
 * an expert saw and decided, kept after the project and the document are gone. The expert and the administrator are offered it; the
 * viewer sees nothing of it, neither the button nor the tab through an address (`useMemoryAccess`: hidden, not disabled). It has its
 * own filters and its open case in the address (`model/memory-address.ts`), and the administrator's «Отозвать» / «Вернуть» and status
 * line; the page only composes it. Unlike the journal it is not a projection: the memory is a primary record from the moment of
 * capture (`ADR-0027`).
 *
 * The category and the verdict are the contract's own, and they mean what the contract says they mean: the **finding's** category, and
 * the verdict that now stands for it. Neither filters the event, so a comment left on a finding that was later accepted is in the
 * `принято` page — which is right: the comment is part of how that finding came to be accepted.
 */

import { useSearchParams } from 'next/navigation';

import type { ErrorStateProps } from '@/shared/ui';
import type { ProjectUid } from '@/shared/api';
import { ApiError, ApiFailure, catalogMessage } from '@/shared/api';
import { switchProject, useAddressState } from '@/shared/lib';
import { LoadingState, PageShell } from '@/shared/ui';
import type { DecisionVerdictTotals } from '@/entities/expert-decision';
import {
  CATEGORY_LABELS, recordCountLabel, useDecisionJournal, useDecisionStatusTotals, useDecisionVerdictTotals, useKnowledgeBaseJournal,
  useProposalDecisionJournal,
} from '@/entities/expert-decision';
import {
  ANY_EXECUTION_STATUS_QUERY, EXECUTION_GROUP_LABELS, EXECUTION_GROUP_STATUSES, executionStatusQuery,
} from '@/entities/finding';
import type { ExecutionGroup } from '@/entities/finding';
import { ProposalDecisions } from '@/widgets/proposal-journal';
import { DecisionMemoryFilters } from '@/widgets/decision-memory';
import { useMemoryAccess } from '@/entities/decision-memory';
import { useCurrentProject } from '@/entities/project';
import { useProjectList } from '@/entities/project';

import {
  CATEGORY_CHOICES, DEFAULT_KB_ADDRESS, readKbAddress, writeKbAddress,
} from '../model/address';
import type { CategoryChoice, KbAddress, KbKind, KbView, VerdictChoice } from '../model/address';
import { NO_CURSORS, useCursorWalk } from '../model/use-cursor-walk';
import { useMemoryTab } from '../model/use-memory-tab';
import { LazyKnowledgeBase } from './lazy-knowledge-base';
import { MemoryResults } from './memory-results';
import styles from './knowledge-base-page.module.css';

/** `UI-B-34`: the labels of how the decisions are drawn (the choice itself is in the address, `model/address.ts`). */
const VIEW_LABELS: Readonly<Record<KbView, string>> = { table: 'Таблица', events: 'События' };

/**
 * `UIP-S12-03`: the cards of the group «Эксперт», in the order of the original's -- decided against, decided for, undecided, everything.
 * A card sets the verdict the list is read under; its number is the server's count of that verdict over the journal
 * (`useDecisionVerdictTotals`), never the length of the page on screen, in the tone the verdict has everywhere (red, green, grey).
 */
const EXPERT_CARDS: readonly {
  readonly choice: VerdictChoice;
  readonly label: string;
  readonly total: keyof DecisionVerdictTotals;
  readonly tone: 'failed' | 'ok' | 'pending' | 'inert';
}[] = [
  { choice: 'rejected', label: 'Отклонено', total: 'rejected', tone: 'failed' },
  { choice: 'accepted', label: 'Принято', total: 'accepted', tone: 'ok' },
  { choice: 'pending', label: 'Не решено', total: 'pending', tone: 'pending' },
  { choice: 'all', label: 'Все', total: 'all', tone: 'inert' },
];

/**
 * `UIP-S12-04`: the cards of the group «Заказчик и проектировщик». A card sets the designer's statuses the list is read under; its number
 * is the server's count of those statuses over the journal (`useDecisionStatusTotals`). Both are the accent tone: the statuses are
 * not the expert's decision, so neither wears the green or the red of a verdict.
 */
const CUSTOMER_CARDS: readonly ExecutionGroup[] = ['working', 'fixed'];

/** The sets the numbers are read for, in this order: the two cards, then «any status at all» (the group is drawn above zero). */
const STATUS_SETS: readonly string[] = [
  executionStatusQuery(EXECUTION_GROUP_STATUSES.working),
  executionStatusQuery(EXECUTION_GROUP_STATUSES.fixed),
  ANY_EXECUTION_STATUS_QUERY,
];

const CATEGORY_CHOICE_LABELS: Readonly<Record<CategoryChoice, string>> = {
  all: 'Любая категория',
  ...CATEGORY_LABELS,
};

/** What a render without a mounted router (a one-pass test render) reads as the query string. */
const NO_PARAMS = new URLSearchParams();

/** This screen's registry address, the one the registry classifies. */
const KNOWLEDGE_BASE_ADDRESS = '/knowledge-base';

/** The scope the screen states when no project is chosen. */
const ALL_PROJECTS = 'Все объекты';

/**
 * The project's name, for the scope line. From the records the server just sent when there are
 * any (they carry `project_name`), otherwise from the project list — the page of it the screens
 * already read — and otherwise the uid the address carries, as it is. An unknown project is not
 * in either, and is never given a name it does not have.
 *
 * Its own component, so the project list is read only when an address names a project.
 */
function ProjectName({ projectUid, recordedName }: { projectUid: ProjectUid; recordedName: string | undefined }) {
  const projects = useProjectList();
  const listedName = projects.data?.items.find((project) => project.project_uid === projectUid)?.name;
  return <>{recordedName ?? listedName ?? projectUid}</>;
}

/**
 * The failure, presented once.
 *
 * `classifyListingFailure` is deliberately not used and not widened. Its subject carries a
 * `parent` — `project`, `document` or `version` — because `W18-SEAL` made an unknown parent
 * a `404` that must not render as "nothing here yet". **This listing has no parent**: its
 * path addresses no identity, the contract declares no `404` on it at all, and an empty
 * journal is an empty page. Adding a fourth parent to a closed type to describe a parent
 * that does not exist would make that type describe something untrue.
 *
 * So: the catalog's own sentence for the reported code, the correlation id, and a retry
 * only where the catalog says the code is retryable — `retryable` is read from the
 * envelope, never inferred from the status.
 */
function journalFailure(error: unknown, retry: () => void): ErrorStateProps {
  if (error instanceof ApiError) {
    return {
      title: 'База знаний не открылась.',
      detail: catalogMessage(error.errorCode),
      correlationId: error.correlationId,
      ...(error.retryable ? { onRetry: retry, retryLabel: 'Повторить' } : {}),
    };
  }
  if (error instanceof ApiFailure) {
    return {
      title: 'База знаний не открылась.',
      detail: 'Сервер не ответил. Проверьте соединение и повторите запрос.',
      correlationId: error.correlationId,
      onRetry: retry,
      retryLabel: 'Повторить',
    };
  }
  return { title: 'База знаний не открылась.', onRetry: retry, retryLabel: 'Повторить' };
}

/** «Тип»: both journals, the decisions on findings, the decisions on optimisation proposals. */
const KIND_LABELS: Readonly<Record<KbKind, string>> = {
  all: 'Все',
  findings: 'Замечания',
  proposals: 'Предложения',
  memory: 'Память решений',
};

/** `UIP-S12-03`: one plain line; what the journal is made of is not the reader's to know. */
const SUBTITLE = 'Решения эксперта по замечаниям, новые сверху.';

/** `D-495`: the memory is not a projection. It is the record of what the expert saw and decided, kept apart from the project. */
const MEMORY_SUBTITLE =
  'Память решений: то, что эксперт видел и решил в момент решения. Хранится отдельно и остаётся после удаления объекта и документа; это история, а не действующий вердикт.';

export function KnowledgeBasePage() {
  // `UIP-G-06`: the object comes from the address (`?project=<uid>`, or `?project=all`), and where it is silent, from the
  // account's last one. Outside the app router `KNOWLEDGE_BASE_ADDRESS` stands in for the screen's own address.
  const searchParams = useSearchParams() ?? NO_PARAMS;
  const { projectUid } = useCurrentProject(KNOWLEDGE_BASE_ADDRESS);

  // The type, the view and the two filters are in the address (`?kind=&view=&category=&verdict=`, `D-372`), so a link, a reload and the
  // side menu's «База знаний» (no query) return to the same filter. A choice REPLACES the entry: a filter is not a place to go Back to.
  // `R-151h`: «Тип» -- the decisions on findings, or on optimisation proposals, as the original's knowledge base, or both as one
  // journal («Все», `D-317`). «Замечания» stays the first screen, as it was before «Все».
  const [address, setAddress] = useAddressState(readKbAddress, writeKbAddress);
  const { view, category, verdict, execution } = address;
  // `D-495`: «Память решений» is for the expert and the administrator. An address that names it for an account known to hold
  // neither (the viewer) shows the first screen, and is not echoed back; while the account is not known the tab waits for it.
  const memoryAccess = useMemoryAccess();
  const kind: KbKind = address.kind === 'memory' && memoryAccess.known && !memoryAccess.read ? DEFAULT_KB_ADDRESS.kind : address.kind;
  const choose = (patch: Partial<KbAddress>) => setAddress({ ...address, kind, ...patch }, 'replace');
  /*
   * The cursors of the pages walked past (see `useCursorWalk`). A cursor belongs to the filters it was issued under, so each stack
   * carries them: the decisions on findings walk under the project, the category and the verdict; the other two under the project.
   */
  const [cursors, setCursors] = useCursorWalk(`${projectUid ?? ''}|${category}|${verdict}|${execution}`);
  const [proposalCursors, setProposalCursors] = useCursorWalk(projectUid ?? '');
  const [allCursors, setAllCursors] = useCursorWalk(projectUid ?? '');
  const cursor = cursors.at(-1);

  const proposals = useProposalDecisionJournal(
    {
      ...(projectUid === null ? {} : { project_uid: projectUid }),
      ...(proposalCursors.length === 0 ? {} : { cursor: proposalCursors.at(-1) }),
    },
    kind === 'proposals',
  );
  const everything = useKnowledgeBaseJournal(
    {
      ...(projectUid === null ? {} : { project_uid: projectUid }),
      ...(allCursors.length === 0 ? {} : { cursor: allCursors.at(-1) }),
    },
    kind === 'all',
  );
  // `UIP-S12-04`: a card of the second group asks for the designer's statuses and the verdict is not a filter then; one of the first
  // group asks for the verdict. Never both: they are one choice.
  const statusFilter = execution === 'any' ? undefined : executionStatusQuery(EXECUTION_GROUP_STATUSES[execution]);
  const journal = useDecisionJournal({
    ...(projectUid === null ? {} : { project_uid: projectUid }),
    ...(category === 'all' ? {} : { category }),
    ...(statusFilter !== undefined ? { execution_status: statusFilter } : verdict === 'all' ? {} : { verdict }),
    ...(cursor === undefined ? {} : { cursor }),
  }, kind !== 'memory');
  // `D-495`: the memory tab's address state and reads; nothing is requested unless the tab is on screen and the account may read it.
  const memory = useMemoryTab(projectUid, kind === 'memory', memoryAccess);
  // `UI-B-32`: the chips' numbers follow the project and the category, and are read only where the chips are drawn.
  const verdictTotals = useDecisionVerdictTotals(
    {
      ...(projectUid === null ? {} : { project_uid: projectUid }),
      ...(category === 'all' ? {} : { category }),
    },
    kind === 'findings',
  );
  // `UIP-S12-04`: the numbers of the second group's cards, under the same project and category, read where the group could be drawn.
  const [workingTotal, fixedTotal, anyStatusTotal] = useDecisionStatusTotals(
    {
      ...(projectUid === null ? {} : { project_uid: projectUid }),
      ...(category === 'all' ? {} : { category }),
    },
    STATUS_SETS,
    kind === 'findings',
  );
  const statusTotals: Readonly<Record<ExecutionGroup, number | undefined>> = { working: workingTotal, fixed: fixedTotal };
  const next = journal.data?.page.next_cursor ?? null;
  const total = journal.data?.total;
  const first = journal.data?.items[0];
  const recordedName = first !== undefined && first.project_uid === projectUid ? first.project_name : undefined;

  /*
   * `D-313`: an empty page under a category, a verdict or a project is about that selection, not
   * about the installation. The way out is the filters reset, and «Все объекты» built like the
   * dashboard builds it (`switchProject(…, null)`, `?project=all`: every other parameter of the address stays).
   */
  // `UIP-S12-03`: the screen opens on «Отклонено», so a narrowed list is the ordinary one; but a journal that holds no decision at all
  // (the server's count of «Все» under this project is zero) is not «narrowed»: there is nothing to widen to.
  const nothingDecided = category === 'all' && verdictTotals.all === 0;
  const filtered = (category !== 'all' || verdict !== 'all' || execution !== 'any') && !nothingDecided;
  const allProjects = switchProject(searchParams, null, projectUid).toString();
  const narrowing =
    !filtered && projectUid === null
      ? undefined
      : {
          ...(filtered
            ? {
                onResetFilters: () => choose({ category: 'all', verdict: 'all', execution: 'any' }),
              }
            : {}),
          ...(projectUid === null
            ? {}
            : {
                allProjectsHref: `${KNOWLEDGE_BASE_ADDRESS}?${allProjects}`,
              }),
        };

  // `UIP-S12-03`: how many of the filters inside «Фильтры ▾» are not at the first screen's value, said as a number on its handle so a
  // filtered list never looks like the whole of it. Only the filters the current type draws are counted.
  const showView = kind === 'findings' || kind === 'all';
  const activeFilters =
    (kind === 'all' || kind === 'proposals' ? 1 : 0) +
    (showView && view !== DEFAULT_KB_ADDRESS.view ? 1 : 0) +
    (kind === 'findings' && category !== 'all' ? 1 : 0);

  return (
    <PageShell
      title="База знаний"
      surface="canvas"
      subtitle={kind === 'memory' ? MEMORY_SUBTITLE : SUBTITLE}
    >
      <div className={styles.topRow} data-kb-top-row="">
        {kind !== 'findings' ? null : (
          <div className={styles.group} role="group" aria-label="Эксперт" data-kb-group="expert">
            <span className={styles.groupName}>Эксперт</span>
            <div className={styles.cards}>
              {EXPERT_CARDS.map(({ choice, label, total: figure, tone }) => {
                const count = verdictTotals[figure];
                const pressed = execution === 'any' && verdict === choice;
                // «Не решено» is drawn only while the journal holds such a decision (or while it is the card that is chosen).
                if (choice === 'pending' && !pressed && !(count !== undefined && count > 0)) return null;
                return (
                  <button
                    key={choice}
                    type="button"
                    className="am-button am-button--quiet"
                    aria-pressed={pressed}
                    data-kb-verdict={choice}
                    data-kb-verdict-total={count}
                    // A cursor belongs to the filter it was issued under: a new verdict starts at the first page (`useCursorWalk`).
                    onClick={() => choose({ verdict: choice, execution: 'any' })}
                  >
                    {label} <span className={`am-badge am-badge--${tone} ${styles.cardCount}`}>{count ?? '—'}</span>
                  </button>
                );
              })}
            </div>
          </div>
        )}
        {kind !== 'findings' || !(execution !== 'any' || (anyStatusTotal !== undefined && anyStatusTotal > 0)) ? null : (
          <div className={styles.group} role="group" aria-label="Заказчик и проектировщик" data-kb-group="customer">
            <span className={styles.groupName}>Заказчик и проектировщик</span>
            <div className={styles.cards}>
              {CUSTOMER_CARDS.map((choice) => {
                const count = statusTotals[choice];
                return (
                  <button
                    key={choice}
                    type="button"
                    className="am-button am-button--quiet"
                    aria-pressed={execution === choice}
                    data-kb-execution={choice}
                    data-kb-execution-total={count}
                    // A cursor belongs to the filter it was issued under: a new set of statuses starts at the first page.
                    onClick={() => choose({ execution: choice })}
                  >
                    {EXECUTION_GROUP_LABELS[choice]} <span className={`am-badge am-badge--active ${styles.cardCount}`}>{count ?? '—'}</span>
                  </button>
                );
              })}
            </div>
          </div>
        )}
        <div className={styles.actions}>
          <details className={styles.filterMenu} data-kb-filter-menu="">
            <summary className="am-button am-button--quiet am-button--small">
              Фильтры ▾
              {activeFilters === 0 ? null : <span className={styles.filterCount} data-kb-filter-count={activeFilters}>{activeFilters}</span>}
            </summary>
            <div className={`am-kb__filters ${styles.filters}`} role="group" aria-label="Отбор решений">
              <div className="am-kb__filter" role="group" aria-label="Тип решений">
                <span>Тип</span>
                {(['all', 'findings', 'proposals'] as const).map((value) => (
                  <button
                    key={value}
                    type="button"
                    className={kind === value ? 'am-button am-button--small' : 'am-button am-button--quiet am-button--small'}
                    aria-pressed={kind === value}
                    data-kb-kind={value}
                    onClick={() => { choose({ kind: value }); setProposalCursors(NO_CURSORS); setAllCursors(NO_CURSORS); }}
                  >
                    {KIND_LABELS[value]}
                  </button>
                ))}
              </div>
              {!showView ? null : (
                <div className="am-kb__filter" role="group" aria-label="Вид списка">
                  <span>Вид</span>
                  {(['table', 'events'] as const).map((value) => (
                    <button
                      key={value}
                      type="button"
                      className={view === value ? 'am-button am-button--small' : 'am-button am-button--quiet am-button--small'}
                      aria-pressed={view === value}
                      data-kb-view={value}
                      onClick={() => choose({ view: value })}
                    >
                      {VIEW_LABELS[value]}
                    </button>
                  ))}
                </div>
              )}
              {kind !== 'findings' ? null : (
                <div className="am-kb__filter">
                  <label htmlFor="kb-filter-category">Категория</label>
                  <select
                    id="kb-filter-category"
                    value={category}
                    onChange={(event) => choose({ category: event.target.value as CategoryChoice })}
                  >
                    {CATEGORY_CHOICES.map((choice) => (
                      <option key={choice} value={choice}>
                        {CATEGORY_CHOICE_LABELS[choice]}
                      </option>
                    ))}
                  </select>
                </div>
              )}
            </div>
          </details>
          {!memoryAccess.read ? null : (
            <button
              type="button"
              className="am-button am-button--quiet"
              aria-pressed={kind === 'memory'}
              data-kb-kind="memory"
              // The same button leaves the tab: it is a switch, and the first screen is where it returns to.
              onClick={() => { choose({ kind: kind === 'memory' ? DEFAULT_KB_ADDRESS.kind : 'memory' }); setProposalCursors(NO_CURSORS); setAllCursors(NO_CURSORS); }}
            >
              {KIND_LABELS.memory}
            </button>
          )}
        </div>
      </div>
      {kind !== 'memory' || !memoryAccess.read || memory.caseId !== null ? null : (
        <div className={`am-kb__filters ${styles.filters} ${styles.memoryFilters}`} role="group" aria-label="Отбор дел памяти">
          <DecisionMemoryFilters value={memory.filters} onChange={memory.setFilters} />
        </div>
      )}
      {kind === 'memory' ? (
        memoryAccess.read ? (
          <MemoryResults
            memory={memory}
            access={memoryAccess}
            narrowedByProject={projectUid !== null}
            scope={projectUid === null ? ALL_PROJECTS : <ProjectName projectUid={projectUid} recordedName={undefined} />}
          />
        ) : (
          <LoadingState what="память решений" />
        )
      ) : null}
      {kind === 'proposals' ? (
        <div className={styles.results}>
          {proposals.data === undefined ? null : (
            <p className={styles.scope} data-proposal-journal-total={proposals.data.total}>
              <span className={styles.count}>{recordCountLabel(proposals.data.total)}</span>
            </p>
          )}
          <ProposalDecisions
            records={proposals.data?.items ?? []}
            isLoading={proposals.isPending}
            error={proposals.error === null ? null : journalFailure(proposals.error, () => void proposals.refetch())}
          />
          {proposalCursors.length === 0 && (proposals.data?.page.next_cursor ?? null) === null ? null : (
            <nav className="am-pager" aria-label="Страницы решений по предложениям">
              <button
                type="button"
                className="am-button am-button--quiet"
                disabled={proposalCursors.length === 0}
                onClick={() => setProposalCursors(proposalCursors.slice(0, -1))}
              >
                Назад
              </button>
              <button
                type="button"
                className="am-button am-button--quiet"
                disabled={(proposals.data?.page.next_cursor ?? null) === null}
                onClick={() => {
                  const nextCursor = proposals.data?.page.next_cursor;
                  if (nextCursor !== null && nextCursor !== undefined) setProposalCursors([...proposalCursors, nextCursor]);
                }}
              >
                Далее
              </button>
            </nav>
          )}
        </div>
      ) : null}
      {kind === 'all' ? (
        <div className={styles.results}>
          {everything.data === undefined ? null : (
            <p className={styles.scope} data-knowledge-base-total={everything.data.total}>
              <span className={styles.count}>{recordCountLabel(everything.data.total)}</span>
            </p>
          )}
          <LazyKnowledgeBase
            view={view}
            records={[]}
            entries={everything.data?.items ?? []}
            isLoading={everything.isPending}
            // «Все» has no category or verdict: only the project narrows it, and «Все проекты» is the way out.
            narrowing={projectUid === null ? undefined : {
              allProjectsHref: `${KNOWLEDGE_BASE_ADDRESS}?${allProjects}`,
            }}
            error={everything.error === null ? null : journalFailure(everything.error, () => void everything.refetch())}
          />
          {allCursors.length === 0 && (everything.data?.page.next_cursor ?? null) === null ? null : (
            <nav className="am-pager" aria-label="Страницы всех решений">
              <button
                type="button"
                className="am-button am-button--quiet"
                disabled={allCursors.length === 0}
                onClick={() => setAllCursors(allCursors.slice(0, -1))}
              >
                Назад
              </button>
              <button
                type="button"
                className="am-button am-button--quiet"
                disabled={(everything.data?.page.next_cursor ?? null) === null}
                onClick={() => {
                  const nextCursor = everything.data?.page.next_cursor;
                  if (nextCursor !== null && nextCursor !== undefined) setAllCursors([...allCursors, nextCursor]);
                }}
              >
                Далее
              </button>
            </nav>
          )}
        </div>
      ) : null}
      {kind !== 'findings' ? null : <div className={styles.results}>
        <p className={styles.scope} data-journal-scope={projectUid === null ? 'all' : 'project'}>
          <span className={styles.scopeKey}>Охват</span>
          <strong className={styles.scopeValue}>
            {projectUid === null ? ALL_PROJECTS : <ProjectName projectUid={projectUid} recordedName={recordedName} />}
          </strong>
          {total === undefined ? null : (
            <span className={styles.count} data-journal-total={total}>
              {recordCountLabel(total)}
            </span>
          )}
        </p>
        <LazyKnowledgeBase
          view={view}
          records={journal.data?.items ?? []}
          isLoading={journal.isPending}
          narrowing={narrowing}
          error={
            journal.error === null
              ? null
              : journalFailure(journal.error, () => void journal.refetch())
          }
        />
        {cursors.length === 0 && next === null ? null : (
          <nav className="am-pager" aria-label="Страницы решений">
            <button
              type="button"
              className="am-button am-button--quiet"
              disabled={cursors.length === 0}
              onClick={() => setCursors(cursors.slice(0, -1))}
            >
              Назад
            </button>
            <button
              type="button"
              className="am-button am-button--quiet"
              disabled={next === null}
              onClick={() => {
                if (next !== null) setCursors([...cursors, next]);
              }}
            >
              Далее
            </button>
          </nav>
        )}
      </div>}
    </PageShell>
  );
}
