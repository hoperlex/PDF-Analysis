'use client';

/**
 * «Скопировать диагностику» on a worker's row (`UI-B-68`): puts the row's facts on the clipboard as text
 * (`workerDiagnosticText`). Client-side: nothing is requested. A browser that refuses the clipboard is
 * told so in words and the row stays to be selected by hand. The confirmation belongs to the text that
 * was copied: when the worker's state changes under it, the message goes, so «Скопировано» never
 * describes a diagnostic that is no longer on the screen.
 *
 * {@link CopyDiagnosticsView} is the markup for an outcome, exported so a static render can draw the
 * message a press would leave.
 */

import { useState } from 'react';

import { browserClipboard, copyToClipboard } from '../model/copy-to-clipboard';

export interface CopyDiagnosticsViewProps {
  /** `null` before the first press; `true` when the text was copied; `false` when the browser refused. */
  readonly outcome: boolean | null;
  readonly onCopy: () => void;
}

export function CopyDiagnosticsView({ outcome, onCopy }: CopyDiagnosticsViewProps) {
  return (
    <p data-worker-diagnostics="">
      <button type="button" className="am-button am-button--quiet am-button--small" onClick={onCopy} data-worker-copy="">
        Скопировать диагностику
      </button>
      {outcome === null ? null : outcome ? (
        <>
          {' '}
          <span className="am-form__hint" role="status" data-worker-copy-result="copied">
            Скопировано
          </span>
        </>
      ) : (
        <>
          {' '}
          <span className="am-form__problem" role="alert" data-worker-copy-result="refused">
            Не удалось скопировать: браузер не дал доступ к буферу обмена. Выделите сведения об исполнителе и скопируйте вручную.
          </span>
        </>
      )}
    </p>
  );
}

export function CopyDiagnostics({ text }: { readonly text: string }) {
  const [outcome, setOutcome] = useState<{ readonly text: string; readonly copied: boolean } | null>(null);
  const shown = outcome !== null && outcome.text === text ? outcome.copied : null;

  async function copy() {
    // A refusal (no permission, no clipboard) is said beside the button, never swallowed.
    setOutcome({ text, copied: await copyToClipboard(text, browserClipboard()) });
  }

  return <CopyDiagnosticsView outcome={shown} onCopy={() => void copy()} />;
}
