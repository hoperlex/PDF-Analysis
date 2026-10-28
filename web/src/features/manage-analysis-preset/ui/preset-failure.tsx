/**
 * The one way a refused or unknown preset command is shown (`ANALYSIS-PRESETS-01`): a single
 * title for every control, and under it the specific sentence (`presetFailure`). A command whose
 * outcome is unknown says so and tells the person to repeat only with the same key, which the
 * control does by holding the key until the command settles.
 */

import type { ExecutionFailure } from '@/entities/execution';
import { ErrorState } from '@/shared/ui';

export function PresetCommandFailure({ failure }: { readonly failure: ExecutionFailure }) {
  return (
    <div data-preset-failure={failure.kind}>
      <ErrorState
        title="Команда пресету не выполнена"
        detail={failure.detail}
        correlationId={failure.correlationId}
      />
    </div>
  );
}
