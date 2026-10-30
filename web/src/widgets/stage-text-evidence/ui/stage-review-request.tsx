'use client';

import { useQueryClient } from '@tanstack/react-query';
import { useRef, useState } from 'react';

import type { StageChangeCard } from '@/shared/api';
import { createStageReviewCard, failureMessage, newIdempotencyKey } from '@/shared/api';
import { resolveIntentKey } from '@/shared/lib';
import type { IntentRecord } from '@/shared/lib';
import { ErrorState } from '@/shared/ui';

import { REVIEW_SOURCE_LIMIT, reviewRequest } from '../model/review-request';
import styles from './stage-text-evidence.module.css';

export interface StageReviewRequestProps {
  readonly runId: string;
  readonly sourceIds: readonly string[];
  readonly mayAct: boolean;
  readonly label: string;
  readonly onCreated?: (card: StageChangeCard) => void;
}

export function StageReviewRequest(props: StageReviewRequestProps) {
  return <ReviewRequestBody key={`${props.runId}|${props.sourceIds.join('|')}`} {...props} />;
}

function ReviewRequestBody({ runId, sourceIds, mayAct, label, onCreated }: StageReviewRequestProps) {
  const cache = useQueryClient();
  const [open, setOpen] = useState(false);
  const [reason, setReason] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const [created, setCreated] = useState<StageChangeCard | null>(null);
  const held = useRef<IntentRecord | null>(null);
  const body = reviewRequest(sourceIds, reason);
  const submit = async () => {
    if (!mayAct || busy || body === null) return;
    const intent = resolveIntentKey(held.current, JSON.stringify([runId, body]), newIdempotencyKey);
    held.current = intent; setBusy(true); setError(null);
    try {
      const result = (await createStageReviewCard({ path: { stage_chain_run_id: runId }, body, idempotencyKey: intent.idempotencyKey })).data;
      if (result.run_id !== runId || result.class_name !== 'REVIEW') throw new Error('Ответ не содержит карточку проверки выбранного запуска.');
      held.current = null; setCreated(result); setOpen(false); setReason('');
      await Promise.all([
        cache.invalidateQueries({ queryKey: ['stage-changes', runId] }),
        cache.invalidateQueries({ queryKey: ['stage-journal', runId] }),
        cache.invalidateQueries({ queryKey: ['stage-run-card-counts', runId] }),
      ]);
      onCreated?.(result);
    } catch (failure) { setError(failure); }
    finally { setBusy(false); }
  };
  const failure = error === null ? null : failureMessage(error);
  if (!mayAct) return null;
  return <div className={styles.reviewRequest}>
    <button type="button" className="am-button" disabled={busy || sourceIds.length === 0}
      onClick={() => { setOpen(true); setCreated(null); setError(null); }}>{label}</button>
    {open ? <section role="group" aria-label="Экспертная проверка свидетельств" data-stage-review-request="">
      <p>Будет создана отдельная карточка проверки. Исходные свидетельства сохранятся.</p>
      <label>Причина экспертной проверки<textarea value={reason} required maxLength={2000}
        aria-invalid={reason.trim() === ''} disabled={busy} onChange={(event) => setReason(event.target.value)} /></label>
      {sourceIds.length > REVIEW_SOURCE_LIMIT ? <p role="alert">Свидетельств больше допустимого объёма одной карточки проверки.</p> : null}
      <div className={styles.actions}>
        <button type="button" className="am-button" disabled={busy || body === null} onClick={() => void submit()}>Создать карточку проверки</button>
        <button type="button" className="am-button" disabled={busy} onClick={() => setOpen(false)}>Отмена</button>
      </div>
    </section> : null}
    {failure === null ? null : <ErrorState title="Карточка проверки не создана" detail={failure.detail} correlationId={failure.correlationId} />}
    {created === null ? null : <p role="status" data-stage-review-created={created.card_id}>Карточка проверки создана.</p>}
  </div>;
}
