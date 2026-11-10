/** @jsxRuntime automatic */

/**
 * The line under a waiting run's sentence that names the model it waits for (`HOSTS-L1`, `D-660`):
 * «Ждём gpt-6-sol: нет сервера с этой моделью; gpt-6-astra: все места сервера заняты; и ещё 2».
 *
 * One line, no control. The words come from `runWaitCellsLine` (`entities/audit-run`): at most two models, then the count of the rest, each
 * with its cause in Russian; the contract value of the cause stays in `data-run-wait-cause`. It draws nothing for a run that is not queued,
 * for a reading without cells, and for causes this screen does not know.
 */

import { Fragment } from 'react';

import type { RunStatus } from '@/shared/api';
import { runWaitCellsLine } from '@/entities/audit-run';

import styles from './run-progress.module.css';

export interface RunWaitCellsProps {
  readonly run: Pick<RunStatus, 'state' | 'wait_cells'>;
}

export function RunWaitCells({ run }: RunWaitCellsProps) {
  const line = runWaitCellsLine(run);
  if (line === null) return null;
  return (
    <p className={styles.caption} role="status" data-run-wait-cells="">
      Ждём{' '}
      {line.models.map((item, at) => (
        <Fragment key={item.model}>
          {at === 0 ? null : '; '}
          <span data-run-wait-model={item.model}>{item.model}</span>: <span data-run-wait-cause={item.cause}>{item.text}</span>
        </Fragment>
      ))}
      {line.more > 0 ? <>; и ещё <span data-run-wait-more="">{line.more}</span></> : null}
    </p>
  );
}
