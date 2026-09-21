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
import { useQuery } from '@tanstack/react-query';
import { useMemo, useState } from 'react';

import type { FindingObservationId, FindingUid, ProjectUid, RunId } from '@/shared/api';
import {
  getFinding,
  getRunStatus,
  listDecisionHistory,
  listRunFindings,
  queryKeys,
} from '@/shared/api';
import { ErrorState, LoadingState, PageShell, RunStateBadge } from '@/shared/ui';
import { routes } from '@/shared/lib';
import { DecisionHistory } from '@/widgets/decision-history';
import { DecisionPanel } from '@/widgets/decision-panel';
import { EvidenceViewer } from '@/widgets/evidence-viewer';
import { ExportPanel } from '@/widgets/export-panel';
import { FindingList } from '@/widgets/finding-list';
import { useAppendComment } from '@/features/append-comment';
import { useEvidenceDocument } from '@/features/open-evidence';
import { useExportRun } from '@/features/export-run';
import type { DecisionIntent } from '@/widgets/decision-panel';
import { useRecordVerdict } from '@/features/record-verdict';
import { admitFindings, groupByCategory } from '@/entities/finding';
import { firstDeclaredPage } from '@/entities/finding-observation';

import { presentFailureOrNull } from '../model/present-failure';
import type { ReviewSelection } from '../model/selection';
import { resolveSelection, selectFinding, selectPage } from '../model/selection';

export interface ReviewPageProps {
  readonly projectUid: ProjectUid;
  readonly runId: RunId;
}

export function ReviewPage({ projectUid, runId }: ReviewPageProps) {
  const [selection, setSelection] = useState<ReviewSelection | null>(null);

  const runQuery = useQuery({
    queryKey: queryKeys.runs.detail(runId),
    queryFn: ({ signal }) => getRunStatus({ path: { run_id: runId } }, { signal }),
  });

  const findingsQuery = useQuery({
    queryKey: queryKeys.runs.findings(runId),
    queryFn: ({ signal }) => listRunFindings({ path: { run_id: runId } }, { signal }),
  });

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

  const resolved = resolveSelection(selection, findingUids);
  const selectedUid = resolved === null ? null : (resolved.findingUid as FindingUid);

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
  const evidence = useEvidenceDocument(versionUid);

  // These three hooks cannot be called conditionally, so they are bound to the empty
  // identity when nothing is selected. Every control that could fire one of them is
  // rendered only inside the `detail !== null` branch below, so the empty identity is
  // never sent.
  const boundFindingUid = (selectedUid ?? '') as FindingUid;
  const verdict = useRecordVerdict({ findingUid: boundFindingUid, runId });
  const comment = useAppendComment({ findingUid: boundFindingUid, runId });
  const exporter = useExportRun({ runId });

  const run = runQuery.data?.data ?? null;

  const pendingIntent: DecisionIntent | null = verdict.isPending
    ? 'accept'
    : comment.isPending
      ? 'comment'
      : null;

  const activePage =
    resolved?.page ?? (detail === null ? null : firstDeclaredPage(detail.observation));

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
      <div className="am-review">
        <div className="am-review__list">
          <FindingList
            groups={groups}
            selectedFindingUid={selectedUid}
            onSelect={(findingUid) => {
              setSelection(selectFinding(findingUid));
            }}
            isLoading={findingsQuery.isPending}
            error={presentFailureOrNull(findingsQuery.error, {
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

        <div className="am-review__detail">
          {selectedUid === null ? null : detailQuery.isPending ? (
            <LoadingState what="the finding" />
          ) : detailQuery.error !== null ? (
            <ErrorState
              {...(presentFailureOrNull(detailQuery.error, {
                title: 'Не удалось загрузить находку',
                onRetry: () => {
                  void detailQuery.refetch();
                },
              }) ?? { title: 'Не удалось загрузить находку' })}
            />
          ) : detail === null ? null : (
            <>
              <article className="am-review__finding" data-finding-uid={detail.finding_uid}>
                <h2>{detail.observation.finding_text}</h2>
                <p className="am-review__recommendation">
                  {detail.observation.recommendation_text}
                </p>
              </article>

              <EvidenceViewer
                observation={detail.observation}
                activePage={activePage ?? 1}
                onPageChange={(page) => {
                  setSelection((current) => selectPage(current ?? resolved, page));
                }}
                documentUrl={evidence.objectUrl}
                isLoading={evidence.isLoading}
                error={presentFailureOrNull(evidence.error, {
                  title: 'Не удалось загрузить страницу документа',
                  onRetry: evidence.refetch,
                })}
              />

              <DecisionPanel
                currentVerdict={verdict.result?.current_verdict ?? detail.current_verdict}
                observationId={detail.observation.finding_observation_id as FindingObservationId}
                onAccept={(observationId) => {
                  verdict.record('accept', observationId);
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
              />

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
        </div>

        <div className="am-review__export">
          {run === null ? (
            <LoadingState what="прогон" />
          ) : (
            <ExportPanel
              runId={runId}
              runState={run.state}
              providerMode={run.provider_mode}
              onExport={exporter.download}
              isPending={exporter.isPending}
              lastFileName={exporter.lastFileName}
              error={presentFailureOrNull(exporter.error, {
                title: 'В выгрузке отказано',
              })}
            />
          )}
        </div>
      </div>
    </PageShell>
  );
}
