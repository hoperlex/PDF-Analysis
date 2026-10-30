import { listStageAiReviews } from '@/shared/api';
import type { StageAiReview } from '@/shared/api';

export async function readAiReviews(runId: string): Promise<StageAiReview[]> {
  const items: StageAiReview[] = [];
  const seen = new Set<string>();
  let cursor: string | undefined;
  do {
    const page = (await listStageAiReviews({ path: { stage_chain_run_id: runId }, query: { limit: 100, ...(cursor === undefined ? {} : { cursor }) } })).data;
    if (page.items.some((item) => item.run_id !== runId)) throw new Error('ИИ-ревизия относится к другому запуску.');
    items.push(...page.items);
    cursor = page.page.next_cursor ?? undefined;
    if (cursor !== undefined && seen.has(cursor)) throw new Error('Список ИИ-ревизий обновился. Повторите запрос.');
    if (cursor !== undefined) seen.add(cursor);
  } while (cursor !== undefined);
  return items;
}
