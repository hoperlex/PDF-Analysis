'use client';

import { useQuery } from '@tanstack/react-query';
import { useEffect, useRef, useState } from 'react';

import type { ComparisonAiEstimate, StageChainBatch, StageChainBatchSelection, StagePair } from '@/shared/api';
import { ApiError, cancelStageChainBatch, estimateStageChainRun, failureMessage, getStageChainBatch,
  getStageSheetMap, newIdempotencyKey, pauseStageChainBatch, resumeStageChainBatch, startStageChainBatch } from '@/shared/api';
import { agreementStands, comparisonFailure, consentOf, isBlocked } from '@/entities/version-series';
import { formatInstant } from '@/shared/lib';
import { ErrorState } from '@/shared/ui';
import { StageEngineSelector } from '@/widgets/stage-v3-experimental';
import type { StageEngine } from '@/widgets/stage-v3-experimental';

import { IntentKey, RUN_WORDS } from '../model/runs';
import { StageEstimateConsent } from './estimate-consent';
import styles from './stage-run-controls.module.css';

export const STAGE_REVIEW_POLL_MS = 1500;

interface PreparedPair { pair: StagePair; revisionId: string; estimate?: ComparisonAiEstimate }
class MissingStageMap extends Error {
  constructor(readonly correlationId: string | null) { super('Stage pair has no saved sheet map.'); }
}
export interface StageBatchControlsProps {
  readonly projectUid: string;
  readonly selectedPairs: readonly StagePair[];
  readonly mayAct: boolean;
  readonly batchId?: string;
  readonly onBatchChange?: (batchId: string) => void;
  readonly onOpenRun?: (runId: string, pairId: string) => void;
}

async function preparePairs(pairs: readonly StagePair[], withAi: boolean, engine: StageEngine): Promise<PreparedPair[]> {
  return Promise.all(pairs.map(async (pair) => {
    const map = await getStageSheetMap({ path: { stage_pair_id: pair.pair_id } }).then((response) => response.data,
      (failure: unknown) => {
        if (failure instanceof ApiError && failure.status === 404) throw new MissingStageMap(failure.correlationId);
        throw failure;
      });
    const estimate = withAi ? (await estimateStageChainRun({ path: { stage_link_revision_id: map.revision_id }, query: { engine } })).data : undefined;
    return { pair, revisionId: map.revision_id, ...(estimate === undefined ? {} : { estimate }) };
  }));
}

export function StageBatchControls(props: StageBatchControlsProps) {
  return <StageBatchBody key={`${props.projectUid}|${props.batchId ?? ''}`} {...props} />;
}

function StageBatchBody({ projectUid, selectedPairs, mayAct, onOpenRun, batchId: suppliedBatchId, onBatchChange }: StageBatchControlsProps) {
  const [withAi, setWithAi] = useState(true);
  const [engine, setEngine] = useState<StageEngine>('classic');
  const [preparing, setPreparing] = useState(false);
  const [agreed, setAgreed] = useState<Record<string, string | null>>({});
  const [batchId, setBatchId] = useState<string | null>(suppliedBatchId ?? null);
  const [started, setStarted] = useState<StageChainBatch | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const held = useRef(new IntentKey(newIdempotencyKey));
  const selectionIds = selectedPairs.map((pair) => pair.pair_id).sort();
  const prepared = useQuery({ queryKey: ['stage-batch-prepare', projectUid, selectionIds, withAi, engine],
    queryFn: () => preparePairs(selectedPairs, withAi, engine), enabled: preparing && selectedPairs.length > 0, retry: false, staleTime: 0 });
  useEffect(() => {
    if (prepared.error !== null) { setAgreed({}); held.current.clear(); }
  }, [prepared.error]);
  const status = useQuery({ queryKey: ['stage-batch', batchId],
    queryFn: async () => (await getStageChainBatch({ path: { stage_chain_batch_id: batchId! } })).data,
    enabled: batchId !== null, retry: false,
    refetchInterval: (query) => query.state.data !== undefined && (['queued', 'running'].includes(query.state.data.state) || query.state.data.items.some((item) => item.state === 'running')) ? STAGE_REVIEW_POLL_MS : false });
  const batch = status.data ?? started;
  const canStart = prepared.error === null && !prepared.isFetching && prepared.data !== undefined && prepared.data.length === selectedPairs.length &&
    prepared.data.every((item) => !withAi || (item.estimate !== undefined && !isBlocked(item.estimate) && agreementStands(agreed[item.pair.pair_id] ?? null, item.estimate)));
  const start = async () => {
    if (!mayAct || busy || !canStart || prepared.data === undefined || selectedPairs.length > 100) return;
    const selections: StageChainBatchSelection[] = prepared.data.map((item) => ({ pair_id: item.pair.pair_id,
      link_revision_id: item.revisionId, ...(withAi && item.estimate !== undefined ? { consent: consentOf(item.estimate) } : {}) }));
    const body = { selections, with_ai: withAi, engine };
    setBusy(true); setError(null);
    try {
      const result = await startStageChainBatch({ path: { project_uid: projectUid }, body, idempotencyKey: held.current.for(['start', projectUid, body]) });
      held.current.clear(); setBatchId(result.data.batch_id); setStarted(result.data); setPreparing(false); setAgreed({});
      onBatchChange?.(result.data.batch_id);
    } catch (failure) {
      setError(failure);
      if (comparisonFailure(failure).estimateStale) { setAgreed({}); void prepared.refetch(); }
    } finally { setBusy(false); }
  };
  const change = async (action: 'pause' | 'resume' | 'cancel') => {
    if (batch === null || !mayAct || busy) return;
    setBusy(true); setError(null);
    const input = { path: { stage_chain_batch_id: batch.batch_id }, idempotencyKey: held.current.for([action, batch.batch_id]) };
    try {
      const result = action === 'pause' ? await pauseStageChainBatch(input) : action === 'resume' ? await resumeStageChainBatch(input) : await cancelStageChainBatch(input);
      held.current.clear(); setStarted(result.data); await status.refetch();
    } catch (failure) { setError(failure); }
    finally { setBusy(false); }
  };
  const failure = error ?? prepared.error ?? status.error;
  const missingMap = prepared.error === failure && failure instanceof MissingStageMap;
  const message = failure === null ? null : missingMap
    ? { detail: 'Для выбранной пары нет сохранённой карты листов. Откройте «2. Сопоставление листов» и нажмите «Сохранить решение эксперта», затем подготовьте запуск снова.', correlationId: failure.correlationId }
    : failureMessage(failure);
  return <section className={styles.batch} aria-label="Очередь сравнения стадий">
    <h3>Сравнить выбранные пары</h3>
    <p>Выбрано: {selectedPairs.length}. Пары выполнятся по очереди.</p>
    {mayAct ? <div className={styles.actions}>
      <StageEngineSelector value={engine} disabled={busy} onChange={(value) => { setEngine(value); if (value === 'v3_native_text_experimental') setWithAi(true); setAgreed({}); setPreparing(false); setError(null); held.current.clear(); }} />
      <label><input type="checkbox" checked={withAi} disabled={busy || engine === 'v3_native_text_experimental'} onChange={(event) => { setWithAi(event.target.checked); setAgreed({}); setPreparing(false); held.current.clear(); }} />С описанием изменений ИИ</label>
      <button type="button" className="am-button" disabled={busy || selectedPairs.length === 0 || selectedPairs.length > 100}
        onClick={() => { setPreparing(true); setAgreed({}); setError(null); void prepared.refetch(); }}>Подготовить запуск</button>
    </div> : null}
    {selectedPairs.length > 100 ? <p role="alert">Выберите не более 100 пар.</p> : null}
    {preparing ? <div>
      {prepared.isFetching ? <p role="status">Читаем карты и оцениваем объём…</p> : null}
      {prepared.data?.map((item) => <div key={item.pair.pair_id} className={styles.selection}>
        <p>Пара <code>{item.pair.pair_id}</code></p>
        {item.estimate === undefined ? <p>Без обращений к ИИ.</p> : <StageEstimateConsent estimate={item.estimate} engine={engine}
          agreedDigest={agreed[item.pair.pair_id] ?? null} disabled={busy || !mayAct}
          onAgree={(digest) => setAgreed((prior) => ({ ...prior, [item.pair.pair_id]: digest }))} />}
      </div>)}
      <div className={styles.actions}><button type="button" className="am-button" disabled={busy || !mayAct || !canStart || prepared.isFetching}
        onClick={() => void start()}>Поставить в очередь</button>
        <button type="button" className="am-button" disabled={busy} onClick={() => setPreparing(false)}>Отмена</button></div>
    </div> : null}
    {message === null ? null : <ErrorState title={missingMap ? 'Сначала сохраните карту листов' : 'Очередь не открыта или команда не выполнена'} detail={message.detail} correlationId={message.correlationId} />}
    {batch === null ? null : <div>
      <p>{RUN_WORDS[batch.state]} · {formatInstant(batch.created_at)}</p>
      <dl>{Object.entries(batch.counts).map(([name, count]) => <div key={name}><dt>{name}</dt><dd>{count}</dd></div>)}</dl>
      <ol>{batch.items.map((item) => <li key={item.item_id}><code>{item.pair_id}</code> · {RUN_WORDS[item.state]}
        {item.run_id === undefined || onOpenRun === undefined ? null : <button type="button" className="am-button" onClick={() => onOpenRun(item.run_id!, item.pair_id)}>Открыть сравнение</button>}</li>)}</ol>
      {mayAct ? <div className={styles.actions}>
        {batch.state === 'queued' || batch.state === 'running' ? <button type="button" className="am-button" disabled={busy} onClick={() => void change('pause')}>Остановить очередь</button> : null}
        {batch.state === 'paused' ? <button type="button" className="am-button" disabled={busy} onClick={() => void change('resume')}>Продолжить очередь</button> : null}
        {['queued', 'running', 'paused'].includes(batch.state) ? <button type="button" className="am-button" disabled={busy} onClick={() => void change('cancel')}>Отменить очередь</button> : null}
      </div> : null}
    </div>}
  </section>;
}
