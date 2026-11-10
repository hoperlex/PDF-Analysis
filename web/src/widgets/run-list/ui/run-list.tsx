'use client';

/**
 * The runs of one published version, read from the server on mount.
 *
 * `D-16`'s last step: a version published yesterday, opened in a fresh tab today, shows
 * the runs made against it and a route into each one's findings. Before this, a run was
 * reachable only from the screen that started it.
 *
 * **It does not poll and it does not wait for `running`.** `D-20`: `execute_run` is
 * inline, so a run is already `published` when `startRun` answers, and a screen that
 * waited for a `running` reading would wait forever. The one polling loop in this
 * application is `useRunStatus`, on the run screen, and there is not a second cadence here.
 *
 * The empty state carries the Start-run control as its action, because a version with no
 * run is exactly the state from which a user needs one.
 *
 * АР has an ordinary text profile sourced from the original application, and that is the default start. AR v3
 * (beta) is an **opt-in** analysis (`AR-V3-OPT-IN`): the start form of an АР version offers the choice of it
 * (`./analysis-start.tsx`) only where the server says a start is allowed (`ArV3BetaPackStatus.start_allowed`), and the
 * standard analysis is selected every time. Where it is not allowed the form is the ordinary start and nothing else, and
 * the version of any other section never asks. Each row says which analysis produced the run: a v3 run always
 * («АР v3 (бета) · F1»), a standard run only where both are on offer («Стандартный»).
 *
 * A `comparison_pdf` has no portal companion. Ordinary section analysis now reads its native
 * PDF text and pages; portal-specific operations remain separate.
 */

import { useState } from 'react';

import type {
  ProjectSection,
  ProjectUid,
  RunStatus,
  VersionUid,
  VersionUploadKind,
} from '@/shared/api';
import { EmptyState, ErrorState, LoadingState } from '@/shared/ui';
import { classifyListingFailure, routes } from '@/shared/lib';
import type { RunTableProps } from '@/entities/audit-run';
import { RunTable, arV3GroupReviewAddress, looksLikeArV3GroupId, useArV3StartAllowed, useRunList } from '@/entities/audit-run';

import { AnalysisStart } from './analysis-start';
import { StartRunWithReadiness } from './start-run-with-readiness';

export interface RunListProps {
  readonly projectUid: ProjectUid;
  readonly versionUid: VersionUid;
  /**
   * The section the version's classification confirms, once the page has read it.
   * `'AR'` now takes the ordinary start and its original-source text profile.
   */
  readonly sectionCode?: ProjectSection | null | undefined;
  /**
   * How the version reached the product, once the page has read it. A comparison PDF uses
   * native-only analysis, so the start explains that portal annotations are absent.
   */
  readonly uploadKind?: VersionUploadKind | undefined;
  /** Called with the 202 reading so the screen can move to run progress. */
  readonly onRunStarted?: ((run: RunStatus) => void) | undefined;
}

/**
 * The table of an АР version, which names a standard run too where the deployment allows a start of v3
 * (`AR-V3-OPT-IN`). A separate component so that only an АР version mounts the status read; every other table is the
 * entity's own, and a v3 run is named in it all the same.
 */
function AnalysedRunTable(props: RunTableProps) {
  return <RunTable {...props} bothAnalyses={useArV3StartAllowed()} />;
}

export function RunList(props: RunListProps) {
  return <VersionRunList key={props.versionUid} {...props} />;
}

function VersionRunList({
  projectUid,
  versionUid,
  sectionCode,
  uploadKind,
  onRunStarted,
}: RunListProps) {
  const [cursor, setCursor] = useState<string | undefined>(undefined);
  const query = useRunList(versionUid, cursor);
  const comparisonOnly = uploadKind === 'comparison_pdf';
  const isAr = sectionCode === 'AR';
  // `AR-V3-OPT-IN`: asked of the server for an АР version that can take a start, and of nobody else.
  const choosesAnalysis = isAr && !comparisonOnly;
  const startControl = (
    <>
      {comparisonOnly ? <p className="am-note">Анализ будет выполнен по исходному PDF без разметки портала.</p> : null}
      {choosesAnalysis ? (
        <AnalysisStart
          projectUid={projectUid}
          versionUid={versionUid}
          {...(onRunStarted === undefined ? {} : { onRunStarted })}
        />
      ) : (
        <StartRunWithReadiness
          projectUid={projectUid}
          versionUid={versionUid}
          {...(onRunStarted === undefined ? {} : { onStarted: onRunStarted })}
        />
      )}
    </>
  );

  if (query.isPending) {
    return <LoadingState what="прогоны этой версии" />;
  }

  if (query.isError) {
    const failure = classifyListingFailure(query.error, {
      collection: 'прогоны этой версии',
      parent: 'version',
    });
    return <ErrorState
      title={failure.title}
      detail={<span data-list-failure={failure.kind}>{failure.detail}</span>}
      correlationId={failure.correlationId}
      {...(failure.retryable
        ? { onRetry: () => void query.refetch(), retryLabel: 'Повторить' }
        : {})}
    />;
  }

  const page = query.data;

  if (page.items.length === 0) {
    return (
      <EmptyState
        title="По этой версии прогонов не запускалось."
        detail="Версия опубликована и неизменяема. Запуск прогона читает её и никогда не меняет."
        action={startControl}
      />
    );
  }

  const nextCursor = page.page.next_cursor;
  const tableProps: RunTableProps = {
    runs: page.items,
    runHref: (run) => routes.run(projectUid, run.run_id),
    reviewHref: (run) => routes.review(projectUid, run.run_id),
    groupReviewHref: (run) => (looksLikeArV3GroupId(run.ar_v3_group_id) ? arV3GroupReviewAddress(run.ar_v3_group_id) : null),
  };

  return (
    <div data-run-count={page.items.length}>
      {choosesAnalysis ? <AnalysedRunTable {...tableProps} /> : <RunTable {...tableProps} />}
      <div className="am-pager">
        {cursor === undefined ? null : (
          <button type="button" className="am-button am-button--quiet am-button--small" onClick={() => setCursor(undefined)}>
            В начало
          </button>
        )}
        {nextCursor === null ? null : (
          <button type="button" className="am-button am-button--quiet am-button--small" onClick={() => setCursor(nextCursor)}>
            Дальше
          </button>
        )}
      </div>
      <h3>
        {comparisonOnly ? 'Запуск прогона' : isAr ? 'Запустить анализ АР' : 'Запустить ещё один прогон'}
      </h3>
      {startControl}
    </div>
  );
}
