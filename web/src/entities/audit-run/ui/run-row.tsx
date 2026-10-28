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
 *
 * `EXEC-PAR-WEB-01`: a run that froze an executor names it, with its pinned model; a run in the
 * queue says it is waiting for that executor. A run with none (the environment source) draws
 * no line at all.
 */

import Link from 'next/link';

import type { RunStatus } from '@/shared/api';
import { RunStateBadge } from '@/shared/ui';
import { formatInstant } from '@/shared/lib';

import { runExecutorLine, runExecutorSentence } from '../model/run-executor';
import { runPresetLine, runPresetSentence } from '../model/run-preset';

export interface RunRowProps {
  readonly run: RunStatus;
  /** Where this row opens. Built by the screen, never by the row. */
  readonly href: string;
}

export function RunRow({ run, href }: RunRowProps) {
  const executor = runExecutorLine(run);
  const preset = runPresetLine(run);
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
          Создан {formatInstant(run.created_at)}
          {run.terminal_at === undefined || run.terminal_at === null
            ? ''
            : ` · завершён ${formatInstant(run.terminal_at)}`}
        </p>
        {executor === null ? null : <p data-run-executor>{runExecutorSentence(executor)}</p>}
        {preset === null ? null : <p data-run-preset>{runPresetSentence(preset)}</p>}
        <p>
          Находок{' '}
          {run.published_finding_count === undefined ? '—' : run.published_finding_count} ·
          этапов {run.stages.length}
        </p>
      </div>
    </li>
  );
}
