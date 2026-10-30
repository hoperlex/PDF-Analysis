'use client';

import { useQuery } from '@tanstack/react-query';
import { useEffect, useRef, useState } from 'react';

import type { ComparisonBox, StageChainRun } from '@/shared/api';
import { failureMessage, getStageChainRun, newIdempotencyKey, recomputeStageTextEvidence } from '@/shared/api';
import { ErrorState } from '@/shared/ui';

import { fragmentBox, fragmentLookup } from '../model/evidence';
import type { StageTextEvidenceData } from '../model/evidence';
import styles from './stage-text-evidence.module.css';

export interface StageTextEvidenceProps {
  readonly revisionId: string | undefined;
  readonly mayAct: boolean;
  readonly dirty: boolean;
  readonly evidence: StageTextEvidenceData | undefined;
  readonly loading: boolean;
  readonly needsRecompute: boolean;
  readonly error: unknown;
  readonly names: ReadonlyMap<string, string>;
  readonly onCompleted: () => void;
  readonly onFocus: (leftProfileId?: string, rightProfileId?: string,
    leftBox?: ComparisonBox, rightBox?: ComparisonBox) => void;
  readonly onHint: (leftProfileId: string, rightProfileId: string, mode: 'add' | 'replace') => void;
}

const RUN_WORDS: Readonly<Record<StageChainRun['state'], string>> = {
  queued: 'В очереди', running: 'Сравнение выполняется', paused: 'Приостановлено',
  completed: 'Сравнение обновлено', failed: 'Пересчёт не выполнен', cancelled: 'Пересчёт отменён',
};

export function StageTextEvidence({ revisionId, mayAct, dirty, evidence, loading,
  needsRecompute, error, names, onCompleted, onFocus, onHint }: StageTextEvidenceProps) {
  const [requested, setRequested] = useState<StageChainRun | null>(null);
  const [sending, setSending] = useState(false);
  const [commandError, setCommandError] = useState<unknown>(null);
  const [visible, setVisible] = useState(50);
  const intent = useRef<{ revision: string; key: string } | null>(null);
  const completed = useRef(onCompleted);
  completed.current = onCompleted;
  const run = useQuery({
    queryKey: ['stage-text-run', requested?.run_id ?? 'none'],
    queryFn: async () => (await getStageChainRun({ path: { stage_chain_run_id: requested!.run_id } })).data,
    enabled: requested !== null, initialData: requested ?? undefined, retry: false,
    refetchInterval: (query) => ['queued', 'running'].includes(query.state.data?.state ?? '') ? 1500 : false,
  });
  useEffect(() => {
    if (run.data?.state === 'completed') completed.current();
  }, [run.data?.run_id, run.data?.state]);

  const start = async () => {
    if (revisionId === undefined || dirty) return;
    if (intent.current?.revision !== revisionId) intent.current = { revision: revisionId, key: newIdempotencyKey() };
    setSending(true);
    setCommandError(null);
    try {
      const answer = await recomputeStageTextEvidence({
        path: { stage_link_revision_id: revisionId }, idempotencyKey: intent.current.key,
      });
      setRequested(answer.data);
      intent.current = null;
    } catch (failure) { setCommandError(failure); }
    finally { setSending(false); }
  };
  const rows = fragmentLookup(evidence);
  const stale = dirty || run.data?.stale === true
    || (run.data !== undefined && run.data.link_revision_id !== revisionId);
  const failure = commandError ?? run.error ?? (needsRecompute ? null : error);
  const message = failure === null || failure === undefined ? null : failureMessage(failure);
  const busy = sending || (run.data?.link_revision_id === revisionId
    && ['queued', 'running'].includes(run.data?.state ?? ''));
  return <section className={styles.panel} aria-labelledby="stage-text-heading">
    <h3 id="stage-text-heading">Текстовые свидетельства</h3>
    {stale ? <p className={styles.stale} role="status">Связи листов изменились — сравнение нужно обновить.</p> : null}
    {revisionId === undefined ? <p>Сохраните карту листов, чтобы начать сравнение текста.</p> : null}
    {needsRecompute ? <p>Нужно пересчитать сравнение, чтобы открыть текст и доказанные совпадения.</p> : null}
    {loading && revisionId !== undefined ? <p role="status">Открываем текстовые свидетельства…</p> : null}
    {mayAct ? <button type="button" className="am-button" disabled={busy || dirty || revisionId === undefined}
      onClick={() => void start()}>Пересчитать текст</button> : null}
    {run.data === undefined ? null : <p role="status">{RUN_WORDS[run.data.state]}
      {run.data.steps.map((step) => step.step_no === 2
        ? ` · Фрагменты: ${step.counts.fragments ?? 0}, совпадения: ${step.counts.exclusions ?? 0}`
        : ` · Различия: ${step.counts.differences ?? 0}, подсказки: ${step.counts.hints ?? 0}`).join('')}</p>}
    {message === null ? null : <ErrorState title="Сравнение не обновилось" detail={message.detail} correlationId={message.correlationId} />}
    {evidence === undefined ? null : <>
      <p>Доказанных совпадений: {evidence.exclusions.length}. Сырых различий: {evidence.differences.length}.</p>
      <details open={evidence.differences.length > 0}>
        <summary>Исходные текстовые различия</summary>
        <div className={styles.tableWrap}><table className={styles.table}>
          <thead><tr><th>Лист П</th><th>Лист Р</th><th>Изменилось</th><th>Удалено</th><th>Добавлено</th><th>На чертеже</th></tr></thead>
          <tbody>{evidence.differences.slice(0, visible).map((difference) => {
            const left = difference.left_fragment_id === undefined ? undefined : rows.get(difference.left_fragment_id);
            const right = difference.right_fragment_id === undefined ? undefined : rows.get(difference.right_fragment_id);
            return <tr key={difference.difference_id}>
              <td>{left === undefined ? '—' : names.get(left.profile_id) ?? 'Лист П'}</td>
              <td>{right === undefined ? '—' : names.get(right.profile_id) ?? 'Лист Р'}</td>
              <td>{difference.status === 'changed' ? `${left?.text ?? '—'} → ${right?.text ?? '—'}` : '—'}</td>
              <td>{difference.status === 'removed' ? left?.text ?? '—' : '—'}</td>
              <td>{difference.status === 'added' ? right?.text ?? '—' : '—'}</td>
              <td><button type="button" className="am-button" onClick={() => onFocus(left?.profile_id, right?.profile_id,
                left === undefined ? undefined : fragmentBox(left) ?? undefined,
                right === undefined ? undefined : fragmentBox(right) ?? undefined)}>Открыть ↗</button></td>
            </tr>;
          })}</tbody>
        </table></div>
        {visible < evidence.differences.length ? <button type="button" className="am-button" onClick={() => setVisible((value) => value + 50)}>Показать ещё</button> : null}
        {evidence.differences.length === 0 ? <p>Исходных текстовых различий не найдено.</p> : null}
      </details>
      {evidence.hints.length === 0 ? null : <details open><summary>Найдено на другом листе ↗</summary>
        <p>Это подсказки для проверки. Решение появится в карте после вашего сохранения.</p>
        <ul className={styles.hints}>{evidence.hints.slice(0, 100).map((hint) => {
          const left = rows.get(hint.source_fragment_id);
          const right = rows.get(hint.target_fragment_id);
          if (left === undefined || right === undefined) return null;
          return <li key={hint.hint_id}>
            <p>{left.text} — {names.get(right.profile_id) ?? 'Лист Р'}</p>
            <button type="button" className="am-button" onClick={() => onFocus(left.profile_id, right.profile_id,
              fragmentBox(left) ?? undefined, fragmentBox(right) ?? undefined)}>Открыть ↗</button>
            {mayAct ? <><button type="button" className="am-button" onClick={() => onHint(left.profile_id, right.profile_id, 'add')}>Добавить связь</button>
              <button type="button" className="am-button" onClick={() => onHint(left.profile_id, right.profile_id, 'replace')}>Заменить связь</button></> : null}
          </li>;
        })}</ul>
      </details>}
    </>}
  </section>;
}
