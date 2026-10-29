/**
 * The banner over the sheet when the reader came from the AI description (`frontend/static/js/version-comparison-viewer.js:36-52`):
 * «Из ИИ-описания: <пункт>», «доказательство N из M», «‹ пред.» / «след. ›» and «Обзор всех» / «Один фрагмент».
 *
 * The place on the drawing belongs to an item the model wrote, so the banner carries the same label as the item does.
 */

import { AiText, evidenceCounter } from '@/entities/version-series';
import type { Evidence } from '@/entities/version-series';

import styles from './comparison-viewer.module.css';

export interface EvidenceState {
  readonly items: readonly Evidence[];
  readonly index: number;
  /** «Обзор всех»: every place is shown at once instead of one at a time. */
  readonly all: boolean;
}

export type EvidenceAction = { readonly type: 'step'; readonly direction: -1 | 1 } | { readonly type: 'toggle-all' } | { readonly type: 'close' };

export function EvidenceBanner({ evidence, onAction }: { readonly evidence: EvidenceState; readonly onAction: (action: EvidenceAction) => void }) {
  const current = evidence.items[evidence.index];
  return (
    <div className={styles.banner} role="status" data-evidence-banner={evidence.all ? 'all' : 'one'}>
      <div>
        Из ИИ-описания: <AiText as="span">{current?.label ?? '—'}</AiText>
      </div>
      <div className={styles.bannerNav}>
        {evidence.all ? (
          <span>обзор всех областей: {evidence.items.length}</span>
        ) : (
          <>
            <button type="button" className="am-button am-button--small am-button--quiet" disabled={evidence.items.length < 2} title="Показать предыдущее место из этого пункта ИИ-описания. Недоступно, если место одно." onClick={() => onAction({ type: 'step', direction: -1 })}>
              ‹ пред.
            </button>
            <span data-evidence-counter="">{evidenceCounter(evidence.index, evidence.items.length)}</span>
            <button type="button" className="am-button am-button--small am-button--quiet" disabled={evidence.items.length < 2} title="Показать следующее место из этого пункта ИИ-описания. Недоступно, если место одно." onClick={() => onAction({ type: 'step', direction: 1 })}>
              след. ›
            </button>
          </>
        )}
        <button type="button" className="am-button am-button--small am-button--quiet" title={evidence.all ? 'Вернуться к просмотру мест по одному, крупно.' : 'Показать сразу все места этого описания на листах.'} onClick={() => onAction({ type: 'toggle-all' })}>
          {evidence.all ? 'Один фрагмент' : 'Обзор всех'}
        </button>
        <button type="button" className="am-button am-button--small am-button--quiet" onClick={() => onAction({ type: 'close' })}>
          Убрать
        </button>
      </div>
    </div>
  );
}
