'use client';

import Link from 'next/link';
import { useQuery } from '@tanstack/react-query';

import { getExtendedRunReview } from '@/shared/api';
import type { Finding } from '@/shared/api';
import { routes } from '@/shared/lib';
import { reviewCandidates } from '../model/review-candidates';
import styles from './extended-review.module.css';
import { CANDIDATES_BLOCK_ID, openCandidatesBlock } from './review-candidates';

type RecordValue = Record<string, unknown>;
function object(value: unknown): RecordValue | null { return typeof value === 'object' && value !== null && !Array.isArray(value) ? value as RecordValue : null; }

/** Counts only real records in the preliminary response, never canonical findings or verdicts. */
export function extendedCandidateCounts(value: unknown) {
  const result = object(value);
  const rows = Array.isArray(result?.observations) ? result.observations.flatMap((item) => { const row = object(item); return row === null ? [] : [row]; }) : [];
  return {
    candidates: reviewCandidates(value).groupCount,
    criticRecommendations: rows.filter((row) => {
      const advice = object(row.review ?? row.critic);
      return typeof advice?.llm_decision === 'string' && advice.llm_decision.trim() !== '';
    }).length,
    correctionProposals: rows.filter((row) => object(object(row.correction)?.candidate) !== null).length,
  };
}

export function ExtendedReviewSummary({ projectUid, runId, oneList = false, published = [] }: {
  readonly projectUid: string; readonly runId: string; readonly oneList?: boolean;
  readonly published?: readonly Finding[];
}) {
  const query = useQuery({
    queryKey: ['extended-run-review', runId],
    queryFn: async () => (await getExtendedRunReview({ path: { run_id: runId } })).data,
    retry: false,
  });
  const counts = extendedCandidateCounts(query.data?.result);
  if (counts.candidates === 0) return null;
  const retained = reviewCandidates(query.data?.result, published).rows.length;
  if (oneList && retained === 0) return null;
  // `UIP-S06-04`: one closed line under the table of «Разбор»; the sentences open with it.
  return <details className={styles.summary} data-extended-summary="" data-extended-candidate-count={counts.candidates}>
    <summary>Сводка расширенного разбора: кандидатов {counts.candidates}</summary>
    <p><strong>{oneList ? 'Прогон использует общий список замечаний для решения экспертом.' : `В расширенном анализе сохранено предварительных кандидатов: ${counts.candidates}.`}</strong></p>
    {oneList ? <p>В расширенном анализе сохранено предварительных кандидатов: {counts.candidates}.</p> : null}
    <p>{oneList ? 'Решение по каждому замечанию принимает эксперт. Оставшиеся машинные кандидаты доступны только для чтения.' : 'Это отдельные машинные наблюдения, доступные ниже для чтения. Они не включены в счётчик замечаний и не являются экспертными решениями.'}</p>
    {retained > 0 ? <p><a href={`#${CANDIDATES_BLOCK_ID}`} onClick={openCandidatesBlock}>Кандидаты для чтения: {retained}</a></p> : null}
    <Link href={`${routes.run(projectUid, runId)}#extended-analysis`}>Открыть расширенный анализ, рекомендации и отчёт</Link>
  </details>;
}
