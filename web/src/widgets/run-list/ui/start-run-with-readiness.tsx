'use client';

/**
 * «Запустить» with the line under it filled from the server (`READINESS-WEB-01`, plan 2026-11-09 §8): one button, one line, and,
 * when the plan names a model no server has, the reason the button is inactive.
 *
 * The control (`features/start-run`) draws the button and the line it is given; this widget reads `getRunStartReadiness` for the
 * version (`useRunStartReadiness`), builds the line and the reason from the answer, and mounts the window that «Модели по этапам ▸»
 * opens (`PlanStagesDialog`, a widget, which a feature does not import). Nothing here decides: the set, the access and `ready` are the
 * server's words.
 *
 * - **The layout is on, every cell has a server:** «Набор: Только Claude · по подписке · ⚠ не для клиентских документов · Модели по
 *   этапам ▸». A part by API: «… · часть по API — покажем оценку · …».
 * - **A cell has no server:** the button is inactive and the reason is said: «Нет Opus 5.5 — Анализ блоков · обратитесь к
 *   администратору». An administrator is told what to do instead of whom to ask: «подключите сервер в «Исполнители»», a link.
 * - **The layout is off:** «Маршрут: прежний», and the button is as it was.
 * - **The server has no layout to speak of (503):** «Маршрут: автоматически», as before: this is not an error for the person.
 *
 * The read is sent for an account that is offered the start; the account that is not (the viewer) reads nothing (`R-150w`).
 */

import { useState } from 'react';
import type { ReactNode } from 'react';

import type { ProjectUid, RunStatus, VersionUid } from '@/shared/api';
import { routes } from '@/shared/lib';
import { useMayActAsExpert, useMe } from '@/entities/account';
import { canExecute } from '@/entities/execution';
import { STAGE_KIT_LABELS, readinessPlan } from '@/entities/stage-layout';
import {
  CONNECT_SERVER,
  CONTACT_ADMIN,
  StartRunControl,
  blockedModels,
  readinessNoteOf,
  useRunStartReadiness,
} from '@/features/start-run';
import { PlanStagesDialog } from '@/widgets/run-stages-dialog';

/** «Исполнители → Модели по этапам»: the tab is a place in the address (`/workers?tab=models`). */
export const MODELS_BY_STAGE_ADDRESS = `${routes.workers()}?tab=models`;

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
      {open && readiness !== null && readiness.route === 'stage_plan' ? (
        <PlanStagesDialog
          rows={readinessPlan(readiness.cells)}
          kit={readiness.kit === undefined ? null : STAGE_KIT_LABELS[readiness.kit]}
          extendedPlan={readiness.extended_plan}
          onClose={() => setOpen(false)}
          editHref={admin ? MODELS_BY_STAGE_ADDRESS : undefined}
        />
      ) : null}
    </>
  );
}
