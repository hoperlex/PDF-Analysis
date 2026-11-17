'use client';

/**
 * The window of «Подтвердить все предложения (N)» (`UIP-S16-03`, `Г3-B`, `Г12-B`): the list the expert is shown and the one
 * confirmation that is asked of them (the shared `Dialog`, `UIP-G-04`).
 *
 * A suggestion is not a decision (`AGENTS` §4); the window does not make one by itself. What it asks is the expert's «yes» to the
 * pairs it lists, and each of them is then confirmed by its own command with its own key (`useConfirmStagePairs`), so the server
 * sees the same decisions as if the expert had pressed «Подтвердить» on each row. The end says «Подтверждено N из M» and names
 * the pairs that were refused with the reason as the server gave it; «Повторить для оставшихся» sends only those, under their
 * held keys.
 *
 * The window is the list of the moment it was opened: the table under it is read again while the pairs are confirmed, and the list
 * the expert agreed to does not change under their eyes. While the commands run the window does not close (Esc and «Закрыть» are
 * held back), so the end is always seen.
 *
 * `ConfirmAllSuggestionsView` is the window as drawn for a given phase: the language guard, the census and the unit suite draw it.
 */

import { useState } from 'react';

import type { ProjectUid, StagePairSuggestion } from '@/shared/api';
import { failureMessage } from '@/shared/api';
import { Dialog } from '@/shared/ui';
import { documentCaption, suggestionReason, useConfirmStagePairs } from '@/entities/stage-pair';
import type { ConfirmAllResult, StageDocumentNames } from '@/entities/stage-pair';

import styles from './stage-pair-catalog.module.css';

export const CONFIRM_ALL_TITLE = 'Подтвердить все предложения';

export type ConfirmAllPhase =
  | { readonly kind: 'review' }
  | { readonly kind: 'running'; readonly done: number }
  | { readonly kind: 'finished'; readonly result: ConfirmAllResult };

export interface ConfirmAllSuggestionsViewProps {
  /** The pairs this window is about: the whole list at the start, the pairs not yet confirmed after a retry is asked. */
  readonly suggestions: readonly StagePairSuggestion[];
  /** The size of the first list, so that the end says «из M» over everything the expert agreed to. */
  readonly total: number;
  readonly names: StageDocumentNames | undefined;
  readonly phase: ConfirmAllPhase;
  readonly onConfirm: () => void;
  readonly onRetry: () => void;
  readonly onClose: () => void;
  /** The census and the unit suite: drawn open without `showModal`. */
  readonly staticOpen?: boolean | undefined;
}

function PairLine({ suggestion, names }: { readonly suggestion: StagePairSuggestion; readonly names: StageDocumentNames | undefined }) {
  return <>П: {documentCaption(names, suggestion.left_document_uid)} · Р: {documentCaption(names, suggestion.right_document_uid)}</>;
}

export function ConfirmAllSuggestionsView({ suggestions, total, names, phase, onConfirm, onRetry, onClose, staticOpen }: ConfirmAllSuggestionsViewProps) {
  const running = phase.kind === 'running';
  // Esc and «Закрыть» ask for a close; while the commands run the answer is no, so that the end of the list is not lost.
  const close = () => { if (!running) onClose(); };
  const failures = phase.kind === 'finished' ? phase.result.failures : [];
  return (
    <Dialog
      title={CONFIRM_ALL_TITLE}
      size="md"
      onClose={close}
      staticOpen={staticOpen}
      markers={{ 'data-confirm-all': phase.kind }}
      actions={
        phase.kind === 'finished' ? (
          <>
            {failures.length === 0 ? null : (
              <button type="button" className="am-button" data-confirm-all-retry="" onClick={onRetry}>Повторить для оставшихся ({failures.length})</button>
            )}
            <button type="button" className="am-button am-button--quiet" onClick={onClose}>Закрыть</button>
          </>
        ) : (
          <>
            <button type="button" className="am-button am-button--quiet" disabled={running} onClick={onClose}>Отмена</button>
            <button type="button" className="am-button" data-confirm-all-submit="" disabled={running || suggestions.length === 0} onClick={onConfirm}>
              Подтвердить все ({suggestions.length})
            </button>
          </>
        )
      }
    >
      {phase.kind === 'finished' ? (
        <>
          <p role="status" data-confirm-all-result="">Подтверждено {phase.result.confirmed} из {total}</p>
          {failures.length === 0 ? null : (
            <>
              <p>Не подтверждены:</p>
              <ul className={styles.confirmList}>
                {failures.map((failure) => (
                  <li key={`${failure.suggestion.left_document_uid}|${failure.suggestion.right_document_uid}`}>
                    <PairLine suggestion={failure.suggestion} names={names} /> — {failureMessage(failure.error).detail}
                  </li>
                ))}
              </ul>
            </>
          )}
        </>
      ) : (
        <>
          <p>Каждая пара подтверждается отдельным решением эксперта. Предложение само ничего не связывает.</p>
          {phase.kind === 'running' ? <p role="status">Подтверждаем: {phase.done} из {suggestions.length}…</p> : null}
          <ol className={styles.confirmList} data-confirm-all-list="">
            {suggestions.map((suggestion) => (
              <li key={`${suggestion.left_document_uid}|${suggestion.right_document_uid}`}>
                <PairLine suggestion={suggestion} names={names} />
                <span className={styles.reason}> — {suggestionReason(suggestion.reason)}</span>
              </li>
            ))}
          </ol>
        </>
      )}
    </Dialog>
  );
}

export interface ConfirmAllSuggestionsProps {
  readonly projectUid: ProjectUid;
  /** The suggestions on the screen at the moment the button was pressed. */
  readonly suggestions: readonly StagePairSuggestion[];
  readonly names: StageDocumentNames | undefined;
  readonly onClose: () => void;
}

export function ConfirmAllSuggestions({ projectUid, suggestions, names, onClose }: ConfirmAllSuggestionsProps) {
  const confirmAll = useConfirmStagePairs();
  // The pairs the running or the last pass is about, and what the earlier passes confirmed: a retry asks only for the refused pairs.
  const [attempt, setAttempt] = useState(suggestions);
  const [confirmedBefore, setConfirmedBefore] = useState(0);
  const last = confirmAll.result;
  const run = (list: readonly StagePairSuggestion[]) => {
    setAttempt(list);
    void confirmAll.run(projectUid, list);
  };

  const phase: ConfirmAllPhase = confirmAll.pending
    ? { kind: 'running', done: confirmAll.done }
    : last === undefined ? { kind: 'review' } : { kind: 'finished', result: { ...last, confirmed: confirmedBefore + last.confirmed } };

  return (
    <ConfirmAllSuggestionsView
      suggestions={attempt}
      total={suggestions.length}
      names={names}
      phase={phase}
      onClose={onClose}
      onConfirm={() => run(suggestions)}
      onRetry={() => {
        if (last === undefined) return;
        setConfirmedBefore(confirmedBefore + last.confirmed);
        run(last.failures.map((failure) => failure.suggestion));
      }}
    />
  );
}
