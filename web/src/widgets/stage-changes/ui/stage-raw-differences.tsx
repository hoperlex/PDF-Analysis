'use client';

import { useQuery } from '@tanstack/react-query';
import { useEffect, useState } from 'react';

import type { StageTextDifference, StageTextFragment } from '@/shared/api';
import { failureMessage, getStageChainRun } from '@/shared/api';
import { fragmentLookup, loadStageTextEvidence } from '@/widgets/stage-text-evidence';
import { ErrorState } from '@/shared/ui';

import styles from './stage-journal.module.css';

export type OpenStageRawDifference = (difference: StageTextDifference,
  left: StageTextFragment | undefined, right: StageTextFragment | undefined) => void;

export function StageRawDifferences({ runId, onOpen }: { readonly runId: string; readonly onOpen?: OpenStageRawDifference }) {
  const [open, setOpen] = useState(false);
  const [visible, setVisible] = useState(50);
  const run = useQuery({ queryKey: ['stage-review-run', runId],
    queryFn: async () => (await getStageChainRun({ path: { stage_chain_run_id: runId } })).data,
    enabled: open, retry: false,
    refetchInterval: (query) => query.state.data !== undefined && ['queued', 'running'].includes(query.state.data.state) ? 1500 : false });
  const revisionId = run.data?.effective_link_revision_id ?? run.data?.link_revision_id;
  const evidence = useQuery({ queryKey: ['stage-review-raw', runId, revisionId],
    queryFn: () => loadStageTextEvidence(run.data!.pair_id, revisionId!),
    enabled: open && revisionId !== undefined, retry: false,
    refetchInterval: run.data !== undefined && ['queued', 'running'].includes(run.data.state) ? 3000 : false });
  useEffect(() => {
    if (open && run.data?.state === 'completed' && revisionId !== undefined) void evidence.refetch();
  }, [open, run.data?.state, run.data?.run_id, revisionId, evidence.refetch]);
  const fragments = fragmentLookup(evidence.data);
  const failure = run.error ?? evidence.error;
  const message = failure === null ? null : failureMessage(failure);
  const text = (id: string | undefined) => id === undefined ? '—' : fragments.get(id)?.text ?? 'Текст этого сохранённого фрагмента недоступен.';
  return <details onToggle={(event) => setOpen(event.currentTarget.open)}>
    <summary>Показать исходные текстовые различия</summary>
    {run.isFetching || evidence.isFetching ? <p role="status">Открываем исходные различия…</p> : null}
    {message === null ? null : <ErrorState title="Исходные различия не открылись" detail={message.detail} correlationId={message.correlationId} />}
    {run.data?.stale ? <p role="status">Показаны сохранённые различия устаревшего сравнения.</p> : null}
    {evidence.data === undefined ? null : <>
      <div className={styles.scroller}><table className={styles.table}>
        <thead><tr><th>Лист П</th><th>Лист РД</th><th>Изменилось</th><th>Удалено</th><th>Добавлено</th>{onOpen === undefined ? null : <th>Открыть</th>}</tr></thead>
        <tbody>{evidence.data.differences.slice(0, visible).map((difference) => {
          const left = difference.left_fragment_id === undefined ? undefined : fragments.get(difference.left_fragment_id);
          const right = difference.right_fragment_id === undefined ? undefined : fragments.get(difference.right_fragment_id);
          return <tr key={difference.difference_id}>
            <td>{left?.profile_id ?? (difference.left_fragment_id === undefined ? '—' : 'Сохранённый лист')}</td>
            <td>{right?.profile_id ?? (difference.right_fragment_id === undefined ? '—' : 'Сохранённый лист')}</td>
            <td>{difference.status === 'changed' ? `${text(difference.left_fragment_id)} → ${text(difference.right_fragment_id)}` : '—'}</td>
            <td>{difference.status === 'removed' ? text(difference.left_fragment_id) : '—'}</td>
            <td>{difference.status === 'added' ? text(difference.right_fragment_id) : '—'}</td>
            {onOpen === undefined ? null : <td><button type="button" className="am-button" disabled={left === undefined && right === undefined}
              onClick={() => onOpen(difference, left, right)}>Открыть ↗</button></td>}
          </tr>;
        })}</tbody>
      </table></div>
      {evidence.data.differences.length === 0 ? <p>Исходных текстовых различий не найдено.</p> : null}
      {visible < evidence.data.differences.length ? <button type="button" className="am-button" onClick={() => setVisible((prior) => prior + 50)}>Показать ещё</button> : null}
    </>}
  </details>;
}
