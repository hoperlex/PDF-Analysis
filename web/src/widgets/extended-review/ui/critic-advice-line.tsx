'use client';

/** @jsxRuntime automatic */

/**
 * The critic's advice for an open block finding, in one line under its recommendation (`F8-WEB`).
 *
 * It reads the run's saved extended review without asking for it again: `useExtendedReviewReading` only subscribes to the entry the
 * review panel and `ExtendedReviewSummary` fill. Until that reading exists, or when it holds no candidate this finding was
 * published from, or the critic gave no recommendation, nothing is drawn: a line that may turn out to be absent is not announced.
 * {@link CriticAdviceView} is the line without the query, so the unit suite and the preview draw the markup the screen draws.
 */

import { adviceForFinding, adviceLine } from '../model/candidate-advice';
import type { AdviceSubject, CandidateAdvice } from '../model/candidate-advice';
import { useExtendedReviewReading } from './extended-review-reading';
import styles from './extended-review.module.css';

export function CriticAdviceView({ advice }: { readonly advice: CandidateAdvice }) {
  return (
    <p
      className={`am-note ${styles.adviceLine}`}
      data-critic-advice={advice.decision}
      data-critic-advice-mode={advice.mode}
      title={`${adviceLine(advice)}\nРекомендация критика не является решением эксперта: решение принимаете вы.`}
    >
      {adviceLine(advice)}
    </p>
  );
}

export function CriticAdviceLine({ runId, subject }: { readonly runId: string; readonly subject: AdviceSubject }) {
  const reading = useExtendedReviewReading(runId);
  const advice = reading === undefined ? null : adviceForFinding(reading.result, subject);
  return advice === null ? null : <CriticAdviceView advice={advice} />;
}
