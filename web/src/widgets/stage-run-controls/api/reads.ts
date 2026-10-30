import { listStageChainRuns, listStageLinkRepairs } from '@/shared/api';
import type { StageChainRun, StageLinkRepair } from '@/shared/api';

export async function readRuns(pairId: string): Promise<StageChainRun[]> {
  const items: StageChainRun[] = [];
  let cursor: string | undefined;
  const seen = new Set<string>();
  do {
    const page = (await listStageChainRuns({ path: { stage_pair_id: pairId },
      query: { limit: 100, ...(cursor === undefined ? {} : { cursor }) } })).data;
    items.push(...page.items);
    cursor = page.page.next_cursor ?? undefined;
    if (cursor !== undefined && seen.has(cursor)) throw new Error('Список запусков обновился. Обновите страницу.');
    if (cursor !== undefined) seen.add(cursor);
  } while (cursor !== undefined);
  return items;
}

export async function readRepairs(runId: string): Promise<StageLinkRepair[]> {
  const items: StageLinkRepair[] = [];
  let cursor: string | undefined;
  const seen = new Set<string>();
  do {
    const page = (await listStageLinkRepairs({ path: { stage_chain_run_id: runId },
      query: { limit: 100, ...(cursor === undefined ? {} : { cursor }) } })).data;
    items.push(...page.items);
    cursor = page.page.next_cursor ?? undefined;
    if (cursor !== undefined && seen.has(cursor)) throw new Error('История связей обновилась. Откройте её заново.');
    if (cursor !== undefined) seen.add(cursor);
  } while (cursor !== undefined);
  return items;
}
