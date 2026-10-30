'use client';

import Link from 'next/link';
import { useQuery } from '@tanstack/react-query';

import { getExtendedRunReview } from '@/shared/api';
import { routes } from '@/shared/lib';
import styles from './extended-review.module.css';

type RecordValue = Record<string, unknown>;
function object(value: unknown): RecordValue | null { return typeof value === 'object' && value !== null && !Array.isArray(value) ? value as RecordValue : null; }

/** Counts only real records in the preliminary response, never canonical findings or verdicts. */
export function extendedCandidateCounts(value: unknown) {
  const result = object(value);
  const rows = Array.isArray(result?.observations) ? result.observations.flatMap((item) => { const row = object(item); return row === null ? [] : [row]; }) : [];
  return {
    candidates: rows.length,
    criticRecommendations: rows.filter((row) => {
      const advice = object(row.review ?? row.critic);
      return typeof advice?.llm_decision === 'string' && advice.llm_decision.trim() !== '';
    }).length,
    correctionProposals: rows.filter((row) => object(object(row.correction)?.candidate) !== null).length,
  };
}

export function ExtendedReviewSummary({ projectUid, runId }: { readonly projectUid: string; readonly runId: string }) {
  const query = useQuery({
    queryKey: ['extended-run-review', runId],
    queryFn: async () => (await getExtendedRunReview({ path: { run_id: runId } })).data,
    retry: false,
  });
  const counts = extendedCandidateCounts(query.data?.result);
  if (counts.candidates === 0) return null;
  return <aside className={styles.summary} aria-label="Предварительные кандидаты расширенного анализа" data-extended-candidate-count={counts.candidates}>
    <p><strong>В расширенном анализе сохранено предварительных кандидатов: {counts.candidates}.</strong></p>
    <p>Это отдельные машинные наблюдения. Они не включены в счётчик канонических находок и не являются экспертными решениями. Нулевой список находок ниже не означает, что расширенный анализ пуст.</p>
    <Link href={`${routes.run(projectUid, runId)}#extended-analysis`}>Открыть расширенный анализ, рекомендации и отчёт</Link>
  </aside>;
}
