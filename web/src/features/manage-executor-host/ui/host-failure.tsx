import type { ExecutionFailure } from '@/entities/execution';
import { ErrorState } from '@/shared/ui';

/**
 * The one way a refused or unknown command on a server, or on the layout that names servers' models, is shown. A refusal says
 * the catalogue sentence, never an identifier; `title` names the command that was refused.
 */
export function HostFailure({
  failure,
  title = 'Команда серверу не выполнена',
}: {
  readonly failure: ExecutionFailure;
  readonly title?: string | undefined;
}) {
  return (
    <div data-host-failure={failure.kind}>
      <ErrorState title={title} detail={failure.detail} correlationId={failure.correlationId} />
    </div>
  );
}
