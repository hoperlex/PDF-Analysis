'use client';

/**
 * «Изменить» in the window «Модели по этапам» (`UIP-S05-03`, `Г10-B`, `Г13-C`; **administrator only**): the existing form of the layout
 * (`LayoutEditor` of `features/manage-stage-layout`) drawn in the same window, in place of the table. It is the form of the tab «Модели по
 * этапам» of «Диспетчер», taken as it is: the sets «Только Claude · Только Codex · Свой набор», a model and an effort for each row,
 * «Сохранить набор» and «Отменить». A save is a new revision of the layout, by the same command, and it refreshes everything filed under
 * `execution`, so the table and the line under «Запустить» (`getRunStartReadiness` lives under the same key) are read again.
 *
 * What the form may offer is what a server can serve now, so the servers and the catalogue of models are read when the form opens, not
 * before. While they are read the window says so in words; if either cannot be read, the form is not drawn and the reason is named,
 * with a way to try again. Nothing is edited in the cells of the table itself.
 */

import { executionFailure } from '@/entities/execution';
import { availableModelIds, useExecutorHosts } from '@/entities/executor-host';
import { useModelCatalogue, useStageModelLayout } from '@/entities/stage-layout';
import { LayoutEditor } from '@/features/manage-stage-layout';
import { ErrorState, LoadingState } from '@/shared/ui';

export interface StageModelsEditProps {
  /** The form is closed (saved, or cancelled): the window goes back to the table. */
  readonly onClose: () => void;
}

export function StageModelsEdit({ onClose }: StageModelsEditProps) {
  const layout = useStageModelLayout(true);
  const hosts = useExecutorHosts(true);
  const catalogue = useModelCatalogue(true);

  const failed = [layout, hosts, catalogue].find((read) => read.data === undefined && read.isError);
  if (failed !== undefined) {
    const failure = executionFailure(failed.error, false);
    const retry = () => {
      for (const read of [layout, hosts, catalogue]) if (read.data === undefined) void read.refetch();
    };
    return (
      <div data-stage-models-edit-failure={failure.kind}>
        <ErrorState title="Набор моделей нельзя изменить" detail={failure.detail} correlationId={failure.correlationId} onRetry={retry} />
      </div>
    );
  }
  if (layout.data === undefined || hosts.data === undefined || catalogue.data === undefined) {
    return <LoadingState what="серверы и каталог моделей" />;
  }
  return (
    <div data-stage-models-edit="">
      <LayoutEditor layout={layout.data} catalogue={catalogue.data} availableModelIds={availableModelIds(hosts.data)} onClose={onClose} />
    </div>
  );
}
