'use client';

import { useQuery } from '@tanstack/react-query';
import { useEffect, useRef, useState } from 'react';
import type { ReactNode } from 'react';

import type { ComparisonAiEstimate, StageChainBatch, StageChainBatchSelection, StagePair } from '@/shared/api';
import { ApiError, cancelStageChainBatch, estimateStageChainRun, failureMessage, getStageChainBatch,
  getStageSheetMap, newIdempotencyKey, pauseStageChainBatch, resumeStageChainBatch, startStageChainBatch } from '@/shared/api';
import { STAGE_REVIEW_POLL_MS } from '@/shared/config';
import { documentCaption, useStageDocumentNames, useStagePairs } from '@/entities/stage-pair';
import { agreementStands, comparisonFailure, consentOf, isBlocked } from '@/entities/version-series';
import { formatInstant } from '@/shared/lib';
import { ErrorState } from '@/shared/ui';
import { StageEngineSelector } from '@/widgets/stage-v3-experimental';
import type { StageEngine } from '@/widgets/stage-v3-experimental';

import { IntentKey, RUN_WORDS } from '../model/runs';
import { StageEstimateConsent } from './estimate-consent';
import styles from './stage-run-controls.module.css';

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
  /**
   * What stands at the left of the line over the table (`UIP-S16-03`): the catalog's counters. The batch's button stands at its
   * right, and the estimate and the consent open under the line, so the line and what it opens are one piece of the screen.
   */
  readonly summary?: ReactNode;
  /** Buttons of the catalog that stand before «Запустить анализ выбранных (N)» in that line. */
  readonly leadingActions?: ReactNode;
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

function StageBatchBody({ projectUid, selectedPairs, mayAct, onOpenRun, batchId: suppliedBatchId, onBatchChange, summary, leadingActions }: StageBatchControlsProps) {
  // `UI-B-85`: a pair is named by its documents (the reads are the catalog's own), and by its identifier only while they are unknown.
  const documentNames = useStageDocumentNames(projectUid).data;
  const knownPairs = useStagePairs(projectUid).data?.items ?? [];
  const pairLabel = (pairId: string): string => {
    const known = [...selectedPairs, ...knownPairs].find((item) => item.pair_id === pairId);
    return known === undefined ? pairId
      : `${documentCaption(documentNames, known.left_document_uid)} → ${known.right_document_uid === undefined ? 'сборка Р' : documentCaption(documentNames, known.right_document_uid)}`;
  };
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
  // A reading of the estimate that failed belongs to the panel that asked for it: once the panel is closed it is not said again.
  const failure = error ?? (preparing ? prepared.error : null) ?? status.error;
  const missingMap = preparing && prepared.error === failure && failure instanceof MissingStageMap;
  const message = failure === null ? null : missingMap
    ? { detail: 'Для выбранной пары нет сохранённой карты листов. Откройте «2. Сопоставление листов» и нажмите «Сохранить решение эксперта», затем подготовьте запуск снова.', correlationId: failure.correlationId }
    : failureMessage(failure);
  // The options change what is estimated, so a changed option clears the agreements and the held keys and reads the estimate again.
  const optionsChanged = () => { setAgreed({}); setError(null); held.current.clear(); };
  const panelOpen = preparing || batch !== null || message !== null;
  return <>
    <div className={styles.bar} data-pair-toolbar="">
      {summary}
      {mayAct || leadingActions !== undefined ? <div className={styles.actions}>
        {leadingActions}
        {mayAct ? <button type="button" className="am-button" data-batch-launch="" aria-expanded={preparing} disabled={busy || selectedPairs.length === 0 || selectedPairs.length > 100}
          onClick={() => { setPreparing(true); setAgreed({}); setError(null); void prepared.refetch(); }}>Запустить анализ выбранных ({selectedPairs.length})</button> : null}
      </div> : null}
    </div>
    {selectedPairs.length > 100 ? <p role="alert">Выберите не более 100 пар.</p> : null}
    {panelOpen ? <section className={styles.batch} aria-label="Очередь сравнения стадий">
      <h3>Сравнить выбранные пары</h3>
      {preparing ? <p>Выбрано: {selectedPairs.length}. Пары выполнятся по очереди.</p> : null}
      {preparing && mayAct ? <div className={styles.actions}>
        <StageEngineSelector value={engine} disabled={busy} onChange={(value) => { setEngine(value); if (value === 'v3_native_text_experimental') setWithAi(true); optionsChanged(); }} />
        <label><input type="checkbox" checked={withAi} disabled={busy || engine === 'v3_native_text_experimental'} onChange={(event) => { setWithAi(event.target.checked); optionsChanged(); }} />С описанием изменений ИИ</label>
      </div> : null}
      {preparing ? <div>
        {prepared.isFetching ? <p role="status">Читаем карты и оцениваем объём…</p> : null}
        {prepared.data?.map((item) => <div key={item.pair.pair_id} className={styles.selection}>
          <p>Пара {pairLabel(item.pair.pair_id)}</p>
          {item.estimate === undefined ? <p>Без обращений к ИИ.</p> : <StageEstimateConsent estimate={item.estimate} engine={engine}
            agreedDigest={agreed[item.pair.pair_id] ?? null} disabled={busy || !mayAct}
            onAgree={(digest) => setAgreed((prior) => ({ ...prior, [item.pair.pair_id]: digest }))} />}
        </div>)}
        <div className={styles.actions}><button type="button" className="am-button" disabled={busy || !mayAct || !canStart || prepared.isFetching}
          onClick={() => void start()}>Поставить в очередь</button>
          <button type="button" className="am-button" disabled={busy} onClick={() => { setPreparing(false); setError(null); }}>Отмена</button></div>
      </div> : null}
      {message === null ? null : <ErrorState title={missingMap ? 'Сначала сохраните карту листов' : 'Очередь не открыта или команда не выполнена'} detail={message.detail} correlationId={message.correlationId} />}
      {batch === null ? null : <div>
        <p>{RUN_WORDS[batch.state]} · {formatInstant(batch.created_at)}</p>
        <dl>{Object.entries(batch.counts).map(([name, count]) => <div key={name}><dt>{name}</dt><dd>{count}</dd></div>)}</dl>
        <ol>{batch.items.map((item) => <li key={item.item_id}>{pairLabel(item.pair_id)} · {RUN_WORDS[item.state]}
          {item.run_id === undefined || onOpenRun === undefined ? null : <button type="button" className="am-button" onClick={() => onOpenRun(item.run_id!, item.pair_id)}>Открыть сравнение</button>}</li>)}</ol>
        {mayAct ? <div className={styles.actions}>
          {batch.state === 'queued' || batch.state === 'running' ? <button type="button" className="am-button" disabled={busy} onClick={() => void change('pause')}>Остановить очередь</button> : null}
          {batch.state === 'paused' ? <button type="button" className="am-button" disabled={busy} onClick={() => void change('resume')}>Продолжить очередь</button> : null}
          {['queued', 'running', 'paused'].includes(batch.state) ? <button type="button" className="am-button" disabled={busy} onClick={() => void change('cancel')}>Отменить очередь</button> : null}
        </div> : null}
      </div>}
    </section> : null}
  </>;
}
