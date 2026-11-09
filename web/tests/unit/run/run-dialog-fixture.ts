/**
 * Renders «Этапы анализа раздела» (`RUN-SCREEN-01a`) for a seeded run, drawn open, as the tests that used to read the executor,
 * the preset and the stage table off the run page read them now: those moved into the dialog a chip of the rail opens.
 */

import { createElement } from 'react';

import type { RunStatus } from '@/shared/api';
import { queryKeys } from '@/shared/api';
import { runChips } from '@/entities/audit-run';
import type { ProcedureReading, RunChipDefinition } from '@/entities/audit-run';
import { RunStagesDialog } from '@/widgets/run-stages-dialog';
import { startedFrom } from '@/widgets/run-progress/model/started-from';

import { newClient, renderScreen } from '../screens/harness';

export interface DialogOptions {
  /** The chip shown on the right; the first chip of the run by default. */
  readonly selected?: RunChipDefinition['id'];
  readonly procedures?: readonly ProcedureReading[];
  readonly showServer?: boolean;
  /** The account the dialog's start control sees; none: not known yet. */
  readonly roles?: readonly string[];
}

export function runDialog(status: RunStatus, options: DialogOptions = {}): string {
  const from = startedFrom(status);
  const chips = runChips({ status, procedures: options.procedures ?? [], reused: from?.reusedStageIds });
  const client = newClient();
  client.setQueryData(queryKeys.runs.detail(status.run_id), status);
  if (options.roles !== undefined) client.setQueryData(queryKeys.account.me(), { roles: options.roles });
  return renderScreen(
    client,
    createElement(RunStagesDialog, {
      status,
      chips,
      selected: options.selected ?? (chips[0]?.definition.id ?? 'preparation'),
      onSelect: () => undefined,
      onClose: () => undefined,
      reusedStageIds: from?.reusedStageIds,
      showServer: options.showServer ?? true,
      staticOpen: true,
    }),
  );
}
