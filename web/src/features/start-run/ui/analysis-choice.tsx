'use client';

/**
 * Which analysis one start sends (`AR-V3-OPT-IN`, design 4.3): the standard one or AR v3 (beta).
 *
 * Presentational. It is a radio with exactly two options and it holds nothing: the value is the caller's, so the
 * caller is where the rules live (`widgets/run-list`):
 *
 *   - it is drawn only where the deployment allows a start of v3 (`ArV3BetaPackStatus.start_allowed`) and only on the
 *     start form of an АР version; nowhere else is there a choice, and where there is none this is not drawn at all;
 *   - the **standard** analysis is selected every time the form opens: nothing is remembered per person, project or
 *     browser, so the caller starts its value at `standard` and never stores it;
 *   - one start sends exactly one analysis's operation, and choosing v3 sends `startArV3BetaGroup`, never `startRun`
 *     with a flag: the form below the radio is the other analysis's own form.
 *
 * No option is described as better, newer or a replacement of the other, and none says anything about review by a
 * human (`SHOW_REVIEW_INDICATION`, `R-146ba`).
 */

import { useId } from 'react';

import styles from './analysis-choice.module.css';

export type AnalysisChoiceValue = 'standard' | 'ar_v3_beta';

export const ANALYSIS_CHOICE_LABEL = 'Анализ';

export const ANALYSIS_CHOICE_OPTIONS: Readonly<Record<AnalysisChoiceValue, string>> = {
  standard: 'Стандартный (профиль АР из исходного приложения)',
  ar_v3_beta: 'АР v3: шесть проверок по нормам (бета)',
};

const ORDER: readonly AnalysisChoiceValue[] = ['standard', 'ar_v3_beta'];

export interface AnalysisChoiceProps {
  readonly value: AnalysisChoiceValue;
  readonly disabled?: boolean | undefined;
  readonly onChange: (next: AnalysisChoiceValue) => void;
}

export function AnalysisChoice({ value, disabled = false, onChange }: AnalysisChoiceProps) {
  const labelId = useId();
  const name = useId();
  return (
    <div className={styles.choice} role="radiogroup" aria-labelledby={labelId} data-analysis-choice={value}>
      <p id={labelId} className={styles.label}>{ANALYSIS_CHOICE_LABEL}</p>
      {ORDER.map((option) => (
        <label key={option} className={styles.option}>
          <input
            type="radio"
            name={name}
            value={option}
            checked={value === option}
            disabled={disabled}
            data-analysis-choice-option={option}
            onChange={() => onChange(option)}
          />
          {ANALYSIS_CHOICE_OPTIONS[option]}
        </label>
      ))}
    </div>
  );
}
