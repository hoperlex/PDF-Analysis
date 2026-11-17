'use client';

/** @jsxRuntime automatic */

/**
 * The severity badge.
 *
 * Same discipline as `VerdictBadge`: the value set is exactly the generated `Severity`, the
 * Russian label comes from `SEVERITY_LABELS`, the contract value stays on `data-severity`
 * and is never rendered as prose, and a value outside the closed union is shown as a fault
 * instead of as a blank.
 *
 * The badge says WHICH severity and nothing about whose it is. The tone comes from
 * `severityTone` (one place, five tones); nothing here picks a colour that implies the
 * model's proposal was approved.
 *
 * **The proposal is a variant, not a look-alike (`UIP-S06-03`, `R-151j`).** `proposed` draws the
 * same pill in the same tone with a dashed edge, the word «предложено» after the label and the
 * tooltip «Предложение модели, не решение эксперта», and it carries `data-proposed-severity`
 * instead of `data-severity`. `data-severity` is the expert's decision: a reader of the markup,
 * a test and a stylesheet all take it as that, so a proposal never wears it (AGENTS §4: the
 * model's output is not the canonical decision). The tooltip is fixed for the variant and is not
 * a prop, so no screen can word a proposal as a decision.
 */

import type { Severity } from '@/shared/api';
import { SEVERITY_VALUES } from '@/shared/api';

import { SEVERITY_LABELS } from '../model/severity-labels';
import { severityTone } from '../model/severity-tone';
import styles from './severity-badge.module.css';

/** The tooltip of a proposed severity; the same words wherever a proposal is drawn. Not exported: this file is a client module. */
const PROPOSED_SEVERITY_TITLE = 'Предложение модели, не решение эксперта';

/** What the pill says after its label when it is the model's proposal. */
const PROPOSED_WORD = 'предложено';

export type SeverityBadgeProps =
  | {
      readonly severity: Severity;
      /** What the badge is about, in Russian. Rendered as a tooltip; never the contract value. */
      readonly title?: string | undefined;
      readonly proposed?: false | undefined;
    }
  | {
      readonly severity: Severity;
      /** The model's proposal, not the expert's decision: dashed, worded and titled as such, and `data-proposed-severity`. */
      readonly proposed: true;
      readonly title?: undefined;
    };

export function SeverityBadge(props: SeverityBadgeProps) {
  const { severity } = props;
  if (!(SEVERITY_VALUES as readonly unknown[]).includes(severity)) {
    return (
      <span
        className="am-badge am-badge--failed"
        role="alert"
        data-closed-vocabulary-fault="severity"
      >
        <span className="am-badge__label">Неизвестная критичность</span>
      </span>
    );
  }

  const tone = severityTone(severity);
  if (props.proposed === true) {
    return (
      <span
        className={`am-badge am-badge--${tone} ${styles.proposed}`}
        data-proposed-severity={severity}
        title={PROPOSED_SEVERITY_TITLE}
      >
        <span className="am-badge__label">{SEVERITY_LABELS[severity]}</span>
        <span className="am-badge__qualifier">{PROPOSED_WORD}</span>
      </span>
    );
  }

  return (
    <span
      className={`am-badge am-badge--${tone}`}
      data-severity={severity}
      {...(props.title === undefined ? {} : { title: props.title })}
    >
      <span className="am-badge__label">{SEVERITY_LABELS[severity]}</span>
    </span>
  );
}
