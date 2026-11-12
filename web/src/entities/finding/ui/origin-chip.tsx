/** @jsxRuntime automatic */

/**
 * The small «Источник» chip of a finding row: «Чертёж» or «Сверка».
 *
 * A text finding draws nothing: «Текст» is what every finding of a `text_only` run is, so naming it on each row would add
 * a concept to a screen that has not changed, and in a `one_list` run the absence of a chip already says it (owner rule:
 * fewer concepts per screen). The words are {@link FINDING_ORIGIN_LABELS}'s, the contract value stays on `data-finding-origin`.
 * It is the global neutral badge: no colour of its own, so it adds no pair for the contrast census to measure.
 */

import type { FindingOrigin } from '@/shared/api';

import { FINDING_ORIGIN_LABELS } from '../model/origin';

export interface OriginChipProps {
  readonly origin: FindingOrigin;
}

export function OriginChip({ origin }: OriginChipProps) {
  if (origin === 'text') return null;
  return (
    <span className="am-badge am-badge--inert" data-finding-origin={origin} title="Источник замечания">
      <span className="am-badge__label">{FINDING_ORIGIN_LABELS[origin]}</span>
    </span>
  );
}
