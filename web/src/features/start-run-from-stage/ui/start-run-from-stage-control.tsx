'use client';

/**
 * `UI-A-60` / `R-151i`: «Запустить с этапа» on the run page, beside «Отменить прогон», as the original's dialog of the same name.
 *
 * It starts a NEW run of this run's document version that takes the results of the stages before the chosen one from this
 * run and computes the chosen one and the rest; this run stays as it is. The dialog asks for the stage, then for a fresh
 * reading of what the remaining stages cost (bound to this run and the stage) and for the person's consent to it, and
 * sends one command under one idempotency key. A refusal of the reuse is shown as the server gave it -- which stage cannot be
 * taken and why -- and nothing is started in its place. The control is offered for an ended run of the standard analysis to
 * an expert or an administrator; anyone else, and every run that is still going, sees nothing here.
 */

import { useQuery } from '@tanstack/react-query';
import { useRouter } from 'next/navigation';
import { useId, useState } from 'react';

import type { RunId, StageId } from '@/shared/api';
import { ApiError, newIdempotencyKey } from '@/shared/api';
import { routes } from '@/shared/lib';
import { CostApproval, runStageLabel } from '@/shared/ui';
import { useMe } from '@/entities/account';
import { runStatusQueryOptions } from '@/entities/audit-run';
import { executionFailure } from '@/entities/execution';

import { STARTABLE_STAGE_IDS, mayStartFromStage, reuseRefusal, startStageOption, startableState } from '../model/stages';
import { useStartFromStageCostApproval } from '../model/use-start-from-stage-cost-approval';
import { useStartRunFromStage } from '../model/use-start-run-from-stage';

type Choice = { readonly stageId: StageId; readonly key: string };

const names = (ids: readonly StageId[]): string => ids.map((id) => `«${runStageLabel(id)}»`).join(', ');

export interface StartRunFromStageControlProps {
  readonly runId: string;
  /**
   * `RUN-SCREEN-01a`: the dialog «Этапы анализа раздела» offers the start from the stage it shows, so it narrows the choice to
   * that stage's startable ids. With one id left the stage is already chosen and no select is drawn; with several the select
   * offers only them. Absent: every startable stage, as the control has always offered.
   */
  readonly stageIds?: readonly StageId[] | undefined;
  /** The offer button's words; absent: «Запустить с этапа». */
  readonly label?: string | undefined;
}

export function StartRunFromStageControl({ runId, stageIds, label }: StartRunFromStageControlProps) {
  const me = useMe();
  const run = useQuery(runStatusQueryOptions(runId as RunId));
  const router = useRouter();
  const selectId = useId();
  const [open, setOpen] = useState(false);
  const [choice, setChoice] = useState<Choice | null>(null);
  const [failure, setFailure] = useState<string | null>(null);
  const start = useStartRunFromStage();
  const cost = useStartFromStageCostApproval(open ? runId : null, choice?.stageId ?? null, choice?.key ?? null);

  const offered = stageIds === undefined ? STARTABLE_STAGE_IDS : STARTABLE_STAGE_IDS.filter((id) => stageIds.includes(id));
  const eligible = offered.length > 0 && mayStartFromStage(me.data?.roles) && startableState(run.data?.state) && run.data?.analysis_kind !== 'ar_v3_beta';
  if (!eligible) return null;
  const onlyStage = offered.length === 1 ? (offered[0] as StageId) : null;

  function close() {
    setOpen(false);
    setChoice(null);
    setFailure(null);
    cost.clear();
  }

  function choose(value: string) {
    const stageId = offered.find((id) => id === value);
    setFailure(null);
    setChoice(stageId === undefined ? null : { stageId, key: newIdempotencyKey() });
  }

  async function send() {
    if (choice === null || cost.consent === undefined || cost.pending) return;
    try {
      const created = await start.mutateAsync({
        runId, stageId: choice.stageId, idempotencyKey: cost.idempotencyKey, costConsent: cost.consent,
      });
      close();
      router.push(routes.run(created.project_uid, created.run_id));
    } catch (error) {
      if (error instanceof ApiError && error.details.conflict_reason === 'run_cost_estimate_stale') {
        cost.clear();
        setFailure('Оценка стоимости устарела. Получите новую оценку и подтвердите лимит снова.');
        return;
      }
      setFailure(reuseRefusal(error) ?? executionFailure(error, true).detail);
    }
  }

  if (!open) {
    return (
      <button
        type="button"
        className="am-button am-button--quiet"
        data-run-start-from-stage="offer"
        onClick={() => {
          setOpen(true);
          if (onlyStage !== null) setChoice({ stageId: onlyStage, key: newIdempotencyKey() });
        }}
      >
        {label ?? 'Запустить с этапа'}
      </button>
    );
  }

  const estimateRefusal = cost.error === null ? null : (reuseRefusal(cost.error) ?? executionFailure(cost.error, false).detail);
  const estimate = cost.estimate;
  return (
    <section className="am-form__field" role="group" aria-label="Запуск с этапа" data-run-start-from-stage="dialog">
      <p className="am-note">
        Будет создан новый прогон этой версии: результаты этапов до выбранного берутся из этого прогона, выбранный этап и
        следующие выполняются заново. Этот прогон не меняется.
      </p>
      {onlyStage !== null ? (
        <p data-start-from-stage-only={onlyStage}>Этап: <strong>{startStageOption(onlyStage)}</strong></p>
      ) : (
        <div>
          <label htmlFor={selectId}>Этап</label>{' '}
          <select id={selectId} value={choice?.stageId ?? ''} disabled={start.isPending} onChange={(event) => choose(event.currentTarget.value)}>
            <option value="">Выберите этап</option>
            {offered.map((id) => <option key={id} value={id}>{startStageOption(id)}</option>)}
          </select>
        </div>
      )}
      {choice === null ? null : cost.pending ? <p className="am-note" role="status">Загрузка: оценка стоимости запуска с этапа</p> : null}
      {estimateRefusal === null ? null : <p className="am-note" role="alert" data-start-from-stage-refusal>{estimateRefusal}</p>}
      {estimate === null ? null : (
        <>
          <p data-start-from-stage-plan>
            {estimate.reused_stage_ids === undefined || estimate.reused_stage_ids.length === 0 ? null
              : <>Берутся из этого прогона: {names(estimate.reused_stage_ids)}. </>}
            {estimate.computed_stage_ids === undefined || estimate.computed_stage_ids.length === 0 ? null
              : <>Будут выполнены: {names(estimate.computed_stage_ids)}. Оценка и согласие — для них.</>}
          </p>
          <CostApproval estimate={estimate} ceiling={cost.ceiling} approved={cost.approved}
            disabled={start.isPending || cost.pending} onCeilingChange={cost.setCeiling} onApprovedChange={cost.setApproved} />
        </>
      )}
      {failure === null ? null : <p className="am-note" role="alert" data-start-from-stage-failure>Прогон не запущен: {failure}</p>}
      <div>
        <button type="button" className="am-button" disabled={start.isPending || cost.pending || cost.consent === undefined}
          onClick={() => void send()}>Запустить</button>{' '}
        {choice === null ? null : (
          <button type="button" className="am-button am-button--quiet" disabled={start.isPending || cost.pending}
            onClick={() => { setFailure(null); cost.refresh(); }}>Обновить оценку стоимости</button>
        )}{' '}
        <button type="button" className="am-button am-button--quiet" disabled={start.isPending} onClick={close}>Отмена</button>
      </div>
    </section>
  );
}
