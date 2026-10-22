'use client';

/** @jsxRuntime automatic */

/**
 * Accept, reject, and append a comment.
 *
 * Three buttons and one textarea, and deliberately no fourth control. There is no "change
 * verdict", no "undo" and no "clear": the ledger is append-only, so a UI affordance that
 * implied otherwise would be lying about what the server will do. `revoke` exists in the
 * contract's event union and has no PC-01 client (seam §10), so it is not offered here.
 *
 * The comment box sits below the verdict buttons rather than inside them, because a comment
 * is not a weaker verdict. It carries `verdict: null`, so appending one after an accept
 * leaves that accept standing — and the panel keeps showing the accept while the comment is
 * being written, which is the honest rendering of what is about to happen.
 *
 * The current verdict is the **server's** projection, passed in. This panel never derives
 * one from the buttons the user pressed.
 *
 * On a finding that carries a proposed severity (`REVIEW-V2-UI-01`), the accept action gets a
 * severity choice. The proposal is shown as the MODEL's and is not copied into the choice:
 * the select starts empty, and an accept with nothing chosen is refused by the feature and
 * said on the screen (`severityRefusal`, rendered on presence like the comment refusal). A
 * finding without a proposal gets exactly the panel it always had.
 */

import { useState } from 'react';

import type { FindingObservationId, Severity, Verdict } from '@/shared/api';
import { SEVERITY_VALUES } from '@/shared/api';
import type { ErrorStateProps } from '@/shared/ui';
import { ErrorState } from '@/shared/ui';
import type { CommentRefusal } from '@/features/append-comment';
import { commentRefusalMessage } from '@/features/append-comment';
import type { VerdictRefusal } from '@/features/record-verdict';
import { verdictRefusalMessage } from '@/features/record-verdict';
import { VerdictBadge } from '@/entities/expert-decision';
import { SEVERITY_LABELS, SeverityBadge } from '@/entities/finding';

import { chosenSeverity, draftFromControl } from '../model/severity-draft';
import type { SeverityDraft } from '../model/severity-draft';

import styles from './decision-panel.module.css';

/** Which intent is in flight, so only that control shows as busy. */
export type DecisionIntent = 'accept' | 'reject' | 'comment';

export interface DecisionPanelProps {
  readonly currentVerdict: Verdict;
  readonly observationId: FindingObservationId;
  /** `severity` is the expert's choice, or nothing; it is only ever offered with a proposal. */
  readonly onAccept: (
    observationId: FindingObservationId,
    severity: Severity | undefined,
  ) => void;
  readonly onReject: (observationId: FindingObservationId) => void;
  readonly onComment: (text: string, observationId: FindingObservationId) => void;
  readonly pendingIntent?: DecisionIntent | null | undefined;
  readonly error?: ErrorStateProps | null | undefined;
  /**
   * Set when the browser refused to send, rather than when the server refused.
   *
   * TYPED, and `D-84` is why it says so here. This read `string` and the panel rendered on
   * `refusal === 'empty'`, so the day `CommentRefusal` gained a second member the comment
   * would have been refused while the screen said nothing at all — the silent fallback
   * `AGENTS.md` §4 forbids by name, and one `tsc` could not see, because `string` accepts
   * every member anyone will ever add. The type is the feature's own union now, and the
   * panel renders on PRESENCE, so a new refusal reaches the reviewer by construction
   * instead of by somebody remembering this line.
   */
  readonly refusal?: CommentRefusal | null | undefined;
  /** The model's proposed severity of the canonical observation, when it has one. */
  readonly proposedSeverity?: Severity | undefined;
  /** The severity the expert decided, as the server's projection serves it. */
  readonly decidedSeverity?: Severity | undefined;
  /** Set when the browser refused to send an accept; rendered on presence. */
  readonly severityRefusal?: VerdictRefusal | null | undefined;
}

export function DecisionPanel({
  currentVerdict,
  observationId,
  onAccept,
  onReject,
  onComment,
  pendingIntent,
  error,
  refusal,
  proposedSeverity,
  decidedSeverity,
  severityRefusal,
}: DecisionPanelProps) {
  const [draft, setDraft] = useState('');
  const [severityDraft, setSeverityDraft] = useState<SeverityDraft | null>(null);
  const chosen = chosenSeverity(severityDraft, observationId);
  const busy = pendingIntent !== undefined && pendingIntent !== null;

  return (
    <section className="am-decision" data-observation-id={observationId}>
      <header className="am-decision__header">
        <h3>Решение</h3>
        <span className="am-decision__current">
          текущий вердикт <VerdictBadge verdict={currentVerdict} />
          {decidedSeverity === undefined ? null : (
            <span className={styles.decided} data-decided-severity={decidedSeverity}>
              важность <SeverityBadge severity={decidedSeverity} title="Важность, решённая экспертом" />
            </span>
          )}
        </span>
      </header>

      {proposedSeverity === undefined ? null : (
        <div className={styles.severity} data-severity-control="accept">
          <p
            className={`am-decision__current ${styles.proposal}`}
            data-proposed-severity={proposedSeverity}
          >
            Предложение модели:{' '}
            <SeverityBadge severity={proposedSeverity} title="Важность, предложенная моделью" />
          </p>
          <label htmlFor="decision-severity">
            Важность при принятии
          </label>
          <select
            id="decision-severity"
            className={styles.select}
            value={chosen ?? ''}
            disabled={busy}
            onChange={(event) => {
              setSeverityDraft(draftFromControl(event.target.value, observationId));
            }}
          >
            <option value="">Выберите важность</option>
            {SEVERITY_VALUES.map((value) => (
              <option key={value} value={value}>
                {SEVERITY_LABELS[value]}
              </option>
            ))}
          </select>
          <p className="am-decision__note">
            Предложение модели не становится решением само: важность записывается только
            при принятии и только та, что выбрана здесь. При отклонении она не записывается.
          </p>
          {severityRefusal === null || severityRefusal === undefined ? null : (
            <p className="am-decision__refusal" role="alert" data-severity-refusal={severityRefusal}>
              {verdictRefusalMessage(severityRefusal)}
            </p>
          )}
        </div>
      )}

      <div className="am-decision__verdicts">
        <button
          type="button"
          className="am-button"
          data-intent="accept"
          disabled={busy}
          onClick={() => {
            onAccept(observationId, chosen);
          }}
        >
          {pendingIntent === 'accept' ? 'Принимаю…' : 'Принять'}
        </button>
        <button
          type="button"
          className="am-button"
          data-intent="reject"
          disabled={busy}
          onClick={() => {
            onReject(observationId);
          }}
        >
          {pendingIntent === 'reject' ? 'Отклоняю…' : 'Отклонить'}
        </button>
      </div>

      <div className="am-decision__comment">
        <label htmlFor="am-decision-comment">Добавить комментарий</label>
        <textarea
          id="am-decision-comment"
          className="am-decision__draft"
          value={draft}
          rows={3}
          onChange={(event) => {
            setDraft(event.target.value);
          }}
        />
        <button
          type="button"
          className="am-button"
          data-intent="comment"
          disabled={busy}
          onClick={() => {
            onComment(draft, observationId);
            setDraft('');
          }}
        >
          {pendingIntent === 'comment' ? 'Добавляю…' : 'Добавить'}
        </button>
        <p className="am-decision__note">
          Комментарий — это новое событие. Он никогда не заменяет вердикт выше и не
          редактирует более раннее событие.
        </p>
        {refusal !== null && refusal !== undefined ? (
          <p className="am-decision__refusal" role="alert" data-comment-refusal={refusal}>
            {commentRefusalMessage(refusal)}
          </p>
        ) : null}
      </div>

      {error !== undefined && error !== null ? <ErrorState {...error} /> : null}
    </section>
  );
}
