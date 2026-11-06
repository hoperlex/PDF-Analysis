'use client';

import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useEffect, useRef, useState } from 'react';

import type { StageChainRun } from '@/shared/api';
import { ApiError, cancelStageChainRun, estimateStageChainRun, failureMessage, getStageChainRun,
  getStageSheetMap, listStageChangeCards, newIdempotencyKey, resumeStageChainRun, startStageChainRun } from '@/shared/api';
import { STAGE_REVIEW_POLL_MS } from '@/shared/config';
import { agreementStands, comparisonFailure, consentOf, isBlocked } from '@/entities/version-series';
import { formatInstant } from '@/shared/lib';
import { ErrorState, LoadingState } from '@/shared/ui';
import { StageEngineSelector, StageExperimentalProgress } from '@/widgets/stage-v3-experimental';
import type { StageEngine } from '@/widgets/stage-v3-experimental';

import { readRuns } from '../api/reads';
import { IntentKey, latestFullRun, RUN_WORDS, runActive, STAGE_RUN_KEYS } from '../model/runs';
import { StageEstimateConsent } from './estimate-consent';
import { StageRail } from './stage-rail';
import { StageRepairHistory } from './stage-repair-history';
import styles from './stage-run-controls.module.css';

export interface StageRunControlsProps {
  readonly pairId: string;
  readonly linkRevisionId?: string;
  readonly runId?: string;
  readonly mayAct: boolean;
  readonly compact?: boolean;
  /** Only what starts and continues a run: no summary, no rail. The catalog's row already says the rest. */
  readonly launcher?: boolean;
  readonly onRunChange?: (run: StageChainRun) => void;
  readonly onOpenBatch?: (batchId: string) => void;
}

export function StageRunControls(props: StageRunControlsProps) {
  return <StageRunBody key={`${props.pairId}|${props.linkRevisionId ?? ''}|${props.runId ?? ''}`} {...props} />;
}

function StageRunBody({ pairId, linkRevisionId, runId, mayAct, compact = false, launcher = false, onRunChange, onOpenBatch }: StageRunControlsProps) {
  const cache = useQueryClient();
  const map = useQuery({ queryKey: STAGE_RUN_KEYS.map(pairId),
    queryFn: async () => {
      try { return (await getStageSheetMap({ path: { stage_pair_id: pairId } })).data; }
      catch (failure) {
        if (failure instanceof ApiError && failure.status === 404) return null;
        throw failure;
      }
    },
    enabled: linkRevisionId === undefined, retry: false });
  const revisionId = linkRevisionId ?? map.data?.revision_id;
  const runs = useQuery({ queryKey: STAGE_RUN_KEYS.list(pairId), queryFn: () => readRuns(pairId),
    retry: false, refetchInterval: (query) => query.state.data?.some(runActive) ? STAGE_REVIEW_POLL_MS : false });
  const [startedId, setStartedId] = useState<string | null>(null);
  const selectedId = startedId ?? runId ?? latestFullRun(runs.data ?? [])?.run_id;
  const current = useQuery({ queryKey: STAGE_RUN_KEYS.run(selectedId ?? ''),
    queryFn: async () => (await getStageChainRun({ path: { stage_chain_run_id: selectedId! } })).data,
    enabled: selectedId !== undefined, retry: false,
    refetchInterval: (query) => runActive(query.state.data) ? STAGE_REVIEW_POLL_MS : false });
  const run = current.data ?? runs.data?.find((item) => item.run_id === selectedId);
  const counts = useQuery({ queryKey: ['stage-run-card-counts', selectedId],
    queryFn: async () => (await listStageChangeCards({ path: { stage_chain_run_id: selectedId! }, query: { limit: 1 } })).data.counts,
    enabled: selectedId !== undefined && run?.state === 'completed', retry: false });
  const [withAi, setWithAi] = useState(true);
  const [engine, setEngine] = useState<StageEngine>('classic');
  const [restart, setRestart] = useState(false);
  const [retryFailed, setRetryFailed] = useState(false);
  const [intent, setIntent] = useState<'start' | 'resume' | null>(null);
  const [agreedDigest, setAgreedDigest] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [commandError, setCommandError] = useState<unknown>(null);
  const held = useRef(new IntentKey(newIdempotencyKey));
  const estimateRevision = intent === 'resume' ? run?.effective_link_revision_id ?? run?.link_revision_id : revisionId;
  const needsAi = intent === 'resume' ? run?.with_ai === true || run?.engine === 'v3_native_text_experimental' : withAi || engine === 'v3_native_text_experimental';
  const estimateEngine = intent === 'resume' ? run?.engine ?? 'classic' : engine;
  const estimate = useQuery({ queryKey: ['stage-run-estimate', estimateRevision, estimateEngine, intent, intent === 'resume' ? run?.run_id : null],
    queryFn: async () => (await estimateStageChainRun({ path: { stage_link_revision_id: estimateRevision! },
      query: { engine: estimateEngine, ...(intent === 'resume' && run !== undefined ? { stage_chain_run_id: run.run_id } : {}) } })).data,
    enabled: intent !== null && needsAi && estimateRevision !== undefined, retry: false, staleTime: 0 });
  useEffect(() => {
    if (estimate.error !== null) { setAgreedDigest(null); held.current.clear(); }
  }, [estimate.error]);
  const callback = useRef(onRunChange);
  callback.current = onRunChange;
  useEffect(() => {
    if (current.data !== undefined && (startedId !== null || runId !== undefined)) callback.current?.(current.data);
  }, [current.data, startedId, runId]);

  const command = async (action: 'start' | 'resume' | 'cancel') => {
    if (!mayAct || busy || (action === 'start' && revisionId === undefined) || (action !== 'start' && run === undefined)) return;
    if (action !== 'cancel' && needsAi && (estimate.isFetching || estimate.error !== null || estimate.data === undefined || isBlocked(estimate.data) || !agreementStands(agreedDigest, estimate.data))) return;
    const consent = action !== 'cancel' && needsAi && estimate.data !== undefined ? consentOf(estimate.data) : undefined;
    const body = action === 'start' ? { link_revision_id: revisionId!, with_ai: withAi, engine, restart,
      ...(consent === undefined ? {} : { consent }) } : { retry_failed: retryFailed, ...(consent === undefined ? {} : { consent }) };
    const key = held.current.for([action, action === 'start' ? pairId : run!.run_id, action === 'cancel' ? null : body]);
    setBusy(true); setCommandError(null);
    try {
      const result = action === 'start'
        ? await startStageChainRun({ path: { stage_pair_id: pairId }, body: { link_revision_id: revisionId!, with_ai: withAi, engine, restart,
          ...(consent === undefined ? {} : { consent }) }, idempotencyKey: key })
        : action === 'resume'
          ? await resumeStageChainRun({ path: { stage_chain_run_id: run!.run_id }, body: { retry_failed: retryFailed,
            ...(consent === undefined ? {} : { consent }) }, idempotencyKey: key })
          : await cancelStageChainRun({ path: { stage_chain_run_id: run!.run_id }, idempotencyKey: key });
      held.current.clear(); setStartedId(result.data.run_id); setIntent(null); setAgreedDigest(null);
      cache.setQueryData(STAGE_RUN_KEYS.run(result.data.run_id), result.data);
      await cache.invalidateQueries({ queryKey: STAGE_RUN_KEYS.list(pairId) });
      callback.current?.(result.data);
    } catch (error) {
      setCommandError(error);
      if (comparisonFailure(error).estimateStale) { setAgreedDigest(null); void estimate.refetch(); }
    } finally { setBusy(false); }
  };
  const failure = commandError ?? current.error ?? runs.error ?? map.error ?? estimate.error ?? counts.error;
  const message = failure === null ? null : failureMessage(failure);
  const sameActive = runActive(run) && run?.link_revision_id === revisionId;
  const openIntent = (next: 'start' | 'resume') => { setIntent(next); setAgreedDigest(null); setCommandError(null); };
  const allowed = !needsAi || (!estimate.isFetching && estimate.error === null && estimate.data !== undefined && !isBlocked(estimate.data) && agreementStands(agreedDigest, estimate.data));
  const full = !compact && !launcher;
  const stopButton = mayAct && runActive(run)
    ? <button type="button" className="am-button" disabled={busy} onClick={() => void command('cancel')}>Остановить сравнение</button> : null;
  const resumeButton = mayAct && (run?.state === 'paused' || run?.state === 'failed')
    ? <button type="button" className="am-button" disabled={busy || intent !== null} onClick={() => openIntent('resume')}>Продолжить</button> : null;
  const refreshButton = <button type="button" className="am-button am-button--quiet" disabled={busy} onClick={() => { void runs.refetch(); if (selectedId !== undefined) void current.refetch(); if (linkRevisionId === undefined) void map.refetch(); }}>Обновить состояние</button>;
  return <section className={styles.controls} aria-label="Полное сравнение стадий">
    {run === undefined ? <p>Полное сравнение ещё не запускалось.</p> : <>
      {/* `UI-B-88`: the head of the rail — the run's state with «Остановить» and «Продолжить» beside it, as the original's «Остановить анализ» sits in the rail's head. */}
      <div className={styles.head}>
        <strong>{RUN_WORDS[run.state]}</strong><span>· {formatInstant(run.created_at)}</span>
        {full ? <><span className={styles.spacer} />{stopButton}{resumeButton}{refreshButton}</> : null}
      </div>
      {launcher ? null : <p>Метод: {run.engine === 'v3_native_text_experimental' ? 'V3 · эксперимент, только текст PDF' : 'Классическая цепочка'}{run.with_ai === false ? ' · без ИИ' : run.with_ai === true ? ' · с ИИ' : ''}</p>}
      {launcher ? null : <p>Изменений проектных решений: {counts.data?.project_changes ?? '—'} · Требуют проверки: {counts.data?.review ?? '—'}</p>}
      {launcher ? null : run.engine === 'v3_native_text_experimental' ? <StageExperimentalProgress progress={run.experimental_progress} state={run.state} /> : full ? <StageRail run={run} /> : <p>Шаги: {run.steps.filter((step) => step.state === 'completed').length} / {run.steps.length}</p>}
      {run.stale ? <p role="status">{mayAct ? 'Результат устарел. Запустите сравнение для текущей карты связей.' : 'Есть новые документы или изменены связи — сравнение ещё не обновлено. Обновит его эксперт.'}</p> : null}
      {run.pause_reason === undefined ? null : <p>Причина остановки: {run.pause_reason}</p>}
      {run.failure_reason === undefined ? null : <p role="alert">{run.failure_reason}</p>}
      {!launcher && onRunChange !== undefined ? <button type="button" className="am-button" onClick={() => onRunChange(run)}>Открыть результат</button> : null}
      {launcher || run.batch_id === undefined || onOpenBatch === undefined ? null : <button type="button" className="am-button" onClick={() => onOpenBatch(run.batch_id!)}>Открыть очередь</button>}
    </>}
    {map.isPending && linkRevisionId === undefined ? <LoadingState what="карту связей" /> : null}
    {linkRevisionId === undefined && map.isSuccess && map.data === null
      ? <p role="status">Сначала откройте «2. Сопоставление листов» и нажмите «Сохранить решение эксперта». После этого сравнение можно запустить.</p> : null}
    {message === null ? null : <ErrorState title="Сравнение не открыто или команда не выполнена" detail={message.detail} correlationId={message.correlationId} />}
    {full && run !== undefined ? null : refreshButton}
    {mayAct ? <div className={styles.actions}>
      <StageEngineSelector value={engine} disabled={busy || intent !== null} onChange={(value) => { setEngine(value); if (value === 'v3_native_text_experimental') setWithAi(true); setAgreedDigest(null); setIntent(null); setCommandError(null); held.current.clear(); }} />
      <label><input type="checkbox" checked={withAi} disabled={busy || intent !== null || engine === 'v3_native_text_experimental'} onChange={(event) => { setWithAi(event.target.checked); setAgreedDigest(null); held.current.clear(); }} />С описанием изменений ИИ</label>
      <label><input type="checkbox" checked={restart} disabled={busy} onChange={(event) => setRestart(event.target.checked)} />Пересчитать заново</label>
      <button type="button" className="am-button" disabled={busy || revisionId === undefined || sameActive || intent !== null}
        onClick={() => openIntent('start')}>Запустить полное сравнение</button>
      {full ? null : resumeButton}
      {full ? null : stopButton}
    </div> : null}
    {mayAct && intent !== null ? <div className={styles.estimate}>
      <h3>{intent === 'start' ? 'Запуск сравнения' : 'Продолжение сравнения'}</h3>
      {needsAi && estimate.isFetching ? <p role="status">Оцениваем объём…</p> : null}
      {needsAi && estimate.data !== undefined ? <StageEstimateConsent estimate={estimate.data} engine={estimateEngine} agreedDigest={agreedDigest} disabled={busy} onAgree={setAgreedDigest} /> : null}
      {!needsAi ? <p>Выполнятся детерминированные шаги без обращений к ИИ.</p> : null}
      {intent === 'resume' ? <label><input type="checkbox" checked={retryFailed} onChange={(event) => setRetryFailed(event.target.checked)} />Повторить шаги с ошибкой</label> : null}
      <div className={styles.actions}><button type="button" className="am-button" disabled={busy || !allowed} onClick={() => void command(intent)}>Подтвердить</button>
        <button type="button" className="am-button" disabled={busy} onClick={() => setIntent(null)}>Отмена</button></div>
    </div> : null}
    {full && run !== undefined && run.engine !== 'v3_native_text_experimental' ? <StageRepairHistory run={run} mayAct={mayAct} /> : null}
  </section>;
}
