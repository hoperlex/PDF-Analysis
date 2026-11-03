/**
 * The one way a refused or unknown group, rule or mode command is shown (`EXEC2-WEB-GROUPS-01`).
 *
 * A single title for every control: the group form, the archive, the rule editor and the cut-over
 * all end here. The sentence under it is the specific one (`groupFailure`); a command whose outcome
 * is unknown says so and tells the person to repeat only with the same key, which each control does
 * by holding the key until the command settles. The cut-over is served by `EXEC2-CUTOVER-01`; until
 * it is, its refusal is shown as the server gave it, and nothing else is offered in its place.
 */

import type { ExecutionFailure } from '@/entities/execution';
import { ErrorState } from '@/shared/ui';

export function GroupCommandFailure({ failure }: { readonly failure: ExecutionFailure }) {
  return (
    <div data-group-failure={failure.kind}>
      <ErrorState
        title="Команда группам или правилам не выполнена"
        detail={failure.detail}
        correlationId={failure.correlationId}
      />
    </div>
  );
}
