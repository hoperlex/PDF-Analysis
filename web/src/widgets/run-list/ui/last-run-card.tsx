'use client';

/**
 * «Последний прогон» (`UIP-S04-03`): the first card of the version's «Инфо», the original's first screen of a document in our
 * nouns — when the version's last run was and how it stands, a row of its stages, the way into the run, and «Запустить».
 *
 *   - **the run**: «Прогон от 16.11.2026 14:05» and its state in a word (the badge of the runs table), «Открыть прогон». A run that is
 *     still going says so and sends the reader to the run's page, because the card is read once and never moves;
 *   - **the stages**: one button for each chip of the run, its name, its state in a word and the time it took (`lastRunChips`). A press
 *     opens the window «Этапы анализа раздела» (`RunStagesDialog`), the run page's own, with «Перезапустить с этого этапа» (a run that ended without a clean result) for the account
 *     that may start a run (the window's control decides that, not this card). No token, no cost and no model is drawn on the card; the
 *     model of a stage is in the chip's hint, for an administrator only (`chipHint`);
 *   - **«Запустить»** with its one line under it, filled as it always was (`StartRunWithReadiness`): the one control of `R-153a`, not
 *     a second one. A version with no run says «По этой версии прогонов не запускалось» and offers the same button.
 *
 * **It reads the progress once.** The runs are the list the table below reads (the first page, the same key, so one request), the
 * stages are `getRunStages` of the newest run; neither polls. The live progress of a run is the run page's (`D-20`, the one loop in the
 * application). A list that could not be read is said in a line; the table below says it with the retry, and the start stays.
 *
 * The usage figures (tokens, calls, minutes) and the pipeline list of the original are not here: they stay on the run's page (`Г12-B`).
 */

import Link from 'next/link';
import { useId, useState } from 'react';

import type { ProjectUid, RunId, RunStatus, VersionUid, VersionUploadKind } from '@/shared/api';
import { formatInstant, routes } from '@/shared/lib';
import { EmptyState, LoadingState, RunStateBadge } from '@/shared/ui';
import { useMe } from '@/entities/account';
import { CHIP_STATE_LABELS, formatElapsed, isRunAnimating, useRunList, useRunStages } from '@/entities/audit-run';
import type { RunChip, RunChipId } from '@/entities/audit-run';
import { canExecute } from '@/entities/execution';
import { RunStagesDialog } from '@/widgets/run-stages-dialog';
import { maySeeServer } from '@/widgets/run-progress';

import { chipHint, lastRunChips, reusedStageIdsOf } from '../model/last-run-chips';
import { StartRunWithReadiness } from './start-run-with-readiness';

import styles from './last-run-card.module.css';

export interface LastRunCardProps {
  readonly projectUid: ProjectUid;
  readonly versionUid: VersionUid;
  /** How the version reached the product; a comparison PDF is analysed without the portal's markup, and the card says so. */
  readonly uploadKind?: VersionUploadKind | undefined;
  /** Called with the 202 reading so the page can move to the run. */
  readonly onRunStarted?: ((run: RunStatus) => void) | undefined;
  /** Test seam: the stage window starts open on this chip, drawn open without `showModal`. */
  readonly initiallyOpenChip?: RunChipId | undefined;
}

/** What a stage chip says of itself, in words: its state, and the time it took. */
function tookOf(chip: RunChip): string | null {
  if (chip.reused) return 'из прогона';
  return chip.elapsedMs === null ? null : formatElapsed(chip.elapsedMs);
}

export function LastRunCard(props: LastRunCardProps) {
  return <VersionLastRun key={props.versionUid} {...props} />;
}

function VersionLastRun({ projectUid, versionUid, uploadKind, onRunStarted, initiallyOpenChip }: LastRunCardProps) {
  const titleId = useId();
  const list = useRunList(versionUid);
  const latest = list.data?.items[0] ?? null;
  // The progress of the newest run, read once: `getRunStages`, the answer the window reads too (no loop of its own).
  const stagesView = useRunStages((latest?.run_id ?? '') as RunId, latest !== null);
  const stages = stagesView.phase === 'read' ? stagesView.stages : null;
  const me = useMe();
  const admin = canExecute(me.data?.roles ?? [], 'connections');
  const [openChip, setOpenChip] = useState<RunChipId | null>(initiallyOpenChip ?? null);

  const chips = latest === null ? [] : lastRunChips(latest, stages);
  const start = (
    <>
      {uploadKind === 'comparison_pdf' ? <p className="am-note">Анализ будет выполнен по исходному PDF без разметки портала.</p> : null}
      <StartRunWithReadiness
        projectUid={projectUid}
        versionUid={versionUid}
        {...(onRunStarted === undefined ? {} : { onStarted: onRunStarted })}
      />
    </>
  );

  let body;
  if (list.isPending) {
    // The runs of the version are what is being read (the table below says the same words), so the one loading label is the table's.
    body = <><LoadingState what="прогоны этой версии" />{start}</>;
  } else if (list.isError) {
    body = (
      <>
        <p className="am-note" role="status" data-last-run-failed="">
          Последний прогон прочитать не удалось: таблица «Прогоны» ниже скажет почему и повторит чтение.
        </p>
        {start}
      </>
    );
  } else if (latest === null) {
    body = (
      <EmptyState
        title="По этой версии прогонов не запускалось."
        detail="Версия опубликована и неизменяема. Запуск прогона читает её и никогда не меняет."
        action={start}
      />
    );
  } else {
    body = (
      <>
        <div className={styles.head}>
          <p className={styles.run} data-last-run-id={latest.run_id}>
            <span>Прогон от <time dateTime={latest.created_at}>{formatInstant(latest.created_at)}</time></span>
            <RunStateBadge state={latest.state} providerMode={latest.provider_mode} />
          </p>
          <Link className="am-button am-button--quiet am-button--small" href={routes.run(projectUid, latest.run_id)} data-last-run-open="">
            Открыть прогон
          </Link>
        </div>
        {isRunAnimating(latest) ? (
          <p className="am-note" data-last-run-live="">Прогон ещё идёт: ход виден на странице прогона, здесь он не обновляется.</p>
        ) : null}
        {chips.length === 0 ? null : (
          <ol className={styles.chips} aria-label="Этапы последнего прогона" data-last-run-chips="">
            {chips.map((chip) => {
              const id = chip.definition.id;
              const took = tookOf(chip);
              return (
                <li key={id} className={styles.chipItem}>
                  <button
                    type="button"
                    className={styles.chip}
                    data-last-run-chip={id}
                    data-chip-state={chip.state}
                    aria-haspopup="dialog"
                    title={chipHint(chip, stages, admin)}
                    onClick={() => setOpenChip(id)}
                  >
                    <span className={styles.chipName}>{chip.definition.short}</span>
                    <span className={styles.chipStatus}>
                      <span>{CHIP_STATE_LABELS[chip.state]}</span>
                      {took === null ? null : <span className={styles.chipTook}>{took}</span>}
                    </span>
                  </button>
                </li>
              );
            })}
          </ol>
        )}
        <div className={styles.start}>{start}</div>
      </>
    );
  }

  return (
    <section className={styles.card} aria-labelledby={titleId} data-last-run-card={versionUid}>
      <h2 id={titleId} className={styles.title}>Последний прогон</h2>
      {body}
      {openChip === null || latest === null ? null : (
        <RunStagesDialog
          status={latest}
          chips={chips}
          selected={openChip}
          onSelect={setOpenChip}
          onClose={() => setOpenChip(null)}
          reusedStageIds={reusedStageIdsOf(latest)}
          showServer={maySeeServer(me.data?.roles)}
          stages={stagesView}
          staticOpen={initiallyOpenChip !== undefined}
        />
      )}
    </section>
  );
}
