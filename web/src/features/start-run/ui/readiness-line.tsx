'use client';

/**
 * The line under «Запустить» (`READINESS-WEB-01`, plan 2026-11-09 §8; `UIP-S05-02`): what the start will use, in one line, and the way to
 * the window «Модели по этапам».
 *
 *   «Набор: Только Claude · по подписке · ⚠ не для клиентских документов · Модели по этапам ▸»
 *   «Набор: Только Claude · часть по API — покажем оценку · …»
 *   «Маршрут: прежний · Модели по этапам ▸»
 *   «Маршрут: автоматически · Модели по этапам ▸»
 *   «Готовность запуска не прочитана; запуск проверит её сам. Повторить · Модели по этапам ▸»
 *   «Проверяем готовность…»                           the one state with no way to the window: there is nothing to look at yet
 *
 * `readinessNoteOf` turns one reading of `getRunStartReadiness` (`../model/use-run-start-readiness.ts`) into the control's
 * `readinessNote`. «Модели по этапам ▸» is a button that calls `onOpenStages`, in every state but the one that is still reading: the
 * window it opens is a widget's (`widgets/run-stages-dialog`), which a feature does not import, so the widget that mounts the control
 * brings it and chooses what it draws from for each state. The button only opens a window to read; «Запустить» stays one button.
 *
 * The `D-291` mark is drawn on the layout's route only, where servers take the work, for as long as the debt is open. A line says
 * what is true of this start; the mark is not decoration and goes the day the debt closes.
 */

import type { ReactNode } from 'react';

import {
  CLIENT_DOCUMENTS_MARK,
  LEGACY_ROUTE_NOTE,
  MODELS_BY_STAGE_LABEL,
  READINESS_NOT_READ,
  READINESS_READING,
  readinessLine,
} from '../model/readiness';
import type { RunStartReadinessReading } from '../model/use-run-start-readiness';
import { DEFAULT_READINESS_NOTE } from './start-run-control';

export interface ReadinessLinePlanProps {
  readonly kit: string | null;
  readonly access: string | null;
  readonly onOpenStages: () => void;
}

/** «Модели по этапам ▸»: the way to the window, the same button in every state that has one. */
function StagesLink({ onOpenStages }: { readonly onOpenStages: () => void }) {
  return (
    <button
      type="button"
      className="am-button am-button--quiet am-button--small"
      aria-haspopup="dialog"
      data-readiness-stages=""
      onClick={onOpenStages}
    >
      {MODELS_BY_STAGE_LABEL}
    </button>
  );
}

/** The layout's route: the set, how it is paid, the `D-291` mark and the way to the stages. */
export function ReadinessLinePlan({ kit, access, onOpenStages }: ReadinessLinePlanProps) {
  const parts: ReactNode[] = [];
  if (kit !== null) parts.push(<span key="kit" data-readiness-kit="">{`Набор: ${kit}`}</span>);
  if (access !== null) parts.push(<span key="access" data-readiness-access="">{access}</span>);
  parts.push(<span key="mark" data-readiness-d291="">{CLIENT_DOCUMENTS_MARK}</span>);
  return (
    <>
      {parts.map((part, at) => (at === 0 ? part : <span key={`more-${at}`}>{' · '}{part}</span>))}
      {' · '}
      <StagesLink onOpenStages={onOpenStages} />
    </>
  );
}

export function readinessNoteOf(reading: RunStartReadinessReading, onOpenStages: () => void): ReactNode | undefined {
  switch (reading.state) {
    case 'loading':
      return <span data-readiness-state="loading">{READINESS_READING}</span>;
    case 'unavailable':
      // The server has no layout to speak of: the route is its own. The control's own words stand, and the window says what it can read.
      return (
        <span data-readiness-state="automatic">
          {DEFAULT_READINESS_NOTE}{' · '}<StagesLink onOpenStages={onOpenStages} />
        </span>
      );
    case 'failed':
      return (
        <span data-readiness-state="failed">
          {READINESS_NOT_READ}{' '}
          <button type="button" className="am-button am-button--quiet am-button--small" data-readiness-retry="" onClick={reading.retry}>
            Повторить
          </button>
          {' · '}
          <StagesLink onOpenStages={onOpenStages} />
        </span>
      );
    case 'ready': {
      const line = readinessLine(reading.readiness);
      // The route's contract value is the marker (`RunStartRoute`); the screen says it in Russian.
      if (line.kind === 'legacy') {
        return (
          <span data-readiness-state="legacy" data-readiness-route={reading.readiness.route}>
            {LEGACY_ROUTE_NOTE}{' · '}<StagesLink onOpenStages={onOpenStages} />
          </span>
        );
      }
      return (
        <span data-readiness-state="plan" data-readiness-route={reading.readiness.route}>
          <ReadinessLinePlan kit={line.kit} access={line.access} onOpenStages={onOpenStages} />
        </span>
      );
    }
  }
}
