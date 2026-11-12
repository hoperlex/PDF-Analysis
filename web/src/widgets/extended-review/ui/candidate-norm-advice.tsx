'use client';

import Link from 'next/link';
import { routes } from '@/shared/lib';
import { candidateOfFinding } from '../model/candidate-advice';
import type { AdviceSubject } from '../model/candidate-advice';
import { candidateObjects, candidateText } from '../model/review-candidates';
import { useExtendedReviewReading } from './extended-review-reading';

/** Search candidates are never promoted to the finding's certified normative citations. */
export function CandidateNormAdvice({ runId, subject }: { readonly runId: string; readonly subject: AdviceSubject }) {
  const reading = useExtendedReviewReading(runId);
  const candidate = reading === undefined ? null : candidateOfFinding(reading.result, subject);
  const norms = candidateObjects(candidate?.norm_candidates);
  if (norms.length === 0) return null;
  return <details><summary>Нормативные кандидаты · {norms.length} · требуют проверки</summary>
    <p className="am-note">Результаты поиска по нормам. Применимость и основание замечания не подтверждены.</p>
    <ul>{norms.map((norm, index) => <li key={`${candidateText(norm.paragraph_id)}:${index}`}>
      <strong>{candidateText(norm.designation) || 'Нормативный кандидат'}</strong>{candidateText(norm.clause_number) ? ` · п. ${candidateText(norm.clause_number)}` : ''}
      {candidateText(norm.quote) ? <blockquote>{candidateText(norm.quote)}</blockquote> : null}
      {candidateText(norm.document_id) ? <Link href={routes.normDocument(candidateText(norm.document_id))}>Открыть норму</Link> : null}
    </li>)}</ul>
  </details>;
}
