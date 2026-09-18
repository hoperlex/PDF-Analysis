/**
 * One run as a row.
 *
 * Presentational. The state badge carries `provider_mode` with it, for the reason
 * `shared/ui` states: a recorded run is not evidence of a live one, and a caption
 * elsewhere on the page is a caption a reader can miss.
 *
 * There is no progress indicator and no "running…" affordance. `D-20`: `execute_run` is
 * inline, so a run is already terminal when `startRun` answers and no client can observe
 * a `running` one. A row that animated towards a state nothing can report would be a
 * promise this system cannot keep.
 */

import Link from 'next/link';

import type { RunStatus } from '@/shared/api';
import { RunStateBadge } from '@/shared/ui';
import { formatInstant } from '@/shared/lib';

export interface RunRowProps {
  readonly run: RunStatus;
  /** Where this row opens. Built by the screen, never by the row. */
  readonly href: string;
}

export function RunRow({ run, href }: RunRowProps) {
  return (
    <li className="am-state" style={{ marginBottom: '0.5rem' }} data-run-id={run.run_id}>
      <p className="am-state__title">
        <Link href={href}>
          <code>{run.run_id}</code>
        </Link>{' '}
        <RunStateBadge state={run.state} providerMode={run.provider_mode} />
      </p>
      <div className="am-state__detail">
        <p>
          Created {formatInstant(run.created_at)}
          {run.terminal_at === undefined || run.terminal_at === null
            ? ''
            : ` · terminal ${formatInstant(run.terminal_at)}`}
        </p>
        <p>
          Findings{' '}
          {run.published_finding_count === undefined ? '—' : run.published_finding_count} ·
          stages {run.stages.length}
        </p>
      </div>
    </li>
  );
}
