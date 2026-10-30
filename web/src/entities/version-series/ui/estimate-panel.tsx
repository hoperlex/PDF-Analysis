/**
 * The estimate an AI start shows and the consent line under it (`Q-CMP-7`, ADR-0025 decision 19; the original's `confirmDialog`,
 * `version-comparison-projects.js:540-556`, and the sheet's own, `version-comparison-sheet-changes.js:33-45`).
 *
 * One component for every start — a pair check, the description of a series or of one sheet, a specification, a report — so that
 * **no start can skip the estimate or the consent**: the confirm button is enabled only for an agreement that was given to the
 * estimate on screen ({@link agreementStands}), never while the estimate is blocked by a ceiling or has nothing to send, and the
 * parent sends `consentOf` this very estimate. It draws; the parent owns the state and the command.
 */

import type { ReactNode } from 'react';

import type { ComparisonAiEstimate } from '@/shared/api';

import { AI_CEILING_LABELS } from '../model/ai-words';
import type { ConsentKind } from '../model/estimate';
import {
  BLOCKED_SENTENCES,
  CONSENT_LINES,
  NOTHING_TO_SEND_SENTENCE,
  NOT_METERED_TITLE,
  RECONSENT_NOTE,
  agreementStands,
  estimateLines,
  isBlocked,
  isNothingToSend,
  isNotMetered,
} from '../model/estimate';
import type { ComparisonFailure } from '../model/failure';

import { AiLabel } from './ai-text';
import styles from './ai-ui.module.css';

export interface EstimatePanelProps {
  readonly title: string;
  readonly consentKind: ConsentKind;
  readonly confirmLabel: string;
  /** The estimate read for this start; `undefined` while it is being read or when the read failed. */
  readonly estimate: ComparisonAiEstimate | undefined;
  readonly loading: boolean;
  /** Why the estimate could not be read, or why the start was refused. */
  readonly failure: ComparisonFailure | null;
  /** The digest the line of consent was ticked against; `null` when it is not ticked. */
  readonly agreedDigest: string | null;
  readonly busy: boolean;
  readonly onAgree: (on: boolean) => void;
  readonly onConfirm: () => void;
  readonly onCancel: () => void;
  /** Lines of the caller's own, above the estimate (what the start does, the queue it joins). */
  readonly intro?: ReactNode;
  /** Report-only, zero-model deterministic PDF assembly under this same estimate digest. */
  readonly allowLocalAssembly?: boolean;
}

export function EstimatePanel({
  title, consentKind, confirmLabel, estimate, loading, failure, agreedDigest, busy, onAgree, onConfirm, onCancel, intro,
  allowLocalAssembly = false,
}: EstimatePanelProps) {
  const blocked = estimate !== undefined && isBlocked(estimate);
  const localAssembly = allowLocalAssembly && estimate?.method === 'report' && estimate.calls === 0;
  const nothing = estimate !== undefined && !blocked && !localAssembly && isNothingToSend(estimate);
  const agreed = agreementStands(agreedDigest, estimate);
  // The reader had ticked the line for an estimate that is no longer the one shown: the tick is void and the line is asked again.
  const reasked = agreedDigest !== null && estimate !== undefined && !agreed;
  const canConfirm = estimate !== undefined && agreed && !blocked && !nothing && !busy;
  return (
    <section className={styles.estimate} role="group" aria-label={title} data-estimate-panel="" {...(estimate === undefined ? {} : { 'data-estimate-method': estimate.method })}>
      <h3 className={styles.estimateTitle}>{title}</h3>
      {intro}
      {loading ? <p className="am-note" role="status">Оценка объёма…</p> : null}
      {failure === null ? null : (
        <p className={styles.refusal} role="alert" data-comparison-failure={failure.kind} data-estimate-refusal={failure.estimateStale ? 'stale' : ''}>
          {failure.detail}
          {failure.correlationId === null ? null : <> Код обращения: <code>{failure.correlationId}</code>.</>}
        </p>
      )}
      {estimate === undefined ? null : (
        <>
          {localAssembly ? <p role="status" data-report-local-assembly="">Будет выполнена программная сборка PDF по сохранённым материалам этой оценки. Новых обращений к модели: 0.</p> : null}
          <ul className={styles.lines} data-estimate-digest={estimate.estimate_digest}>
            {estimateLines(estimate).map((line) => (
              <li key={line.key} className={line.muted === true ? styles.lineMuted : styles.line} data-estimate-line={line.key}>
                {localAssembly && line.key === 'units' ? 'Материалы оценки используются для программной сборки отчёта.' : line.text}
              </li>
            ))}
          </ul>
          {estimate.route.provider_mode === 'recorded' ? (
            <p className={styles.warning} data-provider-recorded="">
              Подключение работает в режиме записи: ответы будут записанными тестовыми, а не ответами модели.
            </p>
          ) : null}
          {isNotMetered(estimate) ? <p className={styles.lineMuted} title={NOT_METERED_TITLE}>{NOT_METERED_TITLE}</p> : null}
          {blocked ? (
            <p className={styles.warning} role="alert" data-estimate-blocked={estimate.blocked_by}>
              {estimate.blocked_by === undefined ? '' : `${AI_CEILING_LABELS[estimate.blocked_by]}: ${BLOCKED_SENTENCES[estimate.blocked_by]}`}
            </p>
          ) : null}
          {nothing ? <p className={styles.warning} data-estimate-nothing="">{NOTHING_TO_SEND_SENTENCE}</p> : null}
          {reasked ? <p className={styles.warning} role="status" data-estimate-reasked="">{RECONSENT_NOTE}</p> : null}
          <label className={styles.consent} data-consent-line="">
            <input
              type="checkbox"
              checked={agreed}
              disabled={blocked || nothing || busy}
              onChange={(event) => onAgree(event.target.checked)}
            />
            <span>{localAssembly ? 'Подтверждаю сборку PDF по сохранённым материалам этой оценки.' : CONSENT_LINES[consentKind]}</span>
          </label>
          <p className={styles.lineMuted}>
            Ответ ИИ — <AiLabel />. Он не заменяет решение эксперта.
          </p>
        </>
      )}
      <div className={styles.actions}>
        <button type="button" className="am-button" disabled={!canConfirm} data-estimate-confirm="" onClick={onConfirm}>
          {busy ? 'Запуск…' : confirmLabel}
        </button>
        <button type="button" className="am-button am-button--quiet" disabled={busy} onClick={onCancel}>
          Отмена
        </button>
      </div>
    </section>
  );
}
