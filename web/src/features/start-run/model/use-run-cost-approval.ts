'use client';

/**
 * The sequence of the one-button start (`RUN-START-ONE-01a`, plan v3 §8): estimate, agree, send.
 *
 * 1. The click reads the estimate (`estimateRunCost`, a POST read that creates no run and no spend).
 * 2. An estimate that charges nothing (`unmetered`) is agreed to by the click itself: the run is sent at
 *    once with the consent of that estimate, and no dialog opens.
 * 3. Any other estimate opens ONE dialog with its figure and the ceiling; the dialog's «Запустить» is the
 *    agreement, and «Отмена» sends nothing.
 * 4. A start the server refuses because the estimate or its binding changed
 *    (`run_cost_estimate_stale`, `cost_estimate_binding_changed`) is estimated again and shown in the
 *    dialog, whatever the new figure: the person sees what changed before anything is sent.
 *
 * **One key per intent.** The intent is the version, the limit choice and the consent it carries
 * (`startRunIntent`). The key is held by `resolveIntentKey`, the rule every write feature uses: the same
 * consent sent again (a second click after a failure, the retry beside a refusal) keeps its key, and any
 * change of the payload, such as another digest or another ceiling, is another intent and gets another one.
 * It is called from the handlers, because the consent exists only after the estimate has answered.
 *
 * **No selector.** The request names no executor, group or preset: the server's automatic route applies.
 * The estimate request is built the same way, so the estimate and the start are about the same run.
 *
 * Both reads and sends of one control are for one version. The control is mounted with `key={versionUid}`,
 * so an answer that arrives for another version finds no observer.
 */

import { useMutation } from '@tanstack/react-query';
import { useRef, useState } from 'react';

import type { RunCostEstimate, RunStatus, VersionUid } from '@/shared/api';
import { estimateRunCost, newIdempotencyKey } from '@/shared/api';
import type { IntentRecord } from '@/shared/lib';
import { resolveIntentKey } from '@/shared/lib';

import {
  automaticConsent, chargesMoney, comparisonOnlyRefusal, dialogConsent, estimateAnswers, estimateChanged,
  estimateRequest, initialCeiling,
} from './one-click-start';
import type { RunCostConsent, StartRunCommand } from './start-run-intent';
import { startRunIntent } from './start-run-intent';
import { useStartRun } from './use-start-run';

/** What the dialog shows: the estimate asked about, the kind of start, and the ceiling being typed. */
export interface RunCostDialog {
  readonly estimate: RunCostEstimate;
  /** The start is «Без денежного потолка (сбор статистики)». */
  readonly relaxed: boolean;
  readonly ceiling: string;
  /** The server said that the estimate or its binding changed, and this is the new one. */
  readonly changed: boolean;
}

export function useRunCostApproval(versionUid: VersionUid, onStarted?: ((run: RunStatus) => void) | undefined) {
  const start = useStartRun();
  const [dialog, setDialog] = useState<RunCostDialog | null>(null);
  const held = useRef<IntentRecord | null>(null);
  const last = useRef<StartRunCommand | null>(null);

  const reading = useMutation<RunCostEstimate, unknown, { relaxed: boolean }>({
    mutationFn: async ({ relaxed }) => {
      const estimate = (await estimateRunCost({ body: estimateRequest(versionUid, relaxed) })).data;
      if (!estimateAnswers(estimate, versionUid, relaxed)) {
        throw new Error('Ответ оценки стоимости не соответствует этому запуску.');
      }
      return estimate;
    },
  });

  /** Sends `command` as it is: a first send and a retry are the same call under the same key. */
  function dispatch(command: StartRunCommand): void {
    const relaxed = command.relaxedLimits === true;
    start.mutate(command, {
      onSuccess: (run) => {
        setDialog(null);
        onStarted?.(run);
      },
      onError: (error) => {
        setDialog(null);
        // The answer to a changed estimate is a new estimate, shown. Anything else stays beside the button.
        if (estimateChanged(error)) estimate(relaxed, true);
      },
    });
  }

  function send(consent: RunCostConsent, relaxed: boolean): void {
    const intent = startRunIntent(versionUid, null, null, relaxed, consent);
    held.current = resolveIntentKey(held.current, intent.signature, newIdempotencyKey);
    const command = intent.command(held.current.idempotencyKey);
    last.current = command;
    dispatch(command);
  }

  function estimate(relaxed: boolean, changed: boolean): void {
    reading.reset();
    reading.mutate({ relaxed }, {
      onSuccess: (value) => {
        // After a changed answer the person always sees the new figure, even when it charges nothing.
        if (!changed && !chargesMoney(value)) send(automaticConsent(value, relaxed), relaxed);
        else setDialog({ estimate: value, relaxed, ceiling: initialCeiling(value, relaxed), changed });
      },
    });
  }

  const busy = reading.isPending || start.isPending;
  // A version this server does not analyse as a section is refused again by every estimate: no repeat request.
  const comparisonOnly = comparisonOnlyRefusal(reading.error);

  return {
    dialog,
    busy,
    estimating: reading.isPending,
    starting: start.isPending,
    /** The estimate could not be read or did not fit this start; nothing was sent. */
    estimateError: reading.error ?? null,
    comparisonOnly,
    /** The refusal of the last send, unless it was the answer that sent the person back to an estimate. */
    startError: estimateChanged(start.error) ? null : (start.error ?? null),
    /** The one click: `relaxed` is «Без денежного потолка (сбор статистики)». */
    start: (relaxed = false): void => {
      if (busy || comparisonOnly) return;
      start.reset();
      setDialog(null);
      estimate(relaxed, false);
    },
    /** The dialog's «Запустить». */
    confirm: (): void => {
      if (dialog === null || busy) return;
      const consent = dialogConsent(dialog.estimate, dialog.relaxed, dialog.ceiling);
      if (consent !== null) send(consent, dialog.relaxed);
    },
    /** The dialog's «Отмена»: nothing is sent and nothing is kept. */
    cancel: (): void => {
      if (!busy) setDialog(null);
    },
    setCeiling: (ceiling: string): void => setDialog((previous) => previous === null ? null : { ...previous, ceiling }),
    /** The retry beside a refusal: the same command under the same key, not a new estimate. */
    retry: (): void => {
      if (last.current !== null && !busy) dispatch(last.current);
    },
  };
}

export type RunCostApproval = ReturnType<typeof useRunCostApproval>;
