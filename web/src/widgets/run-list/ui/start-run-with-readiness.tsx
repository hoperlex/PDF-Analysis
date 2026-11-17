'use client';

/**
 * «Запустить» with the line under it filled from the server (`READINESS-WEB-01`, plan 2026-11-09 §8; `UIP-S05-02`): one button, one line, and,
 * when the plan names a model no server has, the reason the button is inactive.
 *
 * The control (`features/start-run`) draws the button and the line it is given; this widget reads `getRunStartReadiness` for the
 * version (`useRunStartReadiness`), builds the line and the reason from the answer, and mounts the window that «Модели по этапам ▸»
 * opens (`StageModelsDialog`, a widget, which a feature does not import). Nothing here decides: the set, the access and `ready` are the
 * server's words.
 *
 * The line carries «Модели по этапам ▸» in every state but the one that is still reading, and the window opens in every one of them,
 * drawing from what the state has (`stageModelsSourceOf`): the plan the answer states, or, with no plan to read, the saved layout.
 *
 * - **The layout is on, every cell has a server:** «Набор: Только Claude · по подписке · ⚠ не для клиентских документов · Модели по
 *   этапам ▸». A part by API: «… · часть по API — покажем оценку · …».
 * - **A cell has no server:** the button is inactive and the reason is said: «Нет Opus 5.5 — Анализ блоков · обратитесь к
 *   администратору». An administrator is told what to do instead of whom to ask: «подключите сервер в «Диспетчере»», a link.
 * - **The layout is off:** «Маршрут: прежний · Модели по этапам ▸», and the button is as it was.
 * - **The server has no layout to speak of (503):** «Маршрут: автоматически · Модели по этапам ▸», as before: this is not an error for the person.
 * - **The readiness was not read:** «Готовность запуска не прочитана; запуск проверит её сам. Повторить · Модели по этапам ▸».
 *
 * The read is sent for an account that is offered the start; the account that is not (the viewer) reads nothing (`R-150w`).
 */

import { useState } from 'react';
import type { ReactNode } from 'react';

import type { ProjectUid, RunStatus, VersionUid } from '@/shared/api';
import { routes } from '@/shared/lib';
import { useMayActAsExpert, useMe } from '@/entities/account';
import { canExecute } from '@/entities/execution';
import type { RunStartReadinessReading } from '@/features/start-run';
import {
  CONNECT_SERVER,
  CONTACT_ADMIN,
  StartRunControl,
  blockedModels,
  readinessNoteOf,
  useRunStartReadiness,
} from '@/features/start-run';
import { StageModelsDialog } from '@/widgets/run-stages-dialog';
import type { StageModelsSource } from '@/widgets/run-stages-dialog';

/** «Диспетчер → Модели по этапам»: the tab is a place in the address (`/workers?tab=models`). */
export const MODELS_BY_STAGE_ADDRESS = `${routes.workers()}?tab=models`;

/**
 * What the window «Модели по этапам» draws from, for a reading of the readiness: the plan on the layout's route, the saved layout with its word
 * («прежний маршрут», «автоматически», «не прочитано») with no plan to read, and nothing while the answer is still being read.
 */
function stageModelsSourceOf(reading: RunStartReadinessReading): StageModelsSource | null {
  switch (reading.state) {
    case 'loading':
      return null;
    case 'unavailable':
      return { kind: 'automatic' };
    case 'failed':
      return { kind: 'unread' };
    case 'ready':
      return reading.readiness.route === 'stage_plan' ? { kind: 'plan', readiness: reading.readiness } : { kind: 'legacy' };
  }
}

export interface StartRunWithReadinessProps {
  readonly projectUid: ProjectUid;
  readonly versionUid: VersionUid;
  /** Called with the 202 reading, so the screen can move to run progress. */
  readonly onStarted?: ((run: RunStatus) => void) | undefined;
  /** Test seam: the plan's window starts open. */
  readonly initiallyOpen?: boolean | undefined;
}

export function StartRunWithReadiness({ projectUid, versionUid, onStarted, initiallyOpen = false }: StartRunWithReadinessProps) {
  const mayAct = useMayActAsExpert();
  const me = useMe();
  const admin = canExecute(me.data?.roles ?? [], 'connections');
  const reading = useRunStartReadiness(versionUid, mayAct);
  const [open, setOpen] = useState(initiallyOpen);

  const readiness = reading.state === 'ready' ? reading.readiness : null;
  const source = stageModelsSourceOf(reading);
  const missing = readiness === null ? null : blockedModels(readiness);
  const blockedReason: ReactNode = missing === null ? null : admin
    ? <>{`${missing} · `}<a href={routes.workers()} data-blocked-connect="">{CONNECT_SERVER}</a></>
    : `${missing} · ${CONTACT_ADMIN}`;

  return (
    <>
      <StartRunControl
        projectUid={projectUid}
        versionUid={versionUid}
        {...(onStarted === undefined ? {} : { onStarted })}
        readinessNote={readinessNoteOf(reading, () => setOpen(true))}
        blockedReason={blockedReason}
      />
      {open && source !== null ? <StageModelsDialog source={source} onClose={() => setOpen(false)} /> : null}
    </>
  );
}
