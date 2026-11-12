'use client';

/** @jsxRuntime automatic */

/**
 * `/projects/{project_uid}/runs/{run_id}/review` — the first-value screen.
 *
 * A domain expert opens a finding, sees the exact source quotation on its PDF page, and
 * decides. Everything else on this page exists to serve that sentence.
 *
 * This is the single mount point for the finding list, the evidence viewer, the decision
 * panel and history, and the export panel. It owns the queries, the selection and the
 * failure presentation; the widgets own none of those, which is why they stay pure.
 *
 * Two properties this page is responsible for keeping true:
 *
 * 1. **Ungrounded observations never appear.** The API does not return them — an item
 *    whose quotation did not resolve at its declared anchor has no `finding_uid` and is in
 *    no finding query (`P02_SEAMS.md` §5.1). This page runs `admitFindings` over the page
 *    anyway, so the UI has no path to render one even if a fixture, a future endpoint or a
 *    mistake produced one. The run's `diagnostic_observation_count` is reported in the
 *    header **as a diagnostic count**, which is the honest place for it: the reviewer
 *    learns those items exist without one of them ever appearing as a finding.
 *
 * 2. **`provider_mode` stays visible.** It is on the run badge in the header, on the export
 *    panel, and on the evidence viewer's own provenance line. A recorded run must never be
 *    presentable as a live one, and the reviewer should not have to scroll to find out
 *    which they are looking at.
 *
 * There is no polling here. `B7` owns run progress and the seam's single `pollRunStatus`
 * loop; this page reads run state once to decide whether export is offered.
 */

import Link from 'next/link';
import { usePathname, useSearchParams } from 'next/navigation';
import { useQuery } from '@tanstack/react-query';
import { useEffect, useMemo, useState } from 'react';
import type { ReactNode } from 'react';

import type { FindingObservationId, FindingUid, ProjectUid, RunId, VersionUid } from '@/shared/api';
import { getFinding, listDecisionHistory, queryKeys } from '@/shared/api';
import { ErrorState, LoadingState, PageShell, RunStateBadge } from '@/shared/ui';
import { routes } from '@/shared/lib';
import { DecisionHistory } from '@/widgets/decision-history';
import { DecisionPanel } from '@/widgets/decision-panel';
import { useMayActAsExpert } from '@/entities/account';
import { ExportPanel } from '@/widgets/export-panel';
import { blocksOfFinding, findingBlockIndex, sheetOfPage, useRunFindingBlocks, useSheetLabels } from '@/entities/block';
import { FindingList, FindingToolbar, filterBySeverity, filterGroups, findingViewOf, findingsAsShown, pagesLabel, severityFilterOf, verdictFilterOf } from '@/widgets/finding-list';
import type { FindingView, SeverityFilter, VerdictFilter } from '@/widgets/finding-list';
import { CandidateNormAdvice, CriticAdviceLine, ExtendedReviewSummary, ReviewCandidates } from '@/widgets/extended-review';
import { useAppendComment } from '@/features/append-comment';
import { useEvidenceDocument, useVersionBlockIndex } from '@/features/open-evidence';
import { useExportRun } from '@/features/export-run';
import type { DecisionIntent } from '@/widgets/decision-panel';
import { DocumentContext } from '@/widgets/document-context';
import { useRecordVerdict } from '@/features/record-verdict';
import { ExecutionStatusControl } from '@/features/set-execution-status';
import { runStatusQueryOptions } from '@/entities/audit-run';
import { SEVERITY_LABELS, admitFindings, blockEvidenceOf, groupByCategory, runFindingsQueryOptions, runHasNonTextFindings, standsOnBlocksOnly } from '@/entities/finding';
import { findingPages, firstFindingPage } from '@/entities/finding-observation';

import { presentFailureOrNull, presentFindingsFailure } from '../model/present-failure';
import { stripPageOf } from '../model/page-blocks';
import type { ReviewSelection } from '../model/selection';
import { resolveSelection, selectFinding, selectPage } from '../model/selection';

import { BlockEvidence } from './block-evidence';
import { LazyEvidenceViewer } from './lazy-evidence-viewer';
import { ReviewFindingBlocks } from './finding-blocks';
import { OpenedFinding } from './opened-finding';
import { ReviewPageBlocks } from './page-blocks';
import { ReviewRowActions } from './review-row-actions';
import { ReviewViewerAside, ReviewViewerDialog } from './review-viewer-dialog';
import styles from './review-page.module.css';

export interface ReviewPageProps {
  readonly projectUid: ProjectUid;
  readonly runId: RunId;
}

const NO_PARAMS = new URLSearchParams();

export function ReviewPage({ projectUid, runId }: ReviewPageProps) {
  // `R-150e`: recording a decision is an expert's act; the viewer reads the review without the panel.
  const mayAct = useMayActAsExpert();
  // `UI-PARITY-01` completion scenario 5: the chosen finding and the verdict filter live in the address
  // (`?finding=`, `?verdict=`), so a saved link opens the same finding under the same filter. Outside the
  // app router both hooks answer `null` and the page keeps its first finding and «Все».
  const pathname = usePathname() ?? routes.review(projectUid, runId);
  const searchParams = useSearchParams() ?? NO_PARAMS;
  const linkedFinding = searchParams.get('finding');
  const verdictFilter = verdictFilterOf(searchParams.get('verdict'));
  // `R-151j`: the severity filter lives in the address too (`?severity=`).
  const severityFilter = severityFilterOf(searchParams.get('severity'));
  // `UI-A-68`: the findings as the list beside the open finding, or as the original's full-width table (`?view=table`).
  const [selection, setSelectionState] = useState<ReviewSelection | null>(
    linkedFinding === null ? null : selectFinding(linkedFinding),
  );
  const writeAddress = (key: 'finding' | 'verdict' | 'severity' | 'view', value: string | null) => {
    const params = new URLSearchParams(searchParams.toString());
    if (value === null) params.delete(key);
    else params.set(key, value);
    const query = params.toString();
    // Next keeps `usePathname`/`useSearchParams` in step with the native history API, so the address is
    // written without the app router -- and the page renders where no router is mounted (a static render).
    // The data is `null`: Next's patch skips the sync for a state that carries its own marker, which is what
    // `window.history.state` is, and the filters, the view and the finding would then never follow the URL
    // (D-341; `tests/unit/review/review-address-sync.test.ts`).
    window.history.replaceState(null, '', query === '' ? pathname : `${pathname}?${query}`);
  };
  // Choosing a finding writes it to the address; turning a page inside the same finding does not.
  const setSelection = (next: ReviewSelection | null | ((current: ReviewSelection | null) => ReviewSelection | null)) => {
    if (typeof next !== 'function') {
      if (next === null) {
        if (selection !== null) writeAddress('finding', null);
      } else if (next.findingUid !== selection?.findingUid) {
        writeAddress('finding', next.findingUid);
      }
    }
    setSelectionState(next);
  };
  const setView = (next: FindingView) => {
    writeAddress('view', next === defaultView ? null : next);
  };
  const setVerdictFilter = (filter: VerdictFilter) => {
    writeAddress('verdict', filter === 'all' ? null : filter);
  };
  const setSeverityFilter = (filter: SeverityFilter) => {
    writeAddress('severity', filter === 'all' ? null : filter);
  };

  // `D-57`: this query used to build its own options, and its `queryFn` filed the
  // transport envelope under a key the run screen fills with the model. One shape per
  // key is now decided in one place -- `runStatusQueryOptions` -- and this screen reads
  // whatever that place writes.
  const runQuery = useQuery(runStatusQueryOptions(runId));
  const defaultView = runQuery.data?.publication_mode === 'one_list' ? 'table' : 'list';
  const view = findingViewOf(searchParams.get('view') ?? defaultView);

  // The COMPLETE list: every page of the run's findings, or the error of the page that
  // failed. The query resolves only once the last page has arrived, so the list below is
  // never a first page presented as the whole run (`entities/finding`).
  const findingsQuery = useQuery(runFindingsQueryOptions(runId));

  // The admission gate runs before anything is grouped or rendered. Whatever the page
  // contained, only findings reach the widgets.
  const admitted = useMemo(
    () => admitFindings(findingsQuery.data?.data.items ?? []),
    [findingsQuery.data],
  );
  const groups = useMemo(() => groupByCategory(admitted.findings), [admitted.findings]);
  const findingUids = useMemo(
    () => admitted.findings.map((finding) => finding.finding_uid),
    [admitted.findings],
  );

  // «Во весь экран»: ‹ › walk the findings in the order the list shows them under its filters (`UI-A-71`: pending,
  // then accepted, then rejected; by category in the list, flat in the table).
  const [expanded, setExpanded] = useState(false);
  const shownFindings = useMemo(
    () => findingsAsShown(filterBySeverity(filterGroups(groups, verdictFilter), severityFilter), view),
    [groups, verdictFilter, severityFilter, view],
  );

  // The list opens, until one is chosen, the first finding it SHOWS: the first still waiting for a decision (`D-401`).
  // The table opens a row only when it is asked to, as the original's does, so it neither draws a page under its first
  // row nor reads a finding nobody opened.
  const resolved = view === 'table'
    ? (selection !== null && findingUids.includes(selection.findingUid) ? selection : null)
    : resolveSelection(selection, findingUids, shownFindings[0]?.finding_uid ?? null);
  const selectedUid = resolved === null ? null : (resolved.findingUid as FindingUid);
  // ...and keeps it open. A decision re-sorts the list, so a default that went on following the order would move to the
  // next finding the moment the reader decided the one it opened. The default is therefore made the selection as soon as
  // it is resolved, and written to the address as a chosen finding is, so a reload and a saved link keep it too.
  const defaultedUid = resolved !== null && resolved.findingUid !== selection?.findingUid ? resolved.findingUid : null;
  useEffect(() => {
    if (defaultedUid !== null) setSelection(selectFinding(defaultedUid));
  }, [defaultedUid]);
  const shownAt = selectedUid === null ? -1 : shownFindings.findIndex((finding) => finding.finding_uid === selectedUid);
  const stepTo = (at: number) => {
    const target = shownFindings[at];
    return target === undefined ? undefined : () => {
      setSelection(selectFinding(target.finding_uid));
    };
  };
  const selectedSummary = shownAt < 0 ? null : (shownFindings[shownAt] ?? null);

  const detailQuery = useQuery({
    queryKey: queryKeys.findings.detail(selectedUid ?? ''),
    queryFn: ({ signal }) => getFinding({ path: { finding_uid: selectedUid as FindingUid } }, { signal }),
    enabled: selectedUid !== null,
  });

  const historyQuery = useQuery({
    queryKey: queryKeys.findings.decisions(selectedUid ?? ''),
    queryFn: ({ signal }) =>
      listDecisionHistory({ path: { finding_uid: selectedUid as FindingUid } }, { signal }),
    enabled: selectedUid !== null,
  });

  const detail = detailQuery.data?.data ?? null;
  const versionUid = detail?.version_uid ?? null;
  // `UI-PARITY-P0O`: the sheet of each page, so a row says «Лист 3 · стр. 5» as the original's does.
  const sheetLabels = useSheetLabels(runQuery.data?.version_uid ?? versionUid);
  const evidence = useEvidenceDocument(versionUid);
  // The line geometry the viewer frames quotations with. Read here because this page owns the
  // queries; without it (not produced, failed, in flight) the viewer searches the page text.
  const blockIndex = useVersionBlockIndex(versionUid);
  // `UI-A-74`: the table's count of the blocks that hold each finding's evidence, from the run's block links (one read
  // per run, shared with the open finding's «Блоки замечания»). Not produced, not read yet or failed: no count.
  const runFindingBlocks = useRunFindingBlocks(runId);
  const blockLinks = useMemo(() => findingBlockIndex(runFindingBlocks.data), [runFindingBlocks.data]);

  // These three hooks cannot be called conditionally, so they are bound to the empty
  // identity when nothing is selected. Every control that could fire one of them is
  // rendered only inside the `detail !== null` branch below, so the empty identity is
  // never sent.
  const boundFindingUid = (selectedUid ?? '') as FindingUid;
  const verdict = useRecordVerdict({ findingUid: boundFindingUid, runId });
  const comment = useAppendComment({ findingUid: boundFindingUid, runId });
  const exporter = useExportRun({ runId });

  const run = runQuery.data ?? null;

  // The wording follows the request in flight: the verdict feature reads the intent off the
  // pending request, so a pending reject says «Отклоняю…» and not «Принимаю…».
  const pendingIntent: DecisionIntent | null =
    verdict.pendingIntent ?? (comment.isPending ? 'comment' : null);

  const activePage =
    resolved?.page ?? (detail === null ? null : firstFindingPage(detail));

  // One failure for the open finding, inline and in the full-screen view.
  const detailFailure = detailQuery.error === null ? null : (
    <ErrorState
      {...(presentFailureOrNull(detailQuery.error, {
        title: 'Не удалось загрузить находку',
        onRetry: () => {
          void detailQuery.refetch();
        },
      }) ?? { title: 'Не удалось загрузить находку' })}
    />
  );

  // `F8-WEB`, `D-683`: a finding that stands on portal blocks alone has no quotation to show; its card is the page with a frame at
  // each block (`BlockEvidence`), drawn from `block_evidence`. A text finding keeps the quotation viewer exactly as it was.
  const onBlocks = detail !== null && standsOnBlocksOnly(detail);
  // `F8-WEB`: what the critic of the extended review advised about the candidate a block finding came from, in one line.
  const criticAdvice = detail !== null && (onBlocks || detail.observation.extended_observation_ref !== undefined) ? (
    <><CriticAdviceLine
      runId={runId}
      subject={{ findingText: detail.observation.finding_text, blockIds: blockEvidenceOf(detail).map((block) => block.portal_block_id), observationRef: detail.observation.extended_observation_ref }}
    /><CandidateNormAdvice runId={runId} subject={{ findingText: detail.observation.finding_text,
      blockIds: blockEvidenceOf(detail).map((block) => block.portal_block_id), observationRef: detail.observation.extended_observation_ref }} /></>
  ) : null;
  // The same viewer inline and in the full-screen view; only the presentation differs.
  const evidenceProps = detail === null ? null : {
    observation: detail.observation,
    mergedObservations: detail.merged_observations,
    activePage: activePage ?? 1,
    onPageChange: (page: number) => {
      setSelection((current) => selectPage(current ?? resolved, page));
    },
    documentUrl: evidence.objectUrl,
    blockIndex,
    isLoading: evidence.isLoading,
    error: presentFailureOrNull(evidence.error, {
      title: 'Не удалось загрузить страницу документа',
      onRetry: evidence.refetch,
    }),
  };
  // `UI-A-74`: the strip of the page the viewer is on, which is one of the pages the finding cites. The key is
  // the finding and the page, so a block view left open does not outlive either.
  const citedPages = detail === null ? [] : findingPages(detail);
  const stripPage = stripPageOf(citedPages, activePage);
  const pageBlocks = detail === null || stripPage === null ? null : (
    <ReviewPageBlocks
      key={`${detail.finding_uid}:${stripPage}`}
      projectUid={projectUid}
      versionUid={detail.version_uid as VersionUid}
      page={stripPage}
    />
  );
  // `UI-PARITY-C6`: above it, the portal blocks that hold the finding's own evidence, when the server named any.
  const findingBlocks = detail === null ? null : (
    <ReviewFindingBlocks
      key={detail.finding_uid}
      projectUid={projectUid}
      versionUid={detail.version_uid as VersionUid}
      runId={runId}
      findingUid={detail.finding_uid}
    />
  );
  // The block card inline and in the full-screen view, over the same page state as the quotation viewer.
  const blockView = (extra: { readonly presentation?: 'full'; readonly aside?: ReactNode; readonly onExpand?: () => void }) =>
    detail === null || evidenceProps === null ? null : (
      <BlockEvidence
        scope={detail.finding_uid}
        blocks={blockEvidenceOf(detail)}
        activePage={evidenceProps.activePage}
        onPageChange={evidenceProps.onPageChange}
        documentUrl={evidenceProps.documentUrl}
        isLoading={evidenceProps.isLoading}
        error={evidenceProps.error}
        providerMode={detail.observation.provenance.provider_mode}
        unlinkedPages={blockLinks === null ? undefined : blockLinks.unlinkedPages}
        {...extra}
      />
    );
  const blocksUnderThePage = (
    <>
      {findingBlocks}
      {pageBlocks}
    </>
  );
  const decidedOrProposed = detail === null ? null
    : detail.decided_severity !== undefined ? SEVERITY_LABELS[detail.decided_severity]
    : detail.observation.proposed_severity !== undefined
      ? `${SEVERITY_LABELS[detail.observation.proposed_severity]} — предложено моделью`
      : null;

  // The open finding, once: beside the list, or under its row of the table.
  const detailContent = (
    <>
      {selectedUid === null ? null : detailQuery.isPending ? (
        <LoadingState what="выбранная находка" />
      ) : detailFailure !== null ? (
        detailFailure
      ) : detail === null ? null : (
        <>
          {/* The table's row already says the finding and its recommendation whole; only the list needs them again here. */}
          {view === 'table' ? null : (
            <article className={`am-review__finding ${styles.finding}`} data-finding-uid={detail.finding_uid}>
              <h2 className={styles.findingTitle}>{detail.observation.finding_text}</h2>
              <p className={`am-review__recommendation ${styles.recommendation}`}>
                {detail.observation.recommendation_text}
              </p>
            </article>
          )}

          {/* `F8-WEB`: what the critic of the extended review advised about the candidate a block finding came from, in one line;
              in the table too, whose row already says the finding and its recommendation. */}
          {criticAdvice}

          {expanded ? (
            // One page drawn once: while the full-screen view is open it is the only viewer.
            <p className="am-note" data-evidence-expanded="">
              Страница открыта во весь экран.
            </p>
          ) : evidenceProps === null ? null : onBlocks ? (
            blockView({ onExpand: () => { setExpanded(true); } })
          ) : (
            <LazyEvidenceViewer {...evidenceProps} onExpand={() => { setExpanded(true); }} />
          )}

          {expanded ? null : blocksUnderThePage}

          {mayAct ? <DecisionPanel
            currentVerdict={verdict.result?.current_verdict ?? detail.current_verdict}
            // D-343 (lane C4): the carried origin of the verdict the finding holds; a verdict the expert has just given
            // here is direct, so the mark goes with it.
            carriedFrom={verdict.result === null || verdict.result === undefined ? detail.current_verdict_carried_from : undefined}
            observationId={detail.observation.finding_observation_id as FindingObservationId}
            proposedSeverity={detail.observation.proposed_severity}
            decidedSeverity={detail.decided_severity}
            severityRefusal={verdict.refusal}
            onSeverityChosen={verdict.clearRefusal}
            onAccept={(observationId, decided) => {
              verdict.record('accept', observationId, {
                proposed: detail.observation.proposed_severity,
                decided,
              });
            }}
            onReject={(observationId) => {
              verdict.record('reject', observationId);
            }}
            onComment={(text, observationId) => {
              comment.append(text, observationId);
            }}
            pendingIntent={pendingIntent}
            refusal={comment.refusal}
            error={
              presentFailureOrNull(verdict.error, {
                title: 'Вердикт не записан',
              }) ??
              presentFailureOrNull(comment.error, {
                title: 'Комментарий не добавлен',
              })
            }
          /> : <p className="am-note" data-expert-only="DecisionPanel">Решения по находкам записывает эксперт.</p>}
          {/* `R-151g`: what the designer did with an accepted finding, as the original's SU-10 badge. */}
          {mayAct && (verdict.result?.current_verdict ?? detail.current_verdict) === 'accepted' ? (
            <ExecutionStatusControl
              key={detail.finding_uid}
              findingUid={detail.finding_uid as FindingUid}
              runId={runId}
              status={detail.execution_status ?? null}
            />
          ) : null}

          <DecisionHistory
            events={historyQuery.data?.data.items ?? []}
            isLoading={historyQuery.isPending}
            error={presentFailureOrNull(historyQuery.error, {
              title: 'Не удалось загрузить историю решений',
              onRetry: () => {
                void historyQuery.refetch();
              },
            })}
          />
        </>
      )}
    </>
  );

  // The finding at the head of the full-screen view's side column, over the quotation viewer's or the block card's cards.
  const viewerAside = detail === null ? null : (
    <ReviewViewerAside
      findingUid={detail.finding_uid}
      meta={[decidedOrProposed, pagesLabel(findingPages(detail), (page) => sheetOfPage(sheetLabels.data, page))]
        .filter((part) => part !== null && part !== '')
        .join(' · ')}
      text={detail.observation.finding_text}
      recommendation={detail.observation.recommendation_text}
      advice={criticAdvice}
      actions={mayAct && selectedSummary !== null ? (
        <ReviewRowActions
          finding={selectedSummary}
          runId={runId}
          onOpen={(findingUid) => {
            // The severity is chosen in the panel: close the view on it.
            setExpanded(false);
            setSelection(selectFinding(findingUid));
          }}
        />
      ) : null}
      blocks={blocksUnderThePage}
    />
  );

  const exportPanel = run === null ? (
    <LoadingState what="прогон" />
  ) : (
    <ExportPanel
      layout="bar"
      runId={runId}
      runState={run.state}
      providerMode={run.provider_mode}
      onExport={exporter.download}
      isPending={exporter.isPending}
      lastFileName={exporter.lastFileName}
      mayImportDecisions={mayAct}
      // `UI-A-76`: the run's ZIP, for the session that may export, of the version this run read.
      auditPackage={mayAct ? { versionUid: run.version_uid } : undefined}
      error={presentFailureOrNull(exporter.error, {
        title: 'В выгрузке отказано',
      })}
    />
  );

  return (
    <PageShell
      title="Разбор"
      subtitle={
        run === null ? (
          'Загрузка прогона…'
        ) : (
          <>
            <span className="am-uid-row">
              <RunStateBadge state={run.state} providerMode={run.provider_mode} />{' '}
              <span className="am-uid" data-project-uid={projectUid}>
                {projectUid}
              </span>{' '}
              <span className="am-uid" data-run-id={runId}>
                {runId}
              </span>
            </span>
            {run.diagnostic_observation_count !== undefined &&
            run.diagnostic_observation_count > 0 ? (
              <span
                className="am-review__diagnostics"
                data-diagnostic-observation-count={run.diagnostic_observation_count}
              >
                шлюз привязки отклонил непривязанных элементов модели:{' '}
                {run.diagnostic_observation_count}. Это диагностика, а не находки: их нет ни
                в списке ниже, ни в строках CSV.
              </span>
            ) : null}
          </>
        )
      }
      actions={
        <>
          <Link href={routes.run(projectUid, runId)}>К прогону</Link>{' '}
          <Link href={routes.project(projectUid)}>К проекту</Link>{' '}
          <Link href={routes.projects()}>Все проекты</Link>
        </>
      }
    >
      <DocumentContext projectUid={projectUid} runId={runId} current="review" />
      {/* `F8-WEB`: the caption that the candidates are separate machine observations is not true of a run that published them as findings. */}
      <ExtendedReviewSummary projectUid={projectUid} runId={runId} oneList={run?.publication_mode === 'one_list' || runHasNonTextFindings(admitted.findings)} published={admitted.findings} />
      {/*
        The filters, the tally and the file actions across the whole width over the list and the open finding, as the
        original's top row: the total and the severity chips at the left, the file actions at the right. A run with no
        findings has no toolbar, and its file actions stand on their own.
      */}
      {admitted.findings.length === 0 ? <div className={styles.exportAlone}>{exportPanel}</div> : null}
      <FindingToolbar
        groups={groups}
        verdictFilter={verdictFilter}
        onVerdictFilterChange={setVerdictFilter}
        severityFilter={severityFilter}
        onSeverityFilterChange={setSeverityFilter}
        view={view}
        onViewChange={setView}
        actions={admitted.findings.length === 0 ? undefined : exportPanel}
      />
      <div className={view === 'table' ? `am-review ${styles.layout} ${styles.layoutTable}` : `am-review ${styles.layout}`}>
        <div className={view === 'table' ? `am-review__list ${styles.list} ${styles.listTable}` : `am-review__list ${styles.list}`}>
          <FindingList
            groups={groups}
            verdictFilter={verdictFilter}
            onVerdictFilterChange={setVerdictFilter}
            severityFilter={severityFilter}
            onSeverityFilterChange={setSeverityFilter}
            view={view}
            onViewChange={setView}
            toolbar="outside"
            blockCountOf={blockLinks === null ? undefined : (findingUid) => blocksOfFinding(blockLinks, findingUid).length}
            unlinkedPages={blockLinks === null ? undefined : blockLinks.unlinkedPages}
            selectedFindingUid={selectedUid}
            onSelect={(findingUid) => {
              // A second press on the open row of the table closes it, as the original's strip does.
              setSelection(view === 'table' && findingUid === selectedUid ? null : selectFinding(findingUid));
            }}
            renderExpansion={() => <OpenedFinding>{detailContent}</OpenedFinding>}
            sheetOf={(page) => sheetOfPage(sheetLabels.data, page)}
            // `R-151n`: ✓/✕ in each row, for a session that may decide.
            renderRowActions={mayAct ? (finding) => (
              <ReviewRowActions
                finding={finding}
                runId={runId}
                onOpen={(findingUid) => {
                  setSelection(selectFinding(findingUid));
                }}
              />
            ) : undefined}
            isLoading={findingsQuery.isPending}
            emptyDetail={run?.state === 'partial' ? <p>Прогон завершился частично. Отсутствие опубликованных находок не подтверждает отсутствие замечаний.
              {' '}<Link href={routes.run(projectUid, runId)}>Проверить этапы и ограничения прогона</Link>.</p> : undefined}
            error={presentFindingsFailure(findingsQuery.error, {
              title: 'Не удалось загрузить находки',
              onRetry: () => {
                void findingsQuery.refetch();
              },
            })}
            integrityFaults={admitted.integrityFaults.map((fault) => ({
              findingUid: fault.findingUid,
              refusal: fault.refusal,
            }))}
          />
        </div>

        {view === 'table' ? null : <div className={`am-review__detail ${styles.detail}`}>{detailContent}</div>}
      </div>

      <ReviewCandidates projectUid={projectUid} runId={runId} published={admitted.findings} sheetOf={(page) => sheetOfPage(sheetLabels.data, page)} />

      {expanded ? (
        <ReviewViewerDialog
          position={shownAt < 0 ? null : shownAt + 1}
          total={shownFindings.length}
          onPrevious={shownAt < 0 ? stepTo(0) : stepTo(shownAt - 1)}
          onNext={shownAt < 0 ? stepTo(0) : stepTo(shownAt + 1)}
          onClose={() => { setExpanded(false); }}
          title={detail?.observation.finding_text ?? 'Находка'}
        >
          {selectedUid === null ? (
            <p className="am-note">Выберите находку в списке.</p>
          ) : detailQuery.isPending ? (
            <LoadingState what="выбранная находка" />
          ) : evidenceProps === null || detail === null ? (
            detailFailure
          ) : onBlocks ? (
            blockView({ presentation: 'full', aside: viewerAside })
          ) : (
            <LazyEvidenceViewer {...evidenceProps} presentation="full" aside={viewerAside} />
          )}
        </ReviewViewerDialog>
      ) : null}

    </PageShell>
  );
}
