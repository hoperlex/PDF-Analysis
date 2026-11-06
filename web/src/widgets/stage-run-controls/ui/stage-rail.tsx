'use client';

import { useState } from 'react';

import type { StageChainRun } from '@/shared/api';

import { RUN_WORDS, STEP_WORDS } from '../model/runs';
import styles from './stage-run-controls.module.css';

/** What each of the seven steps does, said once; the chip opens it (`pipelineExpanded` of the original). */
export const STEP_DESCRIPTIONS: Readonly<Record<number, string>> = {
  1: 'Пары листов П и Р берутся из сохранённой карты листов. Без сохранённой карты сравнение не начинается.',
  2: 'Текст, который на парных листах совпал дословно, исключается из сравнения и больше не считается отличием.',
  3: 'Строки и ячейки, которые различаются, собираются как исходные текстовые различия. Эти строки ИИ не меняет.',
  4: 'ИИ проверяет различия и предлагает отнести их к совпавшим или изменённым. Его ответ — предложение, решение принимает эксперт.',
  5: 'Различия классифицируются; связи листов, ошибочность которых доказана, исправляются с записью и возможностью откатить.',
  6: 'Одинаковые по смыслу изменения сводятся в одну запись.',
  7: 'Из свода собираются карточки «Было → Стало» с местами на чертежах — для проверки экспертом.',
};

const BADGES: Readonly<Record<StageChainRun['state'], string>> = {
  queued: 'pending', running: 'active', paused: 'degraded', completed: 'ok', failed: 'failed', cancelled: 'inert',
};
const STEP_NUMBERS = [1, 2, 3, 4, 5, 6, 7] as const;

/**
 * The seven steps of a run as one row of chips with arrows between them, each with its state; a chip opens the step's
 * description and counts under the row, a second press closes it (`UI-B-88`: the original's rail on steps 2 and 3). A step the run
 * has not reached is «Ожидает». Colours are the shared badge tones, so the rail declares none of its own.
 */
export function StageRail({ run }: { readonly run: StageChainRun }) {
  const [open, setOpen] = useState<number | null>(null);
  const detail = open === null ? undefined : run.steps.find((step) => step.step_no === open);
  return <div className={styles.rail}>
    <div role="group" aria-label="Семь шагов сравнения" className={styles.railRow}>
      {STEP_NUMBERS.map((number, index) => {
        const step = run.steps.find((item) => item.step_no === number);
        const state = step?.state;
        return <span key={number} className={styles.railItem}>
          {index === 0 ? null : <span aria-hidden="true">→</span>}
          <button type="button" className={open === number ? 'am-button' : 'am-button am-button--quiet'}
            data-stage-step={number} data-step-state={state ?? 'waiting'} aria-expanded={open === number}
            aria-controls="stage-rail-detail" onClick={() => setOpen(open === number ? null : number)}>
            <span>{state === 'completed' ? '✓ ' : ''}{String(number).padStart(2, '0')} {STEP_WORDS[number]}</span>{' '}
            <span className={`am-badge am-badge--${state === undefined ? 'pending' : BADGES[state]}`}>{state === undefined ? 'Ожидает' : RUN_WORDS[state]}</span>
          </button>
        </span>;
      })}
    </div>
    {open === null ? null : <div id="stage-rail-detail" className={styles.railDetail} data-stage-step-detail={open}>
      <strong>{String(open).padStart(2, '0')} {STEP_WORDS[open]} · {detail === undefined ? 'Ожидает' : RUN_WORDS[detail.state]}</strong>
      <p>{STEP_DESCRIPTIONS[open]}</p>
      {detail === undefined ? null : Object.entries(detail.counts).map(([name, count]) => <span key={name}>{name}: {count} </span>)}
    </div>}
  </div>;
}
