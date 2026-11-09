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
 * **The project comes from the address, here, and nowhere else** (`UI-PARITY-01`, «Project
 * context»; the screen's registry class is `optional`). `?project=` is read with
 * `readProjectContext` and sent as `project_uid`; it is one of the journal's filters, so it is in
 * the cache key, and — like a filter change — a project change returns to the first page. No
 * `?project=` is «Все проекты». The screen says which of the two it shows, and how many entries
 * match (`total` of the page, not the length of the page on screen).
 *
 * **The verdict chips** (`UI-B-32`) above the list -- «Принято», «Отклонено», «Не решено», «Все» -- set the same `verdict` the
 * select below them sets, and carry the server's count of that verdict (`useDecisionVerdictTotals`: `total` of
 * `listDecisions` read with `limit=1`, under the same project and category). The page counts nothing itself; a count the
 * server has not answered is drawn «—», not a zero.
 *
 * **«Память решений»** (`D-495`, `DECISION-MEMORY-01`) is the fourth «Тип»: the copy of what an expert saw and decided, kept after the
 * project and the document are gone. The expert and the administrator are offered it; the viewer sees nothing of it, neither the
 * button nor the tab through an address (`useMemoryAccess`: hidden, not disabled). It has its own filters and its open case in the
 * address (`model/memory-address.ts`), and the administrator's «Отозвать» / «Вернуть» and status line; the page only composes it.
 * Unlike the journal it is not a projection: the memory is a primary record from the moment of capture (`ADR-0027`).
 *
 * The two filters are the contract's own `category` and `verdict`, and they mean what the
 * contract says they mean: the **finding's** category, and the verdict that now stands for
 * it. Neither filters the event, so a comment left on a finding that was later accepted is
 * in the `принято` page — which is right: the comment is part of how that finding came to
 * be accepted.
 */

import { usePathname, useSearchParams } from 'next/navigation';

import type { ErrorStateProps } from '@/shared/ui';
import type { ProjectUid } from '@/shared/api';
import { ApiError, ApiFailure, catalogMessage } from '@/shared/api';
import { readProjectContext, switchProject, useAddressState } from '@/shared/lib';
import { LoadingState, PageShell } from '@/shared/ui';
import type { DecisionVerdictTotals } from '@/entities/expert-decision';
import {
  CATEGORY_LABELS, recordCountLabel, useDecisionJournal, useDecisionVerdictTotals, useKnowledgeBaseJournal,
  useProposalDecisionJournal,
} from '@/entities/expert-decision';
import { ProposalDecisions } from '@/widgets/proposal-journal';
import { DecisionMemoryFilters } from '@/widgets/decision-memory';
import { useMemoryAccess } from '@/entities/decision-memory';
import { useProjectList } from '@/entities/project';

import {
  CATEGORY_CHOICES, DEFAULT_KB_ADDRESS, VERDICT_CHOICES, readKbAddress, writeKbAddress,
} from '../model/address';
import type { CategoryChoice, KbAddress, KbKind, KbView, VerdictChoice } from '../model/address';
import { NO_CURSORS, useCursorWalk } from '../model/use-cursor-walk';
import { useMemoryTab } from '../model/use-memory-tab';
import { LazyKnowledgeBase } from './lazy-knowledge-base';
import { MemoryResults } from './memory-results';
import styles from './knowledge-base-page.module.css';

/** `UI-B-34`: the labels of how the decisions are drawn (the choice itself is in the address, `model/address.ts`). */
const VIEW_LABELS: Readonly<Record<KbView, string>> = { table: 'Таблица', events: 'События' };

const VERDICT_CHOICE_LABELS: Readonly<Record<VerdictChoice, string>> = {
  all: 'Любой вердикт',
  pending: 'Не решено',
  accepted: 'Принято',
  rejected: 'Отклонено',
  needs_manual_review: 'Нужен ручной разбор',
};

/**
 * `UI-B-32`: the verdict chips above the list, in the order of the original's cards -- decided for, decided against,
 * undecided, everything. A chip sets the same verdict the «Вердикт» select sets; its number is the server's count of
 * that verdict over the journal (`useDecisionVerdictTotals`), never the length of the page on screen.
 */
const VERDICT_CHIPS: readonly { readonly choice: VerdictChoice; readonly label: string; readonly total: keyof DecisionVerdictTotals }[] = [
  { choice: 'accepted', label: 'Принято', total: 'accepted' },
  { choice: 'rejected', label: 'Отклонено', total: 'rejected' },
  { choice: 'pending', label: 'Не решено', total: 'pending' },
  { choice: 'all', label: 'Все', total: 'all' },
];

const CATEGORY_CHOICE_LABELS: Readonly<Record<CategoryChoice, string>> = {
  all: 'Любая категория',
  ...CATEGORY_LABELS,
};

/** What a render without a mounted router (a one-pass test render) reads as the query string. */
const NO_PARAMS = new URLSearchParams();

/** This screen's registry address, the one `readProjectContext` classifies. */
const KNOWLEDGE_BASE_ADDRESS = '/knowledge-base';

/** The scope the screen states when no project is chosen. */
const ALL_PROJECTS = 'Все проекты';

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

const SUBTITLE =
  'Все решения проверяющего по находкам, новые сверху. Это проекция над журналом решений: ничего не хранится отдельно и всё пересчитывается из событий.';

/** `D-495`: the memory is not a projection. It is the record of what the expert saw and decided, kept apart from the project. */
const MEMORY_SUBTITLE =
  'Память решений: то, что эксперт видел и решил в момент решения. Хранится отдельно и остаётся после удаления проекта и документа; это история, а не действующий вердикт.';

export function KnowledgeBasePage() {
  // `null` only where no router is mounted; the address is then no address and names no project.
  const pathname = usePathname();
  const searchParams = useSearchParams() ?? NO_PARAMS;
  const { projectUid } = readProjectContext(pathname ?? '', searchParams);

  // The type, the view and the two filters are in the address (`?kind=&view=&category=&verdict=`, `D-372`), so a link, a reload and the
  // side menu's «База знаний» (no query) return to the same filter. A choice REPLACES the entry: a filter is not a place to go Back to.
  // `R-151h`: «Тип» -- the decisions on findings, or on optimisation proposals, as the original's knowledge base, or both as one
  // journal («Все», `D-317`). «Замечания» stays the first screen, as it was before «Все».
  const [address, setAddress] = useAddressState(readKbAddress, writeKbAddress);
  const { view, category, verdict } = address;
  // `D-495`: «Память решений» is for the expert and the administrator. An address that names it for an account known to hold
  // neither (the viewer) shows the first screen, and is not echoed back; while the account is not known the tab waits for it.
  const memoryAccess = useMemoryAccess();
  const kind: KbKind = address.kind === 'memory' && memoryAccess.known && !memoryAccess.read ? DEFAULT_KB_ADDRESS.kind : address.kind;
  const choose = (patch: Partial<KbAddress>) => setAddress({ ...address, kind, ...patch }, 'replace');
  /*
   * The cursors of the pages walked past (see `useCursorWalk`). A cursor belongs to the filters it was issued under, so each stack
   * carries them: the decisions on findings walk under the project, the category and the verdict; the other two under the project.
   */
  const [cursors, setCursors] = useCursorWalk(`${projectUid ?? ''}|${category}|${verdict}`);
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
  const journal = useDecisionJournal({
    ...(projectUid === null ? {} : { project_uid: projectUid }),
    ...(category === 'all' ? {} : { category }),
    ...(verdict === 'all' ? {} : { verdict }),
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
  const next = journal.data?.page.next_cursor ?? null;
  const total = journal.data?.total;
  const first = journal.data?.items[0];
  const recordedName = first !== undefined && first.project_uid === projectUid ? first.project_name : undefined;

  /*
   * `D-313`: an empty page under a category, a verdict or a project is about that selection, not
   * about the installation. The way out is the filters reset, and «Все проекты» built like the
   * dashboard builds it (`switchProject(…, null)`: every other parameter of the address stays).
   */
  const filtered = category !== 'all' || verdict !== 'all';
  const withoutProject = switchProject(searchParams, null).toString();
  const narrowing =
    !filtered && projectUid === null
      ? undefined
      : {
          ...(filtered
            ? {
                onResetFilters: () => choose({ category: 'all', verdict: 'all' }),
              }
            : {}),
          ...(projectUid === null
            ? {}
            : {
                allProjectsHref:
                  withoutProject === '' ? KNOWLEDGE_BASE_ADDRESS : `${KNOWLEDGE_BASE_ADDRESS}?${withoutProject}`,
              }),
        };

  return (
    <PageShell
      title="База знаний"
      surface="canvas"
      subtitle={kind === 'memory' ? MEMORY_SUBTITLE : SUBTITLE}
    >
      <div className={`am-kb__filters ${styles.filters}`} role="group" aria-label="Отбор решений">
        <div className="am-kb__filter" role="group" aria-label="Тип решений">
          <span>Тип</span>
          {(memoryAccess.read ? (['all', 'findings', 'proposals', 'memory'] as const) : (['all', 'findings', 'proposals'] as const)).map((value) => (
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
        {kind === 'proposals' || kind === 'memory' ? null : (
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
        {kind !== 'findings' ? null : <>
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
        <div className="am-kb__filter">
          <label htmlFor="kb-filter-verdict">Вердикт</label>
          <select
            id="kb-filter-verdict"
            value={verdict}
            onChange={(event) => choose({ verdict: event.target.value as VerdictChoice })}
          >
            {VERDICT_CHOICES.map((choice) => (
              <option key={choice} value={choice}>
                {VERDICT_CHOICE_LABELS[choice]}
              </option>
            ))}
          </select>
        </div>
        </>}
        {kind !== 'memory' || !memoryAccess.read || memory.caseId !== null ? null : (
          <DecisionMemoryFilters value={memory.filters} onChange={memory.setFilters} />
        )}
      </div>
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
              allProjectsHref: withoutProject === '' ? KNOWLEDGE_BASE_ADDRESS : `${KNOWLEDGE_BASE_ADDRESS}?${withoutProject}`,
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
        {/* `UI-B-32`: the original's verdict cards as chips with the server's counts; a chip sets the «Вердикт» filter. */}
        <div className={styles.chips} role="group" aria-label="Решения по вердикту" data-kb-verdict-chips="">
          {VERDICT_CHIPS.map(({ choice, label, total: figure }) => {
            const count = verdictTotals[figure];
            return (
              <button
                key={choice}
                type="button"
                className={verdict === choice ? 'am-button am-button--small' : 'am-button am-button--quiet am-button--small'}
                aria-pressed={verdict === choice}
                data-kb-verdict={choice}
                data-kb-verdict-total={count}
                // A cursor belongs to the filter it was issued under: a new verdict starts at the first page (`useCursorWalk`).
                onClick={() => choose({ verdict: choice })}
              >
                {label} <span className={styles.chipCount}>{count ?? '—'}</span>
              </button>
            );
          })}
        </div>
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
