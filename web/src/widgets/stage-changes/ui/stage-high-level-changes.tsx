'use client';

import { useQuery } from '@tanstack/react-query';
import { useEffect } from 'react';

import type { StageChangeCard } from '@/shared/api';
import { failureMessage } from '@/shared/api';
import { AiLabel } from '@/entities/version-series';
import { ErrorState } from '@/shared/ui';

import { readSyntheses } from '../api/reads';
import type { OpenStageEvidence } from './stage-changes';
import styles from './stage-changes.module.css';

const SECTIONS = [
  { decision: 'REAL_CHANGE', label: 'Изменения высокого уровня', collapsed: false },
  { decision: 'DETAIL_ONLY', label: 'Детализация увеличена', collapsed: false },
  { decision: 'INSUFFICIENT_CONTEXT', label: 'Обобщения, требующие проверки', collapsed: false },
  { decision: 'NO_HIGH_LEVEL_CHANGE', label: 'Без изменения проектного смысла', collapsed: true },
] as const;

export function StageHighLevelChanges({ runId, cards, running, completed, onOpenEvidence }: {
  readonly runId: string; readonly cards: readonly StageChangeCard[]; readonly running: boolean;
  readonly completed: boolean; readonly onOpenEvidence: OpenStageEvidence;
}) {
  const synthesis = useQuery({ queryKey: ['stage-high-level', runId], queryFn: () => readSyntheses(runId), retry: false,
    refetchInterval: running ? 3000 : false });
  useEffect(() => { if (completed) void synthesis.refetch(); }, [completed, synthesis.refetch]);
  const failure = synthesis.error === null ? null : failureMessage(synthesis.error);
  return <section aria-label="Обобщение проектных изменений">
    {synthesis.isFetching ? <p role="status">Открываем обобщения…</p> : null}
    {failure === null ? null : <ErrorState title="Обобщения не открылись" detail={failure.detail} correlationId={failure.correlationId} />}
    {SECTIONS.map((section) => {
      const items = synthesis.data?.filter((item) => item.result.decision === section.decision) ?? [];
      if (items.length === 0) return null;
      return <details key={section.decision} open={!section.collapsed}>
        <summary>{section.label} · {items.length}</summary>
        <div className={styles.cards}>{items.map((item) => {
          const evidenceIds = new Set(item.result.evidence_ids);
          const sources = cards.filter((card) => card.evidence_ids.some((id) => evidenceIds.has(id)));
          return <article key={item.synthesis_id} className={styles.card}>
            <h4>{item.result.title}</h4><p>{item.result.reason}</p><p><AiLabel /></p>
            <ul>{sources.map((card) => <li key={card.card_id}>
              <a href={`#stage-card-${card.card_id}`}>{card.title}</a>
              {(card.evidence ?? []).filter((evidence) => evidenceIds.has(evidence.evidence_id)).map((evidence) =>
                <button key={evidence.evidence_id} type="button" className="am-button" disabled={evidence.profile_id === undefined}
                  onClick={() => onOpenEvidence(evidence, card)}>Открыть в PDF ↗</button>)}
            </li>)}</ul>
            {sources.length === 0 ? <p>Связанные карточки ещё не загружены.</p> : null}
          </article>;
        })}</div>
      </details>;
    })}
  </section>;
}
