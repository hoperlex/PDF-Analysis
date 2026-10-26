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
 * `AR-V3-BETA-PACK-STATUS-WEB-01`: beside it, and only beside it when the server's reviewed
 * AR v3 pack is installed and its status answer is valid, the control that starts the six
 * checks. While the status is loading, failed, says not installed or breaks the contract the
 * control is not drawn at all — no disabled button, no placeholder; «Настройки анализа»
 * carries the explanation. A started group opens its review on that screen.
 *
 * `AR-V3-BETA-PACK-STATUS-WEB-FIX-01`: a start already sent keeps the control drawn. The status
 * is re-read while the page is open, and a re-read that fails would otherwise take the control
 * off the page under a request in flight — losing the navigation to the group it makes and the
 * idempotency key, so the next press could make a second group. The list therefore holds the
 * key (`useArV3GroupStartIntent`, for as long as the list lives) and draws the control while a
 * start for this version is pending as well as while the pack is installed.
 *
 * `AR-V3-BETA-PACK-STATUS-WEB-FIX-02`: the list itself can stop showing the list. Its query key
 * carries the cursor, so «Дальше» turns it into its loading state, and a failed re-read turns it
 * into its error state; both returned before the control. A control is a different instance in
 * every branch, and the answer of a start is delivered to the observer that sent it. So the
 * observer is held here too (`useArV3GroupStartIntent` owns the start's mutation, and the list
 * is mounted through every branch): the accepted group opens whichever branch is showing, and a
 * refusal waits for the control to come back. While a start is pending the loading and error
 * branches draw the control under their own message; with no start pending they draw nothing
 * more, as before. The component is keyed by the version, so the cursor, the key and the
 * observer belong to one version.
 *
 * `PROD-11-AR-V1-V2-REMOVAL-01`: a version classified АР has no ordinary start. The server refuses
 * `startRun` for it (`section_profile_unavailable`: АР is analysed only by the six-check group), so
 * the list draws the six-check control for it, when the pack allows, and a sentence saying why
 * there is no other — never the ordinary «Запустить прогон». The section comes from the version the
 * page has read; until it arrives (`undefined`) the list is what it always was, and a press in
 * that interval is refused by the server in the same words.
 */

import { useRouter } from 'next/navigation';
import { useState } from 'react';

import type { ProjectSection, ProjectUid, RunStatus, VersionUid } from '@/shared/api';
import { EmptyState, ErrorState, LoadingState } from '@/shared/ui';
import { classifyListingFailure, routes } from '@/shared/lib';
import { AR_START_NOTE } from '@/entities/analysis-profile';
import { RunRow, arV3GroupReviewAddress, useArV3PackStatus, useRunList } from '@/entities/audit-run';
import type { ArV3GroupStartIntent } from '@/features/start-ar-v3-group';
import { StartArV3GroupControl, useArV3GroupStartIntent } from '@/features/start-ar-v3-group';
import { StartRunControl } from '@/features/start-run';

export interface RunListProps {
  readonly projectUid: ProjectUid;
  readonly versionUid: VersionUid;
  /**
   * The section the version's classification confirms, once the page has read it. `'AR'` takes the
   * АР start (the six checks only); anything else, and `undefined`, the ordinary start.
   */
  readonly sectionCode?: ProjectSection | null | undefined;
  /** Called with the 202 reading so the screen can move to run progress. */
  readonly onRunStarted?: ((run: RunStatus) => void) | undefined;
}

/**
 * The six-check start, opening the started group's review. Its own component so the router
 * is read only when the control is drawn: a list without an installed pack mounts none.
 */
function StartArV3Group({
  projectUid,
  versionUid,
  intent,
}: {
  readonly projectUid: ProjectUid;
  readonly versionUid: VersionUid;
  readonly intent: ArV3GroupStartIntent;
}) {
  const router = useRouter();
  return (
    <StartArV3GroupControl
      projectUid={projectUid}
      versionUid={versionUid}
      intent={intent}
      onStarted={(group) => router.push(arV3GroupReviewAddress(group.group_id))}
    />
  );
}

export function RunList(props: RunListProps) {
  return <VersionRunList key={props.versionUid} {...props} />;
}

function VersionRunList({ projectUid, versionUid, sectionCode, onRunStarted }: RunListProps) {
  const [cursor, setCursor] = useState<string | undefined>(undefined);
  const query = useRunList(versionUid, cursor);
  const { view: pack } = useArV3PackStatus();
  const packInstalled = pack.phase === 'read' && pack.reading.kind === 'installed';
  const startIntent = useArV3GroupStartIntent(versionUid);

  const sixChecks =
    packInstalled || startIntent.inFlight ? (
      <StartArV3Group projectUid={projectUid} versionUid={versionUid} intent={startIntent} />
    ) : null;
  // What the loading and error branches add to their message: the control, only for a start
  // already sent. A fresh visit with the list not showing draws no control.
  const sixChecksInFlight = startIntent.inFlight ? sixChecks : null;

  const isAr = sectionCode === 'AR';
  const startControl = isAr ? (
    sixChecks ?? <p className="am-note" data-ar-start-note="">{AR_START_NOTE}</p>
  ) : (
    <>
      <StartRunControl
        projectUid={projectUid}
        versionUid={versionUid}
        {...(onRunStarted === undefined ? {} : { onStarted: onRunStarted })}
      />
      {sixChecks}
    </>
  );

  if (query.isPending) {
    return (
      <>
        <LoadingState what="прогоны этой версии" />
        {sixChecksInFlight}
      </>
    );
  }

  if (query.isError) {
    const failure = classifyListingFailure(query.error, {
      collection: 'прогоны этой версии',
      parent: 'version',
    });
    return (
      <>
        <ErrorState
          title={failure.title}
          detail={<span data-list-failure={failure.kind}>{failure.detail}</span>}
          correlationId={failure.correlationId}
          {...(failure.retryable
            ? { onRetry: () => void query.refetch(), retryLabel: 'Повторить' }
            : {})}
        />
        {sixChecksInFlight}
      </>
    );
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
      <h3>{isAr ? 'Запустить анализ АР' : 'Запустить ещё один прогон'}</h3>
      {startControl}
    </div>
  );
}
