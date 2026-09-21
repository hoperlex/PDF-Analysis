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
 */

import { useState } from 'react';

import type { FindingObservationId, Verdict } from '@/shared/api';
import type { ErrorStateProps } from '@/shared/ui';
import { ErrorState } from '@/shared/ui';
import { VerdictBadge } from '@/entities/expert-decision';

/** Which intent is in flight, so only that control shows as busy. */
export type DecisionIntent = 'accept' | 'reject' | 'comment';

export interface DecisionPanelProps {
  readonly currentVerdict: Verdict;
  readonly observationId: FindingObservationId;
  readonly onAccept: (observationId: FindingObservationId) => void;
  readonly onReject: (observationId: FindingObservationId) => void;
  readonly onComment: (text: string, observationId: FindingObservationId) => void;
  readonly pendingIntent?: DecisionIntent | null | undefined;
  readonly error?: ErrorStateProps | null | undefined;
  /** Set when the browser refused to send, e.g. an empty comment. */
  readonly refusal?: string | null | undefined;
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
}: DecisionPanelProps) {
  const [draft, setDraft] = useState('');
  const busy = pendingIntent !== undefined && pendingIntent !== null;

  return (
    <section className="am-decision" data-observation-id={observationId}>
      <header className="am-decision__header">
        <h3>Решение</h3>
        <span className="am-decision__current">
          текущий вердикт <VerdictBadge verdict={currentVerdict} />
        </span>
      </header>

      <div className="am-decision__verdicts">
        <button
          type="button"
          className="am-button"
          data-intent="accept"
          disabled={busy}
          onClick={() => {
            onAccept(observationId);
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
        {refusal === 'empty' ? (
          <p className="am-decision__refusal" role="alert">
            Событию комментария нужен текст. Ничего не отправлено.
          </p>
        ) : null}
      </div>

      {error !== undefined && error !== null ? <ErrorState {...error} /> : null}
    </section>
  );
}
