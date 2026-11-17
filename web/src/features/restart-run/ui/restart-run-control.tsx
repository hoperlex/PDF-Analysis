'use client';

/**
 * `RUN-RESTART-01` / `R-155a`: «Перезапустить с этого этапа» in the dialog «Этапы анализа раздела», one button for each of the eight chips.
 *
 * It restarts an ENDED run (`partial`, `failed`, `cancelled`) from the chip the dialog shows: a NEW run of the same version is created with
 * every setting of this one, the chips before the chosen one are taken ready from it, the chosen one and the later ones are computed; when
 * the new run publishes the old one is deleted and the expert's decisions move to the findings that repeat verbatim. The button opens the
 * confirmation in place (`RestartRunConfirm`): a fresh reading of what the computed chips cost, bound to this run and the chip, and the
 * person's consent to it; one command goes under one idempotency key and the page moves to the new run. A refusal is shown as the server
 * gave it, in a sentence, and nothing is started in its place. Anyone but an expert or an administrator, and every run that has not ended
 * or has been replaced already, sees nothing here.
 */

import { useRouter } from 'next/navigation';
import { useState } from 'react';

import type { RestartPoint, RunStatus } from '@/shared/api';
import { ApiError, newIdempotencyKey } from '@/shared/api';
import { routes } from '@/shared/lib';
import { CostApproval } from '@/shared/ui';
import { useMe } from '@/entities/account';

import { mayRestart, restartableRun } from '../model/points';
import { restartFailureText } from '../model/refusals';
import { useRestartCostApproval } from '../model/use-restart-cost-approval';
import { useRestartRun } from '../model/use-restart-run';

import { RestartRunConfirm } from './restart-run-confirm';

/** The offer button's words. */
export const RESTART_OFFER = 'Перезапустить с этого этапа';

const STALE = 'Оценка стоимости устарела. Показана новая: подтвердите её снова.';

export interface RestartRunControlProps {
  /** The run to restart, as the screen reads it (`runId`, its state, and whether a restart has replaced it already). */
  readonly run: Pick<RunStatus, 'run_id' | 'state' | 'replaced_by_run_id'>;
  /** The chip the dialog shows. */
  readonly point: RestartPoint;
}

export function RestartRunControl({ run, point }: RestartRunControlProps) {
  const me = useMe();
  const router = useRouter();
  const [key, setKey] = useState<string | null>(null);
  const [failure, setFailure] = useState<string | null>(null);
  const restart = useRestartRun();
  const open = key !== null;
  const cost = useRestartCostApproval(open ? run.run_id : null, open ? point : null, key);

  if (!mayRestart(me.data?.roles) || !restartableRun(run)) return null;

  function close() {
    setKey(null);
    setFailure(null);
    cost.clear();
  }

  async function send() {
    if (cost.consent === undefined || cost.pending) return;
    setFailure(null);
    try {
      const created = await restart.mutateAsync({
        runId: run.run_id, point, idempotencyKey: cost.idempotencyKey, costConsent: cost.consent,
      });
      close();
      router.push(routes.run(created.project_uid, created.run_id));
    } catch (error) {
      if (error instanceof ApiError && error.details.conflict_reason === 'run_cost_estimate_stale') {
        cost.refresh();
        setFailure(STALE);
        return;
      }
      setFailure(restartFailureText(error, true));
    }
  }

  if (!open) {
    return (
      <button type="button" className="am-button am-button--quiet" data-run-restart="offer" onClick={() => setKey(newIdempotencyKey())}>
        {RESTART_OFFER}
      </button>
    );
  }

  const estimate = cost.estimate;
  return (
    <RestartRunConfirm
      point={point}
      taken={cost.taken}
      computed={cost.computed}
      loading={cost.pending}
      cost={estimate === null ? null : (
        <CostApproval estimate={estimate} ceiling={cost.ceiling} approved={cost.approved}
          disabled={restart.isPending || cost.pending} onCeilingChange={cost.setCeiling} onApprovedChange={cost.setApproved} />
      )}
      failure={failure ?? (cost.error === null ? null : restartFailureText(cost.error, false))}
      sending={restart.isPending}
      canSend={cost.consent !== undefined}
      onSend={() => void send()}
      onCancel={close}
    />
  );
}
