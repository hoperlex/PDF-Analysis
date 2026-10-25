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
 */

import { useRouter } from 'next/navigation';
import { useState } from 'react';

import type { ProjectUid, RunStatus, VersionUid } from '@/shared/api';
import { EmptyState, ErrorState, LoadingState } from '@/shared/ui';
import { classifyListingFailure, routes } from '@/shared/lib';
import { RunRow, arV3GroupReviewAddress, useArV3PackStatus, useRunList } from '@/entities/audit-run';
import { StartArV3GroupControl } from '@/features/start-ar-v3-group';
import { StartRunControl } from '@/features/start-run';

export interface RunListProps {
  readonly projectUid: ProjectUid;
  readonly versionUid: VersionUid;
  /** Called with the 202 reading so the screen can move to run progress. */
  readonly onRunStarted?: ((run: RunStatus) => void) | undefined;
}

/**
 * The six-check start, opening the started group's review. Its own component so the router
 * is read only when the control is drawn: a list without an installed pack mounts none.
 */
function StartArV3Group({ projectUid, versionUid }: { readonly projectUid: ProjectUid; readonly versionUid: VersionUid }) {
  const router = useRouter();
  return (
    <StartArV3GroupControl
      projectUid={projectUid}
      versionUid={versionUid}
      onStarted={(group) => router.push(arV3GroupReviewAddress(group.group_id))}
    />
  );
}

export function RunList({ projectUid, versionUid, onRunStarted }: RunListProps) {
  const [cursor, setCursor] = useState<string | undefined>(undefined);
  const query = useRunList(versionUid, cursor);
  const { view: pack } = useArV3PackStatus();
  const packInstalled = pack.phase === 'read' && pack.reading.kind === 'installed';

  const startControl = (
    <>
      <StartRunControl
        projectUid={projectUid}
        versionUid={versionUid}
        {...(onRunStarted === undefined ? {} : { onStarted: onRunStarted })}
      />
      {packInstalled ? <StartArV3Group projectUid={projectUid} versionUid={versionUid} /> : null}
    </>
  );

  if (query.isPending) return <LoadingState what="прогоны этой версии" />;

  if (query.isError) {
    const failure = classifyListingFailure(query.error, {
      collection: 'прогоны этой версии',
      parent: 'version',
    });
    return (
      <ErrorState
        title={failure.title}
        detail={<span data-list-failure={failure.kind}>{failure.detail}</span>}
        correlationId={failure.correlationId}
        {...(failure.retryable
          ? { onRetry: () => void query.refetch(), retryLabel: 'Повторить' }
          : {})}
      />
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
      <h3>Запустить ещё один прогон</h3>
      {startControl}
    </div>
  );
}
