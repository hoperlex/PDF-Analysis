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
 * АР now has an ordinary text profile sourced from the original application. The six-check
 * beta control is no longer offered as the default start; its API and old Run readers remain.
 *
 * `CMP-VERSION-MARK-01`: a version admitted for comparison only (`upload_kind` `comparison_pdf`) has
 * no portal bundle, so no analysis reads it, and the server refuses both starts
 * (`analysis_input_invalid`, `comparison_only_version`). The list draws the start disabled, with the
 * sentence that says why, in place of the ordinary control and of the six checks alike — and in place
 * of the АР sentence for a version classified АР, whose reason is the less basic one. The kind comes
 * from the version the page has read; until it arrives (`undefined`) the list is what it always was.
 * Runs already listed stay listed.
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
import { RunRow, useRunList } from '@/entities/audit-run';
import { ComparisonOnlyStart } from '@/entities/document-version';
import { StartRunControl } from '@/features/start-run';

export interface RunListProps {
  readonly projectUid: ProjectUid;
  readonly versionUid: VersionUid;
  /**
   * The section the version's classification confirms, once the page has read it.
   * `'AR'` now takes the ordinary start and its original-source text profile.
   */
  readonly sectionCode?: ProjectSection | null | undefined;
  /**
   * How the version reached the product, once the page has read it. `'comparison_pdf'` draws the
   * start disabled with its reason; anything else, and `undefined`, the start as before.
   */
  readonly uploadKind?: VersionUploadKind | undefined;
  /** Called with the 202 reading so the screen can move to run progress. */
  readonly onRunStarted?: ((run: RunStatus) => void) | undefined;
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
  const startControl = comparisonOnly ? (
    <ComparisonOnlyStart />
  ) : (
    <StartRunControl
      projectUid={projectUid}
      versionUid={versionUid}
      {...(onRunStarted === undefined ? {} : { onStarted: onRunStarted })}
    />
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

  return (
    <div data-run-count={page.items.length}>
      <ul className="am-rows">
        {page.items.map((run) => (
          <RunRow key={run.run_id} run={run} href={routes.run(projectUid, run.run_id)} />
        ))}
      </ul>
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
