'use client';

import { useQuery } from '@tanstack/react-query';
import { useEffect, useState } from 'react';

import {
  failureMessage, getStageChainRun, getStageChangeJournal, streamStageChangeJournalHtml,
  streamStageChangeJournalPdf, streamStageChangeJournalXlsx,
} from '@/shared/api';
import { browserDownloadSink, deliverDownload } from '@/features/export-run';
import { EmptyState, ErrorState, LoadingState } from '@/shared/ui';

import { STAGE_REVIEW_KEYS } from '../api/reads';
import { journalGroups } from '../model/journal';
import { SYSTEM_WORDS } from '../model/cards';
import type { StageReviewProps } from './stage-changes';
import styles from './stage-journal.module.css';

export const STAGE_REVIEW_POLL_MS = 1500;

type Grouping = 'designation' | 'section' | 'system';
type Format = 'xlsx' | 'pdf' | 'html';

export function StageJournal({ runId, onOpenEvidence }: StageReviewProps) {
  const [grouping, setGrouping] = useState<Grouping>('designation');
  const [downloading, setDownloading] = useState<Format | null>(null);
  const [downloadError, setDownloadError] = useState<unknown>(null);
  const run = useQuery({ queryKey: ['stage-review-run', runId ?? ''],
    queryFn: async () => (await getStageChainRun({ path: { stage_chain_run_id: runId! } })).data,
    enabled: Boolean(runId), retry: false,
    refetchInterval: (query) => query.state.data !== undefined && ['queued', 'running'].includes(query.state.data.state) ? STAGE_REVIEW_POLL_MS : false });
  const journal = useQuery({ queryKey: [...STAGE_REVIEW_KEYS.journal(runId ?? ''), grouping],
    queryFn: async () => {
      const result = (await getStageChangeJournal({ path: { stage_chain_run_id: runId! }, query: { grouping } })).data;
      return { result, groups: journalGroups(result) };
    }, enabled: Boolean(runId), retry: false,
    refetchInterval: () => run.data !== undefined && ['queued', 'running'].includes(run.data.state) ? STAGE_REVIEW_POLL_MS : false });
  useEffect(() => {
    if (run.data?.state === 'completed') void journal.refetch();
  }, [run.data?.state, run.data?.run_id, journal.refetch]);
  const download = async (format: Format) => {
    if (!runId) return;
    setDownloading(format); setDownloadError(null);
    try {
      const input = { path: { stage_chain_run_id: runId } };
      const answer = format === 'xlsx' ? await streamStageChangeJournalXlsx(input)
        : format === 'pdf' ? await streamStageChangeJournalPdf(input) : await streamStageChangeJournalHtml(input);
      deliverDownload(browserDownloadSink(), answer.data, `stage-journal-${runId}.${format}`);
    } catch (failure) { setDownloadError(failure); }
    finally { setDownloading(null); }
  };
  const failure = downloadError ?? journal.error ?? run.error;
  const message = failure === null ? null : failureMessage(failure);
  if (!runId) return <EmptyState title="Выберите сравнение" detail="Журнал появится после подготовки карточек и экспертных решений." />;
  return <section className={styles.journal} aria-labelledby="stage-journal-heading">
    <h2 id="stage-journal-heading">Итоговый журнал изменений</h2>
    <label>Группировать
      <select value={grouping} onChange={(event) => setGrouping(event.target.value as Grouping)}>
        <option value="designation">По шифру</option><option value="section">По разделу</option><option value="system">По системе</option>
      </select>
    </label>
    <div className={styles.actions}>{(['xlsx', 'pdf', 'html'] as const).map((format) => <button key={format}
      type="button" className="am-button" disabled={downloading !== null || journal.data === undefined}
      onClick={() => void download(format)}>{format === 'xlsx' ? 'Excel' : format.toUpperCase()} ↓</button>)}</div>
    {journal.isPending ? <LoadingState what="итоговый журнал" /> : null}
    {message === null ? null : <ErrorState title="Журнал не открылся или файл не скачался" detail={message.detail} correlationId={message.correlationId} />}
    {journal.data === undefined ? null : <>
      <p>Подтверждено изменений: {journal.data.result.accepted_count}.</p>
      <p>Скрыто совпадений после ревизии ИИ: {journal.data.result.ai_hidden_same_count}. Служебных изменений: {journal.data.result.ai_service_count}.</p>
      {journal.data.result.stale ? <p role="status">Сравнение устарело. Журнал относится к сохранённым решениям этого запуска.</p> : null}
      {journal.data.groups.length === 0 ? <EmptyState title="Подтверждённых изменений пока нет" detail="Сохраните решения эксперта на вкладке изменений." /> : null}
      {journal.data.groups.map((group) => <section key={group.key} aria-label={group.label}>
        <h3>{group.label}</h3>
        <div className={styles.scroller}><table className={styles.table}>
          <thead><tr><th>ID</th><th>Изменение</th><th>Было</th><th>Стало</th><th>Источник</th><th>Решение эксперта</th></tr></thead>
          <tbody>{group.rows.map((card) => <tr key={card.card_id}>
            <td><code>{card.card_id}</code></td><td>{card.title}<p>{SYSTEM_WORDS[card.system]}</p></td>
            <td>{card.before || '—'}</td><td>{card.after || '—'}</td>
            <td>{[...new Set((card.evidence ?? []).map((item) => item.kind))].join(', ')}
              {(card.evidence ?? []).map((evidence) => <button key={evidence.evidence_id} type="button" className="am-button"
                disabled={evidence.profile_id === undefined} onClick={() => onOpenEvidence(evidence, card)}>Открыть ↗</button>)}
            </td>
            <td>{card.verdict?.decision === 'accepted' ? 'Принято' : card.verdict?.decision === 'rejected' ? 'Не принято' : 'Не сохранено'}
              {card.verdict?.reason ? <p>{card.verdict.reason}</p> : null}</td>
          </tr>)}</tbody>
        </table></div>
      </section>)}
    </>}
  </section>;
}
