'use client';

/**
 * The start-run command.
 *
 * **`provider_mode` is not sent.** The contract makes it optional and defaults it to the
 * server's configured mode, and it notes that a client asking for `live` is asking to
 * spend money against the `OD-03` ceiling. A screen that offered the choice would also
 * be the screen that offers to retry a failed live run as a recorded one, which is
 * exactly the substitution that makes a replayed run look like evidence of a real
 * provider call. The mode this run actually used is read back from the reading and shown.
 *
 * **`executor_connection_id` is sent only when the person chose a connection** (`EXEC-PAR-WEB-01`,
 * `./start-run-intent.ts`). «По умолчанию (маршрут)» is the absence of the field, which is the
 * start this command always made; a chosen connection is never replaced by the stand, so a
 * refusal of it is shown as itself and not retried on another.
 *
 * The 202 body is a full `RunStatus`, so it seeds `queryKeys.runs.detail(run_id)`: the
 * run screen opens on the run's real first state instead of on a loading state for a
 * reading it was already handed.
 *
 * `W46-WIRE`: the dashboard's one read is invalidated too — a new run moves
 * `run_activity.by_state` the moment the command is accepted, before anything about its
 * cost is known. The other half of that panel, `run_activity.spend`, only settles once
 * the run reaches a terminal state; that invalidation is `useRunStatus`'s, at its own
 * terminal reading, not here.
 *
 * `C-26`: the execution queue and journal are invalidated as well — an accepted run is a new
 * queued job and a new journal entry, and both screens would otherwise keep the page they
 * read before the command.
 */

import { useMutation, useQueryClient } from '@tanstack/react-query';

import type { RunStatus } from '@/shared/api';
import { queryKeys, startRun } from '@/shared/api';

import type { StartRunCommand } from './start-run-intent';
import { startRunBody } from './start-run-intent';

export type { StartRunCommand };

export function useStartRun() {
  const queryClient = useQueryClient();

  return useMutation<RunStatus, unknown, StartRunCommand>({
    mutationFn: async (command) => {
      const response = await startRun({ body: startRunBody(command), idempotencyKey: command.idempotencyKey });
      return response.data;
    },
    onSuccess: (run) => {
      queryClient.setQueryData(queryKeys.runs.detail(run.run_id), run);
      void queryClient.invalidateQueries({ queryKey: queryKeys.dashboard.summary() });
      void queryClient.invalidateQueries({ queryKey: queryKeys.execution.all() });
    },
  });
}
