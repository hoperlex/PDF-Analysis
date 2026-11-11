/** @jsxRuntime automatic */

/**
 * The small neutral label of a finding row: «Обычно отклоняют · 8 из 10» (`PREC-WEB`, plan-v5 2.3).
 *
 * Nothing is drawn for `none` and `few`, and never a «Недоступно»: a finding with no precedents has no mark, and the one line above the list
 * says why (`PrecedentsLine`). It is the global neutral badge: no colour of its own, so a rejection is not painted red and the mark adds no
 * pair for the contrast census. The contract value stays on `data-precedent-label`.
 */

import type { PrecedentFindingLabel } from '@/shared/api';

import { precedentCaption, precedentTitle } from '../model/precedents';

export function PrecedentMark({ label }: { readonly label: PrecedentFindingLabel | undefined }) {
  if (label === undefined) return null;
  const caption = precedentCaption(label);
  if (caption === null) return null;
  return (
    <span className="am-badge am-badge--inert" data-precedent-label={label.label} data-critic-reviewed={String(label.critic_reviewed)} title={precedentTitle(label)}>
      <span className="am-badge__label">{caption}</span>
    </span>
  );
}
