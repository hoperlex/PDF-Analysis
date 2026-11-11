/** @jsxRuntime automatic */

/**
 * The one line above the list while the run has no precedents yet (`PREC-WEB`, plan-v5 section 7): «Прецеденты считаются ночью (01:00–06:00,
 * Asia/Yekaterinburg) и появятся утром; после переезда в Яндекс — сразу после прогона».
 *
 * One line for the whole run and never a mark on each row: a «Недоступно» on every row is a concept repeated a hundred times. The hours and the
 * zone are the setting `vector_window`'s (`window`, from `getVectorControl`); while they are not known the line says only that it is night.
 * The three texts of the night mode go when the temporary decision ends (`ADR-0029`, temporary decision 2).
 */

import type { VectorWindow } from '@/shared/api';
import { precedentsUnavailableLine } from '@/entities/decision-memory';

export function PrecedentsLine({ window }: { readonly window: VectorWindow | null }) {
  return (
    <p className="am-note" data-precedents-line="" role="status">
      {precedentsUnavailableLine(window)}
    </p>
  );
}
