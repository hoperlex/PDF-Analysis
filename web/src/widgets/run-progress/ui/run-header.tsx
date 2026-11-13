'use client';

/** @jsxRuntime automatic */

/**
 * The head of the run screen (`RUN-SCREEN-01a`, plan §9.1): the state, «этап N из M» over the chips this run has, a bar of one segment
 * per chip, the server's estimated finish «≈ до ЧЧ:ММ», what to do next, the live line of an open run, the rail of chips and the caption of
 * a run started from a stage.
 *
 * The provider mode is not a badge here and neither is the sentence about polling; `data-run-activity` stays on the status line as the
 * browser journey reads it, and a sentence is printed only for the stopped-but-open reading (the poll has stopped while the run is
 * not over, so what is on screen is the last reading received). One thing of the provider mode is kept: a run reproduced from recordings
 * carries a small chip «из записи» beside its state, so that it cannot be mistaken for a live one (`recorded`, from `runProviderMode`).
 * A live run draws nothing, and neither does a reading with no mode or an unrecognised one -- those say so in «Подробнее», where the
 * mode has its own row.
 *
 * The count is over the chips present in this run (`chipProgress`); it is a display count and not an ordinal of the contract's graph
 * (`stage-vocabulary.guard.test.ts` holds that the nine stages are not a line). A run that is over says how many chips completed.
 */

import Link from 'next/link';
import type { ReactNode } from 'react';

import type { RunStages, RunStatus } from '@/shared/api';
import { formatInstant, routes } from '@/shared/lib';
import { PROVIDER_MODE_LABELS, RunStateBadge, runStageLabel } from '@/shared/ui';
import { chipProgress, isRunAnimating, runFinishEstimate } from '@/entities/audit-run';
import type { LiveProgress, RunChip, RunChipDefinition, RunExecutorLine, RunFinishEstimate } from '@/entities/audit-run';

import type { StartedFrom } from '../model/started-from';

import { RunLiveLineView, RunWaitLine, liveElapsed, useRunClock } from './run-live-line';
import { RunRail } from './run-rail';
import styles from './run-progress.module.css';

export interface RunHeaderProps {
  readonly status: RunStatus;
  readonly chips: readonly RunChip[];
  readonly executor: RunExecutorLine | null;
  readonly model: { readonly short: string; readonly pin: string } | null;
  /** The stages read for the run (`useRunStages`), for the model each chip names; absent until read. */
  readonly stages?: RunStages | undefined;
  /** Whether the reader may see the server (`maySeeServer`). */
  readonly showServer: boolean;
  readonly liveProgress: LiveProgress | null;
  /** Whether the run's provider mode is `recorded`: the chip «из записи» is drawn only then. */
  readonly recorded: boolean;
  /** Whether the poll is running (`useRunStatus`). */
  readonly polling: boolean;
  readonly from: StartedFrom | null;
  /** The sentence for a run in the queue, or `null`. */
  readonly waiting: string | null;
  /** The group's precise reason, drawn under the waiting line. */
  readonly waitDetail: ReactNode;
  /** «Разобрать находки» and «Отменить». */
  readonly actions: ReactNode;
  readonly onOpenChip: (id: RunChipDefinition['id']) => void;
}

/**
 * `UI-B-45` (contract 1.40.0): «≈ до ЧЧ:ММ» -- the server's estimated finish (`RunStatus.estimated_finish_at`), never computed here and absent
 * for a run without enough similar history. It is worded with the same clock reading as the elapsed time, so it appears after mount, and
 * once the instant is behind that reading it says «дольше обычного» rather than keep promising a time that has passed.
 */
export function RunEta({ finish }: { readonly finish: RunFinishEstimate | null }) {
  if (finish === null) return null;
  return (
    <span className={styles.eta} data-run-eta={finish.iso} data-run-eta-late={finish.late ? '' : undefined}>
      ≈ до <time dateTime={finish.iso} title={formatInstant(finish.iso)}>{finish.clock}</time>
      {finish.late ? ' · дольше обычного' : null}
    </span>
  );
}

function segmentOf(chip: RunChip): string {
  if (chip.state === 'failed') return 'failed';
  if (chip.state === 'running' || chip.state === 'waiting') return 'live';
  return chip.state === 'done' ? 'done' : chip.state === 'pending' ? 'pending' : 'limited';
}

export function RunHeader({
  status, chips, executor, model, stages, showServer, liveProgress, recorded, polling, from, waiting, waitDetail, actions, onOpenChip,
}: RunHeaderProps) {
  const now = useRunClock(status);
  const animating = isRunAnimating(status);
  const progress = chipProgress(chips);
  const finish = animating ? runFinishEstimate(status, now) : null;

  const counter = progress.total === 0
    ? null
    : animating && progress.liveIndex !== null
      ? `этап ${progress.liveIndex} из ${progress.total}`
      : `этапов выполнено успешно ${progress.completed} из ${progress.total}; завершено ${progress.terminal}`;

  const elapsed = liveElapsed(status, progress.live, now);
  const server = showServer && executor !== null && executor.name !== '' ? executor.name : null;

  return (
    <section className={styles.head} aria-label="Этапы и действия" data-run-head="">
      <div className={styles.headTop}>
        <p className={styles.status} data-run-activity={animating && polling ? 'polling' : 'stopped'}>
          <RunStateBadge state={status.state} />
          {recorded ? <span className={styles.recorded} data-run-recorded="">{PROVIDER_MODE_LABELS.recorded}</span> : null}
          {counter === null ? null : <span className={styles.counter} data-run-stage-count={`${progress.liveIndex ?? progress.completed}/${progress.total}`}>{counter}</span>}
          {progress.total === 0 ? null : (
            <span
              className={styles.bar}
              role="progressbar"
              aria-label="Выполнено этапов"
              aria-valuemin={0}
              aria-valuemax={progress.total}
              aria-valuenow={progress.completed}
              aria-valuetext={`выполнено успешно ${progress.completed} из ${progress.total}; завершено ${progress.terminal}`}
              data-run-bar=""
            >
              {chips.map((chip) => (
                <span key={chip.definition.id} className={styles.segment} data-segment={segmentOf(chip)} />
              ))}
            </span>
          )}
          <RunEta finish={finish} />
        </p>
        <div className={styles.headActions}>{actions}</div>
      </div>

      {animating && !polling ? (
        <p className={styles.caption} data-run-poll-stopped="">
          Опрос остановлен, но прогон ещё открыт: показание — последнее полученное, а не окончательное.
        </p>
      ) : null}

      {/* `UI-A-65`: the open run's live line -- the stage it is on, the window or batch, the model, the server and how long. */}
      {!animating ? null : status.state === 'queued' ? (
        waiting === null ? null : (
          <>
            <RunWaitLine sentence={waiting} model={model} />
            {waitDetail}
          </>
        )
      ) : (
        <RunLiveLineView
          chip={progress.live}
          progress={liveProgress}
          model={progress.live !== null && progress.live.definition.callsModel ? model : null}
          server={progress.live !== null && progress.live.definition.callsModel ? server : null}
          elapsed={elapsed.text}
          elapsedOf={elapsed.of}
        />
      )}

      <RunRail chips={chips} model={model} stages={stages} onOpen={onOpenChip} />

      {/* `R-151i`: a run started from a stage says so under its head, with the way back to the run it took the first stages from. */}
      {from === null ? null : (
        <p className={styles.caption} data-run-started-from-note={from.stageId}>
          Запущен с этапа {from.ordinal} «{runStageLabel(from.stageId)}» из прогона{' '}
          <Link href={routes.run(status.project_uid, from.sourceRunId)}><code data-run-started-from={from.sourceRunId}>{from.sourceRunId}</code></Link>:
          результаты предыдущих этапов взяты из него, этот этап и следующие выполнены заново.
        </p>
      )}
    </section>
  );
}
