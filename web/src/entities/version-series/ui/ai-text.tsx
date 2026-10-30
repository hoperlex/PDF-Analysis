/**
 * An AI text with its label. **Every text a model wrote is drawn through here**, so none can appear without «не подтверждено
 * инженером» (plan §1.1; `R-146ba` kept this label for every comparison AI text), and a recorded (test) answer is said to be one
 * instead of passing for a model's description.
 */

import type { ReactNode } from 'react';

import { RECORDED_LABEL, RECORDED_NOTE, UNCONFIRMED_LABEL } from '../model/ai-words';

import styles from './ai-ui.module.css';

/** «тестовый ответ»: the mark of an answer that came from a recording, on a job or a report whose route records. */
export function RecordedMark() {
  return (
    <span className={styles.recordedLabel} data-recorded-label="" title={RECORDED_NOTE}>
      {RECORDED_LABEL}
    </span>
  );
}

export function AiLabel({ recorded }: { readonly recorded?: boolean | undefined }) {
  return (
    <>
      <span className={styles.aiLabel} data-ai-label="" title="Текст составлен ИИ. Инженер его не проверял и не подтверждал.">
        {UNCONFIRMED_LABEL}
      </span>
      {recorded === true ? <RecordedMark /> : null}
    </>
  );
}

export interface AiTextProps {
  readonly children: ReactNode;
  /** The answer is a recorded one, made for a test of the program. */
  readonly recorded?: boolean | undefined;
  readonly as?: 'p' | 'span' | 'div' | undefined;
}

export function AiText({ children, recorded, as = 'span' }: AiTextProps) {
  const Tag = as;
  return (
    <Tag className={styles.aiText} data-ai-text="">
      {children}
      <AiLabel recorded={recorded} />
    </Tag>
  );
}
