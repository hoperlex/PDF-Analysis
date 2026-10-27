'use client';

/**
 * «Запустить проход» on the project's «Оптимизация» tab (`W60-OPT-PROPOSALS-01`): an expert
 * asks for the deterministic proposals of the chosen document set's current version, in
 * whichever section an expert confirmed it (`OPT-PROJECT-ALL-SECTIONS-01`).
 *
 * The server checks every precondition (the classification, the price list, a published run and
 * its saved text, the vendor list of the version's section) and names the first one that is unmet; this control only says
 * that in Russian. It offers nothing to anyone but an expert.
 */

import type { DocumentUid, ProjectUid } from '@/shared/api';
import type { FailureMessage } from '@/shared/api/failure-message';
import { ErrorState, LoadingState } from '@/shared/ui';
import { startPassFailureMessage } from '@/entities/optimisation-proposal';

import { useStartOptimisationPass } from '../model/use-start-optimisation-pass';

export interface StartOptimisationPassViewProps {
  /** Whether the session holds `expert`; the API checks again. */
  readonly canStart: boolean;
  /** The set to start for; `null` while none is chosen. */
  readonly chosen: boolean;
  readonly pending: boolean;
  readonly failure: FailureMessage | null;
  readonly onStart: () => void;
}

/** The control from state already in hand. Rendered by the static harness in every branch. */
export function StartOptimisationPassView({
  canStart,
  chosen,
  pending,
  failure,
  onStart,
}: StartOptimisationPassViewProps) {
  if (!canStart) {
    return (
      <p className="am-note" data-start-pass="readonly">
        Запустить проход может эксперт. Администратор читает проходы и решения экспертов.
      </p>
    );
  }
  return (
    <div data-start-pass="">
      <button type="button" className="am-button" disabled={!chosen || pending} onClick={onStart}>
        Запустить проход
      </button>
      <p className="am-form__hint">
        Проход читает текущую версию выбранного комплекта, последний опубликованный прогон,
        действующий прайс-лист и вендор-лист раздела этого комплекта и сохраняет предложения
        «более дешёвый аналог». Тот же набор исходных данных второй раз не создаёт нового прохода.
      </p>
      {pending ? <LoadingState what="предложений" /> : null}
      {failure !== null ? (
        <ErrorState
          title="Проход не запущен."
          detail={failure.detail}
          correlationId={failure.correlationId}
          onRetry={failure.retryable ? onStart : undefined}
        />
      ) : null}
    </div>
  );
}

export interface StartOptimisationPassProps {
  readonly projectUid: ProjectUid;
  readonly documentUid: DocumentUid | null;
  readonly canStart: boolean;
  /** Told the stored pass, so the caller can open it. */
  readonly onStarted?: (passId: string) => void;
}

export function StartOptimisationPass({
  projectUid,
  documentUid,
  canStart,
  onStarted,
}: StartOptimisationPassProps) {
  const mutation = useStartOptimisationPass();
  const start = () => {
    if (documentUid === null) return;
    mutation.mutate(
      { projectUid, documentUid },
      { onSuccess: (pass) => onStarted?.(pass.optimisation_pass_id) },
    );
  };
  return (
    <StartOptimisationPassView
      canStart={canStart}
      chosen={documentUid !== null}
      pending={mutation.isPending}
      failure={
        mutation.error === null || mutation.error === undefined
          ? null
          : startPassFailureMessage(mutation.error)
      }
      onStart={start}
    />
  );
}
