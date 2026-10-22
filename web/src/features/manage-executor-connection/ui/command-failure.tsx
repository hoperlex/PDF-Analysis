/**
 * The one way a refused or unknown connection command is shown (`EXEC-HTTP-01`).
 *
 * A single title for every control: «Проверить», «Архивировать», «Создать ключ», the settings
 * forms and the route editor all end here. The sentence under it is the specific one
 * (`connectionFailure`); a command whose outcome is unknown says so and tells the person to
 * repeat only with the same key, which the control does by holding the key until the command
 * settles.
 */

import type { ExecutionFailure } from '@/entities/execution';
import { ErrorState } from '@/shared/ui';

export function CommandFailure({ failure }: { readonly failure: ExecutionFailure }) {
  return (
    <div data-executor-failure={failure.kind}>
      <ErrorState
        title="Команда подключению не выполнена"
        detail={failure.detail}
        correlationId={failure.correlationId}
      />
    </div>
  );
}
